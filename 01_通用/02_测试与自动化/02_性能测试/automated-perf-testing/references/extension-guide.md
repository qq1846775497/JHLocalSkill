# Extension Guide

Step-by-step guide for extending AutomatedPerfTesting with custom test controllers.

## Quick Start

### 1. Create Test Controller Class

**MyCustomPerfTest.h:**
```cpp
#pragma once

#include "AutomatedPerfTestControllerBase.h"
#include "MyCustomPerfTest.generated.h"

UCLASS()
class MYPROJECT_API UMyCustomPerfTest : public UAutomatedPerfTestControllerBase
{
    GENERATED_BODY()

public:
    virtual void OnInit() override;
    virtual void SetupTest() override;
    virtual void RunTest() override;
    virtual void TeardownTest(bool bExitAfterTeardown = true) override;
    virtual FString GetTestID() override;

private:
    FTimerHandle TestTimerHandle;
    void OnTestComplete();
};
```

**MyCustomPerfTest.cpp:**
```cpp
#include "MyCustomPerfTest.h"

void UMyCustomPerfTest::OnInit()
{
    Super::OnInit();

    // Read custom commandline params
    // Bind delegates
}

void UMyCustomPerfTest::SetupTest()
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

void UMyCustomPerfTest::RunTest()
{
    Super::RunTest();

    // Run test for 60 seconds
    GetWorld()->GetTimerManager().SetTimer(
        TestTimerHandle,
        this,
        &UMyCustomPerfTest::OnTestComplete,
        60.0f,
        false
    );
}

void UMyCustomPerfTest::OnTestComplete()
{
    TeardownTest(true);
}

void UMyCustomPerfTest::TeardownTest(bool bExitAfterTeardown)
{
    // Stop profiling BEFORE Super
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

FString UMyCustomPerfTest::GetTestID()
{
    return TEXT("MyCustomTest");
}
```

### 2. Register with Module

In your module's `.Build.cs`, add dependency:
```csharp
PublicDependencyModuleNames.AddRange(new string[] {
    "AutomatedPerfTesting",
    "Gauntlet"
});
```

### 3. Run Test

```bash
RunUnreal -project=MyProject.uproject \
  -platform=Win64 \
  -TestControllerClass=MyProject.MyCustomPerfTest \
  -InsightsTrace -CSVProfiler
```

## Common Extension Patterns

### Pattern 1: Sequence Playback Test

Test that plays a Level Sequence with profiling.

```cpp
UCLASS()
class UMySequenceTest : public UAutomatedPerfTestControllerBase
{
    GENERATED_BODY()

public:
    virtual void RunTest() override;

private:
    UPROPERTY()
    ALevelSequenceActor* SequenceActor;

    UPROPERTY()
    ULevelSequencePlayer* SequencePlayer;

    UFUNCTION()
    void OnSequenceFinished();
};

void UMySequenceTest::RunTest()
{
    Super::RunTest();

    // Load sequence
    ULevelSequence* Sequence = LoadObject<ULevelSequence>(nullptr, TEXT("/Game/Sequences/MySequence"));

    // Create player
    FMovieSceneSequencePlaybackSettings Settings;
    SequencePlayer = ULevelSequencePlayer::CreateLevelSequencePlayer(
        GetWorld(),
        Sequence,
        Settings,
        SequenceActor
    );

    // Bind completion
    SequencePlayer->OnFinished.AddDynamic(this, &UMySequenceTest::OnSequenceFinished);

    // Play
    SequencePlayer->Play();
}

void UMySequenceTest::OnSequenceFinished()
{
    TeardownTest(true);
}
```

### Pattern 2: Camera Flythrough Test

Test that moves camera through waypoints.

```cpp
UCLASS()
class UCameraFlythroughTest : public UAutomatedPerfTestControllerBase
{
    GENERATED_BODY()

public:
    virtual void RunTest() override;
    virtual void OnTick(float TimeDelta) override;

private:
    TArray<FVector> Waypoints;
    int32 CurrentWaypointIndex = 0;
    float MoveSpeed = 500.0f;
};

void UCameraFlythroughTest::RunTest()
{
    Super::RunTest();

    // Define waypoints
    Waypoints = {
        FVector(0, 0, 200),
        FVector(1000, 0, 200),
        FVector(1000, 1000, 200),
        FVector(0, 1000, 200)
    };

    CurrentWaypointIndex = 0;
}

void UCameraFlythroughTest::OnTick(float TimeDelta)
{
    Super::OnTick(TimeDelta);

    if (CurrentWaypointIndex >= Waypoints.Num())
    {
        TeardownTest(true);
        return;
    }

    APlayerController* PC = GetPlayerController();
    if (!PC) return;

    FVector CurrentPos = PC->GetPawn()->GetActorLocation();
    FVector TargetPos = Waypoints[CurrentWaypointIndex];

    // Move towards waypoint
    FVector Direction = (TargetPos - CurrentPos).GetSafeNormal();
    FVector NewPos = CurrentPos + Direction * MoveSpeed * TimeDelta;

    PC->GetPawn()->SetActorLocation(NewPos);

    // Check if reached
    if (FVector::Dist(NewPos, TargetPos) < 50.0f)
    {
        CurrentWaypointIndex++;
    }
}
```

### Pattern 3: Multi-Map Test

Test that cycles through multiple maps.

```cpp
UCLASS()
class UMultiMapTest : public UAutomatedPerfTestControllerBase
{
    GENERATED_BODY()

public:
    virtual void OnInit() override;
    virtual void SetupTest() override;
    virtual void TeardownTest(bool bExitAfterTeardown) override;

private:
    TArray<FString> MapsToTest;
    int32 CurrentMapIndex = 0;

    void LoadNextMap();
};

void UMultiMapTest::OnInit()
{
    Super::OnInit();

    MapsToTest = {
        TEXT("/Game/Maps/Map1"),
        TEXT("/Game/Maps/Map2"),
        TEXT("/Game/Maps/Map3")
    };
}

void UMultiMapTest::SetupTest()
{
    Super::SetupTest();

    if (CurrentMapIndex < MapsToTest.Num())
    {
        LoadNextMap();
    }
}

void UMultiMapTest::LoadNextMap()
{
    FString MapName = MapsToTest[CurrentMapIndex];

    // Start profiling for this map
    if (RequestsCSVProfiler())
    {
        FString CSVName = FString::Printf(TEXT("Map_%d"), CurrentMapIndex);
        TryStartCSVProfiler(CSVName);
    }

    // Load map
    ConsoleCommand(*FString::Printf(TEXT("open %s"), *MapName));

    // Wait 30 seconds then move to next
    GetWorld()->GetTimerManager().SetTimer(
        TestTimerHandle,
        [this]() { TeardownTest(false); },
        30.0f,
        false
    );
}

void UMultiMapTest::TeardownTest(bool bExitAfterTeardown)
{
    // Stop profiling for current map
    if (RequestsCSVProfiler())
    {
        TryStopCSVProfiler();
    }

    Super::TeardownTest(false);

    CurrentMapIndex++;

    if (CurrentMapIndex < MapsToTest.Num())
    {
        SetupTest();
    }
    else
    {
        Exit();
    }
}
```

### Pattern 4: Stress Test with Spawning

Test that spawns actors to stress the system.

```cpp
UCLASS()
class UStressTest : public UAutomatedPerfTestControllerBase
{
    GENERATED_BODY()

public:
    virtual void RunTest() override;

private:
    int32 NumActorsToSpawn = 1000;
    TArray<AActor*> SpawnedActors;

    void SpawnActors();
};

void UStressTest::RunTest()
{
    Super::RunTest();

    SpawnActors();

    // Run for 60 seconds
    GetWorld()->GetTimerManager().SetTimer(
        TestTimerHandle,
        [this]() { TeardownTest(true); },
        60.0f,
        false
    );
}

void UStressTest::SpawnActors()
{
    UWorld* World = GetWorld();

    for (int32 i = 0; i < NumActorsToSpawn; i++)
    {
        FVector Location = FVector(
            FMath::RandRange(-5000.0f, 5000.0f),
            FMath::RandRange(-5000.0f, 5000.0f),
            100.0f
        );

        FActorSpawnParameters SpawnParams;
        AActor* Actor = World->SpawnActor<AActor>(
            AStaticMeshActor::StaticClass(),
            Location,
            FRotator::ZeroRotator,
            SpawnParams
        );

        SpawnedActors.Add(Actor);
    }
}
```

## Project Settings Integration

### 1. Create Settings Class

```cpp
UCLASS(Config=Engine, DefaultConfig, DisplayName="My Custom Test")
class UMyCustomTestSettings : public UDeveloperSettings
{
    GENERATED_BODY()

public:
    virtual FName GetContainerName() const override { return FName("Project"); }
    virtual FName GetCategoryName() const override { return FName("Plugins"); }

    UPROPERTY(Config, EditAnywhere, Category="Test Settings")
    TArray<FSoftObjectPath> MapsToTest;

    UPROPERTY(Config, EditAnywhere, Category="Test Settings")
    float TestDuration = 60.0f;
};
```

### 2. Access Settings in Controller

```cpp
void UMyCustomPerfTest::OnInit()
{
    Super::OnInit();

    const UMyCustomTestSettings* Settings = GetDefault<UMyCustomTestSettings>();
    TestDuration = Settings->TestDuration;
}
```

## Gauntlet Integration

### 1. Create Config Class (C#)

**MyCustomTestConfig.cs:**
```csharp
public class MyCustomTestConfig : AutomatedPerfTestConfigBase
{
    [AutoParam("")]
    public string MapName = "";

    [AutoParam(60)]
    public int TestDuration = 60;

    public override void ApplyToConfig(UnrealAppConfig AppConfig, UnrealSessionRole ConfigRole, IEnumerable<UnrealSessionRole> OtherRoles)
    {
        base.ApplyToConfig(AppConfig, ConfigRole, OtherRoles);

        AppConfig.CommandLine += $" -MapName={MapName}";
        AppConfig.CommandLine += $" -TestDuration={TestDuration}";
    }
}
```

### 2. Create Test Node (C#)

**MyCustomTestNode.cs:**
```csharp
public class MyCustomTestNode : AutomatedPerfTestNode<MyCustomTestConfig>
{
    public MyCustomTestNode(UnrealTestContext InContext) : base(InContext)
    {
    }

    public override MyCustomTestConfig GetConfiguration()
    {
        MyCustomTestConfig Config = base.GetConfiguration() as MyCustomTestConfig;
        Config.TestControllerClass = "MyProject.MyCustomPerfTest";
        return Config;
    }
}
```

### 3. Run via UAT

```bash
RunUnreal -project=MyProject.uproject \
  -test=MyCustomTest \
  -MapName=MyMap \
  -TestDuration=120 \
  -InsightsTrace
```

## Troubleshooting

**Controller not found:**
- Verify module dependency in `.Build.cs`
- Check class name matches `-TestControllerClass` parameter
- Ensure `UCLASS()` macro is present

**Profiling not working:**
- Call `TryStartX()` in `SetupTest()` or `RunTest()`
- Call `TryStopX()` in `TeardownTest()` BEFORE `Super::TeardownTest()`
- Pass commandline flags (`-InsightsTrace`, `-CSVProfiler`)

**Test never exits:**
- Ensure `TeardownTest(true)` is called when test completes
- Check timer/delegate callbacks are firing
- Verify no infinite loops in `OnTick()`

**CSV files empty:**
- Ensure sufficient time between start/stop (at least 1 frame)
- Check CSV output mode matches expectations
- Verify write permissions on output directory
