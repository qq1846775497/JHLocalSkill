# Gauntlet Integration Guide

How to integrate AutomatedPerfTesting with Gauntlet/BuildGraph for CI/CD pipelines.

## Overview

The plugin provides C# Gauntlet nodes in `Build/Scripts/` for UAT/BuildGraph integration:
- `AutomatedPerfTestNode.cs`: Base Gauntlet test node
- `AutomatedPerfTestConfig.cs`: Configuration classes
- `AutomatedPerfTest.Bridge.cs`: Horde report integration
- `AutomatedPerfTest.Util.cs`: Utility functions

## Running Tests via UAT

### Basic Command

```bash
RunUnreal -project=MyProject.uproject \
  -platform=Win64 \
  -test=AutomatedPerfTest.SequenceTest \
  -build=editor
```

### With Profiling

```bash
RunUnreal -project=MyProject.uproject \
  -platform=Win64 \
  -test=AutomatedPerfTest.SequenceTest \
  -InsightsTrace \
  -CSVProfiler \
  -FPSChart \
  -VideoCapture
```

### Test-Specific Parameters

**Sequence Test:**
```bash
-AutomatedPerfTest.SequenceTest.MapSequenceComboName=MyCombo
```

**Replay Test:**
```bash
-AutomatedPerfTest.ReplayTest.ReplayName=MyReplay
```

**Static Camera Test:**
```bash
-AutomatedPerfTest.StaticCameraTest.MapName=MyMap
```

## Custom Config Classes

Create a config class inheriting from `AutomatedPerfTestConfigBase`:

```csharp
public class MyCustomTestConfig : AutomatedPerfTestConfigBase
{
    [AutoParam("")]
    public string CustomParam = "";

    public override void ApplyToConfig(UnrealAppConfig AppConfig, UnrealSessionRole ConfigRole, IEnumerable<UnrealSessionRole> OtherRoles)
    {
        base.ApplyToConfig(AppConfig, ConfigRole, OtherRoles);

        // Add custom commandline args
        if (!string.IsNullOrEmpty(CustomParam))
        {
            AppConfig.CommandLine += $" -CustomParam={CustomParam}";
        }
    }
}
```

## Custom Test Nodes

Create a test node inheriting from `AutomatedPerfTestNode<TConfigClass>`:

```csharp
public class MyCustomTestNode : AutomatedPerfTestNode<MyCustomTestConfig>
{
    public MyCustomTestNode(UnrealTestContext InContext) : base(InContext)
    {
    }

    public override MyCustomTestConfig GetConfiguration()
    {
        MyCustomTestConfig Config = base.GetConfiguration() as MyCustomTestConfig;

        // Set test controller class
        Config.TestControllerClass = "MyProject.MyCustomPerfTest";

        return Config;
    }
}
```

## BuildGraph Integration

### XML Node Definition

```xml
<Node Name="PerfTest_Sequence">
    <Command Name="RunUnreal" Arguments="-project=$(ProjectPath) -platform=Win64 -test=AutomatedPerfTest.SequenceTest -InsightsTrace -CSVProfiler -build=editor"/>
</Node>
```

### With Artifacts

```xml
<Node Name="PerfTest_Sequence" Produces="#PerfTestArtifacts">
    <Command Name="RunUnreal" Arguments="-project=$(ProjectPath) -platform=Win64 -test=AutomatedPerfTest.SequenceTest -InsightsTrace -CSVProfiler -ArtifactPath=$(ArtifactDir)"/>
    <Tag Files="$(ArtifactDir)/..." With="#PerfTestArtifacts"/>
</Node>
```

## Report Generation

The plugin automatically generates reports for Horde integration.

### Report Structure

```json
{
    "TestSessionInfo": {
        "TestName": "MyTest",
        "TestID": "unique-id",
        "Platform": "Win64",
        "BuildName": "MyBuild"
    },
    "TestResults": [
        {
            "TestName": "MyTest",
            "Status": "Passed",
            "Duration": 120.5,
            "Artifacts": [
                "MyTest.utrace",
                "MyTest.csv"
            ]
        }
    ]
}
```

### Custom Report Data

Override `CreateReport()` in your test node:

```csharp
public override ITestReport CreateReport(TestResult Result, UnrealTestContext Context, UnrealBuildSource Build, IEnumerable<UnrealRoleResult> Artifacts, string ArtifactPath)
{
    var Report = base.CreateReport(Result, Context, Build, Artifacts, ArtifactPath);

    // Add custom data
    // ...

    return Report;
}
```

## Artifact Management

### Output Paths

Default artifact path: `<ProjectDir>/Saved/Automation/Logs/<TestID>/`

Override with `-ArtifactPath=<path>`

### Artifact Types

- `.utrace`: Insights trace files
- `.csv`: CSV profiler output
- `.png`: Screenshots
- `.mp4`: Video captures
- `.log`: Test logs

### Collecting Artifacts

```csharp
protected override void CollectArtifacts(UnrealRoleResult RoleResult)
{
    base.CollectArtifacts(RoleResult);

    // Collect custom artifacts
    string CustomFile = Path.Combine(ArtifactPath, "custom.txt");
    if (File.Exists(CustomFile))
    {
        RoleResult.Artifacts.Add(CustomFile);
    }
}
```

## Commandline Parameters

### Base Parameters

```bash
-test=<TestName>              # Test to run
-platform=<Platform>          # Target platform
-build=<BuildType>            # editor/game/client/server
-project=<ProjectPath>        # .uproject path
```

### Profiling Parameters

```bash
-InsightsTrace                # Enable Insights
-TraceChannels=<Channels>     # Trace channels
-CSVProfiler                  # Enable CSV profiler
-FPSChart                     # Enable FPS chart
-VideoCapture                 # Enable video capture
-LockedDynRes                 # Lock dynamic resolution
```

### Test Identification

```bash
-TestName=<Name>              # Test name
-TestID=<ID>                  # Unique test ID
-BuildName=<Name>             # Build name for reports
```

### Output Control

```bash
-ArtifactPath=<Path>          # Output directory
-DeviceProfile=<Profile>      # Device profile override
```

## Best Practices

1. **Use unique TestIDs** for each test run to avoid artifact conflicts
2. **Specify artifact paths** explicitly in CI/CD to control output location
3. **Collect all artifacts** in BuildGraph for archival
4. **Parse CSV files** in post-processing for metric extraction
5. **Use Horde reports** for dashboard integration
6. **Set timeouts** appropriately for long-running tests
7. **Clean up artifacts** after successful runs to save space
