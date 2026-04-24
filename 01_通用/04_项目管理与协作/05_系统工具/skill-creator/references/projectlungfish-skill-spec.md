# ProjectLungfish SKILL.md Creation Specification

Guidelines for creating SKILL.md documentation for ProjectLungfish.

## 1. Quick Start

### Minimal Template

```markdown
---
name: my-module
title: My Module System
description: Brief description of what this module does and why it exists.
tags: [C++, Gameplay, Component-Based]
---

# My Module System

> Layer: Tier 3 (Module Documentation)

## System Overview

[Your content here...]

## Architecture

[Your content here...]

## Code Locations

**Primary Files:**
- `Main/Plugins/MyPlugin/Source/MyModule.h`
- `Main/Plugins/MyPlugin/Source/MyModule.cpp`
```

## 2. YAML Frontmatter

### Required Fields

```yaml
---
name: unique-module-id    # kebab-case, unique across all SKILL.md
title: Human Readable Title
description: Natural language description (1-3 sentences)
tags: [Tag1, Tag2, Tag3]  # 3-8 tags
---
```

### Field Details

**`name`**: kebab-case, unique identifier
- Examples: `claudetasks-building`, `main-plugins`, `engine-modifications`
- No spaces, underscores, or special characters except hyphens

**`title`**: Human-readable title case
- Examples: "Building System", "Plugin Ecosystem"

**`description`**: Natural language, explain WHAT and WHY
- Good: "Building system covering block merge, placement validation, recipe generators..."
- Bad: "This module handles building."

**`tags`**: 3-8 tags, Title-Case with hyphens
- Examples: `[Building, Block-Merge, C++, Component-Based]`

## 3. Tag Classification System

### Categories

**Technology**:
```
C++, Blueprint, Python, AngelScript
GAS, CommonUI, Enhanced-Input
```

**Domain**:
```
Building, Crafting, Combat, Equipment
Weather, Inventory, Damage
```

**Architecture**:
```
Plugin-Architecture, Modular-System, Component-Based
Data-Driven, State-Machine
```

## 4. File Location Requirements

**MUST** be in root directory of scope, NOT in subdirectories:

```
✅ SKILL.md                          # Project root (Tier 1)
✅ Main/SKILL.md                     # Main project (Tier 2)
✅ Main/Plugins/SKILL.md             # Plugins overview (Tier 2)
✅ Main/Plugins/AssetScanner/SKILL.md # Plugin root (Tier 3)
```

**NOT**:
```
❌ Main/Plugins/AssetScanner/Docs/SKILL.md
❌ Main/Plugins/AssetScanner/Docs/skills/SKILL.md
```

### Three-Tier Architecture

| Tier | Location | Purpose |
|------|----------|---------|
| 1 | `SKILL.md` | Project overview |
| 2 | `Main/SKILL.md`, `ClaudeTasks/SKILL.md` | Domain overviews |
| 3 | `ClaudeTasks/Building/SKILL.md` | Module docs |

## 5. Standard Section Structure

```markdown
# Module Name

> Layer: Tier 3

## System Overview

Brief introduction

## Architecture

High-level design

## Key Components

- Component A: Description

## Code Locations

**Primary Files:**
- Path/To/File.h

## Debugging

Console commands, debug tools
```

### Markdown Rules

- `#` = document title (once only)
- `##` = major sections
- `###` = subsections
- Code blocks: use language-specific highlighting
- Links: prefer relative paths `[Link](RelativePath/SKILL.md)`

## 6. Examples

### Tier 1 (Project Root)

```markdown
---
name: projectlungfish
title: ProjectLungfish - Survival/Crafting Game
description: UE5 survival/crafting game with building system, GAS abilities, and multiplayer. Plugin-based architecture.
tags: [Unreal-Engine, GAS, Survival, Crafting, Building, Multiplayer, C++]
---

# ProjectLungfish

> Layer: Tier 1
```

### Tier 3 (Module)

```markdown
---
name: claudetasks-building
title: Building System
description: Building system covering block merge, placement validation, recipe generators, variant system, and auto-attach modes.
tags: [Building, Block-Merge, Spatial-Check, Recipe-System, C++, Component-Based]
---

# Building System

> Layer: Tier 3

## System Overview

The building system allows players to construct structures...

## Architecture

UPLBuildingComponent
├── Block Merge Manager
└── Placement Validator
```

---

## Summary

- **Required**: name, title, description, tags
- **Tags**: 3-8 per module
- **Location**: Root of scope, not subdirectories
- **Sections**: Use `##` for major sections
