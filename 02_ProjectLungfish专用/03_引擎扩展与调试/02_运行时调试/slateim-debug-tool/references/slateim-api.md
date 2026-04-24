# SlateIM API Reference

SlateIM (Slate Immediate Mode) primitives commonly used in debug tools.

## Text Display

### SlateIM::Text()

Display static or dynamic text.

```cpp
// Static text
SlateIM::Text(TEXT("Performance Metrics"));

// Dynamic text with formatting
SlateIM::Text(FString::Printf(TEXT("FPS: %.1f"), CurrentFPS));
SlateIM::Text(FString::Printf(TEXT("Memory: %.2f MB"), MemoryMB));

// Multi-line
SlateIM::Text(TEXT("Line 1"));
SlateIM::Text(TEXT("Line 2"));
SlateIM::Text(TEXT("Line 3"));
```

## Layout Primitives

### SlateIM::Spacer()

Add vertical or horizontal spacing.

```cpp
// Vertical spacing (most common)
SlateIM::Spacer(FVector2D(0, 5));   // 5 pixels vertical gap
SlateIM::Spacer(FVector2D(0, 10));  // 10 pixels vertical gap

// Horizontal spacing (within HorizontalStack)
SlateIM::BeginHorizontalStack();
SlateIM::Text(TEXT("Label:"));
SlateIM::Spacer(FVector2D(10, 0));  // 10 pixels horizontal gap
SlateIM::Text(TEXT("Value"));
SlateIM::EndHorizontalStack();
```

### SlateIM::BeginHorizontalStack() / EndHorizontalStack()

Arrange widgets horizontally (left-to-right).

```cpp
SlateIM::BeginHorizontalStack();
SlateIM::Text(TEXT("FPS: 60"));
SlateIM::Text(TEXT("Frame Time: 16ms"));
SlateIM::EndHorizontalStack();

// With buttons
SlateIM::BeginHorizontalStack();
if (SlateIM::Button(TEXT("Button 1"))) { /* ... */ }
if (SlateIM::Button(TEXT("Button 2"))) { /* ... */ }
SlateIM::EndHorizontalStack();
```

### SlateIM::BeginVerticalStack() / EndVerticalStack()

Arrange widgets vertically (top-to-bottom) - usually default behavior.

```cpp
SlateIM::BeginVerticalStack();
SlateIM::Text(TEXT("Line 1"));
SlateIM::Text(TEXT("Line 2"));
SlateIM::Text(TEXT("Line 3"));
SlateIM::EndVerticalStack();
```

## Interactive Controls

### SlateIM::Button()

Create clickable button, returns true on click.

```cpp
// Simple button
if (SlateIM::Button(TEXT("Force GC")))
{
    GEngine->ForceGarbageCollection(true);
    UE_LOG(LogTemp, Log, TEXT("GC triggered"));
}

// Conditional button
if (SlateIM::Button(TEXT("Toggle Feature")))
{
    bFeatureEnabled = !bFeatureEnabled;
}

// Multiple buttons in a row
SlateIM::BeginHorizontalStack();
if (SlateIM::Button(TEXT("Start"))) { /* ... */ }
if (SlateIM::Button(TEXT("Stop"))) { /* ... */ }
if (SlateIM::Button(TEXT("Reset"))) { /* ... */ }
SlateIM::EndHorizontalStack();
```

### SlateIM::CheckBox()

Create checkbox, returns current state.

```cpp
// Basic checkbox
bool bNewState = SlateIM::CheckBox(TEXT("Enable Feature"), bCurrentState);
if (bNewState != bCurrentState)
{
    bCurrentState = bNewState;
    UE_LOG(LogTemp, Log, TEXT("Feature %s"), bNewState ? TEXT("enabled") : TEXT("disabled"));
}

// Inline checkbox with state update
bShowDebugInfo = SlateIM::CheckBox(TEXT("Show Debug Info"), bShowDebugInfo);
```

## Common Layout Patterns

### Section Headers

```cpp
void DrawSlateIMContent() override
{
    SlateIM::Text(TEXT("=== Section 1 ==="));
    SlateIM::Spacer(FVector2D(0, 5));
    // Section 1 content...

    SlateIM::Spacer(FVector2D(0, 10));
    SlateIM::Text(TEXT("=== Section 2 ==="));
    SlateIM::Spacer(FVector2D(0, 5));
    // Section 2 content...
}
```

### Data Display Grid

```cpp
void DrawSlateIMContent() override
{
    SlateIM::Text(TEXT("=== Player Info ==="));
    SlateIM::Spacer(FVector2D(0, 5));

    SlateIM::Text(FString::Printf(TEXT("Location: X=%.1f Y=%.1f Z=%.1f"),
        Location.X, Location.Y, Location.Z));
    SlateIM::Text(FString::Printf(TEXT("Rotation: Pitch=%.1f Yaw=%.1f Roll=%.1f"),
        Rotation.Pitch, Rotation.Yaw, Rotation.Roll));
    SlateIM::Text(FString::Printf(TEXT("Velocity: %.2f units/s"), Velocity.Size()));
}
```

### Control Panel

```cpp
void DrawSlateIMContent() override
{
    SlateIM::Text(TEXT("=== Controls ==="));
    SlateIM::Spacer(FVector2D(0, 5));

    SlateIM::BeginHorizontalStack();
    if (SlateIM::Button(TEXT("Action 1")))
    {
        PerformAction1();
    }
    if (SlateIM::Button(TEXT("Action 2")))
    {
        PerformAction2();
    }
    SlateIM::EndHorizontalStack();

    SlateIM::Spacer(FVector2D(0, 5));

    bOption1 = SlateIM::CheckBox(TEXT("Enable Option 1"), bOption1);
    bOption2 = SlateIM::CheckBox(TEXT("Enable Option 2"), bOption2);
}
```

### Multi-Column Layout

```cpp
void DrawSlateIMContent() override
{
    SlateIM::BeginHorizontalStack();

    // Column 1
    SlateIM::BeginVerticalStack();
    SlateIM::Text(TEXT("Column 1"));
    SlateIM::Text(TEXT("Data 1"));
    SlateIM::Text(TEXT("Data 2"));
    SlateIM::EndVerticalStack();

    SlateIM::Spacer(FVector2D(20, 0));  // Column separator

    // Column 2
    SlateIM::BeginVerticalStack();
    SlateIM::Text(TEXT("Column 2"));
    SlateIM::Text(TEXT("Data 3"));
    SlateIM::Text(TEXT("Data 4"));
    SlateIM::EndVerticalStack();

    SlateIM::EndHorizontalStack();
}
```

## Best Practices

### 1. Use Consistent Spacing

```cpp
// Good: Consistent spacing
SlateIM::Text(TEXT("=== Header ==="));
SlateIM::Spacer(FVector2D(0, 5));    // Always 5px after headers
// Content...
SlateIM::Spacer(FVector2D(0, 10));   // Always 10px between sections

// Bad: Inconsistent spacing
SlateIM::Text(TEXT("=== Header ==="));
SlateIM::Spacer(FVector2D(0, 3));
// Content...
SlateIM::Spacer(FVector2D(0, 15));
```

### 2. Section Organization

```cpp
// Good: Clear section separation
void DrawSlateIMContent() override
{
    DrawMetricsSection();
    SlateIM::Spacer(FVector2D(0, 10));
    DrawControlsSection();
    SlateIM::Spacer(FVector2D(0, 10));
    DrawInfoSection();
}

void DrawMetricsSection()
{
    SlateIM::Text(TEXT("=== Metrics ==="));
    SlateIM::Spacer(FVector2D(0, 5));
    // Metrics content...
}

// Bad: Everything in one function
void DrawSlateIMContent() override
{
    SlateIM::Text(TEXT("=== Metrics ==="));
    // 100 lines of content...
}
```

### 3. Readable Formatting

```cpp
// Good: Clear formatting with line breaks
SlateIM::Text(FString::Printf(
    TEXT("Player Location: X=%.1f Y=%.1f Z=%.1f"),
    Location.X, Location.Y, Location.Z
));

// Bad: Hard to read
SlateIM::Text(FString::Printf(TEXT("Player Location: X=%.1f Y=%.1f Z=%.1f"), Location.X, Location.Y, Location.Z));
```

### 4. Button Grouping

```cpp
// Good: Related buttons grouped
SlateIM::Text(TEXT("=== Game Controls ==="));
SlateIM::Spacer(FVector2D(0, 5));
SlateIM::BeginHorizontalStack();
if (SlateIM::Button(TEXT("Pause"))) { /* ... */ }
if (SlateIM::Button(TEXT("Resume"))) { /* ... */ }
SlateIM::EndHorizontalStack();

// Bad: Buttons scattered
SlateIM::Text(TEXT("=== Game Controls ==="));
if (SlateIM::Button(TEXT("Pause"))) { /* ... */ }
SlateIM::Text(TEXT("Some other text"));
if (SlateIM::Button(TEXT("Resume"))) { /* ... */ }
```

## Common Pitfalls

### ❌ Forgetting EndHorizontalStack()

```cpp
// BAD: Missing End call
SlateIM::BeginHorizontalStack();
SlateIM::Text(TEXT("Item 1"));
SlateIM::Text(TEXT("Item 2"));
// SlateIM::EndHorizontalStack();  // MISSING!

// Will cause layout issues!
```

### ❌ Nesting Without Clear Structure

```cpp
// BAD: Hard to track nesting
SlateIM::BeginVerticalStack();
SlateIM::BeginHorizontalStack();
SlateIM::BeginVerticalStack();
// Which End matches which Begin?
SlateIM::EndVerticalStack();
SlateIM::EndHorizontalStack();
SlateIM::EndVerticalStack();
```

### ✅ Good Nesting Practice

```cpp
// GOOD: Indentation makes structure clear
SlateIM::BeginVerticalStack();
{
    SlateIM::Text(TEXT("Outer"));

    SlateIM::BeginHorizontalStack();
    {
        SlateIM::Text(TEXT("Left"));
        SlateIM::Text(TEXT("Right"));
    }
    SlateIM::EndHorizontalStack();
}
SlateIM::EndVerticalStack();
```

## Performance Tips

1. **Avoid Heavy Computations**: Do calculations outside DrawSlateIMContent(), cache results
2. **Update Frequency**: Use timers to control data update rate (not every frame)
3. **Conditional Display**: Only show sections when needed

```cpp
// Good: Cached data, timer-driven updates
void UpdateData()  // Called by timer
{
    CachedFPS = CalculateFPS();
    CachedMemory = GetMemoryUsage();
}

void DrawSlateIMContent() override
{
    SlateIM::Text(FString::Printf(TEXT("FPS: %.1f"), CachedFPS));
}

// Bad: Heavy calculation every frame
void DrawSlateIMContent() override
{
    float FPS = CalculateFPS();  // Expensive!
    SlateIM::Text(FString::Printf(TEXT("FPS: %.1f"), FPS));
}
```