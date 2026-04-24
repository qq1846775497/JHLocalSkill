# Gauntlet Self-Tests

Reference for `Engine/Source/Programs/AutomationTool/Gauntlet/SelfTest/` — Gauntlet validates itself using its own framework.

---

## Why Self-Tests Matter

Gauntlet's self-tests serve as a regression guard for the framework itself. They verify that:
- The `TestExecutor` lifecycle (NotStarted → InProgress → Complete) works correctly
- `[AutoParam]` binds CLI arguments to the right types
- `UnrealLogParser` accurately detects fatals, ensures, errors, warnings
- Device pool reservation and release works
- Timeout/retry logic fires at the right time
- Build resolution works for each build reference type

If any self-test fails, the Gauntlet framework itself is broken — **run these before blaming a test node**.

---

## Running Self-Tests

**Entry point:** `SelfTest/TestGauntlet.cs` — `TestGauntlet : BuildCommand`

```bash
# Run all self-tests:
RunUAT TestGauntlet

# Run a named group:
RunUAT TestGauntlet -Group=LogParser
RunUAT TestGauntlet -Group=Framework
RunUAT TestGauntlet -Group=Unreal

# Run a single test:
RunUAT TestGauntlet -Test=OrderOfOpsTest
RunUAT TestGauntlet -Test=LogParserFatalError
RunUAT TestGauntlet -Test=TimeoutTest

# Verbose output:
RunUAT TestGauntlet -Verbose
```

---

## Self-Test Coverage Map

### Framework/ — Core Executor and Utilities

| Test | Group | What It Validates |
|------|-------|-----------------|
| `OrderOfOpsTest` | Framework | Lifecycle method call order: SetContext → IsReadyToStart → StartTest → TickTest → StopTest → CleanupTest |
| `TimeoutTest` | Framework | `MaxDuration` fires at the correct time; `MaxDurationReachedResult` respected |
| `TestAutoParam` | Framework | `[AutoParam]` binds string, bool, int, float, enum, List<string> correctly |
| `TestParsing` | Framework | `Gauntlet.Params` CLI parsing: `-flag`, `-key=value`, comma-separated lists |
| `CreateGif` | Framework | `ReportGenUtils` GIF creation from screenshot frames |

### Unreal/ — UE-Specific Logic

| Test | Group | What It Validates |
|------|-------|-----------------|
| `LogParserTest*` | LogParser | `UnrealLogParser` accuracy against fixture log files |
| `TestUnrealBuildParsing` | Unreal | `UnrealBuildSource` resolves various `-Build=` references |
| `TestUnrealBuildSource` | Unreal | `IFolderBuildSource` discovery via reflection |
| `TestUnrealSession` | Unreal | `UnrealSession` launch and shutdown lifecycle |
| `TestUnrealInstallAndRunDesktop` | Unreal | Full install-and-run cycle on the current desktop platform |
| `TestUnrealOptions` | Unreal | `UnrealTestConfiguration` option binding |

### Devices/

| Test | Group | What It Validates |
|------|-------|-----------------|
| `TestTargetDevice*` | Platform | `ITargetDevice` contract per platform |

### Platform-Specific (co-located with platform sources)

| Test | What It Validates |
|------|-----------------|
| `TestTargetDeviceWindows` | Windows device install/run |
| `TestTargetDeviceLinux` | Linux SSH device install/run |
| `TestTargetDeviceMac` | Mac device install/run |
| `TestUnrealInstallAndRunWindows` | Full Win64 round-trip |
| `TestUnrealInstallAndRunLinux` | Full Linux round-trip |
| `TestUnrealInstallAndRunMac` | Full Mac round-trip |

---

## Log Parser Self-Tests

`SelfTest/Unreal/Gauntlet.SelfTest.LogParserTest.cs`

Uses fixture log files in `SelfTest/TestData/LogParser/` to validate parser accuracy.

**Covered scenarios:**

| Test Class | Fixture File | Validates |
|-----------|-------------|-----------|
| `LogParserNormalExit` | `Win64NormalExit.txt` | Clean exit code detection |
| `LogParserFatalError` | `*FatalError.txt` | Fatal with callstack extraction |
| `LogParserEnsure` | `*Ensure.txt` | Ensure violation detection |
| `LogParserCircularBuffer` | `*CircularBuffer.txt` | Fatal in circular log buffer |
| `LogParserRequestExit` | `*RequestExit.txt` | `RequestedExit` + reason extraction |
| `LogParserChannels` | `*Channels.txt` | Channel-filtered log extraction |
| `LogParserErrors` | `*Errors.txt` | Error/warning count accuracy |
| `LogParserAutomation` | `*Automation.txt` | AutomationLogParser per-test events |

---

## NullDevice and NullBuildSource as Test Doubles

The self-tests use `TargetDeviceNull` and no-op build sources to test framework logic without real hardware:

- `TargetDeviceNull` satisfies `ITargetDevice` with no-ops
- `NullBuildSource` returns a stub `IBuild` with `BuildFlags.None`
- Allows testing `TestExecutor`, `DevicePool`, and `UnrealSession` lifecycle without real devices

This pattern is useful for unit-level testing of custom `UnrealTestNode` subclasses in isolation.

---

## Writing a New Self-Test

Self-tests extend `BaseTestNode : ITestNode` (defined in `SelfTest/Gauntlet.SelfTest.BaseNode.cs`), which adds assertion helpers:

```csharp
[TestGroup("MyCustomGroup")]
public class MyLogicTest : BaseTestNode
{
    public override string Name => "SelfTest.MyLogicTest";
    public override float MaxDuration => 30f;

    public override bool StartTest(int Pass, int NumPasses)
    {
        // Test runs synchronously on the start thread
        var result = MyGauntletUtil.DoSomething();

        // Assertion helper: accumulates failures without throwing
        CheckResult(result != null, "DoSomething returned null");
        CheckResult(result.Value == 42, $"Expected 42, got {result.Value}");

        // Signal completion
        MarkComplete(HasFailed ? TestResult.Failed : TestResult.Passed);
        return true;
    }

    public override void CleanupTest() { /* no-op */ }
}
```

**Key helpers from `BaseTestNode`:**

| Method | Effect |
|--------|--------|
| `CheckResult(bool, string)` | Logs failure message if false; sets `HasFailed = true` |
| `MarkComplete(TestResult)` | Transitions to `Complete` with the given result |
| `HasFailed` | True if any `CheckResult()` check failed |
| `TestException` | Exception type that maps to `TestResult.Failed` when thrown |

---

## CI Integration

The self-tests run in Horde on every engine changelist:

```
BuildGraph Node: "GauntletSelfTest"
  Runs: RunUAT TestGauntlet -Group=Framework -Group=LogParser -Group=Unreal
  Platform: Win64 agent
  MaxDuration: 300s
  Artifacts: TestData.json for dashboard
```

Self-test failures block the engine CL from submitting.

---

## TestData/ — Fixture Files

`SelfTest/TestData/`

| Subdirectory | Contents |
|-------------|---------|
| `LogParser/` | Sample UE log files for parser fixture tests |
| `GifTest/` | PNG frame sequences for GIF creation test |

The `LogParser/` files are real log excerpts (sanitized) that cover each parser scenario. When adding a new parser feature, add a corresponding fixture file and test class.
