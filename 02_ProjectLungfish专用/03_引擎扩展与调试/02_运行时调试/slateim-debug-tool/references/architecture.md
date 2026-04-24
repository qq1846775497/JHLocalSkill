# Three-Layer Architecture Design

Complete architectural design for the SlateIM debug system following the principle: "Window只负责'容器与调度', Tool只负责'内容与状态'"

## Layer 1: Window/Container (FPLDebugWindow)

**Responsibility**: Pure container and dispatcher - NO content logic

### Key Responsibilities

1. **Tool Registry Access**: Query registered tools from FPLDebugToolRegistry
2. **Tool Tree Building**: Organize tools by category with priority sorting
3. **Navigation Management**: Switch between hub view and tool view
4. **Tool Lifecycle**: Call OnActivated()/OnDeactivated() on tool transitions
5. **Console Command Integration**: Register and handle console commands

### Implementation Pattern

```cpp
class FPLDebugWindow : public FSlateIMWindowBase
{
private:
    TArray<TSharedRef<FPLDebugToolItem>> ToolTreeItems;  // Tool organization
    IPLDebugTool* CurrentActiveTool = nullptr;            // Active tool pointer

public:
    void DrawWindow(float DeltaTime) override
    {
        if (CurrentActiveTool)
        {
            // Tool View - Hub HIDDEN
            DrawToolViewNavigation();
            DrawActiveToolContent();
        }
        else
        {
            // Hub View - Tool selection
            DrawHubView();
        }
    }
};
```

### Navigation Flow

```
Hub View (CurrentActiveTool == nullptr):
┌─────────────────────────────────────┐
│ ProjectLungfish Debug Hub           │
│ Available Tools: 3                  │
│                                     │
│ === System ===                      │
│ [Performance]  [Game State]         │
│                                     │
│ === Audio ===                       │
│ [Audio Debug]                       │
│                                     │
│ Console Commands: ...               │
└─────────────────────────────────────┘

            ↓ User clicks "Performance"
            ↓ ActivateTool("Performance")
            ↓

Tool View (CurrentActiveTool != nullptr):
┌─────────────────────────────────────┐
│ [← Back to Hub] Debug Tool: Performance
│                                     │
│ === Performance Metrics ===         │
│ FPS: 60.0                          │
│ Frame Time: 16.67 ms               │
│                                     │
│ [Force GC] [Flush Rendering]       │
│ ...                                │
└─────────────────────────────────────┘

            ↓ User clicks "← Back to Hub"
            ↓ CurrentActiveTool->OnDeactivated()
            ↓ CurrentActiveTool = nullptr
            ↓

Back to Hub View
```

## Layer 2: Tool Interface (IPLDebugTool)

**Responsibility**: Define tool contract and metadata

### Interface Definition

```cpp
class IPLDebugTool
{
public:
    // Identification
    virtual FName GetToolId() const = 0;           // Unique ID
    virtual FText GetDisplayName() const = 0;      // UI display name
    virtual FName GetCategory() const = 0;         // Category for grouping
    virtual int32 GetPriority() const = 0;         // Sort order (lower = higher)

    // Content Rendering
    virtual TSharedRef<SWidget> BuildWidget() = 0;      // Slate widget (optional)
    virtual void DrawSlateIMContent() {}                // SlateIM display (REQUIRED)

    // Lifecycle
    virtual void OnActivated() {}                  // Tool becomes active
    virtual void OnDeactivated() {}                // Tool becomes inactive
    virtual void OnToolRegistered() {}             // One-time init
    virtual void OnToolUnregistered() {}           // Final cleanup

    // Advanced Features
    virtual bool SupportIndependentWindow() const { return false; }
    virtual TSharedPtr<FSlateIMWindowBase> CreateIndependentWindow() { return nullptr; }
};
```

### Tool Metadata

- **ToolId**: Machine-readable unique identifier (e.g., "Performance", "AudioDebug")
- **DisplayName**: Human-readable name shown in UI (e.g., "Performance Debug", "Audio Debug Tool")
- **Category**: Grouping for organization (e.g., "System", "Audio", "Gameplay")
- **Priority**: Sort order within category (10, 20, 30... lower = higher priority)

## Layer 3: Tool Implementation

**Responsibility**: Actual debug functionality and state management

### Implementation Requirements

1. **Inherit from TSharedFromThis**: Required for timer delegate support
2. **Implement DrawSlateIMContent()**: Primary display method for SlateIM
3. **Manage State**: Track tool-specific data and update it
4. **Handle Lifecycle**: Properly start/stop timers and delegates
5. **Provide Content**: Display data and interactive controls

### Example Implementation

```cpp
class FPLPerformanceDebugTool
    : public IPLDebugTool
    , public TSharedFromThis<FPLPerformanceDebugTool>  // CRITICAL
{
private:
    // State
    float CurrentFPS = 0.0f;
    float FrameTime = 0.0f;
    FTimerHandle UpdateTimerHandle;

public:
    void OnActivated() override
    {
        // Start real-time updates
        GEngine->GetWorld()->GetTimerManager().SetTimer(
            UpdateTimerHandle,
            FTimerDelegate::CreateSP(AsShared(), &FPLPerformanceDebugTool::UpdateData),
            0.5f, true
        );
    }

    void OnDeactivated() override
    {
        // CRITICAL: Cleanup
        if (UpdateTimerHandle.IsValid())
        {
            GEngine->GetWorld()->GetTimerManager().ClearTimer(UpdateTimerHandle);
        }
    }

    void DrawSlateIMContent() override
    {
        // Display current state
        SlateIM::Text(FString::Printf(TEXT("FPS: %.1f"), CurrentFPS));
        SlateIM::Text(FString::Printf(TEXT("Frame Time: %.2f ms"), FrameTime));
    }
};
```

## Component Interactions

### Tool Registration Flow

```
1. PLGameInstance::Init()
   ↓
2. DebugWindow = MakeUnique<FPLDebugWindow>()
   ↓
3. RegisterGlobalTools()
   ↓
4. Registry.RegisterTool(MakeShared<FPLPerformanceDebugTool>())
   ↓
5. Tool→OnToolRegistered()
   ↓
6. RefreshToolList() → BuildToolTree()
```

### Tool Activation Flow

```
1. User clicks tool button OR console command
   ↓
2. FPLDebugWindow::ActivateTool(ToolId)
   ↓
3. Find tool in registry
   ↓
4. Deactivate current tool (if any)
   ↓
5. CurrentActiveTool = NewTool
   ↓
6. NewTool→OnActivated()
   ↓
7. Next frame: DrawWindow() shows tool view
```

### Tool Rendering Flow

```
1. DrawWindow(DeltaTime) called each frame
   ↓
2. if (CurrentActiveTool) → Tool View
   ├─ DrawToolViewNavigation()
   └─ DrawActiveToolContent()
      └─ CurrentActiveTool→DrawSlateIMContent()
   ↓
3. else → Hub View
   └─ DrawHubView()
      ├─ Show tool categories
      └─ Show tool buttons
```

## Design Patterns

### Pattern 1: Singleton Registry

FPLDebugToolRegistry provides centralized tool management:

```cpp
class FPLDebugToolRegistry
{
public:
    static FPLDebugToolRegistry& Get();  // Thread-safe singleton

    void RegisterTool(TSharedRef<IPLDebugTool> Tool);
    void UnregisterTool(FName ToolId);
    IPLDebugTool* FindTool(FName ToolId) const;

    void GetAllTools(TArray<IPLDebugTool*>& OutTools) const;
};
```

### Pattern 2: Hierarchical Tool Tree

FPLDebugToolItem provides category-based organization:

```cpp
struct FPLDebugToolItem
{
    FName ToolId;
    FText DisplayName;
    FName Category;
    bool bIsCategory;
    TArray<TSharedRef<FPLDebugToolItem>> Children;  // Recursive structure
};
```

### Pattern 3: TUniquePtr Singleton Window

PLGameInstance owns the debug window as unique pointer:

```cpp
class UPLGameInstance
{
private:
    TUniquePtr<FPLDebugWindow> DebugWindow;  // Globally unique
};
```

## Key Architectural Decisions

### Why TUniquePtr for Window?

- **Global Uniqueness**: Only one main debug window should exist
- **Clear Ownership**: PLGameInstance owns the window lifecycle
- **No Sharing**: Window doesn't need to be shared between systems

### Why TSharedPtr for Tools?

- **Shared Ownership**: Registry and window both reference tools
- **Lifecycle Management**: Tools may outlive individual references
- **Delegate Support**: TSharedFromThis enables CreateSP for timers

### Why Separate DrawSlateIMContent()?

- **SlateIM Requirement**: SlateIM is immediate-mode, requires function calls each frame
- **BuildWidget Alternative**: BuildWidget returns Slate widget (retained-mode)
- **Both Supported**: Tools can provide both for flexibility

### Why Hide Hub When Tool Active?

- **Focused Experience**: Tool gets full window space without distraction
- **Clear Navigation**: Explicit back button makes navigation obvious
- **Layer Separation**: Maintains clean architectural boundaries

## Performance Considerations

1. **Tool Activation**: Only active tool receives OnActivated() and updates
2. **Timer Efficiency**: Each tool manages its own update frequency
3. **Lazy Loading**: Tools only allocated when registered, not on every frame
4. **Registry Caching**: Tool tree built once, reused across frames

## Extension Points

1. **New Categories**: Add new category names in GetCategory()
2. **Custom Priorities**: Adjust priority values for sort order
3. **Independent Windows**: Implement SupportIndependentWindow() for complex tools
4. **Console Commands**: Tools can register custom commands via HasConsoleCommands()
5. **Multi-Tab Tools**: Complex tools can implement internal tab systems