---
name: automated-perf-testing
title: Automated Performance Testing Plugin
description: UE5 Gauntlet-based automated performance testing framework for running profiled tests with Insights traces, CSV profiler, FPS charts, and video capture. Use when working with performance testing, benchmarking, profiling automation, or extending test controllers for sequence playback, replay analysis, static camera tests, or custom perf scenarios.
tags: [Performance, Testing, Gauntlet, Profiling, Automation, Engine-Plugin]
---

# Automated Performance Testing Plugin

Epic's official plugin for automated performance testing via Gauntlet framework. Provides test controllers, BuildGraph integration, and profiling automation for UE5 projects.

## Architecture Overview

**Location:** `Engine/Plugins/Performance/AutomatedPerfTesting/`

**Core Components:**
- **Test Controllers (C++)**: `UAutomatedPerfTestControllerBase` and specialized subclasses
- **Gauntlet Nodes (C#)**: `AutomatedPerfTestNode<T>` for BuildGraph/UAT integration
- **Project Settings**: Per-test-type configuration in Project Settings > Plugins
- **Profiling Integration**: Insights, CSV Profiler, FPS Chart, Video Capture

## Test Controller Types

| Controller Class | Purpose | Config Location |
|-----------------|---------|-----------------|
| `UAutomatedSequencePerfTest` | Play Level Sequences with profiling | Project Settings > Sequence |
| `UAutomatedPlacedStaticCameraPerfTest` | Profile from placed camera actors | Project Settings > Static Camera |
| `UAutomatedReplayPerfTest` | Profile replay file playback | Project Settings > Replay |
| `UAutomatedMaterialPerfTest` | Material performance testing | N/A |
| `UAutomatedSoakTest` | Long-running stability tests | N/A |
| `UAutomatedProfileGoTest` | ProfileGo integration | N/A |

## Key Features

### Profiling Automation
- **Insights Trace**: Automatic trace start/stop with custom channels
- **CSV Profiler**: Three output modes (Single/Separate/Granular)
- **FPS Chart**: Automatic chart generation
- **Video Capture**: Synchronized video recording
- **Dynamic Resolution Lock**: Optional DynRes locking during tests

### Test Lifecycle
```
OnInit → SetupTest → RunTest → TeardownTest → Exit
```

Each phase can start/stop profiling tools independently.

### CSV Output Modes
- **Single**: One CSV for entire session (SetupTest → ExitTest)
- **Separate**: One CSV per test run (RunTest → TeardownTest)
- **Granular**: Multiple CSVs during test (e.g., per camera cut in sequences)

## Common Use Cases

### Extending for Custom Tests

Create a new test controller by inheriting from `UAutomatedPerfTestControllerBase`:

```cpp
UCLASS()
class UMyCustomPerfTest : public UAutomatedPerfTestControllerBase
{
    GENERATED_BODY()

    virtual void SetupTest() override;
    virtual void RunTest() override;
    virtual void TeardownTest(bool bExitAfterTeardown = true) override;
    virtual FString GetTestID() override;
};
```

**Key overrides:**
- `SetupTest()`: Initialize test, load maps, start profiling
- `RunTest()`: Execute test logic
- `TeardownTest()`: Stop profiling, cleanup
- `GetTestID()`: Return unique test identifier for output files

### Running Tests via UAT

```bash
RunUnreal -project=MyProject.uproject -platform=Win64 \
  -test=AutomatedPerfTest.SequenceTest \
  -AutomatedPerfTest.SequenceTest.MapSequenceComboName=MyCombo \
  -InsightsTrace -CSVProfiler -FPSChart
```

### Configuring Sequence Tests

1. Open **Project Settings > Plugins > Automated Performance Testing | Sequence**
2. Add entries to **Maps And Sequences To Test**:
   - **Combo Name**: Unique identifier
   - **Map**: Level to load
   - **Sequence**: Level Sequence to play
   - **Game Mode Override**: Optional GameMode alias
3. Set **CSV Output Mode** (Single/Separate/Granular)
4. Adjust **Sequence Start Delay** (default 5s)

### Accessing Test Context

```cpp
// Get test ID (passed via -TestID commandline)
FString TestID = GetTestID();

// Check profiling requests
bool bWantsInsights = RequestsInsightsTrace();
bool bWantsCSV = RequestsCSVProfiler();

// Manual profiling control
TryStartInsightsTrace();
TryStartCSVProfiler();
TryStopInsightsTrace();
TryStopCSVProfiler();

// Console commands
ConsoleCommand(TEXT("stat fps"));

// Screenshots
TakeScreenshot(TEXT("MyScreenshot"));
```

## Gauntlet Integration

The plugin provides C# Gauntlet nodes for BuildGraph integration. See `references/gauntlet-integration.md` for details on:
- Custom config classes
- Report generation
- Horde integration
- Commandline parameters

## Project Settings

Each test type has dedicated settings in **Project Settings > Plugins**:
- **Automated Performance Testing**: Base settings (teardown delay)
- **Sequence**: Map/sequence combos, CSV mode
- **Replay**: Replay file paths, CSV mode
- **Static Camera**: Map/camera configurations

## Troubleshooting

**Test doesn't start:**
- Verify GameMode is set to `AAutomatedPerfTestGameModeBase` or derived class
- Check `-TestControllerClass` commandline parameter
- Ensure plugin is enabled in `.uproject`

**Profiling not working:**
- Pass `-InsightsTrace`, `-CSVProfiler`, or `-FPSChart` on commandline
- Check `RequestsInsightsTrace()` returns true in controller
- Verify output path is writable

**CSV files missing:**
- Check CSV output mode matches expectations
- Ensure `TryStartCSVProfiler()` is called in `RunTest()`
- Verify `TryStopCSVProfiler()` is called in `TeardownTest()`

## References

For detailed implementation guidance:
- **Gauntlet Integration**: `references/gauntlet-integration.md`
- **Controller API**: `references/controller-api.md`
- **Extension Guide**: `references/extension-guide.md`

## File Locations

```
Engine/Plugins/Performance/AutomatedPerfTesting/
├── Source/AutomatedPerfTesting/
│   ├── Public/
│   │   ├── AutomatedPerfTestControllerBase.h      # Base controller
│   │   ├── AutomatedSequencePerfTest.h            # Sequence tests
│   │   ├── AutomatedReplayPerfTest.h              # Replay tests
│   │   ├── StaticCameraTests/                     # Static camera tests
│   │   └── ProfileGo/                             # ProfileGo integration
│   └── Private/                                   # Implementations
├── Build/Scripts/
│   ├── AutomatedPerfTestNode.cs                   # Gauntlet node
│   ├── AutomatedPerfTestConfig.cs                 # Config classes
│   └── PerfReport/                                # Report generation
└── Config/                                        # Default settings
```
