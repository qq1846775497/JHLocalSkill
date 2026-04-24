---
name: gauntlet-test-automation
title: Gauntlet Test Automation Framework
description: >
  Gauntlet is UE5's C# test orchestration layer inside AutomationTool that
  drives multi-device, multi-process automated tests across all supported
  platforms. It manages the full lifecycle from device reservation and build
  installation through process launch, heartbeat monitoring, log parsing,
  retry logic, and structured report generation. Use this skill whenever
  working with Gauntlet test nodes, RunUnreal, device pools, UnrealSession,
  UnrealTestNode, or UE automation test authoring in C#.
tags: [Automation, Testing, AutomationTool, CSharp, DevOps, Gauntlet, CI, MultiPlatform]
---

# Gauntlet Test Automation Framework

**Location:** `Engine/Source/Programs/AutomationTool/Gauntlet/`
**Language:** C# (part of AutomationTool / UAT)
**Project file:** `Gauntlet.Automation.csproj`

## Overview

Gauntlet is UE5's automated test orchestration framework. It sits on top of AutomationTool (UAT) and is responsible for:

- Reserving physical or virtual devices across platforms
- Installing UE builds onto those devices
- Launching multi-process test sessions (client + server + editor combinations)
- Ticking running tests, enforcing timeouts, monitoring heartbeats
- Collecting logs, artifacts, crash dumps, screenshots
- Parsing structured results and emitting reports to Horde CI

**Gauntlet is NOT:**
- The in-engine UE Automation framework (`FAutomationTestBase`, Python tests). Those run *inside* a UE process. Gauntlet *orchestrates* that process from outside.
- A unit test runner. It targets integration/functional/smoke tests at the binary level.

**When to use Gauntlet:** Any test that needs to launch an actual UE process, manage real devices, coordinate multiple processes, or verify behavior that only appears at runtime.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Entry Points (UAT BuildCommands)                           │
│  RunUnreal.cs · RunEditorTests.cs · TestGauntlet.cs         │
├─────────────────────────────────────────────────────────────┤
│  Unreal/  — UE-specific orchestration                       │
│  UnrealTestNode<T> · UnrealSession · UnrealBuildSource      │
│  UnrealLogParser · AutomationLogParser · UnrealTelemetry    │
│  Unreal/Automation/  (20+ ready-to-use test nodes)          │
├─────────────────────────────────────────────────────────────┤
│  Platform/  — per-OS device + build source                  │
│  Windows · Linux · Mac · Android(ADB) · iOS(idevice) · Null │
├─────────────────────────────────────────────────────────────┤
│  Framework/  — pure abstractions + executor                 │
│  ITestNode · BaseTest · TestExecutor (500ms poll loop)      │
│  DevicePool · AutoParam · HordeReport · RpcFramework        │
└─────────────────────────────────────────────────────────────┘
```

Layer responsibilities:
- **Framework/Base** — C# interfaces only; zero UE or platform knowledge
- **Framework/** root — `TestExecutor` drives the lifecycle; `AutoParam` binds CLI→fields; `DevicePool` brokers devices
- **Platform/** — one subdirectory per OS; implements `ITargetDevice` + `IFolderBuildSource`
- **Unreal/** — UE-aware layer: session management, build resolution, log parsing, report generation
- **Unreal/Automation/** — concrete, reusable test nodes (BootTest, Cook, Networking, etc.)

## Core Interfaces

### ITestNode Lifecycle

| Method | When Called | Contract |
|--------|-------------|---------|
| `SetContext(ITestContext)` | Before any other call | Inject build/platform context |
| `IsReadyToStart()` | Polled until true | Check device availability |
| `StartTest(pass, numPasses)` | Once ready | Launch processes; return false to abort |
| `TickTest()` | Every 500ms while running | Non-blocking status check only |
| `StopTest(StopReason)` | On completion or timeout | Tear down processes, save artifacts |
| `CleanupTest()` | After stop | Release devices; must be idempotent |
| `GetTestStatus()` | Anytime | `NotStarted / Pending / InProgress / Complete` |
| `GetTestResult()` | After complete | `Passed / Failed / WantRetry / Cancelled / TimedOut / InsufficientDevices` |
| `GetTestSummary()` | After complete | Human-readable result string |

### Key Enums

```
TestStatus:  NotStarted → Pending → InProgress → Complete
TestResult:  Invalid · Passed · Failed · WantRetry · Cancelled · TimedOut · InsufficientDevices
StopReason:  Completed · MaxDuration
EventSeverity: Info · Warning · Error · Fatal
UnrealProcessResult: ExitOk · InitializationFailure · LoginFailed · EncounteredFatalError
                     EncounteredEnsure · TestFailure · TimeOut · EngineTestError · Unknown
```

→ Full interface contracts: `references/gauntlet-interfaces.md`

## Test Class Hierarchy

```
ITestNode                               (Framework/Base/Gauntlet.TestNode.cs)
  └── BaseTest                          (Framework/Base/Gauntlet.BaseTestNode.cs)
        └── UnrealTestNode<TConfigClass> (Unreal/Base/Gauntlet.UnrealTestNode.cs)
              └── YourTest              (your plugin or Unreal/Automation/)
```

`TConfigClass` must extend `UnrealTestConfiguration`. The pattern:

```csharp
public class MyConfig : UnrealTestConfiguration
{
    [AutoParam("soakminutes")]
    public int SoakMinutes = 5;
}

[TestGroup("MyGame")]
public class MySoakTest : UnrealTestNode<MyConfig>
{
    public MySoakTest(UnrealTestContext ctx) : base(ctx) { }
    public override string Name => "MyGame.SoakTest";
    // Override GetConfiguration(), TickTest(), GetTestResult() as needed
}
```

→ Full annotated example + decision tree: `references/gauntlet-writing-tests.md`

## TestExecutor — The Poll Loop

`TestExecutor` (`Framework/Gauntlet.TestExecutor.cs`) is the only scheduler. It runs a **single-threaded 500ms tick loop** across all active tests:

```
PendingTests ──IsReadyToStart?──► StartingTests (thread) ──StartTest?──► RunningTests ──Complete──► CompletedTests
```

Key behaviors:
- `StartTest` runs on a **spawned thread** (to allow parallel launches), but `TickTest` is always on the main thread
- When a test completes with `WantRetry` and retries remain (`MaxRetries` default = 3), `CleanupTest()` is called and then `StartTest()` again on the **same instance**
- Ctrl-C sets a global cancellation flag; all running tests receive `StopTest(Cancelled)`
- Global `Monitor.Enter(Globals.MainLock)` guards all state transitions

**TestExecutorOptions:**

| Option | Type | Effect |
|--------|------|--------|
| `Parallel` | bool | Allow multiple tests to be in Starting/Running simultaneously |
| `MaxDuration` | float | Global wall-clock timeout for the entire run (seconds) |
| `NoTimeout` | bool | Disable both global and per-test timeouts |
| `StopOnError` | bool | Abort remaining tests on first failure |
| `Wait` | int | Seconds to wait for devices before failing with InsufficientDevices (default 300) |
| `TestIterations` | int | Run the full test list N times |

## Device Pool & Reservation

`DevicePool` (`Framework/Devices/Gauntlet.DevicePool.cs`) is a **singleton** inventory broker.

**DeviceDefinition** fields:

| Field | Type | Notes |
|-------|------|-------|
| `Name` | string | Friendly name |
| `Address` | string | Hostname or ADB serial |
| `Platform` | string | e.g. `"Win64"`, `"Android"` |
| `PerfSpec` | EPerfSpec | `Unspecified / Minimum / Recommended / High` |
| `Model` | string | Device model string for constraint matching |
| `Tags` | string[] | Arbitrary labels for selection |
| `Available` | TimeRange | Window when device can be used |

Devices are **unprovisioned** until demanded — provisioning is lazy. A test's `IsReadyToStart()` triggers `DevicePool.CheckAvailableDevices()` via `UnrealSession.TryReserveDevices()`.

**CLI device specification:**
```bash
-Devices=Win64:hostname1,Win64:hostname2   # explicit by address
-Devices=Win64                              # any Win64 in pool
```

Remote reservation (Horde backend) is via `IDeviceReservationService` — see `Framework/Devices/Gauntlet.DeviceReservationService.cs`.

→ Full DeviceDefinition schema, validators, troubleshooting: `references/gauntlet-devices.md`

## UnrealTestNode Deep Dive

`UnrealTestNode<TConfigClass>` (`Unreal/Base/Gauntlet.UnrealTestNode.cs`, ~2838 lines) is the central class. It owns an `UnrealSession` and drives the full UE-specific lifecycle.

### UnrealSession Launch Flow

```
TryReserveDevices()
    └─► TryAssignDevicesToRoles()
         └─► ReadyDevicesForSession()
              ├─ PreConfigureDevice()
              ├─ CreateConfiguration()  ← builds UnrealAppConfig per role
              ├─ FullClean()            ← optional, clears sandbox
              ├─ InstallBuild()         ← ITargetDevice.InstallBuild()
              ├─ CreateAppInstall()     ← returns IAppInstall
              └─ ConfigureDevice()
         └─► LaunchProcesses()         ← IAppInstall.Run() → IAppInstance
```

### Session Roles

`UnrealSessionRole` defines one process to launch:

| Field | Notes |
|-------|-------|
| `RoleType` | `UnrealTargetRole`: Client / Server / Editor |
| `Platform` | `UnrealTargetPlatform` |
| `Configuration` | Debug / Development / Shipping etc. |
| `CommandLine` | Extra args appended to base config |
| `RoleModifier` | `None` / `Dummy` (no install) / `Null` (no device) |
| `DeferredLaunch` | Don't launch at session start; call `Session.LaunchDeferredRoles()` manually |

### Heartbeat Monitoring

While running, `UnrealTestNode` reads live log buffers for:
- `GauntletHeartbeat: Active` — test is actively progressing
- `GauntletHeartbeat: Idle` — test is running but idle (waiting)

If `TimeoutBeforeFirstActiveHeartbeat` or `TimeoutBetweenActiveHeartbeats` is exceeded, the test is failed with `TimedOut`. This catches hung processes that have not crashed.

### UnrealRoleResult (per process, after stop)

| Field | Content |
|-------|---------|
| `ProcessResult` | `UnrealProcessResult` enum value |
| `ExitCode` | Raw process exit code |
| `Summary` | Human-readable summary string |
| `LogSummary` | `UnrealLog` — parsed errors, warnings, callstacks |
| `Artifacts` | `UnrealRoleArtifacts` — log path, artifact dir |
| `Events` | `IEnumerable<UnrealTestEvent>` |

→ Full property tables, session flowchart, retry mechanics: `references/gauntlet-unreal-test-node.md`

## Build Sources

`UnrealBuildSource` (`Unreal/BuildSource/Gauntlet.UnrealBuildSource.cs`) resolves the `-Build=` CLI argument:

| `-Build=` value | Resolution |
|-----------------|-----------|
| `AutoP4` | Sync from Perforce |
| `Editor` | Local editor binary (dev machines only) |
| `Local` / `Staged` | Path on disk |
| `LatestGood` / `LKG` | Via `IBuildValidator` lookup |
| `UseSyncedBuild` | Already-synced workspace |
| `<direct path>` | Absolute or relative filesystem path |

`IFolderBuildSource` implementations are **discovered at runtime via reflection** — each platform registers itself without a central list. `BuildFlags` controls what operations are permitted on a build (e.g., `CanReplaceCommandLine`, `Bulk`, `ContentOnlyProject`).

⚠️ `-Build=Editor` only works when a local editor binary exists. On CI agents using packaged builds, use `-Build=Staged` or `-Build=AutoP4`.

## AutoParam — Config Binding

`[AutoParam("name")]` on a `public` field or property in `TConfigClass` automatically binds it from the CLI at test start time via `AutoParam.ApplyParamsAndDefaults(...)`.

| C# Type | CLI Syntax | Example |
|---------|-----------|---------|
| `string` | `-name=value` | `-testmap=MyLevel` |
| `bool` | `-name` / `-noname` | `-verbose` |
| `int` / `float` | `-name=N` | `-soakminutes=10` |
| `enum` | `-name=EnumValue` | `-perfspec=High` |
| `List<string>` | `-name=a+b+c` | `-tags=Smoke+Perf` |

Child configs inherit parent params. Name collisions silently shadow the parent — use unique prefixes.

```csharp
public class MyConfig : UnrealTestConfiguration
{
    [AutoParam("mygame-map")]        // prefix avoids collisions
    public string MapName = "TestLevel";

    [AutoParam("mygame-duration")]
    public float TestDuration = 120f;
}
```

## Entry Points (UAT BuildCommands)

All invoked via `RunUAT <CommandName> <flags>`:

**`RunUnreal`** (`Unreal/RunUnreal.cs`) — primary entry point:
```bash
RunUAT RunUnreal \
  -Project=MyGame \
  -Platform=Win64 \
  -Configuration=Development \
  -Build=Staged \
  -Tests=UE.BootTest,MyGame.SoakTest \
  -Devices=Win64:myhost \
  -Parallel \
  -MaxDuration=1800
```

Key flags: `-Tests=` (comma-separated class names), `-Namespaces=` (discovery scope), `-NumClients=`, `-Server`, `-NullRHI`, `-SkipDeploy`, `-Reboot`, `-Args=`/`-ClientArgs=`/`-ServerArgs=`, `-TestIterations=`, `-LogDir=`, `-Verbose`.

**`RunEditorTests`** (`Unreal/RunUnreal.cs`) — editor-only variant, same flags.

**`TestGauntlet`** (`SelfTest/TestGauntlet.cs`) — runs Gauntlet's own self-tests:
```bash
RunUAT TestGauntlet -Group=LogParser       # run a group
RunUAT TestGauntlet -Test=OrderOfOpsTest   # run one test
RunUAT TestGauntlet                        # run all self-tests
```

**Telemetry commands:** `PublishUnrealAutomationTelemetry` (CSV → DB), `FetchUnrealAutomationTelemetry` (DB → CSV).

**Utility commands:** `CheckBuildSize` (size threshold enforcement), `CleanDevices`, `InstallUnrealBuild`.

## Log Parsing & Events

**`UnrealLogParser`** (`Unreal/Utils/Gauntlet.UnrealLogParser.cs`) parses a completed log file into an `UnrealLog`:

| Field | Content |
|-------|---------|
| `LogEntries` | All parsed lines as `LogEntry` (Prefix, Category, Level, Message) |
| `Errors` / `Warnings` | Filtered by severity |
| `FatalError` | First fatal with `CallstackMessage` |
| `Ensures` | All ensure violations with callstacks |
| `EngineInitialized` | Bool — did the engine finish startup? |
| `HasTestExitCode` / `TestExitCode` | Exit code set by test logic |
| `RequestedExit` / `RequestedExitReason` | Voluntary shutdown info |

**`AutomationLogParser`** (`Unreal/Utils/Gauntlet.AutomationLogParser.cs`) wraps `UnrealLogParser` to extract in-engine automation suite results:
- Per-test pass/fail via `Test Started` / `Test Completed` log patterns
- Per-test events scraped between `BeginEvents:` / `EndEvents:` markers
- `AutomationReportPath` / `AutomationReportURL` regex extraction

Structured events flow via `ITestNode.AddTestEvent(UnrealTestEvent)` and surface in reports and Horde dashboards.

## Reporting

`ITestReport` (`Framework/Base/Gauntlet.TestReport.cs`) is the output contract:
- `SetProperty(key, value)` — key-value metadata
- `SetMetadata(key, value)` — Horde dashboard metadata
- `AddEvent(EventType, message)` — Info / Warning / Error events
- `AttachArtifact(path, name)` — associate files with the report
- `FinalizeReport()` — write output

**Report implementations:**
- `HordeReport.SimpleTestReport` — v1, lightweight
- `HordeReport.AutomatedTestSessionData` — v2, full phase/step structure
- `HtmlBuilder` / `MarkdownBuilder` — fluent local report builders
- `UnrealTelemetry` — CSV files → telemetry DB via `ITelemetryReport`

→ Full API, schemas, CSV format: `references/gauntlet-reporting.md`

## Ready-to-Use Test Nodes

Located in `Unreal/Automation/` and `Unreal/Engine/`, `Unreal/Editor/`:

- **`UE.BootTest`** — boot engine to main menu and exit cleanly
- **`UE.Automation`** — run in-engine `UE.Automation.*` suites via `-ExecCmds`
- **`UE.CookByTheBook`** — default content cook
- **`UE.CookByTheBook.Cold`** — cook from empty cache
- **`UE.CookByTheBook.Fast`** — cook with pre-warmed DDC
- **`UE.CookByTheBook.Incremental`** — cook only changed assets
- **`UE.CookByTheBook.Iterative`** — iterative cook validation
- **`UE.CookByTheBook.Interrupted`** — cook interrupted mid-run and resumed
- **`UE.CookByTheBook.Unversioned`** — unversioned asset cook
- **`UE.CookByTheBook.SinglePackage`** — single-package cook
- **`UE.CookByTheBook.DLC`** / `.Client` / `.Server` / `.All` — role-specific cook variants
- **`UE.Networking`** — client + server multi-player session
- **`UE.PLMTest`** — mobile process lifecycle (suspend/resume/constrain)
- **`UE.ZenLoaderTest`** — Zen I/O async streaming
- **`UE.ZenStreaming`** — Zen streaming stress test
- **`UE.ErrorTest`** — intentional crash/assert to validate detection pipeline
- **`UE.InstallOnly`** — install build without launching (packaging smoke test)
- **`EngineTest`** (`RunUnrealTests`) — runs editor automation pass
- **`EditorTest.BootTest`** — editor boot validation

→ Full catalog with params and failure modes: `references/gauntlet-builtin-tests.md`

## Platform Support

| Platform | `ITargetDevice` impl | Build source | Special notes |
|----------|---------------------|-------------|---------------|
| Win64 | `TargetDeviceWindows` | `WindowsBuildSources` | NativeStagedBuild / EditorBuild / StagedBuild |
| Linux | `TargetDeviceLinux` | `LinuxBuildSources` | SSH + SCP; requires `mono` on agent |
| Mac | `TargetDeviceMac` | `MacBuildSource` | Local + SSH; `.app` bundles; codesign awareness |
| Android | `TargetDeviceAndroid` | `AndroidBuildSource` | ADB-based; APK+OBB; PLM suspend/resume |
| iOS | `TargetDeviceIOS` | `IOSBuildSource` | libimobiledevice; UDID; provisioning profile |
| Null | `TargetDeviceNull` | — | Headless stub; for server-only or mock roles |

→ Per-platform quirks, build discovery paths, cross-compilation: `references/gauntlet-platforms.md`

## Common Patterns & Pitfalls

### Pattern: Minimal RunUnreal invocation
```bash
RunUAT RunUnreal \
  -Project=MyGame -Platform=Win64 -Configuration=Development \
  -Build=Staged -Tests=UE.BootTest -Parallel
```

### Pattern: Adding a custom session role (client + server)
```csharp
protected override void PopulateSessionParamsWithDefaultRoles(
    UnrealSessionParams sp, MyConfig cfg)
{
    sp.Roles.Add(new UnrealSessionRole(
        UnrealTargetRole.Server,
        Context.GetRoleContext(UnrealTargetRole.Server).Platform,
        cfg.Build.Configuration));

    sp.Roles.Add(new UnrealSessionRole(
        UnrealTargetRole.Client,
        Context.GetRoleContext(UnrealTargetRole.Client).Platform,
        cfg.Build.Configuration,
        "-ExecCmds=\"Automation RunTests MyGame.Client\""));
}
```

### Pattern: Custom pass/fail logic from role results
```csharp
public override TestResult GetTestResult()
{
    var server = GetRoleResult(UnrealTargetRole.Server);
    if (server?.ProcessResult != UnrealProcessResult.ExitOk)
        return TestResult.Failed;
    if (!server.LogSummary.LogEntries.Any(e => e.Message.Contains("SESSION_COMPLETE")))
        return TestResult.Failed;
    return TestResult.Passed;
}
```

---

### ⚠️ P1 — `TickTest()` Must Never Block
`TestExecutor` runs all active tests on a **single thread**. Any `TickTest()` doing `Thread.Sleep()`, synchronous I/O, or network waits stalls every other running test. Use a state machine or fire-and-forget tasks.

### ⚠️ P2 — `InsufficientDevices` Looks Like a Silent Skip
When the device pool has no matching devices and `-Wait=` is not set (or expires), the test is immediately marked `InsufficientDevices` — no loud error. Always set `-Wait=60` on CI and check for this result code in aggregation.

### ⚠️ P3 — Retry Requires Idempotent Cleanup
On `WantRetry`, `CleanupTest()` is called then `StartTest()` again on the **same instance**. The base class resets `RoleResults` and the session, but any fields your subclass wrote during start/tick must be manually cleared in `CleanupTest()`.

### ⚠️ P4 — `[AutoParam]` Name Shadowing
If a child `TConfigClass` declares `[AutoParam("build")]`, it silently shadows `UnrealTestConfiguration.Build`. The parent build resolver then sees `null`. Always prefix custom param names (e.g., `"mygame-buildvariant"`).

### ⚠️ P5 — `DeferredLaunch` + Retry
With `DeferredLaunch = true`, only non-deferred roles are auto-launched on retry. Your `TickTest()` must re-check on every tick (including post-retry) whether deferred roles have been launched, and call `Session.LaunchDeferredRoles()` again if needed.

### ⚠️ P6 — Custom Log Categories Invisible to Parser
`UnrealLogParser` matches standard prefixes (`LogGauntlet`, `LogAutomation`, `Error:`, `Warning:`). Game output via custom categories (e.g., `LogMyGameTest:`) is silently ignored. Override `GetCustomLogParserPatterns()` or add your categories to the parser config.

### ⚠️ P7 — `-Build=Editor` Fails on CI Agents
On CI, editor binaries are often absent. Use `-Build=Staged` or `-Build=AutoP4`. Omitting a valid `-Build=` value produces a cryptic "No valid build found" exception rather than a clear error message.

### ⚠️ P8 — `MaxDuration` Is Dual-Level
`-MaxDuration=600` sets **both** the per-test timeout (`UnrealTestConfiguration.MaxDuration`) **and** the global run wall-clock limit (`TestExecutorOptions.MaxDuration`). With 10 tests, each gets 600s individually, but the entire run also times out at 600s. Use `-NoTimeout` with care — it disables both levels.

## Self-Tests

Gauntlet validates itself using its own framework in `SelfTest/`:
- **Framework/** — lifecycle ordering, AutoParam binding, CLI parsing, timeout behavior
- **Unreal/** — log parser accuracy, build resolution, session launch/shutdown
- **Devices/** — TargetDevice contract, GIF creation

```bash
RunUAT TestGauntlet                      # run all
RunUAT TestGauntlet -Group=LogParser     # run a group
RunUAT TestGauntlet -Test=TimeoutTest    # run one
```

→ Self-test patterns and writing new self-tests: `references/gauntlet-self-tests.md`

## Related Systems

| System | Notes |
|--------|-------|
| **Horde CI** | Device reservation backend, report ingestion, test dashboard — `references/gauntlet-horde.md` |
| **RpcFramework** | Multi-machine test coordination — `references/gauntlet-rpc.md` |
| **Account Pool** | `Framework/Account/` — online test account management to prevent parallel-run collisions |
| **AutomationTool** | Parent C# program; Gauntlet `BuildCommand`s are discovered by UAT via reflection |
| **BuildGraph** | Invokes `RunUnreal` as a BuildGraph task on Horde agents |
| **In-Engine Automation** | `FAutomationTestBase` / Python — runs *inside* UE; Gauntlet orchestrates it via `UE.Automation` node |
