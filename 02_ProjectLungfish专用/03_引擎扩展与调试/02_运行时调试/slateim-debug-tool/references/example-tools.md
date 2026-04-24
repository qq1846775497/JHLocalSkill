# Example Tool Implementations

Complete reference implementations of debug tools demonstrating different patterns and complexity levels.

## Simple Tool: Performance Debug Tool

**Characteristics**: Single-page, real-time data display, basic controls

### Header (PLPerformanceDebugTool.h)

```cpp
// Copyright Cyan Cook. All Right Reserved. 2023

#pragma once

#include "CoreMinimal.h"
#include "Debug/Core/IPLDebugTool.h"

/**
 * Performance Debug Tool - Shows FPS, frame time, memory usage, and performance controls
 * Simple single-page tool example
 */
class GASEXTENDEDPL_API FPLPerformanceDebugTool
    : public IPLDebugTool
    , public TSharedFromThis<FPLPerformanceDebugTool>
{
public:
    FPLPerformanceDebugTool();
    virtual ~FPLPerformanceDebugTool();

    // IPLDebugTool interface
    virtual FName GetToolId() const override;
    virtual FText GetDisplayName() const override;
    virtual FName GetCategory() const override;
    virtual int32 GetPriority() const override;
    virtual TSharedRef<SWidget> BuildWidget() override;
    virtual void DrawSlateIMContent() override;
    virtual void OnActivated() override;
    virtual void OnDeactivated() override;

private:
    void UpdatePerformanceData(float DeltaTime);

    float CurrentFPS = 0.0f;
    float FrameTime = 0.0f;
    FTimerHandle UpdateTimerHandle;
};
```

### Implementation (PLPerformanceDebugTool.cpp)

```cpp
// Copyright Cyan Cook. All Right Reserved. 2023

#include "Debug/Tools/System/PLPerformanceDebugTool.h"
#include "Engine/Engine.h"
#include "HAL/PlatformMemory.h"
#include "RenderingThread.h"
#include "TimerManager.h"
#include "SlateIM.h"

FPLPerformanceDebugTool::FPLPerformanceDebugTool()
{
}

FPLPerformanceDebugTool::~FPLPerformanceDebugTool()
{
}

FName FPLPerformanceDebugTool::GetToolId() const
{
    return "Performance";
}

FText FPLPerformanceDebugTool::GetDisplayName() const
{
    return FText::FromString(TEXT("Performance"));
}

FName FPLPerformanceDebugTool::GetCategory() const
{
    return "System";
}

int32 FPLPerformanceDebugTool::GetPriority() const
{
    return 10;  // High priority in System category
}

void FPLPerformanceDebugTool::OnActivated()
{
    // Start update timer
    if (GEngine && GEngine->GetWorld())
    {
        GEngine->GetWorld()->GetTimerManager().SetTimer(
            UpdateTimerHandle,
            FTimerDelegate::CreateSP(AsShared(), &FPLPerformanceDebugTool::UpdatePerformanceData, 0.5f),
            0.5f,
            true
        );
    }

    UE_LOG(LogTemp, Log, TEXT("PLPerformanceDebugTool: Activated"));
}

void FPLPerformanceDebugTool::OnDeactivated()
{
    // Clear update timer
    if (GEngine && GEngine->GetWorld() && UpdateTimerHandle.IsValid())
    {
        GEngine->GetWorld()->GetTimerManager().ClearTimer(UpdateTimerHandle);
    }

    UE_LOG(LogTemp, Log, TEXT("PLPerformanceDebugTool: Deactivated"));
}

void FPLPerformanceDebugTool::UpdatePerformanceData(float DeltaTime)
{
    // Calculate FPS
    CurrentFPS = 1.0f / DeltaTime;

    // Calculate frame time in milliseconds
    FrameTime = DeltaTime * 1000.0f;
}

void FPLPerformanceDebugTool::DrawSlateIMContent()
{
    // Performance metrics section
    SlateIM::Text(TEXT("=== Performance Metrics ==="));
    SlateIM::Spacer(FVector2D(0, 5));

    SlateIM::Text(FString::Printf(TEXT("FPS: %.1f"), CurrentFPS));
    SlateIM::Text(FString::Printf(TEXT("Frame Time: %.2f ms"), FrameTime));

    SlateIM::Spacer(FVector2D(0, 10));
    SlateIM::Text(TEXT("=== Memory Information ==="));
    SlateIM::Spacer(FVector2D(0, 5));

    FPlatformMemoryStats MemStats = FPlatformMemory::GetStats();
    SlateIM::Text(FString::Printf(TEXT("Used Memory: %.2f MB"),
        MemStats.UsedPhysical / (1024.0f * 1024.0f)));
    SlateIM::Text(FString::Printf(TEXT("Available Memory: %.2f MB"),
        MemStats.AvailablePhysical / (1024.0f * 1024.0f)));

    SlateIM::Spacer(FVector2D(0, 10));
    SlateIM::Text(TEXT("=== Performance Controls ==="));
    SlateIM::Spacer(FVector2D(0, 5));

    SlateIM::BeginHorizontalStack();
    if (SlateIM::Button(TEXT("Force GC")))
    {
        if (GEngine)
        {
            GEngine->ForceGarbageCollection(true);
            UE_LOG(LogTemp, Log, TEXT("PLPerformanceDebugTool: Forced garbage collection"));
        }
    }
    if (SlateIM::Button(TEXT("Flush Rendering")))
    {
        FlushRenderingCommands();
        UE_LOG(LogTemp, Log, TEXT("PLPerformanceDebugTool: Flushed rendering commands"));
    }
    SlateIM::EndHorizontalStack();

    SlateIM::Spacer(FVector2D(0, 10));
    SlateIM::Text(TEXT("=== Thread Information ==="));
    SlateIM::Spacer(FVector2D(0, 5));

    SlateIM::Text(FString::Printf(TEXT("Rendering Thread: %s"),
        IsInRenderingThread() ? TEXT("YES") : TEXT("NO")));
    SlateIM::Text(FString::Printf(TEXT("Game Thread: %s"),
        IsInGameThread() ? TEXT("YES") : TEXT("NO")));
}

TSharedRef<SWidget> FPLPerformanceDebugTool::BuildWidget()
{
    // Placeholder for independent window support
    return SNew(STextBlock)
        .Text(FText::FromString(TEXT("Performance Tool")));
}
```

## Medium Complexity: Game State Debug Tool

**Characteristics**: Game world interaction, dynamic player data, game controls

### Key Implementation Patterns

```cpp
void FPLGameStateDebugTool::DrawSlateIMContent()
{
    // Game information section
    SlateIM::Text(TEXT("=== Game Information ==="));
    SlateIM::Spacer(FVector2D(0, 5));

    SlateIM::Text(FString::Printf(TEXT("Level: %s"), *CurrentLevelName));
    SlateIM::Text(FString::Printf(TEXT("Game Mode: %s"), *CurrentGameModeName));
    SlateIM::Text(FString::Printf(TEXT("Player Count: %d"), PlayerCount));

    SlateIM::Spacer(FVector2D(0, 10));
    SlateIM::Text(TEXT("=== Player Information ==="));
    SlateIM::Spacer(FVector2D(0, 5));

    // Real-time player info query
    if (UWorld* World = GEngine->GetCurrentPlayWorld())
    {
        if (APawn* PlayerPawn = World->GetFirstPlayerController() ?
            World->GetFirstPlayerController()->GetPawn() : nullptr)
        {
            FVector Location = PlayerPawn->GetActorLocation();
            FRotator Rotation = PlayerPawn->GetActorRotation();
            FVector Velocity = PlayerPawn->GetVelocity();

            SlateIM::Text(FString::Printf(TEXT("Player Location: X=%.1f Y=%.1f Z=%.1f"),
                Location.X, Location.Y, Location.Z));
            SlateIM::Text(FString::Printf(TEXT("Player Rotation: Pitch=%.1f Yaw=%.1f Roll=%.1f"),
                Rotation.Pitch, Rotation.Yaw, Rotation.Roll));
            SlateIM::Text(FString::Printf(TEXT("Player Velocity: %.2f units/s"),
                Velocity.Size()));
        }
    }

    SlateIM::Spacer(FVector2D(0, 10));
    SlateIM::Text(TEXT("=== Game Controls ==="));
    SlateIM::Spacer(FVector2D(0, 5));

    // Interactive game controls
    SlateIM::BeginHorizontalStack();
    FString PauseButtonText = GetPauseButtonText().ToString();
    if (SlateIM::Button(*PauseButtonText))
    {
        if (UWorld* World = GEngine->GetCurrentPlayWorld())
        {
            APlayerController* PC = World->GetFirstPlayerController();
            if (PC)
            {
                PC->SetPause(!PC->IsPaused());
                UE_LOG(LogTemp, Log, TEXT("PLGameStateDebugTool: Game %s"),
                    PC->IsPaused() ? TEXT("paused") : TEXT("unpaused"));
            }
        }
    }

    if (SlateIM::Button(TEXT("Reload Level")))
    {
        if (UWorld* World = GEngine->GetCurrentPlayWorld())
        {
            World->ServerTravel(World->GetMapName());
            UE_LOG(LogTemp, Log, TEXT("PLGameStateDebugTool: Reloading level"));
        }
    }
    SlateIM::EndHorizontalStack();
}
```

**Key Patterns Used**:
- Real-time world queries in DrawSlateIMContent()
- Conditional rendering based on world state
- Dynamic button text based on game state
- Multiple control types (pause, reload)

## Complex Tool: Audio Debug Tool

**Characteristics**: Multi-section layout, simulated multi-tab structure, complex data display

### Key Implementation Patterns

```cpp
void FPLAudioDebugTool::DrawSlateIMContent()
{
    // Quick stats header - Horizontal layout
    SlateIM::Text(TEXT("=== Audio Debug Tool - Multi-Tab Example ==="));
    SlateIM::Spacer(FVector2D(0, 5));

    SlateIM::BeginHorizontalStack();
    SlateIM::Text(FString::Printf(TEXT("Events: %d"), ActiveEventsCount));
    SlateIM::Text(FString::Printf(TEXT("Sources: %d"), ActiveSourcesCount));
    SlateIM::Text(FString::Printf(TEXT("Memory: %.1f MB"), AudioMemoryUsage));
    SlateIM::EndHorizontalStack();

    // Section 1: Audio Events
    SlateIM::Spacer(FVector2D(0, 10));
    SlateIM::Text(TEXT("=== Audio Events ==="));
    SlateIM::Spacer(FVector2D(0, 5));

    SlateIM::Text(TEXT("This section shows active Wwise events"));
    SlateIM::Text(FString::Printf(TEXT("Current active events: %d"), ActiveEventsCount));

    if (SlateIM::Button(TEXT("Stop All Audio")))
    {
        UE_LOG(LogTemp, Log, TEXT("PLAudioDebugTool: Stop all audio requested"));
    }

    // Section 2: Audio Sources
    SlateIM::Spacer(FVector2D(0, 10));
    SlateIM::Text(TEXT("=== Audio Sources ==="));
    SlateIM::Spacer(FVector2D(0, 5));

    SlateIM::Text(TEXT("This section shows 3D positioned audio sources"));
    SlateIM::Text(FString::Printf(TEXT("Active sources: %d"), ActiveSourcesCount));

    // Section 3: Audio Memory
    SlateIM::Spacer(FVector2D(0, 10));
    SlateIM::Text(TEXT("=== Audio Memory ==="));
    SlateIM::Spacer(FVector2D(0, 5));

    SlateIM::Text(FString::Printf(TEXT("Memory Usage: %.2f MB"), AudioMemoryUsage));
    SlateIM::Text(FString::Printf(TEXT("CPU Usage: %.2f%%"), AudioCPUUsage));

    if (SlateIM::Button(TEXT("Reset Audio Stats")))
    {
        ActiveEventsCount = 0;
        ActiveSourcesCount = 0;
        AudioMemoryUsage = 0.0f;
        AudioCPUUsage = 0.0f;
        UE_LOG(LogTemp, Log, TEXT("PLAudioDebugTool: Audio stats reset"));
    }
}
```

**Key Patterns Used**:
- Multi-section organization for complex data
- Horizontal summary statistics at top
- Multiple data categories (events, sources, memory)
- Section-specific controls
- Support for independent window mode (SupportIndependentWindow() = true)

## Tool Registration Pattern

All tools follow the same registration pattern in PLDebugWindow.cpp:

```cpp
void FPLDebugWindow::RegisterGlobalTools()
{
    FPLDebugToolRegistry& Registry = FPLDebugToolRegistry::Get();

    // Register system tools
    Registry.RegisterTool(MakeShared<FPLPerformanceDebugTool>());
    Registry.RegisterTool(MakeShared<FPLGameStateDebugTool>());

    // Register audio tools
    Registry.RegisterTool(MakeShared<FPLAudioDebugTool>());

    // Refresh tool list to show newly registered tools
    RefreshToolList();

    UE_LOG(LogTemp, Log, TEXT("PLDebugWindow: Global tools registration complete"));
}
```

## Common Implementation Patterns

### Pattern 1: Cached Data with Timer Updates

```cpp
class FMyDebugTool : public IPLDebugTool, public TSharedFromThis<FMyDebugTool>
{
private:
    // Cached data (updated by timer)
    float CachedValue1 = 0.0f;
    float CachedValue2 = 0.0f;
    FTimerHandle UpdateTimerHandle;

    void UpdateData()
    {
        // Expensive calculation happens here
        CachedValue1 = CalculateExpensiveValue1();
        CachedValue2 = CalculateExpensiveValue2();
    }

public:
    void OnActivated() override
    {
        GEngine->GetWorld()->GetTimerManager().SetTimer(
            UpdateTimerHandle,
            FTimerDelegate::CreateSP(AsShared(), &FMyDebugTool::UpdateData),
            0.5f,  // Update every 0.5 seconds
            true
        );
    }

    void DrawSlateIMContent() override
    {
        // Fast - just display cached data
        SlateIM::Text(FString::Printf(TEXT("Value 1: %.2f"), CachedValue1));
        SlateIM::Text(FString::Printf(TEXT("Value 2: %.2f"), CachedValue2));
    }
};
```

### Pattern 2: Direct World Queries

```cpp
void DrawSlateIMContent() override
{
    if (UWorld* World = GEngine->GetCurrentPlayWorld())
    {
        // Safe to query world directly for UI
        APawn* PlayerPawn = World->GetFirstPlayerController()->GetPawn();
        if (PlayerPawn)
        {
            FVector Location = PlayerPawn->GetActorLocation();
            SlateIM::Text(FString::Printf(TEXT("Location: %s"),
                *Location.ToString()));
        }
    }
}
```

### Pattern 3: Section-Based Organization

```cpp
void DrawSlateIMContent() override
{
    DrawHeaderSection();
    SlateIM::Spacer(FVector2D(0, 10));

    DrawDataSection();
    SlateIM::Spacer(FVector2D(0, 10));

    DrawControlsSection();
}

void DrawHeaderSection()
{
    SlateIM::Text(TEXT("=== Header ==="));
    SlateIM::Spacer(FVector2D(0, 5));
    // Header content...
}

void DrawDataSection()
{
    SlateIM::Text(TEXT("=== Data ==="));
    SlateIM::Spacer(FVector2D(0, 5));
    // Data content...
}

void DrawControlsSection()
{
    SlateIM::Text(TEXT("=== Controls ==="));
    SlateIM::Spacer(FVector2D(0, 5));
    // Control content...
}
```

## Build.cs Consideration

Ensure SlateIM module is included:

```cpp
PublicDependencyModuleNames.AddRange(
    new string[]
    {
        "Core",
        "Engine",
        "Slate",
        "SlateCore",
        "SlateIM",  // REQUIRED for debug tools
        // ... other modules
    }
);
```