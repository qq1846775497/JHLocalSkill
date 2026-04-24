# UnrealTestNode Deep Reference

`Engine/Source/Programs/AutomationTool/Gauntlet/Unreal/Base/Gauntlet.UnrealTestNode.cs` (~2838 lines)

---

## Overview

`UnrealTestNode<TConfigClass>` is the central class for all UE-aware tests. It inherits from `BaseTest` and adds:
- Typed configuration via `TConfigClass : UnrealTestConfiguration`
- An `UnrealSession` that manages devices and processes
- Live heartbeat monitoring via log-line scanning
- Per-role result collection after shutdown
- Horde report generation and submission

---

## UnrealTestConfiguration Base Properties

All `TConfigClass` instances inherit these. All are bindable via `[AutoParam]` with their listed CLI name.

| Property | CLI Name | Type | Default | Purpose |
|----------|----------|------|---------|---------|
| `MaxDuration` | `maxduration` | float | 600 | Per-test timeout in seconds |
| `MaxRetries` | `maxretries` | int | 3 | Max `WantRetry` cycles |
| `SkipDeploy` | `skipdeploy` | bool | false | Skip build installation |
| `FullClean` | `fullclean` | bool | false | Full sandbox wipe before install |
| `Verbose` | `verbose` | bool | false | Extra logging |
| `CommandLine` | `args` | string | "" | Extra args for all roles |
| `ClientCommandLine` | `clientargs` | string | "" | Extra args for client roles |
| `ServerCommandLine` | `serverargs` | string | "" | Extra args for server roles |
| `EditorCommandLine` | `editorargs` | string | "" | Extra args for editor roles |
| `NullRHI` | `nullrhi` | bool | false | `-nullrhi` on all roles |
| `Windowed` | `windowed` | bool | false | `-windowed` on all roles |
| `ResX` / `ResY` | `resx` / `resy` | int | 0 | Window size |
| `Reboot` | `reboot` | bool | false | Reboot device before install |
| `SimpleHordeReport` | `simplehordeReport` | bool | true | Use HordeReport v1 |
| `WriteTestResultsForHorde` | `writetestresults` | bool | false | Write `.TestData.json` for Horde |
| `HordeReportPath` | `hordereportpath` | string | "" | Override report output path |

---

## UnrealSession Launch Sequence (Detailed)

### Phase 1: TryReserveDevices

```
UnrealSession.TryReserveDevices()
  └─► For each non-Null UnrealSessionRole:
        Create UnrealDeviceTargetConstraint(Platform, PerfSpec, Model, Tags)
        Call DevicePool.CheckAvailableDevices(constraints)
          ├─ If local pool satisfied: return available DeviceDefinitions
          └─ If not: call IDeviceReservationService.ReserveDevices(constraints, WaitSeconds)
  Returns: bool (true = all roles have devices assigned)
```

Called from `ITestNode.IsReadyToStart()`. `TestExecutor` polls this every 30 seconds until it returns `true` or `Wait` timeout expires.

### Phase 2: TryAssignDevicesToRoles

Maps reserved `DeviceDefinition` entries to `UnrealSessionRole` instances. Considers:
- Platform match
- PerfSpec match
- Tag requirements / exclusions
- Model match if specified

### Phase 3: ReadyDevicesForSession

For each assigned device–role pair:

```
1. PreConfigureDevice(device, role)
      └─► Call UnrealSessionRole.PreConfigureDevice delegate (custom pre-install hook)

2. CreateConfiguration(role, buildSource)
      └─► UnrealBuildSource.CreateConfiguration(role)
           └─► Returns UnrealAppConfig with:
                 ProjectFile, ProjectName, ProcessType, CommandLineParams,
                 FilesToCopy, Sandbox, SkipInstall, FullClean, OverlayExecutable

3. FullClean(device, config)      [if config.FullClean == true]
      └─► ITargetDevice.FullClean(config) — removes sandbox directory

4. InstallBuild(device, config)   [if config.SkipInstall == false]
      └─► ITargetDevice.InstallBuild(config) → IAppInstall

5. CreateAppInstall(device, config)
      └─► Returns IAppInstall handle (stored in UnrealSessionRole)

6. CopyAdditionalFiles(device, config.FilesToCopy)

7. ConfigureDevice(device, role)
      └─► Call UnrealSessionRole.ConfigureDevice delegate (custom post-install hook)
```

### Phase 4: LaunchProcesses

For each non-deferred role (in order):

```
IAppInstall.Run() → IAppInstance
Start log reader thread for this instance
Store in UnrealSessionInstance.RunningRoles
```

`DeferredLaunch = true` roles are stored in `UnrealSessionInstance.DeferredRoles` and launched when `Session.LaunchDeferredRoles()` is called from `TickTest()`.

---

## Heartbeat System

### Log Pattern Matching

While `TickTest()` runs, `UnrealTestNode` reads each role's live log buffer looking for:

```
LogGauntlet: GauntletHeartbeat: Active
LogGauntlet: GauntletHeartbeat: Idle
```

- **Active** — test is making progress; resets the "between active heartbeats" timer
- **Idle** — test is running but waiting for something external; resets only the "between any heartbeats" timer

These lines must be emitted by the running UE process. The UE-side Gauntlet plugin emits them automatically for tests that use `IGauntletController`.

### Timeout Configuration

| Property (on TConfigClass) | Default | Meaning |
|---------------------------|---------|---------|
| `TimeoutBeforeFirstActiveHeartbeat` | 120s | How long to wait for the first `Active` heartbeat before failing |
| `TimeoutBetweenActiveHeartbeats` | 120s | How long between consecutive `Active` heartbeats before failing |
| (implicit idle timeout) | MaxDuration | If only `Idle` heartbeats received, eventually MaxDuration fires |

### Timeout Handling

When a heartbeat timeout fires:
1. `StopTest(StopReason.MaxDuration)` is called
2. If `MaxDurationReachedResult == EMaxDurationReachedResult.Failure` → `TestResult.TimedOut`
3. If `MaxDurationReachedResult == EMaxDurationReachedResult.Success` → `TestResult.Passed`

The second option is useful for soak tests that are "done when they time out" rather than when they signal completion.

---

## UnrealRoleResult (Post-Stop, Per Process)

After `StopTest()`, each launched process has a corresponding `UnrealRoleResult`:

```csharp
class UnrealRoleResult
{
    UnrealSessionRole   Role;          // Which role this result is for
    UnrealProcessResult ProcessResult; // What the process exit means
    int                 ExitCode;      // Raw process exit code
    string              Summary;       // Human-readable result description
    UnrealLog           LogSummary;    // Full parsed log (errors, warnings, callstacks)
    UnrealRoleArtifacts Artifacts;     // Paths to log files, crash dumps, etc.
    IEnumerable<UnrealTestEvent> Events; // Structured events extracted from log
}
```

Access pattern:
```csharp
// Get result for a specific role type:
var server = GetRoleResult(UnrealTargetRole.Server);

// Get all results:
foreach (var result in RoleResults) { ... }
```

### UnrealProcessResult Mapping

| Value | Meaning | Typical Cause |
|-------|---------|--------------|
| `ExitOk` | Clean exit | Process exited normally |
| `InitializationFailure` | Engine didn't initialize | Missing DLLs, bad config, startup crash |
| `LoginFailed` | Online login rejected | Invalid credentials, service down |
| `EncounteredFatalError` | `ensure`/`check` violated | Logic bug, assert failure |
| `EncounteredEnsure` | Non-fatal ensure fired | Warning-level logic violation |
| `TestFailure` | Test-signaled failure | `UE_LOG(LogGauntlet, Error, ...)` |
| `TimeOut` | Process didn't respond | Deadlock, infinite loop |
| `EngineTestError` | Engine test framework error | Automation test failure |
| `Unknown` | Unclassified exit | Anything else |

---

## Artifact Collection

When `StopTest()` runs, `UnrealSession.SaveRoleArtifacts()` is called for each role:

1. **Log files** — copied from device to `ArtifactPath/Logs/<RoleName>/`
2. **Crash dumps** — detected by platform-specific patterns and copied
3. **Screenshots** — if `CompressScreenshots` or `CreateGifFromScreenshots` is set on the role
4. **PSO cache** — if the role had PSO collection enabled
5. **Custom artifacts** — any files in `CopyAdditionalFiles` output locations

`UnrealRoleArtifacts` fields:
```csharp
class UnrealRoleArtifacts
{
    UnrealSessionRole Role;
    IAppInstance      AppInstance;
    string            ArtifactPath;  // Local output directory
    string            LogPath;       // Primary log file path
}
```

Override `GetExtraArtifacts()` to add custom paths:
```csharp
protected override IEnumerable<string> GetExtraArtifacts()
{
    yield return Path.Combine(ArtifactPath, "Profiling", "FPSChartStats");
}
```

---

## RestartSession vs. Full Retry

| Scenario | Mechanism |
|----------|----------|
| `GetTestResult() == WantRetry` | `CleanupTest()` → `RestartTest()` → `StartTest()` → full session rebuild |
| In-test transient issue | `Session.RestartSession()` — tears down processes and re-launches without releasing devices |

`RestartSession()` (called from `TickTest()`) is faster (no device re-reservation) but only valid when devices are healthy. Use `WantRetry` when you want full device re-acquisition.

---

## Retry Mechanics — What Is and Isn't Reset

| State | Reset on Retry? | Mechanism |
|-------|----------------|----------|
| `UnrealSession` | ✅ Rebuilt | `CleanupTest()` calls `ShutdownSession()`, `StartTest()` calls `LaunchSession()` |
| `RoleResults` | ✅ Cleared | Base class clears before each `StartTest()` |
| `TestStatus` / `TestResult` | ✅ Reset | Base class state machine |
| Retry counter | Incremented | `Retries` field on `UnrealTestNode` |
| `[AutoParam]` config | ✅ Re-applied | `GetConfiguration()` called again |
| Subclass bool/int fields | ❌ NOT reset | Your responsibility in `CleanupTest()` |
| Log reader state | ❌ NOT reset | New log readers are created per session |
| Device reservation | ❌ NOT released (usually) | Devices held across retries unless validation fails |

---

## BehaviorFlags

`UnrealTestNode` has a `BehaviorFlags` bitfield:

| Flag | Effect |
|------|--------|
| `None` | Default behavior |
| `PromoteErrors` | Escalate warnings to errors in result reporting |
| `PromoteWarnings` | Escalate infos to warnings |

Set in constructor or `GetConfiguration()`:
```csharp
BehaviorFlags = EBehaviorFlags.PromoteErrors;
```

---

## LogSummary Construction

After `StopTest()`, for each role:
1. `UnrealLogParser.GetSummary()` is called on the role's log file
2. Returns `UnrealLog` with all extracted data
3. `UnrealRoleResult.LogSummary` is set to this `UnrealLog`
4. Events (errors, ensures, fatals) are extracted and added via `AddTestEvent()`

The `UnrealLog` is the primary source for pass/fail determination in many test nodes.

---

## Report Generation Flow

Called from `StopTest()` after artifact collection:

```
CreateReport()
  ├─ If WriteTestResultsForHorde: write .TestData.json
  ├─ If SimpleHordeReport: CreateSimpleReportForHorde()
  │     └─► Creates HordeReport.SimpleTestReport
  │          Adds events, metadata, artifacts
  │          Calls report.FinalizeReport()
  └─ Else: CreateUnrealEngineTestPassReport(ReportPath, ReportURL)
          └─► Full HTML report via HtmlBuilder
               + Horde report v2
```

Override `CreateReport()` to add custom report content or a second report format.
