---
name: unreal-build-fix
description: Unreal Engine build error diagnosis and resolution. Use when encountering "error", "build failed", "compilation", "linking", "LNK", "C2065", "unresolved", or any build/compile errors. Provides systematic troubleshooting for common build issues, module dependency errors, reflection macro problems, and linker errors.
tags: [fix, compile, error]
---

# Unreal Engine Build Troubleshooting

## Quick Diagnosis Workflow

When a build fails, follow this systematic approach:

1. **Identify Error Type**: Compilation, linking, or module loading
2. **Locate Root Cause**: First error in output (ignore cascading errors)
3. **Apply Fix**: Use appropriate solution from this guide
4. **Rebuild**: Clean build if necessary
5. **Verify**: Ensure error is resolved and no new errors introduced

## Common Error Categories

### 1. Missing Include Errors

**Error Pattern**:
```
error C2065: 'UGameplayAbility': undeclared identifier
error C2653: 'FGameplayTag': is not a class or namespace name
error: unknown type name 'UAbilitySystemComponent'
```

**Diagnosis**:
- Class/type used but header not included
- Forward declaration insufficient for usage

**Solutions**:

**Quick Fix**: Add missing include
```cpp
// Add to .cpp file (preferred) or .h file if needed
#include "Abilities/GameplayAbility.h"
#include "GameplayTagContainer.h"
#include "AbilitySystemComponent.h"
```

**Prevention**: Use forward declarations in headers
```cpp
// In .h file - forward declare
class UGameplayAbility;
class UAbilitySystemComponent;

// In .cpp file - full include
#include "Abilities/GameplayAbility.h"
#include "AbilitySystemComponent.h"
```

**Common Missing Includes**:
```cpp
// Gameplay Abilities
#include "AbilitySystemComponent.h"
#include "Abilities/GameplayAbility.h"
#include "AttributeSet.h"
#include "GameplayEffect.h"

// Gameplay Tags
#include "GameplayTagContainer.h"
#include "NativeGameplayTags.h"

// Core
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "Components/ActorComponent.h"

// UI
#include "Blueprint/UserWidget.h"
#include "Components/Widget.h"
```

### 2. Unresolved External Symbol (Linker Errors)

**Error Pattern**:
```
error LNK2019: unresolved external symbol "public: __cdecl UAbilitySystemComponent::UAbilitySystemComponent"
error LNK2001: unresolved external symbol "public: virtual void __cdecl UMyClass::Function"
```

**Diagnosis**:
- Function declared but not implemented
- Module dependency missing in Build.cs
- Library not linked

**Solutions**:

**Solution 1**: Add missing module dependency
```csharp
// In YourModule.Build.cs
PublicDependencyModuleNames.AddRange(new string[]
{
    "Core",
    "CoreUObject",
    "Engine",
    "GameplayAbilities",  // Add this if using GAS
    "GameplayTags",       // Add this if using tags
});
```

**Solution 2**: Implement declared function
```cpp
// If function is declared in .h but not implemented
void UMyClass::MyFunction()
{
    // Implementation here
}
```

**Solution 3**: Check template/inline implementations
```cpp
// Templates must be in header or explicitly instantiated
template<typename T>
void MyTemplateFunction(T Value)  // Must be in .h file
{
    // Implementation
}
```

### 3. Module Dependency Errors

**Error Pattern**:
```
error: Module 'YourModule' depends on 'GameplayAbilities' which is not loaded
error: Unable to instantiate module 'YourModule': Unable to load dependent module 'SomeModule'
```

**Diagnosis**:
- Build.cs missing module in dependencies
- Module not enabled in .uproject
- Circular dependency

**Solutions**:

**Solution 1**: Add to Build.cs
```csharp
PublicDependencyModuleNames.AddRange(new string[]
{
    "GameplayAbilities",
    "GameplayTags",
    "GameplayTasks",
});
```

**Solution 2**: Enable in .uproject
```json
{
    "Name": "GameplayAbilities",
    "Enabled": true
}
```

**Solution 3**: Fix circular dependency
```cpp
// Break cycle with forward declarations
// Or refactor common code to new module
```

### 4. Reflection Macro Errors

**Error Pattern**:
```
error: Expected a UCLASS, USTRUCT or UENUM
error: UPROPERTY is not allowed here
error: UFUNCTION not valid in this context
```

**Diagnosis**:
- Missing or incorrect reflection macro
- Macro in wrong location
- Syntax error in macro parameters

**Solutions**:

**Correct UCLASS usage**:
```cpp
// In .h file
UCLASS()
class YOURMODULE_API UMyClass : public UObject
{
    GENERATED_BODY()

public:
    UPROPERTY(BlueprintReadWrite, Category = "MyCategory")
    int32 MyValue;

    UFUNCTION(BlueprintCallable, Category = "MyCategory")
    void MyFunction();
};
```

**Common macro patterns**:
```cpp
// Class
UCLASS(BlueprintType, Blueprintable)
class MODULENAME_API UMyClass : public UObject

// Struct
USTRUCT(BlueprintType)
struct FMyStruct

// Enum
UENUM(BlueprintType)
enum class EMyEnum : uint8

// Property
UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Name")

// Function
UFUNCTION(BlueprintCallable, Category = "Name")
```

### 5. Missing API Export Macro

**Error Pattern**:
```
warning C4275: non dll-interface class used as base
error LNK2019: unresolved external symbol (in other modules using this class)
```

**Diagnosis**:
- Class declared without MODULE_API macro
- Trying to use class across module boundaries

**Solution**:
```cpp
// Add MODULE_API macro to class declaration
// Replace YOURMODULE with your module name in uppercase
class YOURMODULE_API UMyClass : public UObject
{
    // ...
};

// For structs
struct YOURMODULE_API FMyStruct
{
    // ...
};
```

**Module Name Mapping**:
- `ProjectLungfishGame` → `PROJECTLUNGFISHGAME_API`
- `PLCoreGame` → `PLCOREGAME_API`
- `GASExtendedPL` → `GASEXTENDEDPL_API`

### 6. Precompiled Header Errors

**Error Pattern**:
```
fatal error C1010: unexpected end of file while looking for precompiled header
error: expected precompiled header
```

**Diagnosis**:
- Missing #include for PCH
- PCH not first include

**Solution**:
```cpp
// First line of every .cpp file must be:
#include "YourModule.h"  // Or your module's PCH file

// Then other includes
#include "OtherHeaders.h"
```

**Or disable PCH** (in Build.cs):
```csharp
PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
// Or
PCHUsage = PCHUsageMode.NoPCHs;  // If PCH causes issues
```

### 7. Build Tool Errors

**Error Pattern**:
```
error: Couldn't find target rules file for target 'ProjectLungfishEditor'
error: Unable to instantiate instance of 'YourModule' because unable to find type
```

**Diagnosis**:
- Project files out of sync
- Build.cs syntax error
- Target.cs misconfiguration

**Solutions**:

**Solution 1**: Regenerate project files
```bash
GenerateProjectFiles.bat
```

**Solution 2**: Check Build.cs syntax
```csharp
// Ensure proper syntax
public class YourModule : ModuleRules
{
    public YourModule(ReadOnlyTargetRules Target) : base(Target)
    {
        // Configuration
    }
}
```

**Solution 3**: Verify module registration
```cpp
// In YourModule.cpp
IMPLEMENT_MODULE(FDefaultModuleImpl, YourModule)
// Or for custom module:
IMPLEMENT_GAME_MODULE(FYourModule, YourModule);
```

## Systematic Debugging Process

### Step 1: Read Error Message Carefully

**Focus on**:
- First error in output (others may be cascading)
- File and line number
- Specific symbol or type mentioned

**Ignore**:
- Cascading errors (fix first error first)
- Warnings (unless they're related)

### Step 2: Identify Error Category

Use patterns above to categorize:
- Missing include? → Add header
- Unresolved external? → Check module dependencies
- Macro error? → Fix reflection syntax
- Linker error? → Add module to Build.cs

### Step 3: Apply Appropriate Fix

**For includes**:
```bash
# Search for header location
grep -r "class UGameplayAbility" Engine/Source/
# Then add: #include "Path/To/Header.h"
```

**For module dependencies**:
```csharp
// Add to Build.cs
PublicDependencyModuleNames.Add("ModuleName");
```

### Step 4: Clean Build if Needed

**When to clean build**:
- Changing module dependencies
- After regenerating project files
- Persistent errors after fix
- Random "already defined" errors

**How to clean**:
```bash
# Delete intermediate files
rm -rf Main/Intermediate/
rm -rf Main/Binaries/

# Rebuild
"Engine/Binaries/DotNET/UnrealBuildTool/UnrealBuildTool.exe" ProjectLungfishEditor Win64 Development -Project="<PROJECT_ROOT>/Main/ProjectLungfish.uproject"
```

## Advanced Troubleshooting

### Circular Include Detection

**Problem**: Headers including each other
**Symptom**: "class already defined" or compilation hangs

**Solution**:
```cpp
// Break cycle with forward declarations
// In Header1.h
class UClass2;  // Forward declare instead of #include

class MODULENAME_API UClass1 : public UObject
{
    UClass2* MyReference;  // Pointer only, forward declaration OK
};

// In Header1.cpp
#include "Class2.h"  // Full include in .cpp file
```

### Template Compilation Issues

**Problem**: Template function linker errors
**Solution**: Templates must be in headers
```cpp
// In .h file
template<typename T>
void MyFunction(T Value)
{
    // Implementation must be here, not in .cpp
}

// Or use explicit instantiation in .cpp:
template void MyFunction<int>(int);
template void MyFunction<float>(float);
```

### Hot Reload Failures

**Problem**: Changes not reflecting, or editor crashes
**Solution**:
1. Close editor completely
2. Full rebuild from command line
3. Relaunch editor
4. Never trust hot reload for major changes

### Module Loading Order Issues

**Problem**: Module initialization errors
**Solution**: Check .uproject loading phase
```json
{
    "Name": "YourModule",
    "Type": "Runtime",
    "LoadingPhase": "Default"  // Try "PostEngineInit" if issues
}
```

## Quick Reference

### Most Common Fixes

```cpp
// 1. Add include
#include "RequiredHeader.h"

// 2. Add module dependency (Build.cs)
PublicDependencyModuleNames.Add("ModuleName");

// 3. Add API export
class YOURMODULE_API UMyClass : public UObject

// 4. Fix UCLASS
UCLASS()
class YOURMODULE_API UMyClass : public UObject
{
    GENERATED_BODY()
};

// 5. Forward declaration
class USomeClass;  // In header
#include "SomeClass.h"  // In .cpp
```

### Build Commands

```bash
# Standard build
"Engine/Binaries/DotNET/UnrealBuildTool/UnrealBuildTool.exe" ProjectLungfishEditor Win64 Development -Project="<PROJECT_ROOT>/Main/ProjectLungfish.uproject"

# Regenerate project files
GenerateProjectFiles.bat

# Clean build
rm -rf Main/Intermediate/ Main/Binaries/
# Then rebuild
```

### Diagnostic Commands

```bash
# Find header location
grep -r "class UMyClass" Engine/Source/ Main/

# Check module dependencies
cat Main/Source/YourModule/YourModule.Build.cs

# View build errors only
# (Build output) | grep "error"
```

## Error Priority

Fix errors in this order:

1. **PCH errors** - Must be fixed first (affects entire module)
2. **Module dependency errors** - Blocks other compilation
3. **Missing includes** - Usually easy quick wins
4. **Reflection macro errors** - Fix before linker errors
5. **Linker errors** - Usually fixed by above steps
6. **Warnings** - Address after all errors resolved

## Related Skills

- **unreal-cpp-workflow**: General C++ development workflow
- **Engine/SKILL.md**: Engine source modifications (@CYANCOOK standards)
- **p4-workflow**: Version control integration

## When to Escalate

If standard fixes don't work:
1. Check UE5 documentation for breaking changes
2. Search AnswerHub/Forums for specific error
3. Verify engine version compatibility
4. Consider if engine modification caused issue
5. Try minimal reproduction in clean project
