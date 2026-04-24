# Gauntlet Horde CI Integration

Reference for Horde device reservation backend, report ingestion, BuildGraph integration, and test dashboard mapping.

---

## Overview

Horde is Epic's internal CI/CD and device management platform. Gauntlet integrates with Horde at three layers:

1. **Device reservation** — Horde manages a fleet of physical devices; Gauntlet leases them via REST API
2. **Report ingestion** — Gauntlet submits test results in Horde-compatible JSON format
3. **BuildGraph orchestration** — Horde agents invoke `RunUAT RunUnreal` as BuildGraph tasks

---

## Framework/Horde/

`Framework/Horde/Gauntlet.Horde.cs`

Top-level integration class. Responsibilities:
- Artifact upload to Horde artifact storage
- Result submission via `HordeReport` v1/v2
- Agent environment variable injection into `AutoParam` binding

---

## Device Reservation Backend

### IDeviceReservationService Implementation

`Framework/Devices/Gauntlet.DeviceReservationService.cs` provides a REST client for the Horde device service.

**Endpoints used:**

| Operation | HTTP | Path |
|-----------|------|------|
| Request lease | POST | `/api/v1/reservations` |
| Release lease | DELETE | `/api/v1/reservations/{id}` |
| Extend lease | PUT | `/api/v1/reservations/{id}` |
| List devices | GET | `/api/v1/devices` |

**Request payload:**
```json
{
  "requirements": [
    { "platform": "Android", "perfSpec": "Recommended", "tags": ["Mobile"] }
  ],
  "duration": 3600,
  "poolId": "your-pool-id"
}
```

**Response:**
```json
{
  "id": "lease-abc123",
  "devices": [
    {
      "name": "Pixel7Pro-01",
      "address": "R5CT300ABCD",
      "platform": "Android",
      "perfSpec": "Recommended",
      "model": "Pixel 7 Pro"
    }
  ]
}
```

### Authentication

The Horde service URL and token are configured via environment variables injected by the Horde agent:

| Variable | Value |
|----------|-------|
| `UE_HORDE_URL` | `https://horde.mycompany.com` |
| `UE_HORDE_TOKEN` | Bearer token for API auth |
| `UE_HORDE_POOL` | Device pool identifier |

These are read by `GauntletHttpClient` and don't need to be manually set when running under Horde.

### Heartbeat Thread

Once a lease is acquired, a background thread calls `IDeviceReservation.Extend()` every 60 seconds. If the Gauntlet process dies without releasing the lease, Horde will reclaim the device after the lease TTL expires (typically 15 minutes).

---

## Report Ingestion

### Writing TestData.json (Horde v1)

Enabled by `-writetestresults` flag or `WriteTestResultsForHorde = true` on the config.

Output file: `<ArtifactPath>/<TestName>.TestData.json`

Horde picks up files matching `*.TestData.json` from the artifact directory and ingests them into the test database.

**Schema overview:**
```json
{
  "name": "MyGame.SoakTest",
  "state": "Success",
  "errors": 0,
  "warnings": 2,
  "artifacts": [
    { "name": "ClientLog", "type": "log", "path": "Logs/client.log" }
  ],
  "events": [
    { "type": "warning", "message": "Frame rate dipped to 45 fps", "time": "2024-01-15T10:30:00Z" }
  ],
  "metadata": {
    "Project": "MyGame",
    "Platform": "Win64",
    "Changelist": "12345678"
  }
}
```

### HordeReport v1 vs v2

| Feature | v1 (SimpleTestReport) | v2 (AutomatedTestSessionData) |
|---------|----------------------|-------------------------------|
| Structure | Flat events + metadata | Hierarchical phases/steps |
| Use case | Simple pass/fail tests | Multi-phase test suites |
| Dashboard | Single result row | Expandable phase tree |
| Default | Yes (`SimpleHordeReport = true`) | Opt-in by overriding `CreateReport()` |

### Submitting via API (not disk file)

```csharp
// If submitting programmatically rather than via file:
var client = new GauntletHttpClient(hordeUrl, token);
await client.PostTestResultAsync(reportJson);
```

---

## BuildGraph Integration

Horde executes Gauntlet tests as BuildGraph tasks on agent machines.

**Typical BuildGraph node:**
```xml
<Node Name="RunSmokeTests" Requires="CompileGame;CookGame">
  <RunUnreal
    Project="MyGame"
    Platform="Win64"
    Configuration="Development"
    Build="$(CookedOutputDir)"
    Tests="UE.BootTest;MyGame.SoakTest"
    MaxDuration="1800"
    WriteTestResultsForHorde="true"
  />
</Node>
```

**What happens on the agent:**
1. Horde agent receives the BuildGraph task
2. Injects `UE_HORDE_*` environment variables
3. Agent runs: `RunUAT RunUnreal -Project=MyGame ... -writetestresults`
4. Gauntlet acquires devices via Horde device service
5. After tests complete, Gauntlet writes `*.TestData.json` to artifact dir
6. Horde agent uploads artifact dir to Horde storage
7. Horde ingests `*.TestData.json` and displays results in test dashboard

---

## Environment Variables Horde Injects

When running under a Horde agent, these variables are available and read by `AutoParam`:

| Variable | CLI Equivalent | Notes |
|----------|---------------|-------|
| `UE_HORDE_URL` | N/A | Device service endpoint |
| `UE_HORDE_TOKEN` | N/A | Auth bearer token |
| `UE_HORDE_POOL` | N/A | Device pool ID |
| `UE_CHANGELIST` | `-changelist=` | Current P4 CL number |
| `UE_BRANCH` | `-branch=` | P4 branch stream |
| `UE_AGENT_ID` | N/A | Agent identifier for logging |
| `UE_JOB_ID` | N/A | Horde job identifier |
| `UE_BATCH_ID` | N/A | Horde batch identifier |

---

## Test Dashboard Mapping

How Gauntlet data appears in the Horde test dashboard:

| Gauntlet Output | Horde Dashboard |
|----------------|----------------|
| `TestResult.Passed` | ✅ Green pass |
| `TestResult.Failed` | ❌ Red fail |
| `TestResult.Skipped` | ⚪ Gray skip |
| `SetMetadata("Project", ...)` | "Project" column |
| `SetMetadata("Platform", ...)` | "Platform" column |
| `AddEvent(Error, ...)` | Red event in detail view |
| `AttachArtifact(...)` | Download link in detail view |
| `SetMetadata("ReportURL", ...)` | "View Report" button |

### Test Grouping

Tests are grouped in the dashboard by the name segments separated by `.`:
- `MyGame.SoakTest` → group `MyGame`, test `SoakTest`
- `UE.BootTest` → group `UE`, test `BootTest`

The `[TestGroup("name")]` attribute affects batch invocation, not dashboard grouping.

---

## Horde Artifact Storage

When the agent uploads the artifact directory:
- All files in `<ArtifactPath>/` are uploaded with their relative paths preserved
- Files attached via `AttachArtifact()` get clickable links in the dashboard
- Large files (crash dumps, videos) are stored but may not display inline

**Artifact path conventions:**
```
<ArtifactPath>/
  Logs/
    client.log
    server.log
  Screenshots/
    frame1234.png
  CrashDumps/
    crash.dmp
  <TestName>.TestData.json   ← Horde ingests this
  report.html                ← Linked via SetMetadata("ReportURL")
```

---

## Troubleshooting Horde Integration

| Problem | Likely Cause | Fix |
|---------|-------------|-----|
| "No devices available" from Horde | Pool full or constraint mismatch | Check Horde device dashboard; verify platform/tags |
| `*.TestData.json` not appearing in dashboard | File not written or wrong path | Confirm `-writetestresults` is set; check artifact upload succeeded |
| Lease expired mid-test | Test exceeded device TTL | Increase Horde lease duration or reduce `MaxDuration` |
| Auth failure on device reservation | Token expired | Re-generate Horde agent token |
| Tests not grouped correctly | Name format wrong | Use `Group.TestName` dot-separated format |
