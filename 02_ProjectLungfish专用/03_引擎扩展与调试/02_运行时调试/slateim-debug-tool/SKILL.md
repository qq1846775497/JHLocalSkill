---
name: slateim-debug-tool
description: "Complete workflow for creating and modifying SlateIM-based debug tools in Unreal Engine ProjectLungfish. Use when user requests: (1) Adding new SlateIM debug pages/tools, (2) Modifying existing debug tool architecture, (3) Creating hierarchical debug interfaces, (4) Implementing tool registration systems. Covers three-layer architecture (Window/Container, Tool Interface, Tool Implementation), proper navigation patterns, and SlateIM integration best practices."
---

# SlateIM Debug Tool Development

Complete workflow for creating SlateIM-based debug tools in the ProjectLungfish Unreal Engine project following the established three-layer architecture pattern.

## Core Architecture Principles

**Design Principle**: "Window只负责'容器与调度', Tool只负责'内容与状态'"
- **Window/Container**: Handles tool dispatch, navigation, and lifecycle
- **Tool Interface**: Defines tool contract and metadata
- **Tool Implementation**: Contains actual debug functionality and state

**Navigation Pattern**: Hierarchical layer separation
- **Hub View**: Tool selection interface (no active tool)
- **Tool View**: Full tool content (hub hidden, focused experience)
- **Back Navigation**: Clear return path via "← Back to Hub" button

## File Organization

```
Main/Plugins/GASExtendedPL/Source/GASExtendedPL/
├── Public/Debug/
│   ├── PLDebugWindow.h                    # Main container (TUniquePtr singleton)
│   ├── Core/
│   │   ├── IPLDebugTool.h                 # Tool interface
│   │   ├── PLDebugToolRegistry.h          # Registry singleton
│   │   └── PLDebugToolItem.h              # Tree structure
│   └── Tools/
│       ├── System/
│       │   ├── PLPerformanceDebugTool.h
│       │   └── PLGameStateDebugTool.h
│       └── Audio/
│           └── PLAudioDebugTool.h
└── Private/Debug/
    └── (matching .cpp files)
```

## Step-by-Step Workflow

### Step 1: Create Tool Header

Create header in `Public/Debug/Tools/<Category>/<ToolName>.h`:

```cpp
#pragma once

#include "CoreMinimal.h"
#include "Debug/Core/IPLDebugTool.h"

class GASEXTENDEDPL_API F<ToolName>DebugTool
    : public IPLDebugTool
    , public TSharedFromThis<F<ToolName>DebugTool>  // CRITICAL: Required for timer delegates
{
public:
    F<ToolName>DebugTool();
    virtual ~F<ToolName>DebugTool();

    // IPLDebugTool interface - ALL REQUIRED
    virtual FName GetToolId() const override;
    virtual FText GetDisplayName() const override;
    virtual FName GetCategory() const override;
    virtual int32 GetPriority() const override;
    virtual TSharedRef<SWidget> BuildWidget() override;
    virtual void DrawSlateIMContent() override;  // CRITICAL: SlateIM display
    virtual void OnActivated() override;
    virtual void OnDeactivated() override;

private:
    // Tool-specific state
    FTimerHandle UpdateTimerHandle;
    // ... other members
};
```

**CRITICAL Requirements**:
- Inherit from `TSharedFromThis<YourClass>` for timer delegate support
- Implement `DrawSlateIMContent()` for SlateIM display (NOT just BuildWidget)
- Use `AsShared()` in timer delegate creation

### Step 2: Implement Tool Logic

Create implementation in `Private/Debug/Tools/<Category>/<ToolName>.cpp`:

```cpp
#include "Debug/Tools/<Category>/<ToolName>.h"
#include "Engine/Engine.h"
#include "TimerManager.h"
#include "SlateIM.h"  // CRITICAL: Required for DrawSlateIMContent

F<ToolName>DebugTool::F<ToolName>DebugTool()
{
}

FName F<ToolName>DebugTool::GetToolId() const
{
    return "<ToolName>";
}

FText F<ToolName>DebugTool::GetDisplayName() const
{
    return FText::FromString(TEXT("<Display Name>"));
}

FName F<ToolName>DebugTool::GetCategory() const
{
    return "<Category>";  // e.g., "System", "Audio", "Gameplay"
}

int32 F<ToolName>DebugTool::GetPriority() const
{
    return 10;  // Lower = higher priority in category
}

void F<ToolName>DebugTool::OnActivated()
{
    // Start timers, bind delegates
    if (GEngine && GEngine->GetWorld())
    {
        GEngine->GetWorld()->GetTimerManager().SetTimer(
            UpdateTimerHandle,
            FTimerDelegate::CreateSP(AsShared(), &F<ToolName>DebugTool::UpdateData),
            0.5f,  // Update interval
            true   // Looping
        );
    }
}

void F<ToolName>DebugTool::OnDeactivated()
{
    // Clear timers, unbind delegates
    if (GEngine && GEngine->GetWorld() && UpdateTimerHandle.IsValid())
    {
        GEngine->GetWorld()->GetTimerManager().ClearTimer(UpdateTimerHandle);
    }
}

void F<ToolName>DebugTool::DrawSlateIMContent()
{
    // CRITICAL: This is the MAIN display method for SlateIM interface

    SlateIM::Text(TEXT("=== Section Header ==="));
    SlateIM::Spacer(FVector2D(0, 5));

    // Display data
    SlateIM::Text(FString::Printf(TEXT("Value: %.2f"), SomeValue));

    // Horizontal layout for buttons
    SlateIM::BeginHorizontalStack();
    if (SlateIM::Button(TEXT("Action Button")))
    {
        // Handle button click
        UE_LOG(LogTemp, Log, TEXT("Button clicked"));
    }
    SlateIM::EndHorizontalStack();

    SlateIM::Spacer(FVector2D(0, 10));
}

TSharedRef<SWidget> F<ToolName>DebugTool::BuildWidget()
{
    // Optional: For independent window support
    // Can return placeholder or full Slate widget hierarchy
    return SNew(STextBlock).Text(FText::FromString(TEXT("Tool Content")));
}
```

### Step 3: Register Tool

Add to `PLDebugWindow::RegisterGlobalTools()` in `PLDebugWindow.cpp`:

```cpp
#include "Debug/Tools/<Category>/<ToolName>.h"

void FPLDebugWindow::RegisterGlobalTools()
{
    FPLDebugToolRegistry& Registry = FPLDebugToolRegistry::Get();

    // Existing registrations...

    // Register new tool
    Registry.RegisterTool(MakeShared<F<ToolName>DebugTool>());

    RefreshToolList();
}
```

### Step 4: Test and Validate

1. **Build project** to ensure compilation
2. **Launch game** and open console (~)
3. **Test commands**:
   - `PL.Debug.Show` - Open debug window
   - `PL.Debug.ListTools` - Verify tool appears
   - `PL.Debug.ShowTool <ToolName>` - Direct activation
4. **Verify navigation**:
   - Tool button appears in hub
   - Clicking activates tool (hub hides)
   - "← Back to Hub" returns to selection
   - Tool data updates in real-time

## Common Patterns

### Pattern 1: Real-time Data Display

```cpp
void DrawSlateIMContent() override
{
    // Section header
    SlateIM::Text(TEXT("=== Performance Metrics ==="));
    SlateIM::Spacer(FVector2D(0, 5));

    // Dynamic data (updates via timer)
    SlateIM::Text(FString::Printf(TEXT("FPS: %.1f"), CurrentFPS));
    SlateIM::Text(FString::Printf(TEXT("Frame Time: %.2f ms"), FrameTime));
}
```

### Pattern 2: Interactive Controls

```cpp
void DrawSlateIMContent() override
{
    SlateIM::Text(TEXT("=== Controls ==="));

    SlateIM::BeginHorizontalStack();
    if (SlateIM::Button(TEXT("Force GC")))
    {
        if (GEngine)
        {
            GEngine->ForceGarbageCollection(true);
        }
    }
    if (SlateIM::Button(TEXT("Reset Stats")))
    {
        ResetData();
    }
    SlateIM::EndHorizontalStack();
}
```

### Pattern 3: Multi-Section Layout

```cpp
void DrawSlateIMContent() override
{
    // Section 1
    SlateIM::Text(TEXT("=== Section 1 ==="));
    SlateIM::Spacer(FVector2D(0, 5));
    // ... section 1 content

    SlateIM::Spacer(FVector2D(0, 10));

    // Section 2
    SlateIM::Text(TEXT("=== Section 2 ==="));
    SlateIM::Spacer(FVector2D(0, 5));
    // ... section 2 content
}
```

## Critical Implementation Notes

### ✅ DO

1. **Inherit from TSharedFromThis** - Required for timer delegates
2. **Implement DrawSlateIMContent()** - Primary display method
3. **Use AsShared() for delegates** - Not `this` pointer
4. **Clear timers in OnDeactivated()** - Prevent memory leaks
5. **Test navigation flow** - Hub → Tool → Back to Hub
6. **Include SlateIM.h** - Required for SlateIM calls

### ❌ DON'T

1. **Don't use `this` in CreateSP()** - Use `AsShared()` instead
2. **Don't skip DrawSlateIMContent()** - BuildWidget alone is insufficient
3. **Don't show hub and tool together** - Maintain layer separation
4. **Don't forget OnDeactivated cleanup** - Timers must be cleared
5. **Don't auto-show window** - Wait for user activation
6. **Don't mix retained-mode Slate with SlateIM** - Use SlateIM primitives

## Console Commands

- `PL.Debug.Show` - Show debug window (hub view)
- `PL.Debug.Hide` - Hide debug window
- `PL.Debug.Toggle` - Toggle debug window visibility
- `PL.Debug.ShowTool <ToolName>` - Show window with specific tool active
- `PL.Debug.ListTools` - List all registered tools

## Troubleshooting

**Problem**: Timer delegate compilation error "AsShared is not a member"
- **Solution**: Add `public TSharedFromThis<YourClass>` to class inheritance

**Problem**: Tool content not showing, just placeholder text
- **Solution**: Implement `DrawSlateIMContent()` method in your tool

**Problem**: Hub buttons still visible when tool active
- **Solution**: Check PLDebugWindow.cpp DrawWindow() - should hide hub in tool view

**Problem**: Tool data not updating
- **Solution**: Verify timer is started in OnActivated() and cleared in OnDeactivated()

**Problem**: Crash when switching tools
- **Solution**: Clear all timers and delegates in OnDeactivated()

## Reference Files

- **Architecture Details**: See [references/architecture.md](references/architecture.md) for complete three-layer design
- **SlateIM API**: See [references/slateim-api.md](references/slateim-api.md) for available SlateIM primitives
- **Example Tools**: See [references/example-tools.md](references/example-tools.md) for complete reference implementations

## Integration with PLGameInstance

Debug window lifecycle is managed in PLGameInstance:

```cpp
// In Init()
DebugWindow = MakeUnique<FPLDebugWindow>();  // No auto-show

// In Shutdown()
if (DebugWindow.IsValid())
{
    DebugWindow->Hide();
    DebugWindow.Reset();
}
```

Window appears only when user activates via console commands.