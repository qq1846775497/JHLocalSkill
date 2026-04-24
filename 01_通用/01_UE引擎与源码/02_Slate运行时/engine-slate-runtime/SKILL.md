---
name: engine-slate-runtime
title: Slate UI Runtime
description: Unreal Engine Slate UI framework — widget base classes, declarative syntax, paint/layout pipeline, invalidation fast-path, input routing, style system, and UMG bridge. Reference when writing custom SWidget subclasses, debugging rendering issues, or understanding the Slate/UMG UI architecture.
tags: [Slate, UI, C++, Rendering, Layout, Input, Unreal-Engine]
---

# Slate UI Runtime

> Layer: Tier 3 (Engine Module Documentation)
> Parent: [Engine Modifications](../../../SKILL.md)

## System Overview

Slate is UE5's retained-mode immediate-style UI framework. It has two distinct modules:

| Module | Location | Role |
|--------|----------|------|
| **SlateCore** | `Engine/Source/Runtime/SlateCore/` | Base types: `SWidget`, geometry, rendering primitives, invalidation system, input, style |
| **Slate** | `Engine/Source/Runtime/Slate/` | Application layer (`SlateApplication`), full widget library, framework subsystems |
| **UMG** | `Engine/Source/Runtime/UMG/` | UObject/Blueprint wrapper layer on top of Slate (see [UMG Bridge](#umg-bridge)) |

The stack from low to high: `SlateCore → Slate → UMG → Blueprint`

**Do not inherit `SWidget` directly.** Use `SLeafWidget` (no children), `SCompoundWidget` (one child slot), or `SPanel` (N children with custom layout).

## Module Layout

```
Engine/Source/Runtime/Slate/Public/
├── Framework/
│   ├── Application/        SlateApplication.h (singleton), SlateUser, input processors
│   ├── Commands/           UICommandInfo, UICommandList, UIAction, InputChord
│   ├── Docking/            TabManager (dockable layouts), SDockTab
│   ├── Layout/             Scroll helpers, inertia, overscroll
│   ├── MultiBox/           Menu/toolbar builder (MultiBoxBuilder)
│   ├── Notifications/      NotificationManager, toast popups
│   ├── Styling/            Per-widget style structs (FButtonStyle, FTextBlockStyle, …)
│   ├── Text/               TextLayout engine, rich text, syntax highlighter
│   └── Views/              ITypedTableView, TreeFilterHandler
├── Widgets/
│   ├── Input/              ~35 interactive controls (SButton, SCheckBox, SComboBox, …)
│   ├── Layout/             ~25 layout panels (SBox, SBorder, SSplitter, SScrollBox, …)
│   ├── Text/               STextBlock, SRichTextBlock, SMultiLineEditableText, …
│   ├── Views/              SListView<>, STreeView<>, STileView<>, STableRow<>
│   ├── Colors/             SColorBlock, SColorWheel, SColorSpectrum, …
│   ├── Notifications/      SNotificationList, SProgressBar, SErrorText, …
│   └── (root)              SCanvas, SInvalidationPanel, SViewport, SVirtualWindow
```

For the full widget catalog see [`references/slate-widget-library.md`](references/slate-widget-library.md).
For Framework subsystem details see [`references/slate-framework-subsystems.md`](references/slate-framework-subsystems.md).

## SWidget Lifecycle

Every widget must implement three private virtual methods (called by non-virtual public wrappers):

```cpp
// 1. Bottom-up: what size does this widget WANT?
virtual FVector2D ComputeDesiredSize(float LayoutScaleMultiplier) const = 0;

// 2. Top-down: given allotted geometry, place children
virtual void OnArrangeChildren(
    const FGeometry& AllottedGeometry,
    FArrangedChildren& ArrangedChildren) const = 0;

// 3. Top-down: emit draw elements for this widget (and call Paint on children)
virtual int32 OnPaint(
    const FPaintArgs& Args,
    const FGeometry& AllottedGeometry,
    const FSlateRect& MyCullingRect,
    FSlateWindowElementList& OutDrawElements,
    int32 LayerId,
    const FWidgetStyle& InWidgetStyle,
    bool bParentEnabled) const = 0;
```

**Key header:** `Engine/Source/Runtime/SlateCore/Public/Widgets/SWidget.h`

### Declarative Syntax (SLATE_BEGIN_ARGS)

Widgets expose construction arguments via a nested `FArguments` struct:

```cpp
SLATE_BEGIN_ARGS(SMyWidget)
    , _Label(FText::GetEmpty())
    , _OnClicked()
    {}
    SLATE_ATTRIBUTE(FText, Label)          // bindable TAttribute<FText>
    SLATE_ARGUMENT(int32, MaxCount)        // plain value
    SLATE_EVENT(FOnClicked, OnClicked)     // delegate
    SLATE_SLOT_ARGUMENT(FSlot, Slots)      // child slots (panels)
SLATE_END_ARGS()

void Construct(const FArguments& InArgs);
```

- `SLATE_ATTRIBUTE` → `TAttribute<T>` (can bind a getter delegate; auto-invalidates via `TSlateAttribute`)
- `SLATE_ARGUMENT` → plain typed field; no binding
- `SLATE_EVENT` → delegate field with overloads `_Lambda`, `_Static`, `_UObject`, `_Raw`

Usage: `SNew(SMyWidget).Label(LOCTEXT("…","Foo")).OnClicked(this, &FMyClass::HandleClick)`

**Key header:** `Engine/Source/Runtime/SlateCore/Public/Widgets/DeclarativeSyntaxSupport.h`

## Layout Pass (Three Phases)

```
SlatePrepass (bottom-up)
  └─ ComputeDesiredSize() on leaves → cache DesiredSize → propagate upward

ArrangeChildren (top-down, per window)
  └─ OnArrangeChildren(AllottedGeometry, ArrangedChildren)
       └─ parent distributes space → FArrangedWidget{Widget, FGeometry}

Paint (top-down)
  └─ OnPaint(AllottedGeometry, …, OutDrawElements, LayerId)
       └─ FSlateDrawElement::MakeBox/MakeText/…(OutDrawElements, LayerId, Geometry, …)
```

Key types:

| Type | File | Purpose |
|------|------|---------|
| `FGeometry` | `SlateCore/Public/Layout/Geometry.h` | Widget's size, position, DPI scale, transforms |
| `FArrangedWidget` | `SlateCore/Public/Layout/ArrangedWidget.h` | Widget + its computed geometry |
| `FArrangedChildren` | `SlateCore/Public/Layout/ArrangedChildren.h` | Filtered array of arranged widgets |
| `FSlateLayoutTransform` | `SlateCore/Public/Rendering/SlateLayoutTransform.h` | Position + scale; affects layout & hit-testing |
| `FSlateRenderTransform` | `SlateCore/Public/Rendering/SlateRenderTransform.h` | Full 2D matrix; visual-only (no layout impact) |

`FGeometry::ToPaintGeometry()` converts to `FPaintGeometry` expected by `FSlateDrawElement`.

## Invalidation / Fast-Path System

The **fast path** skips `OnPaint` for unchanged widgets, reusing cached GPU batches. The slow path does a full traversal. `SWindow` inherits `FSlateInvalidationRoot`, which owns the decision.

```cpp
// Trigger from within a widget when state changes:
Invalidate(EInvalidateWidgetReason::Paint);   // visual only — no relayout
Invalidate(EInvalidateWidgetReason::Layout);  // size changed — expensive
```

`EInvalidateWidgetReason` bitmask (key values):

| Reason | Cost | Use when |
|--------|------|----------|
| `Paint` | Low | Color/brush changed, no size change |
| `Layout` | High | DesiredSize changed |
| `Visibility` | Medium | Collapsed/Hidden toggled (implies Layout) |
| `ChildOrder` | High | Children added/removed |
| `RenderTransform` | Low | Render transform changed (visual-only) |
| `Prepass` | High | Force re-cache desired size recursively |

**TSlateAttribute** — Attributes declared as `TSlateAttribute<T, EInvalidateWidgetReason::Paint>` automatically call `Invalidate()` when their bound delegate's return value changes, without manual tracking.

**Volatility** — Override `ComputeVolatility()` → `return true` for widgets that change every frame (animations, world-space). Volatile widgets bypass caching and always repaint.

**Key headers:**
- `SlateCore/Public/FastUpdate/SlateInvalidationRoot.h` — `FSlateInvalidationRoot`
- `SlateCore/Public/FastUpdate/WidgetProxy.h` — `FWidgetProxy` (per-widget flat-list entry)
- `SlateCore/Public/Widgets/InvalidateWidgetReason.h` — `EInvalidateWidgetReason`

## Input System

**Hit testing:** `FHittestGrid` (per-window spatial grid) maps desktop pixel coordinates to a bubble path — ordered list of widgets from outermost to innermost under the cursor.

**Event routing:** `FEventRouter` in `SlateApplication` walks the bubble path delivering the event. Routing stops when a widget returns `FReply::Handled()`.

```cpp
// Widget event handler pattern:
virtual FReply OnMouseButtonDown(const FGeometry& MyGeometry, const FPointerEvent& MouseEvent) override
{
    // Handle and optionally capture mouse:
    return FReply::Handled().CaptureMouse(SharedThis(this));
    // Or: return FReply::Unhandled(); // let parent handle
}
```

`FReply` is a builder — chain modifiers:
- `.CaptureMouse(Widget)` — route all future mouse events to Widget
- `.SetUserFocus(Widget, Cause)` — request keyboard focus
- `.BeginDragDrop(Op)` / `.EndDragDrop()` — initiate drag-and-drop
- `.SetMousePos(Pos)` — warp cursor

**Key note:** Slate uses *bubbling only* (no separate WPF-style tunneling phase). `OnPreviewMouseButtonDown` is a preview hook on the bubble path but not a true tunnel.

**Key headers:**
- `SlateCore/Public/Input/HittestGrid.h` — `FHittestGrid`, `ICustomHitTestPath`
- `SlateCore/Public/Input/Reply.h` — `FReply`
- `SlateCore/Public/Input/Events.h` — `FPointerEvent`, `FKeyEvent`, `FFocusEvent`

## Style System

```
FSlateStyleRegistry                       (global name → ISlateStyle* map)
  └─ FSlateStyleSet : ISlateStyle         (owns maps: FName → brush/color/font/widget-style)
       └─ FSlateStyleSet::SetParentStyleName()  (fallback chain)
```

**Lookup pattern:**
```cpp
const ISlateStyle* Style = FSlateStyleRegistry::FindSlateStyle("EditorStyle");
const FButtonStyle& BtnStyle = Style->GetWidgetStyle<FButtonStyle>("Button");
const FSlateBrush* Brush = Style->GetBrush("Icons.Star");
```

**Style primitives:**
- `FSlateBrush` — DrawType (Box/Border/Image/RoundedBox), tiling, mirroring, outline settings
- `FSlateColor` — `UseColor_Specified` (literal) | `UseColor_Foreground` (inherits from tree) | `UseColor_ColorTable`
- `FTextBlockStyle`, `FButtonStyle`, `FCheckBoxStyle`, … — widget-specific style structs in `SlateTypes.h`

**Registration** — typically done in a module's `StartupModule()`:
```cpp
FSlateStyleRegistry::RegisterSlateStyle(*MyStyleSet);
// OnShutdownModule:
FSlateStyleRegistry::UnRegisterSlateStyle(*MyStyleSet);
```

**Key headers:**
- `SlateCore/Public/Styling/ISlateStyle.h`
- `SlateCore/Public/Styling/SlateStyle.h` — `FSlateStyleSet`
- `SlateCore/Public/Styling/SlateStyleRegistry.h`
- `SlateCore/Public/Styling/SlateTypes.h` — all widget style structs
- `SlateCore/Public/Styling/SlateBrush.h`, `SlateColor.h`

## UMG Bridge

UMG wraps Slate with a UObject layer for Blueprint and the visual designer.

```
UWidget (UObject)
  ├── RebuildWidget()        → creates SWidget (called lazily by TakeWidget())
  ├── SynchronizeProperties() → pushes UObject property values into SWidget attributes
  ├── Slot (UPanelSlot*)     → mirrors Slate slot layout params
  └── SObjectWidget          → SCompoundWidget that GC-roots the UUserWidget*
```

**Binding pattern (PROPERTY_BINDING macro):**
```cpp
// In UWidget subclass: generates TAttribute<T> from Blueprint binding or literal
UPROPERTY(EditAnywhere, BlueprintReadWrite)
FText LabelText;
PROPERTY_BINDING(FText, LabelText);  // → TAttribute<FText> bound or literal
```

**Key header:** `Engine/Source/Runtime/UMG/Public/Components/Widget.h`

## Key Types Quick Reference

| Type | Header (under SlateCore/ or Slate/) | Purpose |
|------|-------------------------------------|---------|
| `SWidget` | `SlateCore/Public/Widgets/SWidget.h` | Base widget |
| `SLeafWidget` | `SlateCore/Public/Widgets/LeafWidgetBase.h` | No-children base |
| `SCompoundWidget` | `SlateCore/Public/Widgets/CompoundWidget.h` | Single-child base |
| `SPanel` | `SlateCore/Public/Widgets/Panel.h` | N-children base |
| `FGeometry` | `SlateCore/Public/Layout/Geometry.h` | Widget space/position |
| `FArrangedChildren` | `SlateCore/Public/Layout/ArrangedChildren.h` | Layout result array |
| `FSlateDrawElement` | `SlateCore/Public/Rendering/DrawElementTypes.h` | Atomic draw call |
| `FSlateWindowElementList` | `SlateCore/Public/Rendering/DrawElements.h` | Per-window draw list |
| `FSlateDrawBuffer` | `SlateCore/Public/Rendering/SlateDrawBuffer.h` | All-windows draw buffer |
| `FSlateInvalidationRoot` | `SlateCore/Public/FastUpdate/SlateInvalidationRoot.h` | Fast/slow path controller |
| `EInvalidateWidgetReason` | `SlateCore/Public/Widgets/InvalidateWidgetReason.h` | Invalidation bitmask |
| `FHittestGrid` | `SlateCore/Public/Input/HittestGrid.h` | Spatial hit-test index |
| `FReply` | `SlateCore/Public/Input/Reply.h` | Event handler return |
| `FSlateStyleSet` | `SlateCore/Public/Styling/SlateStyle.h` | Named style container |
| `FSlateBrush` | `SlateCore/Public/Styling/SlateBrush.h` | Draw brush descriptor |
| `SlateApplication` | `Slate/Public/Framework/Application/SlateApplication.h` | App singleton |

## References

Detailed content split into reference files to keep this document scannable:

| File | Contents |
|------|----------|
| [`references/slate-widget-library.md`](references/slate-widget-library.md) | Full widget catalog: all Input/Layout/Text/Views/Colors/Notification widgets with file paths |
| [`references/slate-framework-subsystems.md`](references/slate-framework-subsystems.md) | SlateApplication, Commands, Docking/TabManager, MultiBox, Text layout engine |
| [`references/slate-rendering-pipeline.md`](references/slate-rendering-pipeline.md) | FSlateDrawElement factory methods, batching, cached fast-path data structures |
