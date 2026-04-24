# Unreal Engine Module Dependencies Reference

## Core Engine Modules

### Essential Modules
```csharp
PublicDependencyModuleNames.AddRange(new string[] {
    "Core",           // Fundamental types, containers, math
    "CoreUObject",    // UObject system, reflection
    "Engine",         // Core engine functionality
});
```

### Input and Player
```csharp
"InputCore",          // Input system
"EnhancedInput",      // Enhanced input system (UE5)
"SlateCore",          // UI core
"Slate",              // UI widgets
"UMG",                // Unreal Motion Graphics (UI)
```

### Gameplay Framework
```csharp
"GameplayAbilities",  // Gameplay Ability System
"GameplayTags",       // Gameplay tag system
"GameplayTasks",      // Async gameplay tasks
"ModularGameplay",    // Modular gameplay features
"AIModule",           // AI framework
```

### Networking
```csharp
"OnlineSubsystem",    // Online services
"OnlineSubsystemUtils", // Online utilities
"Sockets",            // Network sockets
"Networking",         // Network layer
"ReplicationGraph",   // Replication optimization
```

### Rendering and VFX
```csharp
"RenderCore",         // Core rendering
"RHI",                // Render Hardware Interface
"Niagara",            // Niagara VFX system
"NiagaraCore",        // Niagara core
```

### Audio
```csharp
"AudioMixer",         // Audio engine
"AkAudio",            // Wwise integration (third-party)
```

### Physics
```csharp
"PhysicsCore",        // Core physics
"Chaos",              // Chaos physics engine
"ChaosVehicles",      // Vehicle physics
```

## Editor-Only Modules

Use in `PrivateDependencyModuleNames` and wrap code with `#if WITH_EDITOR`:

```csharp
PrivateDependencyModuleNames.AddRange(new string[] {
    "UnrealEd",           // Editor framework
    "EditorSubsystem",    // Editor subsystems
    "AssetTools",         // Asset management
    "ContentBrowser",     // Content browser
    "PropertyEditor",     // Property customization
    "Kismet",             // Blueprint editor
    "KismetCompiler",     // Blueprint compiler
    "BlueprintGraph",     // Blueprint graph
    "GameProjectGeneration", // Project tools
});
```

## ProjectLungfish Modules

### Core Game Modules
```csharp
"ProjectLungfishGame",    // Main game module
"PLCoreGame",             // Core game framework
"GASExtendedPL",          // Extended GAS features
```

### Editor Modules (Editor builds only)
```csharp
"ProjectLungfishEditor",  // Editor extensions
"PLCoreEditor",           // Core editor tools
```

### Plugins
```csharp
"PLPythonPipeline",       // Python automation
"AngelscriptCode",        // AngelScript integration
```

## Third-Party Modules

### Wwise Audio
```csharp
"AkAudio",
"WwiseResourceLoader",
"WwiseSoundEngine",
```

### Graphics Enhancement
```csharp
"DLSS",                   // NVIDIA DLSS
"DLSSBlueprint",          // DLSS Blueprint support
"Streamline",             // NVIDIA Streamline
"StreamlineBlueprint",    // Streamline Blueprint
```

### Marketplace Plugins
```csharp
"ElectronicNodes",        // Visual scripting enhancement
"DragonIKPlugin",         // IK system
"OceanologyPlugin",       // Water system
```

## Dependency Rules

### Public vs Private Dependencies

**PublicDependencyModuleNames**:
- Exposed in header files
- Required by code that includes your headers
- Transitive to dependent modules

**PrivateDependencyModuleNames**:
- Only used in .cpp files
- Not exposed to dependent modules
- Faster compile times (use when possible)

### Example
```csharp
// YourModule.Build.cs
public class YourModule : ModuleRules
{
    public YourModule(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

        PublicDependencyModuleNames.AddRange(new string[]
        {
            "Core",
            "CoreUObject",
            "Engine",
            "GameplayAbilities",  // Used in headers
        });

        PrivateDependencyModuleNames.AddRange(new string[]
        {
            "Slate",
            "SlateCore",
            "UMG",                // Only used in .cpp files
        });

        // Editor-only dependencies
        if (Target.bBuildEditor)
        {
            PrivateDependencyModuleNames.AddRange(new string[]
            {
                "UnrealEd",
                "PropertyEditor",
            });
        }
    }
}
```

## Common Dependency Errors

### Error: Unresolved external symbol
**Cause**: Missing module dependency
**Solution**: Add required module to Build.cs

### Error: Cannot open include file
**Cause**: Header from module not in dependencies
**Solution**:
1. Add module to PublicDependencyModuleNames (if used in headers)
2. Or add to PrivateDependencyModuleNames (if only in .cpp)

### Error: Circular dependency detected
**Cause**: Two modules depend on each other
**Solution**:
1. Use forward declarations instead of includes in headers
2. Refactor common code to a new module
3. Use interfaces to break the cycle

## Module Loading Order

Specified in `.uproject` file:

```json
{
    "Name": "YourModule",
    "Type": "Runtime",
    "LoadingPhase": "Default"
}
```

**Loading Phases**:
- **PreDefault**: Before engine initialization
- **Default**: Normal game modules (most common)
- **PostEngineInit**: After engine is initialized
- **PreLoadingScreen**: Before loading screen
- **PostDefault**: After default modules

## Performance Tips

### Minimize Public Dependencies
```csharp
// Good - only expose what's needed
PublicDependencyModuleNames.AddRange(new string[] {
    "Core", "CoreUObject", "Engine"
});
PrivateDependencyModuleNames.AddRange(new string[] {
    "Slate", "SlateCore", "UMG", "AIModule"
});

// Bad - exposing everything
PublicDependencyModuleNames.AddRange(new string[] {
    "Core", "CoreUObject", "Engine", "Slate", "SlateCore", "UMG", "AIModule"
});
```

### Use Forward Declarations
```cpp
// Header file - forward declare instead of include
class UGameplayAbility;
class UAbilitySystemComponent;

// CPP file - include here
#include "Abilities/GameplayAbility.h"
#include "AbilitySystemComponent.h"
```

### Circular Include Prevention
```cpp
// Instead of:
#include "CharacterSystem.h"  // In both headers

// Use:
class UCharacterSystem;  // Forward declaration
```

## Verification Commands

### Check Module Dependencies
```bash
# View module dependencies in .uproject
cat Main/ProjectLungfish.uproject | grep -A5 "Modules"

# Check specific Build.cs file
cat Main/Source/ProjectLungfishGame/ProjectLungfishGame.Build.cs
```

### Build Specific Module
```bash
"Engine/Binaries/DotNET/UnrealBuildTool/UnrealBuildTool.exe" YourModule Win64 Development
```
