# Writing Gauntlet Tests

Reference for creating new test nodes.

---

## Which Base Class to Extend?

```
Need a UE process launched?
  YES → extend UnrealTestNode<TConfig>
       Need server + client?  → add roles in PopulateSessionParamsWithDefaultRoles()
       Using an existing node? → subclass UE.BootTest, UE.Automation, etc. instead
  NO  → extend BaseTest directly (pure C# logic, no device/build needed)
        (Used for self-tests, utility tasks, data validation)
```

---

## Minimal Custom Test Node

```csharp
// 1. Define a strongly-typed config
public class MySoakConfig : UnrealTestConfiguration
{
    // [AutoParam("cli-name")] binds a CLI flag to this field automatically
    [AutoParam("mygame-soak-duration")]
    public float SoakDuration = 300f;   // seconds

    [AutoParam("mygame-map")]
    public string MapName = "TestLevel";
}

// 2. Tag with TestGroup for batch invocation (-Group=MyGame)
[TestGroup("MyGame")]
public class MySoakTest : UnrealTestNode<MySoakConfig>
{
    public MySoakTest(UnrealTestContext InContext) : base(InContext) { }

    public override string Name => "MyGame.SoakTest";

    // 3. Config roles: what processes to launch
    public override MySoakConfig GetConfiguration()
    {
        var cfg = base.GetConfiguration();
        // Add exactly one client role
        var roleCtx = Context.GetRoleContext(UnrealTargetRole.Client);
        cfg.Roles.Add(new UnrealTestRole(UnrealTargetRole.Client, roleCtx.Platform));
        cfg.MaxDuration = cfg.SoakDuration + 60f; // test duration + buffer
        return cfg;
    }

    // 4. Optional: post-launch per-tick logic
    protected override void TickTest(TestExecutionInfo TestInfo)
    {
        base.TickTest(TestInfo);  // handles heartbeat, common checks
        // Add custom checks here using GetRoleArtifacts() or log reader
    }

    // 5. Optional: custom pass/fail logic from role results
    public override TestResult GetTestResult()
    {
        var clientResult = GetRoleResult(UnrealTargetRole.Client);
        if (clientResult == null)
            return TestResult.Failed;

        // Check process exit
        if (clientResult.ProcessResult != UnrealProcessResult.ExitOk)
            return TestResult.Failed;

        // Check for custom success token in log
        if (!clientResult.LogSummary.LogEntries
            .Any(e => e.Message.Contains("SOAK_TEST_COMPLETE")))
        {
            SetTestResult(TestResult.Failed);
            return TestResult.Failed;
        }

        return TestResult.Passed;
    }

    // 6. Optional: custom summary
    public override string GetTestSummary()
    {
        var result = GetRoleResult(UnrealTargetRole.Client);
        return $"{Name}: {GetTestResult()} — "
             + $"{result?.LogSummary?.Errors?.Count() ?? 0} errors";
    }
}
```

---

## Adding Custom Session Roles

Override `PopulateSessionParamsWithDefaultRoles()` to control which processes launch:

```csharp
protected override void PopulateSessionParamsWithDefaultRoles(
    UnrealSessionParams Params, MySoakConfig cfg)
{
    // Server role
    var serverCtx = Context.GetRoleContext(UnrealTargetRole.Server);
    Params.Roles.Add(new UnrealSessionRole(
        UnrealTargetRole.Server,
        serverCtx.Platform,
        cfg.Build.Configuration,
        "-log -port=7777")
    {
        // Constrain to a device with a specific tag
        Constraint = new UnrealDeviceTargetConstraint(
            serverCtx.Platform, requiredTags: new[]{"server-capable"})
    });

    // Client role (different device)
    var clientCtx = Context.GetRoleContext(UnrealTargetRole.Client);
    Params.Roles.Add(new UnrealSessionRole(
        UnrealTargetRole.Client,
        clientCtx.Platform,
        cfg.Build.Configuration,
        $"-connect=server -ExecCmds=\"Automation RunTests MyGame.Client\""
    ));
}
```

### ERoleModifier Values

| Value | Effect |
|-------|--------|
| `None` | Normal role: reserve device, install build, launch process |
| `Dummy` | Reserve and install, but don't launch (useful for dedicated install verification) |
| `Null` | Skip device reservation entirely (use `TargetDeviceNull`) — for server-only headless configs |

---

## DeferredLaunch Pattern

Use `DeferredLaunch = true` on a role when you need the server to be ready before the client starts:

```csharp
// In PopulateSessionParamsWithDefaultRoles:
Params.Roles.Add(new UnrealSessionRole(UnrealTargetRole.Server, ...)
{
    DeferredLaunch = false  // launch at session start
});

Params.Roles.Add(new UnrealSessionRole(UnrealTargetRole.Client, ...)
{
    DeferredLaunch = true   // hold until TickTest calls LaunchDeferredRoles()
});

// In TickTest:
protected override void TickTest(TestExecutionInfo TestInfo)
{
    base.TickTest(TestInfo);

    if (!DeferredRolesLaunched && ServerIsReady())
    {
        Session.LaunchDeferredRoles();
        DeferredRolesLaunched = true;
    }
}
```

⚠️ After a `WantRetry`, the session is rebuilt but deferred roles are still deferred. Re-check `DeferredRolesLaunched` on every tick including post-retry ticks.

---

## TestGroup Registration

```csharp
// Tag a test class for group batch execution:
[TestGroup("MyGame")]           // -Group=MyGame selects all tests in this group
[TestGroup("MyGame", priority: 3)]  // lower number = higher priority within group
public class MyTest : UnrealTestNode<MyConfig> { ... }

// Invoke a group:
// RunUAT RunUnreal -Tests=MyGame -IsTestGroup -Project=... -Build=...
// OR: RunUAT TestGauntlet -Group=MyGame
```

Priority sorts within the group: 1 = highest, default = 5, higher numbers run last.

---

## Retry State Reset Checklist

When `WantRetry` fires, the framework calls `CleanupTest()` then `StartTest()` again on the **same object instance**. The framework resets:
- `RoleResults` list (cleared)
- `UnrealSession` (rebuilt)
- Test status/result state machine

You must manually reset in `CleanupTest()`:
- [ ] Any `bool` flags set during `StartTest()` or `TickTest()`
- [ ] Any cached log readers or file handles
- [ ] Any per-run accumulators (error counts, screenshot indices, etc.)
- [ ] Any `DeferredRolesLaunched` flags

```csharp
public override void CleanupTest()
{
    DeferredRolesLaunched = false;
    CurrentPhase = Phase.WaitingForServer;
    ErrorsSeenThisRun.Clear();
    base.CleanupTest();  // must call — releases devices
}
```

---

## Emitting Structured Events

```csharp
// Inside TickTest() or StopTest():
if (SomethingBadHappened)
{
    AddTestEvent(new UnrealTestEvent(
        EventSeverity.Error,
        "Renderer crashed at frame 1234",
        details: new[] { "RHI: D3D12", "GPU: RTX 3080" },
        callstack: new[] { "UEngine::Render()", "..." }
    ));
}

// Info-level breadcrumbs:
AddTestEvent(new UnrealTestEvent(
    EventSeverity.Info,
    $"Phase complete: {PhaseName} in {elapsed:F1}s"
));
```

Events accumulate in `GetErrors()` / `GetWarnings()` and are attached to Horde reports.

---

## BaseTest Pattern (no UE process)

For tests that don't need a UE process or device:

```csharp
[TestGroup("Utilities")]
public class MyDataValidationTest : BaseTest
{
    public override string Name => "Utilities.DataValidation";
    public override float MaxDuration => 60f;

    public override bool StartTest(int Pass, int NumPasses)
    {
        // Do work synchronously (StartTest runs on its own thread)
        var data = LoadTestData();
        if (!ValidateData(data))
        {
            SetTestResult(TestResult.Failed);
            MarkComplete();
            return true;
        }
        SetTestResult(TestResult.Passed);
        MarkComplete();
        return true;
    }

    public override void CleanupTest() { /* nothing to release */ }
}
```

For self-tests, extend `BaseTestNode : ITestNode` (in `SelfTest/`) which adds `CheckResult()` assertion helpers.

---

## Common Mistakes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| Work done in `TickTest()` that blocks | All other tests hang for that tick | Move blocking work to a `Task` or background thread; only check result in `TickTest()` |
| Forgetting `base.CleanupTest()` | Devices never returned to pool; pool exhausted on retry | Always call `base.CleanupTest()` last |
| Forgetting `base.TickTest()` | Heartbeat not checked; test hangs forever | Always call `base.TickTest()` first |
| Not calling `MarkComplete()` | Test runs until `MaxDuration` timeout | Call `MarkComplete()` with the appropriate `TestResult` |
| `GetRoleResult()` before `StopTest()` | Returns `null` | Only call after `StopTest()` has run |
| Role count mismatch with device pool | `InsufficientDevices` | Ensure device pool has enough devices for all non-Null roles |
