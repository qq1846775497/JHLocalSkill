# Slate Rendering Pipeline Reference

> Referenced from: `Engine/Source/Runtime/Slate/SKILL.md`
> Source: `Engine/Source/Runtime/SlateCore/Public/Rendering/`

## Pipeline Overview

```
FSlateApplication::DrawWindows()
  └─ FSlateDrawBuffer (lock)
       └─ per SWindow → FSlateWindowElementList
            └─ SWindow::PaintInvalidationRoot()
                 ├─ FAST PATH: FWidgetProxy::Update() → reuse FSlateCachedElementList
                 └─ SLOW PATH: SWidget::Paint() → SWidget::OnPaint() → FSlateDrawElement::Make*()
  └─ FSlateDrawBuffer (unlock + submit)
       └─ FSlateRenderer::DrawWindows(Buffer)
            └─ FSlateElementBatcher → FSlateRenderBatch[]
                 └─ GPU submission
```

## FSlateDrawBuffer

**Header:** `Engine/Source/Runtime/SlateCore/Public/Rendering/SlateDrawBuffer.h`

Top-level container holding one `FSlateWindowElementList` per visible window. Thread-safe:
- `Lock()` / `Unlock(UE::Tasks::FTask Prerequisite)` — game thread owns during fill; render thread owns during draw
- `AddWindowElementList(TSharedRef<SWindow>)` — creates per-window list

Typically accessed as `FSlateApplication::Get().GetDrawBuffer()`.

## FSlateWindowElementList

**Header:** `Engine/Source/Runtime/SlateCore/Public/Rendering/DrawElements.h`

Per-window ordered list of draw elements plus fast-path cached data:

```cpp
class FSlateWindowElementList
{
    TArray<FSlateDrawElement>         UncachedDrawElements;    // slow-path elements
    FSlateCachedElementData*          CachedElementData;       // fast-path cache root
    TSharedPtr<SWindow>               Window;
    FHittestGrid*                     HittestGrid;
    // Also: overlay elements (popups, tooltips rendered above everything)
};
```

## FSlateDrawElement — Factory Methods

**Header:** `Engine/Source/Runtime/SlateCore/Public/Rendering/DrawElementTypes.h`

All draw calls go through `FSlateDrawElement` static factory methods. Every method takes:
- `FSlateWindowElementList& OutDrawElements` — target list
- `uint32 InLayer` — paint layer; higher = drawn on top
- `const FPaintGeometry& PaintGeometry` — position + size from `FGeometry::ToPaintGeometry()`

### Image / Brush

```cpp
// Nine-sliced or simple image:
FSlateDrawElement::MakeBox(
    OutDrawElements, LayerId,
    AllottedGeometry.ToPaintGeometry(),
    Brush,                              // const FSlateBrush*
    DrawEffects,                        // ESlateDrawEffect (None, DisabledEffect, etc.)
    FLinearColor::White                 // tint
);

// Rotated image:
FSlateDrawElement::MakeRotatedBox(
    OutDrawElements, LayerId, PaintGeometry, Brush,
    DrawEffects, AngleInRadians,
    TOptional<FVector2D> RotationPoint, // pivot (default: center)
    ERotationSpace::RelativeToElement
);
```

### Text

```cpp
// Simple string (fast):
FSlateDrawElement::MakeText(
    OutDrawElements, LayerId, PaintGeometry,
    Text,           // FString or FText
    FontInfo,       // FSlateFontInfo
    DrawEffects, FLinearColor::White
);

// Pre-shaped glyphs (output from FShapedTextCache — avoids re-shaping):
FSlateDrawElement::MakeShapedText(
    OutDrawElements, LayerId, PaintGeometry,
    ShapedGlyphSequence,    // TSharedRef<FShapedGlyphSequence>
    DrawEffects, BaseTint, OutlineTint
);
```

### Lines and Splines

```cpp
// Polyline:
TArray<FVector2D> Points = { {0,0}, {100,0}, {100,100} };
FSlateDrawElement::MakeLines(
    OutDrawElements, LayerId, PaintGeometry,
    Points, DrawEffects, FLinearColor::Red,
    /*bAntialias=*/true, /*Thickness=*/1.5f
);

// Cubic bezier:
FSlateDrawElement::MakeCubicBezierSpline(
    OutDrawElements, LayerId, PaintGeometry,
    P0, P1, P2, P3,        // FVector2D control points
    Thickness, DrawEffects, Color
);

// Dashed line:
FSlateDrawElement::MakeDashedLine(OutDrawElements, LayerId, PaintGeometry,
    Points, DashSize, DrawEffects, Color, Thickness);
```

### Gradient

```cpp
TArray<FSlateGradientStop> Stops = {
    { FVector2D(0,0), FLinearColor::Black },
    { FVector2D(1,0), FLinearColor::White }
};
FSlateDrawElement::MakeGradient(
    OutDrawElements, LayerId, PaintGeometry,
    Stops, EOrientation::Orient_Horizontal, DrawEffects
);
```

### Debug / Outline

```cpp
FSlateDrawElement::MakeDebugQuad(OutDrawElements, LayerId, PaintGeometry, Color);
FSlateDrawElement::MakeGeometryOutline(OutDrawElements, LayerId, PaintGeometry, Brush, DrawEffects, Color);
```

## ESlateDrawEffect

Bitmask controlling rendering variants:

| Flag | Effect |
|------|--------|
| `None` | Normal |
| `DisabledEffect` | Greyed-out (desaturated + dimmed) |
| `NoPixelSnapping` | Skip sub-pixel rounding |
| `PreMultipliedAlpha` | Input already has pre-multiplied alpha |
| `NoBlending` | Opaque output |
| `ReverseGamma` | Write in linear space (for render targets) |
| `IgnoreTextureAlpha` | Use only vertex color alpha |

## Fast-Path Cached Data Structures

### FSlateCachedElementList

Per-widget cache entry. When a widget is in the fast path, its `OnPaint` is skipped and this is used directly.

```cpp
struct FSlateCachedElementList
{
    TArray<FSlateDrawElement>                      CachedDrawElements;   // the cached elements
    TUniquePtr<FSlateCachedFastPathRenderingData>  CachedRenderingData;  // GPU-ready batches
    // Invalidated by FWidgetProxy when EInvalidateWidgetReason::Paint is set
};
```

`FSlateCachedFastPathRenderingData` holds pre-built vertex/index buffers that can be submitted to the GPU without re-batching.

### Cache Lifetime

- Created when a widget first paints successfully on the fast path
- Invalidated (cleared) by `FSlateInvalidationRoot` when any widget on the tree calls `Invalidate()`
- Rebuilt during the next slow-path paint pass

## FSlateElementBatcher

**Header:** `Engine/Source/Runtime/SlateCore/Public/Rendering/ElementBatcher.h`

Consumes the `FSlateWindowElementList` and groups elements into `FSlateRenderBatch` objects sharing the same texture, shader, and blend state. Works on the render thread.

Key grouping rules:
- Adjacent elements with the same texture/brush → merged into one batch (fewer draw calls)
- Elements on different layers that share properties may still batch if no depth change is needed
- Text elements use an atlas texture → batched separately per atlas page

## Layer ID Conventions

Higher `LayerId` values render on top. Typical conventions in editor code:

| Range | Usage |
|-------|-------|
| 0 | Background |
| 1–10 | Normal widget content |
| 10–20 | Hover effects, selection highlights |
| 20–50 | Popup overlays, tooltips anchored to widgets |
| 50+ | Drag-drop visuals, global overlays |

Panels typically pass `MaxLayerId + 1` as the starting layer for child paint calls:
```cpp
int32 MaxChildLayer = 0;
for (auto& Arranged : ArrangedChildren)
{
    MaxChildLayer = FMath::Max(MaxChildLayer,
        Arranged.Widget->Paint(Args, Arranged.Geometry, MyCullingRect,
                               OutDrawElements, LayerId, WidgetStyle, bEnabled));
}
return MaxChildLayer; // return highest layer used
```

## Culling

`FSlateRect MyCullingRect` passed to `OnPaint` — widgets should skip emitting elements whose paint geometry does not intersect this rect:

```cpp
if (!FSlateRect::DoRectanglesIntersect(MyCullingRect, AllottedGeometry.GetLayoutBoundingRect()))
{
    return LayerId; // nothing to draw
}
```

`SWidget::CullingBoundsExtension` (FMargin) — expands the cull rect for this widget (used by e.g. shadow-casting widgets that draw slightly outside their geometry).

## FSlateRenderer Interface

The abstract renderer (`ISlateRenderer`) has these implementations:
- `FSlateRHIRenderer` — main renderer using UE's RHI (D3D12, Vulkan, Metal)
- `FSlateNullRenderer` — no-op for headless/server builds

Custom renderers can be set via `FSlateApplication::InitializeRenderer()`.
