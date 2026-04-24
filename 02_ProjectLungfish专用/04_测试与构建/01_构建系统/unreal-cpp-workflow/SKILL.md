---
name: unreal-cpp-workflow
description: Core Unreal Engine C++ development workflow for ProjectLungfish. Use when working with .cpp, .h, .build.cs files, C++ code, or when user mentions "cpp", "header", "source", "compile", "build". Handles code modification, compilation, module dependencies, and basic testing. Essential for all C++ development in Main/Source/ directory.
---

# Unreal C++ Development Workflow

## Quick Reference

### Build Command (From Project Root)
```bash
cd <PROJECT_ROOT>
"Engine/Binaries/DotNET/UnrealBuildTool/UnrealBuildTool.exe" ProjectLungfishEditor Win64 Development -Project="<PROJECT_ROOT>/Main/ProjectLungfish.uproject"
```

### Common Module Dependencies (Build.cs)
```csharp
PublicDependencyModuleNames.AddRange(new string[] {
    "Core", "CoreUObject", "Engine",
    "GameplayAbilities", "GameplayTags", "GameplayTasks"
});
```

## Standard Workflow

### 1. Check File Permissions
Before modifying any file:
```bash
ls -la "path/to/file.cpp"
```

If file is read-only (P4 managed):
- The `p4-workflow` skill will be auto-triggered
- File will be checked out to appropriate changelist

### 2. Make Code Changes

Follow Unreal Engine C++ coding standards:
- Use proper UE5 reflection macros: `UCLASS()`, `UPROPERTY()`, `UFUNCTION()`
- Include required headers
- Maintain separation between runtime and editor code
- Use forward declarations to minimize compile dependencies

**IMPORTANT**: If modifying files in `Engine/` or `Main/Plugins/Marketplace/` directories, follow the @CYANCOOK comment block standards documented in `.claude/rules/cyancook-annotation.md`.

### 3. Update Module Dependencies

If adding new functionality that requires additional modules, update the `.Build.cs` file:

```csharp
// In YourModule.Build.cs
PublicDependencyModuleNames.AddRange(new string[] {
    "NewModule",  // Add required modules
});

// Or for private dependencies:
PrivateDependencyModuleNames.AddRange(new string[] {
    "InternalModule",
});
```

Common modules:
- **Core**: Basic UE types and containers
- **CoreUObject**: UObject system
- **Engine**: Core engine functionality
- **GameplayAbilities**: GAS framework
- **GameplayTags**: Tag system
- **ModularGameplay**: Modular game features
- **CommonUI**: Advanced UI framework
- **Niagara**: VFX system

### 4. Build the Project

```bash
cd <PROJECT_ROOT>
"Engine/Binaries/DotNET/UnrealBuildTool/UnrealBuildTool.exe" ProjectLungfishEditor Win64 Development -Project="<PROJECT_ROOT>/Main/ProjectLungfish.uproject"
```

**Build Configurations**:
- **Development Editor**: Primary development (recommended)
- **Development**: Game without editor
- **Shipping**: Final release with optimizations

**Build Targets**:
- **ProjectLungfishEditor**: Editor build (most common)
- **ProjectLungfishGame**: Game runtime
- **ProjectLungfishClient**: Client-only
- **ProjectLungfishServer**: Dedicated server

### 5. Handle Build Errors

If build fails, the `unreal-build-fix` skill will be auto-triggered to help diagnose issues.

Common quick fixes:
- **Missing include**: Add `#include "RequiredHeader.h"`
- **Unresolved external**: Add module to Build.cs dependencies
- **Reflection error**: Check UCLASS/UPROPERTY syntax
- **Circular dependency**: Use forward declarations

### 6. Verify in Editor

After successful build:
1. Launch Unreal Editor
2. Check Output Log for warnings/errors
3. Test modified functionality
4. For AngelScript issues: Check `Main/Saved/Logs/ProjectLungfish.log` (Angelscript channel)

## Code Quality Standards

### Keep Changes Minimal
- Only modify what's necessary for the task
- Avoid over-engineering and premature abstractions
- Don't add unnecessary error handling for impossible scenarios
- Don't add comments/docstrings to unchanged code

### Proper Error Handling
- Validate at system boundaries (user input, external APIs)
- Trust internal code and framework guarantees
- Use `check()` for programmer errors
- Use `ensure()` for recoverable errors with logging

### Performance Considerations
- Avoid unnecessary allocations in hot paths
- Use `const&` for large parameters
- Prefer `TArrayView` over copying arrays
- Consider replication costs for multiplayer code

## Integration with Other Skills

### Auto-Triggered Skills

This skill may automatically trigger related skills:

- **p4-workflow**: When encountering read-only files
- **Engine/SKILL.md**: Reference for modifying `Engine/` directory files
- **@CYANCOOK spec**: `.claude/rules/cyancook-annotation.md` — patterns and scope rules
- **unreal-build-fix**: When build errors occur
- **unreal-angelscript**: When working with script integration

### Documentation Updates

After completing C++ changes:
- Update relevant `ClaudeTasks/*.md` files
- Document new features in appropriate category
- Update module documentation if architecture changed

## Testing and Validation

### Basic Testing
- Compile with no warnings (when practical)
- Launch editor and verify no runtime errors
- Test the specific functionality you modified
- Check for replication issues if multiplayer-relevant

### Advanced Testing
- Use Unreal's automation framework for unit tests
- Profile performance-critical changes with Unreal Insights
- Test with different build configurations if appropriate
- Verify hot reload functionality works

## Common File Locations

### Source Code
- **Main Game**: `Main/Source/ProjectLungfishGame/`
- **Editor**: `Main/Source/ProjectLungfishEditor/`
- **Core Plugin**: `Main/Plugins/ProjectLungfishCore/`
- **Extended GAS**: `Main/Plugins/GASExtendedPL/`

### Build Files
- **Game Target**: `Main/Source/ProjectLungfish.Target.cs`
- **Editor Target**: `Main/Source/ProjectLungfishEditor.Target.cs`
- **Module Build**: `Main/Source/*/[ModuleName].Build.cs`

### Configuration
- **Project**: `Main/ProjectLungfish.uproject`
- **Config**: `Main/Config/*.ini`

## Build System Details

### Generate Project Files
If Visual Studio project files are out of sync:
```bash
GenerateProjectFiles.bat
```

### Hot Reload
For small changes during editor runtime:
- Use Ctrl+Alt+F11 in editor (if configured)
- Or close editor, rebuild, relaunch for guaranteed clean state

### Module Loading
Modules load in phases specified in `.uproject`:
- **PreDefault**: Before engine init
- **Default**: Normal game modules (most common)
- **PostEngineInit**: After engine initialization

## Best Practices

### Before Starting
1. Create P4 changelist for this task
2. Check out all files you'll modify
3. Verify build is clean before making changes

### During Development
1. Make incremental changes
2. Build frequently to catch errors early
3. Test each change before moving on
4. Keep commits focused and atomic

### Before Completing
1. Final build with no errors/warnings
2. Test in editor
3. Update ClaudeTasks documentation
4. Verify P4 changelist contains only relevant files
5. Update changelist description

## Debugging Tools

### Built-in Tools
- **Output Log**: Runtime errors and warnings
- **Visual Logger**: Gameplay debugging
- **Stats System**: Performance monitoring
- **Memory Profiler**: Memory usage analysis

### External Tools
- **Visual Studio Debugger**: C++ debugging
- **Unreal Insights**: Advanced profiling
- **ReSharper C++**: Code analysis and refactoring

### Logging
```cpp
UE_LOG(LogTemp, Warning, TEXT("Debug message: %s"), *SomeString);
UE_LOG(LogTemp, Error, TEXT("Error occurred: %d"), ErrorCode);
```

## Additional Resources

For specialized workflows, see:
- **references/module-dependencies.md**: Detailed module dependency reference
- **Engine/SKILL.md**: Engine source modifications
- **@CYANCOOK spec**: `.claude/rules/cyancook-annotation.md` — patterns and scope rules
- **unreal-build-fix** skill: Build error troubleshooting
- **unreal-angelscript** skill: Script integration
