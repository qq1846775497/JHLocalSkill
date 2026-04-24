# Controller API Reference

Complete API reference for `UAutomatedPerfTestControllerBase` and extension patterns.

## Base Class: UAutomatedPerfTestControllerBase

Inherits from `UGauntletTestController` (Gauntlet plugin).

### Lifecycle Methods

#### OnInit()
Called once when controller is created. Use for:
- Reading commandline parameters
- Initializing member variables
- Binding delegates

```cpp
virtual void OnInit() override
{
    Super::OnInit();

    // Read custom commandline params
    FParse::Value(FCommandLine::Get(), TEXT("-MyParam="), MyValue);

    // Bind delegates
    FWorldDelegates::OnWorldBeginPlay.AddUObject(this, &UMyTest::OnWorldBeginPlay);
}
```

#### SetupTest()
Called after world is loaded. Use for:
- Starting profiling tools
- Spawning actors
- Configuring game state

```cpp
virtual void SetupTest() override
{
    Super::SetupTest();

    // Start profiling
    if (RequestsInsightsTrace())
    {
        TryStartInsightsTrace();
    }

    if (RequestsCSVProfiler())
    {
        TryStartCSVProfiler();
    }
}
```

#### RunTest()
Main test execution. Use for:
- Triggering test logic
- Playing sequences
- Moving cameras
- Waiting for completion

```cpp
virtual void RunTest() override
{
    Super::RunTest();

    // Your test logic here
    // Use timers, delegates, or state machines
}
```

#### TeardownTest(bool bExitAfterTeardown)
Called when test completes. Use for:
- Stopping profiling
- Cleanup
- Triggering exit

```cpp
virtual void TeardownTest(bool bExitAfterTeardown = true) override
{
    // Stop profiling BEFORE calling Super
    if (RequestsCSVProfiler())
    {
        TryStopCSVProfiler();
    }

    if (RequestsInsightsTrace())
    {
        TryStopInsightsTrace();
    }

    Super::TeardownTest(bExitAfterTeardown);
}
```

#### Exit()
Final cleanup before application exit.

```cpp
virtual void Exit() override
{
    UnbindAllDelegates();
    Super::Exit();
}
```

### Profiling API

#### Insights Trace

```cpp
// Check if requested via commandline
bool RequestsInsightsTrace() const;

// Start/stop trace
bool TryStartInsightsTrace();
bool TryStopInsightsTrace();

// Get output filename
virtual FString GetInsightsFilename();

// Get trace channels (from -TraceChannels)
FString GetTraceChannels();
```

**Commandline:**
- `-InsightsTrace`: Enable Insights tracing
- `-TraceChannels="cpu,gpu,frame"`: Specify channels

#### CSV Profiler

```cpp
// Check if requested
bool RequestsCSVProfiler() const;

// Start/stop profiler
virtual bool TryStartCSVProfiler();
virtual bool TryStartCSVProfiler(FString CSVFileName, const FString& DestinationFolder = FString(), int32 Frames = -1);
bool TryStopCSVProfiler();

// Get output filename
virtual FString GetCSVFilename();

// Set output mode
void SetCSVOutputMode(EAutomatedPerfTestCSVOutputMode NewOutputMode);
EAutomatedPerfTestCSVOutputMode GetCSVOutputMode() const;
```

**CSV Output Modes:**
- `Single`: One CSV for entire session
- `Separate`: One CSV per RunTest/TeardownTest cycle
- `Granular`: Multiple CSVs during test (manual control)

**Commandline:**
- `-CSVProfiler`: Enable CSV profiling

#### FPS Chart

```cpp
bool RequestsFPSChart() const;
bool TryStartFPSChart();
bool TryStopFPSChart();
```

**Commandline:**
- `-FPSChart`: Enable FPS chart generation

#### Video Capture

```cpp
bool RequestsVideoCapture() const;
bool TryStartVideoCapture();
bool TryFinalizingVideoCapture(const bool bStopAutoContinue = false);

// Override to handle completion
virtual void OnVideoRecordingFinalized(bool Succeeded, const FString& FilePath);
```

**Commandline:**
- `-VideoCapture`: Enable video recording

#### Dynamic Resolution Lock

```cpp
bool RequestsLockedDynRes() const;
```

**Commandline:**
- `-LockedDynRes`: Lock dynamic resolution during test

### Utility Methods

#### Test Identification

```cpp
// Get test name (from -TestName)
FString GetTestName();

// Get unique test ID (from -TestID or generated)
virtual FString GetTestID();

// Get device profile (from -DeviceProfile)
FString GetDeviceProfile();

// Get overall region name for profiling
FString GetOverallRegionName();
```

#### World/GameMode Access

```cpp
// Get current game mode
AGameModeBase* GetGameMode() const;

// Get player controller
APlayerController* GetPlayerController();
```

#### Console Commands

```cpp
// Execute console command
void ConsoleCommand(const TCHAR* Cmd);

// Example usage
ConsoleCommand(TEXT("stat fps"));
ConsoleCommand(TEXT("r.ScreenPercentage 100"));
```

#### Screenshots

```cpp
// Take named screenshot
void TakeScreenshot(FString ScreenshotName);
```

### Delegate Management

```cpp
// Override to unbind custom delegates
virtual void UnbindAllDelegates();
```

Always unbind delegates in `UnbindAllDelegates()` and call it in `Exit()`.

### State Management

Inherited from `UGauntletTestController`:

```cpp
// State change notification
virtual void OnStateChange(FName OldState, FName NewState) override;

// Map change notification
virtual void OnPreMapChange() override;

// Tick
virtual void OnTick(float TimeDelta) override;
```

### Ending Tests

```cpp
// End with exit code
void EndAutomatedPerfTest(const int32 ExitCode = 0);

// Convenience methods
void EndTestSuccess();  // Calls EndAutomatedPerfTest(0)
void EndTestFailure();  // Calls EndAutomatedPerfTest(-1)
```

## Common Patterns

### Waiting for Sequence Completion

```cpp
void UMyTest::RunTest()
{
    Super::RunTest();

    // Play sequence
    SequencePlayer->Play();

    // Bind to completion
    SequencePlayer->OnFinished.AddDynamic(this, &UMyTest::OnSequenceFinished);
}

void UMyTest::OnSequenceFinished()
{
    TeardownTest(true);
}
```

### Timer-Based Tests

```cpp
void UMyTest::RunTest()
{
    Super::RunTest();

    // Run for 60 seconds
    GetWorld()->GetTimerManager().SetTimer(
        TestTimerHandle,
        this,
        &UMyTest::OnTestComplete,
        60.0f,
        false
    );
}

void UMyTest::OnTestComplete()
{
    TeardownTest(true);
}
```

### Multi-Map Tests

```cpp
void UMyTest::SetupTest()
{
    Super::SetupTest();

    if (CurrentMapIndex < MapsToTest.Num())
    {
        // Load next map
        FString MapName = MapsToTest[CurrentMapIndex];
        ConsoleCommand(*FString::Printf(TEXT("open %s"), *MapName));
    }
    else
    {
        // All maps tested
        TeardownTest(true);
    }
}

void UMyTest::TeardownTest(bool bExitAfterTeardown)
{
    Super::TeardownTest(false);  // Don't exit yet

    CurrentMapIndex++;

    if (CurrentMapIndex < MapsToTest.Num())
    {
        // Load next map (will call SetupTest again)
        SetupTest();
    }
    else
    {
        // All done, now exit
        Exit();
    }
}
```

### Granular CSV Output

```cpp
void UMyTest::OnInit()
{
    Super::OnInit();
    SetCSVOutputMode(EAutomatedPerfTestCSVOutputMode::Granular);
}

void UMyTest::OnCameraCut(UCameraComponent* Camera)
{
    // Stop previous CSV
    if (bCSVRunning)
    {
        TryStopCSVProfiler();
    }

    // Start new CSV for this camera cut
    FString CSVName = FString::Printf(TEXT("CameraCut_%d"), CameraCutIndex++);
    TryStartCSVProfiler(CSVName);
    bCSVRunning = true;
}
```

## Commandline Reference

Common parameters:

```bash
# Test identification
-TestName=MyTest
-TestID=unique-id-123

# Profiling
-InsightsTrace
-TraceChannels="cpu,gpu,frame,loadtime"
-CSVProfiler
-FPSChart
-VideoCapture
-LockedDynRes

# Device profile
-DeviceProfile=MyProfile

# Test-specific (varies by controller)
-AutomatedPerfTest.SequenceTest.MapSequenceComboName=MyCombo
-AutomatedPerfTest.ReplayTest.ReplayName=MyReplay
```

## Best Practices

1. **Always call Super::Method()** in overrides
2. **Stop profiling in TeardownTest()** before calling Super
3. **Unbind delegates in UnbindAllDelegates()** and Exit()
4. **Use GetTestID()** for unique output filenames
5. **Check RequestsX()** before starting profiling tools
6. **Use timers or delegates** for async operations, not blocking loops
7. **Call TeardownTest(true)** when test completes to trigger exit
8. **Use ConsoleCommand()** for runtime configuration changes
