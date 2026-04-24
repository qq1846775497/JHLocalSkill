# Slate Framework Subsystems Reference

> Referenced from: `Engine/Source/Runtime/Slate/SKILL.md`
> Source: `Engine/Source/Runtime/Slate/Public/Framework/`

## SlateApplication (Application/)

`FSlateApplication` is a singleton (`FSlateApplication::Get()`) that owns the entire Slate lifecycle:

- **Window management** — creates, destroys, and tracks `SWindow` instances
- **Draw loop** — calls `DrawWindows()` each frame, building `FSlateDrawBuffer`
- **Input dispatch** — receives OS input events, uses `FHittestGrid` to find target widgets, routes via `FEventRouter`
- **Focus management** — per-user keyboard focus state
- **DPI scaling** — queries `ICurveEditorDelegate` / platform for per-monitor DPI
- **Cursor management** — controls OS cursor shape based on widget `OnCursorQuery` responses
- **Menu stack** — `FMenuStack` tracks open popup menus for correct dismissal
- **Tick** — calls `SWidget::Tick()` on all widgets with `NeedsTick` flag set

```cpp
// Common access patterns:
FSlateApplication::Get().SetKeyboardFocus(MyWidget, EFocusCause::SetDirectly);
FSlateApplication::Get().DismissAllMenus();
TSharedRef<SWindow> Win = FSlateApplication::Get().GetActiveTopLevelWindow().ToSharedRef();
```

Related types:
- `FSlateUser` (`SlateUser.h`) — per-user state (cursor position, keyboard focus widget)
- `FAnalogCursor` (`AnalogCursor.h`) — maps gamepad analog stick to a virtual mouse cursor
- `FGestureDetector` (`GestureDetector.h`) — touch pinch/swipe recognition
- `IInputProcessor` (`IInputProcessor.h`) — inject pre/post input processing via `FSlateApplication::RegisterInputPreProcessor()`
- `FNavigationConfig` (`NavigationConfig.h`) — maps gamepad buttons to `EUINavigation` directions

**Key header:** `Engine/Source/Runtime/Slate/Public/Framework/Application/SlateApplication.h`

## Commands System (Commands/)

The commands system provides a layer between "what the user did" (key press) and "what the app does" (action). Commands are declared once and bound separately from where they are executed.

### Core Types

| Type | Header | Role |
|------|--------|------|
| `FUICommandInfo` | `UICommandInfo.h` | Named command descriptor — label, tooltip, icon, default chord |
| `FUIAction` | `UIAction.h` | Delegate bundle: `ExecuteAction`, `CanExecuteAction`, `IsCheckedAction` |
| `FUICommandList` | `UICommandList.h` | Maps `FUICommandInfo → FUIAction` (the binding table) |
| `TCommands<T>` | `Commands.h` | CRTP base; modules register command sets here |
| `FInputChord` | `InputChord.h` | Key + modifier combination (e.g. Ctrl+S) |
| `FInputBindingManager` | `InputBindingManager.h` | Global registry; resolves key chords to commands at runtime |

### Declaration Pattern

```cpp
class FMyCommands : public TCommands<FMyCommands>
{
public:
    FMyCommands() : TCommands<FMyCommands>(
        TEXT("MyContext"), LOCTEXT("MyContext","My Context"),
        NAME_None, FMyStyle::GetStyleSetName()) {}

    virtual void RegisterCommands() override;

    TSharedPtr<FUICommandInfo> OpenSettings;
    TSharedPtr<FUICommandInfo> SaveAll;
};

// In RegisterCommands():
UI_COMMAND(OpenSettings, "Settings", "Open project settings", EUserInterfaceActionType::Button, FInputChord(EKeys::Comma, EModifierKey::Control));
```

### Binding Pattern

```cpp
CommandList->MapAction(
    FMyCommands::Get().OpenSettings,
    FExecuteAction::CreateRaw(this, &FMyClass::HandleOpenSettings),
    FCanExecuteAction::CreateLambda([]{ return true; })
);
```

### Extending Commands into MultiBox

See [MultiBox section](#multibox-menus--toolbars-multibox) — `FMenuBuilder::AddMenuEntry(FMyCommands::Get().OpenSettings, CommandList)`.

## Docking / Tab Manager (Docking/)

`FTabManager` manages a **layout** — a hierarchy of splitters and tab wells that can be serialized to/from JSON for workspace persistence.

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Tab spawner** | `FTabManager::RegisterTabSpawner(TabId, SpawnDelegate)` — registers how to create the content for a named tab |
| **Layout** | `FTabManager::FLayout` — tree of `FSplitter`/`FStack`/`FArea` nodes describing tab arrangement |
| **Tab well** | A `FStack` — a group of tabs sharing one space |
| **Nomad tab** | A tab not anchored to a specific area; can float or dock anywhere |
| **Major tab** | Top-level window-like tab (gets its own OS titlebar area in windowed mode) |

### Usage Pattern

```cpp
// Register spawners:
TabManager->RegisterTabSpawner(MyTabId, FOnSpawnTab::CreateLambda([](const FSpawnTabArgs&)
{
    return SNew(SDockTab).TabRole(ETabRole::PanelTab)
        [ SNew(SMyContent) ];
}));

// Define layout:
auto Layout = FTabManager::NewLayout("MyLayout_v1")
->AddArea(FTabManager::NewPrimaryArea()
    ->SetOrientation(Orient_Horizontal)
    ->Split(FTabManager::NewStack()->AddTab(MyTabId, ETabState::OpenedTab))
);

// Restore:
TSharedRef<SWidget> DockArea = TabManager->RestoreFrom(Layout, ParentWindow).ToSharedRef();
```

`FLayoutExtender` — add additional tabs to an existing layout without modifying the original layout definition (useful for plugins extending editor layouts).

**Key header:** `Engine/Source/Runtime/Slate/Public/Framework/Docking/TabManager.h`

## MultiBox — Menus & Toolbars (MultiBox/)

MultiBox is the unified system for menus, context menus, menu bars, and toolbars. All are built from a list of `FMultiBlock` entries.

### Builder API

| Builder | Produces |
|---------|----------|
| `FMenuBuilder` | Dropdown menu or context menu |
| `FMenuBarBuilder` | Top-level menu bar (File/Edit/Help row) |
| `FToolBarBuilder` | Horizontal toolbar |

```cpp
// Menu example:
FMenuBuilder MenuBuilder(/*bInShouldCloseWindowAfterMenuSelection=*/true, CommandList);
MenuBuilder.BeginSection("MySection", LOCTEXT("Section","My Section"));
MenuBuilder.AddMenuEntry(FMyCommands::Get().DoThing);
MenuBuilder.AddMenuSeparator();
MenuBuilder.AddSubMenu(
    LOCTEXT("SubMenu","Sub Menu"), LOCTEXT("SubMenuTip","..."),
    FNewMenuDelegate::CreateLambda([](FMenuBuilder& Sub){ Sub.AddMenuEntry(...); })
);
MenuBuilder.EndSection();
TSharedRef<SWidget> Menu = MenuBuilder.MakeWidget();
```

```cpp
// Toolbar example:
FToolBarBuilder TB(CommandList, FMultiBoxCustomization::None);
TB.BeginSection("Primary");
TB.AddToolBarButton(FMyCommands::Get().SaveAll);
TB.AddComboButton(FUIAction(), FOnGetContent::CreateLambda([](){ return SNew(SButton); }),
    LOCTEXT("More","More"), LOCTEXT("MoreTip","…"), FSlateIcon());
TB.EndSection();
```

### Extension Points

`FExtender` allows third-party code to inject entries into a pre-existing MultiBox:

```cpp
TSharedPtr<FExtender> Ext = MakeShared<FExtender>();
Ext->AddMenuExtension("MySection", EExtensionHook::After, CommandList,
    FMenuExtensionDelegate::CreateLambda([](FMenuBuilder& B){ B.AddMenuEntry(...); }));
```

**Key header:** `Engine/Source/Runtime/Slate/Public/Framework/MultiBox/MultiBoxBuilder.h`

## Text Layout Engine (Framework/Text/)

A complete text subsystem covering measurement, wrapping, shaping, editing, and rich markup.

### Architecture

```
FTextLayout (abstract base)
  └─ FSlateTextLayout (Slate integration)
       └─ FSlateEditableTextLayout (adds editing: cursor, selection, IME)

FTextLayout internals:
  ├─ FTextLayout::FLineModel[]     — one per paragraph (source text + runs)
  ├─ FTextLayout::FLineView[]      — one per visual line after wrapping
  └─ IRun[]                        — text segments with uniform formatting
       ├─ FSlateTextRun            — plain text run
       ├─ FSlateHyperlinkRun       — clickable hyperlink
       ├─ FSlateImageRun           — inline image
       └─ FSlateWidgetRun          — inline arbitrary SWidget
```

### Rich Text

```cpp
SNew(SRichTextBlock)
    .Text(LOCTEXT("Rich","Hello <TextStyle.Bold>world</> and <img id=\"star\"/>"))
    .DecoratorStyleSet(&FMyStyle::Get())
    + SRichTextBlock::ImageDecorator()
    + SRichTextBlock::HyperlinkDecorator("link", FSlateHyperlinkRun::FOnClick::CreateLambda([](const FSlateHyperlinkRun::FMetadata&){}))
```

### Syntax Highlighting

`FSyntaxHighlighterTextLayoutMarshaller` + `ISyntaxTokenizer` — tokenize source text and assign per-token `FTextBlockStyle` for colorized display. Used by the Blueprint string editor, shader source viewer, etc.

### Text Shaping

`FShapedTextCache` (`ShapedTextCache.h`) — caches `FShapedGlyphSequence` objects produced by HarfBuzz/ICU. Avoids re-shaping unchanged text runs. Cache is per `FSlateRenderer` and keyed by (font, text, scale).

**Key headers:**
- `Engine/Source/Runtime/Slate/Public/Framework/Text/TextLayout.h`
- `Engine/Source/Runtime/Slate/Public/Framework/Text/SlateTextLayout.h`
- `Engine/Source/Runtime/Slate/Public/Framework/Text/IRichTextMarkupParser.h`
- `Engine/Source/Runtime/Slate/Public/Framework/Text/ITextDecorator.h`

## Scroll Subsystem (Framework/Layout/)

| Type | Header | Description |
|------|--------|-------------|
| `FInertialScrollManager` | `InertialScrollManager.h` | Applies momentum after touch lift — call `UpdateScrollVelocity` each tick |
| `FOverscroll` | `Overscroll.h` | Rubber-band bounce physics at scroll boundaries |
| `FScrollyZoomy` | `ScrollyZoomy.h` | Unified pan+zoom input handler (canvas editors, image viewers) |
| `IScrollableWidget` | `IScrollableWidget.h` | Interface for programmatic `ScrollTo` |

## Notification Manager (Framework/Notifications/)

```cpp
// Fire a toast from anywhere:
FNotificationInfo Info(LOCTEXT("Saved","File saved successfully"));
Info.Image = FAppStyle::GetBrush("Icons.SuccessWithColor");
Info.FadeInDuration = 0.5f;
Info.ExpireDuration = 3.0f;
Info.FadeOutDuration = 0.5f;
Info.bUseThrobber = false;
TWeakPtr<SNotificationItem> Toast = FSlateNotificationManager::Get().AddNotification(Info);
// To update state:
if (Toast.IsValid()) Toast.Pin()->SetCompletionState(SNotificationItem::CS_Success);
```

**Key header:** `Engine/Source/Runtime/Slate/Public/Framework/Notifications/NotificationManager.h`
