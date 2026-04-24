# Slate Widget Library Reference

> Referenced from: `Engine/Source/Runtime/Slate/SKILL.md`
> Source: `Engine/Source/Runtime/Slate/Public/Widgets/`

## Widget Inheritance Hierarchy

```
SWidget (SlateCore — base, never inherit directly)
├── SLeafWidget       — no children (images, text blocks, primitives)
├── SCompoundWidget   — exactly one child slot
└── SPanel            — N children with custom layout logic
```

## Input Widgets (`Widgets/Input/`)

Interactive controls. All handle focus and produce `FReply`.

| Widget | Header | Description |
|--------|--------|-------------|
| `SButton` | `SButton.h` | Clickable button with Normal/Hovered/Pressed/Disabled brushes |
| `SCheckBox` | `SCheckBox.h` | Check/radio box with tri-state support |
| `SComboBox<T>` | `SComboBox.h` | Generic dropdown list |
| `SComboButton` | `SComboButton.h` | Button that opens a popup content area |
| `SEditableText` | `SEditableText.h` | Single-line editable text input |
| `SEditableTextBox` | `SEditableTextBox.h` | SEditableText wrapped in a box brush |
| `SMultiLineEditableTextBox` | `SMultiLineEditableTextBox.h` | Multi-line editor |
| `SSearchBox` | `SSearchBox.h` | SEditableTextBox with clear button and search icon |
| `SSlider` | `SSlider.h` | Horizontal/vertical value slider |
| `SSpinBox<T>` | `SSpinBox.h` | Numeric entry with drag-to-change and arrow buttons |
| `SVectorInputBox` | `SVectorInputBox.h` | 2/3/4-component numeric input (FVector, FVector4) |
| `SRotatorInputBox` | `SRotatorInputBox.h` | FRotator (Pitch/Yaw/Roll) input |
| `SNumericEntryBox<T>` | `SNumericEntryBox.h` | Numeric box with optional label and custom labeler |
| `SHyperlink` | `SHyperlink.h` | Clickable text link |
| `SInputKeySelector` | `SInputKeySelector.h` | Records a key chord from user input |
| `SVirtualJoystick` | `SVirtualJoystick.h` | On-screen touch joystick (mobile) |
| `SVirtualKeyboardEntry` | `SVirtualKeyboardEntry.h` | Touch keyboard trigger |
| `SVolumeControl` | `SVolumeControl.h` | Volume slider with mute button |
| `SSegmentedControl<T>` | `SSegmentedControl.h` | Exclusive-select button group (tab bar style) |
| `SMenuAnchor` | `SMenuAnchor.h` | Anchors and positions a popup menu |

## Layout Widgets (`Widgets/Layout/`)

Panels that arrange children. No input handling.

| Widget | Header | Description |
|--------|--------|-------------|
| `SBox` | `SBox.h` | Fixed or min/max size box; wraps one child |
| `SBorder` | `SBorder.h` | Draws a brush around one child |
| `SConstraintCanvas` | `SConstraintCanvas.h` | Absolute positioning with anchor/offset constraints |
| `SCanvas` | `../SCanvas.h` | Free-placement canvas (local coordinates) |
| `SSplitter` | `SSplitter.h` | Horizontal/vertical resizable split between children |
| `SScrollBox` | `SScrollBox.h` | Scrollable list of children in one axis |
| `SScrollBar` | `SScrollBar.h` | Standalone scroll bar widget |
| `SGridPanel` | `SGridPanel.h` | Row/column grid with optional spanning |
| `SUniformGridPanel` | `SUniformGridPanel.h` | Fixed-cell-size grid |
| `SWrapBox` | `SWrapBox.h` | Wraps children to next row when width exceeded |
| `SUniformWrapPanel` | `SUniformWrapPanel.h` | Wrap box with uniform cell sizes |
| `SWidgetSwitcher` | `SWidgetSwitcher.h` | Shows one child at a time by index |
| `SExpandableArea` | `SExpandableArea.h` | Collapsible section with header |
| `SSafeZone` | `SSafeZone.h` | Insets content to avoid screen notches/overscan |
| `SScaleBox` | `SScaleBox.h` | Scales content to fit/fill/stretch within allotted space |
| `SBackgroundBlur` | `SBackgroundBlur.h` | Blurs whatever is behind the widget |
| `SRadialBox` | `SRadialBox.h` | Arranges children in a circular arc |
| `SResponsiveGridPanel` | `SResponsiveGridPanel.h` | Grid that reflows columns by width |
| `SHeader` | `SHeader.h` | Section divider/header bar |
| `SSeparator` | `SSeparator.h` | Horizontal or vertical rule line |
| `SSpacer` | `SSpacer.h` | Empty space of fixed or flexible size |

## Text Widgets (`Widgets/Text/`)

| Widget | Header | Description |
|--------|--------|-------------|
| `STextBlock` | `STextBlock.h` | Static single/multi-line text |
| `SRichTextBlock` | `SRichTextBlock.h` | Markup-driven text with inline decorators |
| `SMultiLineEditableText` | `SMultiLineEditableText.h` | Multi-line text editor (no border) |
| `SInlineEditableTextBlock` | `SInlineEditableTextBlock.h` | Label that switches to editor on double-click |
| `STextScroller` | `STextScroller.h` | Auto-scrolling marquee text |
| `SlateEditableTextLayout` | `SlateEditableTextLayout.h` | Shared logic backing all editable text widgets |

## Data-Bound Views (`Widgets/Views/`)

High-performance virtualized lists — only create row widgets for visible items.

| Widget | Header | Description |
|--------|--------|-------------|
| `SListView<T>` | `SListView.h` | Vertically scrolling list |
| `STreeView<T>` | `STreeView.h` | Hierarchical tree with expand/collapse |
| `STileView<T>` | `STileView.h` | Grid of same-size tiles |
| `STableRow<T>` | `STableRow.h` | Base class for row widgets in any table view |
| `SHeaderRow` | `SHeaderRow.h` | Column header bar with sortable columns |
| `SExpanderArrow` | `SExpanderArrow.h` | Tree expand/collapse chevron |

Common pattern:
```cpp
SNew(SListView<TSharedPtr<FMyItem>>)
    .ListItemsSource(&Items)
    .OnGenerateRow(this, &FMyClass::MakeRow)
    .SelectionMode(ESelectionMode::Single)
```

## Notification / Progress Widgets (`Widgets/Notifications/`)

| Widget | Header | Description |
|--------|--------|-------------|
| `SNotificationList` | `SNotificationList.h` | Container for toast notifications |
| `SProgressBar` | `SProgressBar.h` | Horizontal or vertical progress bar |
| `SErrorText` | `SErrorText.h` | Red error message label |
| `SErrorHint` | `SErrorHint.h` | Compact error icon with tooltip |
| `SPopUpErrorText` | `SPopUpErrorText.h` | Error popup anchored to a widget |

Toast notifications (via `NotificationManager`):
```cpp
FNotificationInfo Info(LOCTEXT("Done","Operation complete"));
Info.ExpireDuration = 4.0f;
FSlateNotificationManager::Get().AddNotification(Info);
```

## Color Picker Widgets (`Widgets/Colors/`)

| Widget | Header | Description |
|--------|--------|-------------|
| `SColorBlock` | `SColorBlock.h` | Solid color swatch (optionally clickable) |
| `SColorWheel` | `SColorWheel.h` | Hue/saturation wheel |
| `SColorGradingWheel` | `SColorGradingWheel.h` | Film-style color grading wheel |
| `SColorSpectrum` | `SColorSpectrum.h` | Value/lightness spectrum strip |
| `SSimpleGradient` | `SSimpleGradient.h` | Two-stop linear gradient display |
| `SComplexGradient` | `SComplexGradient.h` | Multi-stop gradient display |

## Viewport and Special Widgets

| Widget | Header | Description |
|--------|--------|-------------|
| `SViewport` | `Widgets/SViewport.h` | Hosts an `ISlateViewport` (3D scene, render target) |
| `SVirtualWindow` | `Widgets/SVirtualWindow.h` | Window rendered into a render target (world-space UMG) |
| `SInvalidationPanel` | `Widgets/SInvalidationPanel.h` | Caches child subtree paint; skips repaint when unchanged |
| `SToolTip` | `Widgets/SToolTip.h` | Standard tooltip popup |
| `SWeakWidget` | `Widgets/SWeakWidget.h` | Holds weak ref to child; collapses when widget is gone |
| `SDockTab` | `Widgets/Docking/SDockTab.h` | The dockable tab widget |
| `SLayerManager` | `Widgets/LayerManager/SLayerManager.h` | Manages overlay layers (tooltips, popups) |
| `STooltipPresenter` | `Widgets/LayerManager/STooltipPresenter.h` | Renders tooltip above all other content |

## Animated / Throbber Widgets

| Widget | Header | Description |
|--------|--------|-------------|
| `SThrobber` | `Widgets/Images/SThrobber.h` | Animated loading indicator (bouncing dots) |
| `SSpinningImage` | `Widgets/Images/SSpinningImage.h` | Rotating image spinner |
