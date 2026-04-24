# Gauntlet Core Interfaces Reference

All interfaces live in `Engine/Source/Programs/AutomationTool/Gauntlet/Framework/Base/`.

---

## ITestNode

`Framework/Base/Gauntlet.TestNode.cs`

The fundamental contract. Every test — framework self-tests, Unreal tests, custom tests — implements this.

### Method Contracts

```csharp
void SetContext(ITestContext Context)
```
Called once before anything else. Inject the execution environment (build info, platform, options). Store in a field; `ITestContext` is a marker interface — cast to `UnrealTestContext` for UE-specific data.

```csharp
bool IsReadyToStart()
```
Polled repeatedly (every 30s by `TestExecutor`) while the test is `Pending`. Return `true` when devices have been reserved and the test can proceed. Throwing here marks the test `Failed`. Must be non-blocking.

```csharp
bool StartTest(int Pass, int NumPasses)
```
Called once when `IsReadyToStart()` returns true. Run on a **spawned thread** (parallel launch). Return `false` to abort immediately. `Pass` is the current iteration index (0-based).

```csharp
void TickTest()
```
Called every **500ms** on the **main executor thread** while `GetTestStatus() == InProgress`. Must never block. Read log buffers, check heartbeats, detect completion, set internal state.

```csharp
void StopTest(StopReason Reason)
```
Called when the test completes or is forced to stop. `StopReason`: `Completed` (normal) or `MaxDuration` (timeout). Save artifacts here. Begin log parsing. Set final `TestResult`.

```csharp
bool RestartTest()
```
Called after `CleanupTest()` when `GetTestResult() == WantRetry`. Return `true` if the restart was accepted. Base implementation in `BaseTest` always returns `true`.

```csharp
void CleanupTest()
```
Called after `StopTest()`. Release all device reservations, close file handles, delete temp files. **Must be idempotent** — called once per retry attempt.

```csharp
TestStatus GetTestStatus()
```
Returns current state. Transitions: `NotStarted` → `Pending` (after `SetContext`) → `InProgress` (after `StartTest` succeeds) → `Complete` (after `StopTest`).

```csharp
TestResult GetTestResult()
```
Valid only when status is `Complete`. Values:
- `Passed` — test succeeded
- `Failed` — test failed (check summary for reason)
- `WantRetry` — transient failure; `TestExecutor` will retry
- `Cancelled` — Ctrl-C abort
- `TimedOut` — exceeded `MaxDuration`
- `InsufficientDevices` — device pool couldn't satisfy requirements
- `Invalid` — result not yet determined (don't call before `Complete`)

```csharp
void SetTestResult(TestResult Result)
```
Allows external override (e.g., `TestExecutor` sets `Cancelled` on Ctrl-C).

```csharp
void AddTestEvent(UnrealTestEvent Event)
```
Accumulate structured events. These surface in `GetTestSummary()`, `GetErrors()`, `GetWarnings()` and are attached to reports.

```csharp
string GetTestSummary()
IEnumerable<string> GetWarnings()
IEnumerable<string> GetErrors()
```
Human-readable output, logged at test completion and included in Horde reports.

```csharp
string GetRunLocalCommand(string BuildPath)
```
Returns a CLI string that reproduces this test locally. Logged after failures so engineers can reproduce without running the full CI pipeline.

```csharp
void DisplayCommandlineHelp()
```
Print `[AutoParam]` parameter help to the log. Called when `-help` is passed.

### State Transition Rules

```
NotStarted ──SetContext()──► Pending
Pending    ──IsReadyToStart()==true──► [StartTest thread spawned]
                                        ──StartTest()==true──► InProgress
                                        ──StartTest()==false──► Complete(Failed)
InProgress ──TickTest() detects complete──► [StopTest called] ──► Complete
InProgress ──MaxDuration exceeded──► [StopTest(MaxDuration)] ──► Complete(TimedOut)
InProgress ──Ctrl-C──► [StopTest(Completed)] ──► Complete(Cancelled)
Complete(WantRetry) ──CleanupTest, RestartTest──► InProgress (retry)
Complete ──CleanupTest()──► [devices released]
```

### Properties

| Property | Type | Notes |
|----------|------|-------|
| `Name` | string | Unique test identifier used in reports |
| `MaxDuration` | float | Per-test timeout in seconds |
| `Priority` | TestPriority | `Critical / High / Normal / Low / Idle` — affects scheduling order |
| `LogWarningsAndErrorsAfterSummary` | bool | Whether to print warnings/errors after the summary block |
| `MaxDurationReachedResult` | EMaxDurationReachedResult | `Failure` or `Success` when timeout fires |

---

## ITestContext

`Framework/Base/Gauntlet.TestContext.cs`

Intentionally a **marker interface** — no members. Concrete implementations:
- `UnrealTestContext` — carries `UnrealBuildSource`, role contexts, platform, options

Cast pattern:
```csharp
void SetContext(ITestContext InContext)
{
    var ueCtx = InContext as UnrealTestContext
        ?? throw new AutomationException("Expected UnrealTestContext");
    Context = ueCtx;
}
```

---

## ITargetDevice

`Framework/Base/Gauntlet.TargetDevice.cs`

Abstraction over a physical or virtual device. Implements `IDisposable`.

### Core Methods

```csharp
bool Connect()           // Establish connection (SSH, ADB, etc.)
bool Disconnect()        // Close connection
void PowerOn()           // Optional — power cycle if supported
void PowerOff()

bool IsConnected { get; }
string Name { get; }
UnrealTargetPlatform Platform { get; }
```

### App Lifecycle

```csharp
IAppInstall InstallBuild(IAppConfig Config)
    // Install a build; returns handle for launching

void FullClean(IAppConfig Config)
    // Remove all installed files and sandboxes for the config

void CopyAdditionalFiles(IEnumerable<string> Files)
    // Copy extra files to device (e.g., test data)
```

### Artifact Collection

```csharp
string GetCachedArtifactPath()     // Where to find post-run artifacts
void GetArtifacts(string OutputDir) // Pull artifacts from device
```

### Related Interfaces

| Interface | Purpose |
|-----------|---------|
| `IDeviceSource` | Provides `ITargetDevice` instances to `DevicePool` |
| `IDefaultDeviceSource` | Provides the localhost as a device |
| `IDeviceFactory` | Creates `ITargetDevice` from `DeviceDefinition` (discovered via reflection) |
| `IDeviceService` | Manages a collection of devices (cloud/remote) |
| `IVirtualLocalDevice` | Marks devices that run locally but are logically remote |
| `IDeviceBuildSupport` | Extended build installation capabilities |
| `IPlatformTargetSupport` | Per-platform helpers discovered by reflection |
| `IWithPLMSuspend` | Mobile: suspend/resume via PLM |
| `IWithPLMConstrain` | Mobile: CPU/memory constrain via PLM |

---

## IAppInstall

`Framework/Base/Gauntlet.AppInstall.cs`

An installed-but-not-yet-running application handle.

```csharp
IAppInstance Run()
    // Launch the installed app; returns a running instance handle
    // Called by UnrealSession.LaunchProcesses()

IAppInstance Run(CommandLineArguments AdditionalArgs)
    // Launch with extra args appended (used by DeferredLaunch)
```

Optional inner interface `IDynamicCommandLine`:
```csharp
void AddCommandLineArgument(string Arg)
    // Modify command line after install but before first Run()
```

---

## IAppInstance

`Framework/Base/Gauntlet.AppInstance.cs`

A running process handle.

```csharp
bool HasExited { get; }
int ExitCode { get; }         // Valid only after HasExited == true
string ArtifactPath { get; } // Where logs/dumps will be found

IProcessResult WaitForExit()  // Block until exit (use sparingly — TickTest must not block)
void Kill(bool Force = false)  // Terminate process

ILogReader GetLogReader()     // Stream live log output
```

`ILogReader` allows `UnrealTestNode.TickTest()` to read log lines without blocking.

---

## IBuild / IBuildSource / IFolderBuildSource

`Framework/Base/Gauntlet.BuildSource.cs`

```csharp
// BuildFlags — bitfield on IBuild
enum BuildFlags
{
    None,
    Packaged,           // Full packaged build
    Loose,              // Loose file layout
    CanReplaceCommandLine,
    CanReplaceExecutable,
    Bulk,               // Bulk content build
    NotBulk,
    ContentOnlyProject
}

interface IBuild
{
    BuildFlags Flags { get; }
    UnrealTargetPlatform Platform { get; }
    string BuildPath { get; }
}

interface IBuildSource
{
    // Resolves a build reference string to an IBuild
    IBuild GetBuild(UnrealTargetPlatform Platform, BuildFlags Flags, string BuildReference);
}

interface IFolderBuildSource
{
    // Discovers builds at a filesystem path (platform-specific implementations)
    List<IBuild> GetBuildsAtPath(string Path, BuildFlags Flags);
    bool CanSupportPlatform(UnrealTargetPlatform Platform);
}
```

`IFolderBuildSource` implementations are discovered at runtime via reflection. Each platform's `*BuildSource.cs` file implements this interface without any central registration.

---

## IDeviceReservationService

`Framework/Devices/Gauntlet.DeviceReservationService.cs`

Pluggable backend for remote device reservation (e.g., Horde device farm).

```csharp
interface IDeviceReservationService
{
    // Request a lease on devices matching the constraint
    IDeviceReservation ReserveDevices(
        IEnumerable<UnrealDeviceTargetConstraint> Constraints,
        int WaitSeconds);

    // Check if this service can handle the given platform
    bool CanReserveDevices(UnrealTargetPlatform Platform);
}

interface IDeviceReservation : IDisposable
{
    IEnumerable<DeviceDefinition> ReservedDevices { get; }
    bool IsValid { get; }
    void Extend();   // Heartbeat to keep lease alive
}
```

---

## ITestReport

`Framework/Base/Gauntlet.TestReport.cs`

```csharp
interface ITestReport
{
    string Type { get; }   // Report format identifier

    void SetProperty(string Name, string Value);
    void SetMetadata(string Name, string Value);   // Horde dashboard metadata
    void AddEvent(EventType Type, string Message); // Info / Warning / Error
    void AttachArtifact(string FilePath, string Name = null);
    IReadOnlyDictionary<string, object> GetReportDependencies();
    void FinalizeReport();
}

interface ITelemetryReport
{
    void AddTelemetry(string TestName, string DataPoint,
        double Measurement, string Context = null,
        string Unit = null, double? Baseline = null);
    IEnumerable<TelemetryData> GetAllTelemetryData();
}

// EventType enum
enum EventType { Unknown, Info, Warning, Error }

// TestStateType enum
enum TestStateType { Unknown, NotRun, InProcess, Fail, Success, Skipped }
```

---

## Interface Implementation Cross-Reference

| Interface | Framework/Base | Platform/ | Unreal/ |
|-----------|---------------|-----------|---------|
| `ITestNode` | `BaseTest` | — | `UnrealTestNode<T>` → concrete nodes |
| `ITestContext` | — | — | `UnrealTestContext` |
| `ITargetDevice` | `TargetDeviceDesktopCommon` | `TargetDeviceWindows`, `Linux`, `Mac`, `Android`, `iOS`, `Null` | — |
| `IAppInstall` | — | Platform-specific inner classes | `UnrealAppInstall` |
| `IAppInstance` | — | Platform-specific process wrappers | — |
| `IBuildSource` | — | — | `UnrealBuildSource` |
| `IFolderBuildSource` | — | `*BuildSources` per platform | `StagedBuildSource` |
| `IDeviceReservationService` | — | — | `UnrealDeviceReservation` (Horde) |
| `ITestReport` | `BaseTestReport` | — | `HordeReport.*` |
| `ITelemetryReport` | `BaseTestReport` | — | `UnrealTelemetry` consumers |
