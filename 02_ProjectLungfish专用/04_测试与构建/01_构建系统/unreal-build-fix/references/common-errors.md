# Common Unreal Build Errors - Quick Reference

## Error Code Quick Lookup

### C2065: Undeclared Identifier
**Quick Fix**: Add include for the type
```cpp
#include "Path/To/TypeHeader.h"
```

### C2653: Not a Class or Namespace
**Quick Fix**: Add include or check spelling
```cpp
#include "Correct/Path/Header.h"
```

### LNK2019: Unresolved External Symbol
**Quick Fix**: Add module to Build.cs
```csharp
PublicDependencyModuleNames.Add("MissingModule");
```

### C1010: Unexpected End of File (PCH)
**Quick Fix**: Ensure PCH include is first
```cpp
#include "YourModule.h"  // Must be first
```

### C4275: Non DLL-Interface Class
**Quick Fix**: Add API export macro
```cpp
class YOURMODULE_API UMyClass : public UObject
```

## Error Message Patterns

### "Cannot open include file"
**Cause**: Missing include path or wrong path
**Fix**:
```cpp
// Check exact path in engine source
grep -r "class UClassName" Engine/Source/
// Then use correct path
#include "Correct/Path/ClassName.h"
```

### "Undefined symbol" or "Unresolved external"
**Cause**: Module not linked
**Fix**: Add to Build.cs dependencies

### "Expected a UCLASS, USTRUCT or UENUM"
**Cause**: Missing or misplaced reflection macro
**Fix**: Ensure GENERATED_BODY() is present
```cpp
UCLASS()
class MODULENAME_API UMyClass : public UObject
{
    GENERATED_BODY()
};
```

### "Unable to instantiate module"
**Cause**: Module dependency chain broken
**Fix**: Check all dependencies in Build.cs are correct

## Module-Specific Error Fixes

### GameplayAbilities Errors
```csharp
// Add to Build.cs
PublicDependencyModuleNames.AddRange(new string[] {
    "GameplayAbilities",
    "GameplayTags",
    "GameplayTasks",
});
```

```cpp
// Common includes
#include "AbilitySystemComponent.h"
#include "Abilities/GameplayAbility.h"
#include "AttributeSet.h"
#include "GameplayEffect.h"
#include "GameplayTagContainer.h"
```

### CommonUI Errors
```csharp
// Add to Build.cs
PublicDependencyModuleNames.AddRange(new string[] {
    "CommonUI",
    "CommonInput",
    "UMG",
});
```

```cpp
// Common includes
#include "CommonActivatableWidget.h"
#include "CommonUserWidget.h"
#include "Input/CommonUIInputTypes.h"
```

### Niagara Errors
```csharp
// Add to Build.cs
PublicDependencyModuleNames.AddRange(new string[] {
    "Niagara",
    "NiagaraCore",
});
```

```cpp
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
```

### Enhanced Input Errors
```csharp
// Add to Build.cs
PublicDependencyModuleNames.Add("EnhancedInput");
```

```cpp
#include "InputAction.h"
#include "InputMappingContext.h"
#include "EnhancedInputComponent.h"
```

## ProjectLungfish Specific

### PLCoreGame Module Errors
```csharp
PublicDependencyModuleNames.Add("PLCoreGame");
```

```cpp
// Common PLCore includes (adjust path as needed)
#include "AbilitySystem/PLAbilitySystemComponent.h"
#include "Character/PLCharacter.h"
#include "Equipment/PLEquipmentDefinition.h"
```

### GASExtendedPL Module Errors
```csharp
PublicDependencyModuleNames.Add("GASExtendedPL");
```

```cpp
// Extended GAS includes
#include "Building/PLBuildingComponent.h"
#include "Crafting/PLCraftingComponent.h"
```

### AngelScript Integration Errors
```csharp
PublicDependencyModuleNames.Add("AngelscriptCode");
```

```cpp
#include "AngelscriptBinds.h"
#include "AngelscriptManager.h"
```

## Syntax Error Quick Fixes

### UPROPERTY Syntax
```cpp
// Correct
UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "MyCategory")
int32 MyValue;

// Common mistakes:
// - Missing comma between specifiers
// - Category without equals sign
// - Missing semicolon after property
```

### UFUNCTION Syntax
```cpp
// Correct
UFUNCTION(BlueprintCallable, Category = "MyCategory")
void MyFunction();

// Common mistakes:
// - BlueprintCallable on private function (won't work)
// - Missing Category (causes warning)
// - Return value not UPARAM annotated for out params
```

### UCLASS Syntax
```cpp
// Correct
UCLASS(BlueprintType, Blueprintable)
class MODULENAME_API UMyClass : public UObject
{
    GENERATED_BODY()

public:
    // Members
};

// Common mistakes:
// - Missing GENERATED_BODY()
// - Wrong API macro (module name mismatch)
// - Missing public: section for exposed members
```

## Build Configuration Issues

### "Target rules file not found"
**Fix**: Regenerate project files
```bash
GenerateProjectFiles.bat
```

### "Unable to find type for module"
**Check**:
1. Module name matches folder name
2. Build.cs has correct class name
3. .uproject lists module correctly

### "Module already loaded"
**Fix**: Clean intermediate files
```bash
rm -rf Main/Intermediate/
```

## Platform-Specific Errors

### Windows Errors
- Path too long: Use shorter paths or enable long path support
- Permission denied: Run as administrator or check antivirus

### Build Tool Errors
- Out of memory: Close other applications or increase page file
- Access denied on DLL: Close editor before building

## Quick Diagnosis Flow

```
Error Occurred
│
├─ Contains "C2065" or "undeclared"? → Add include
├─ Contains "LNK2019" or "unresolved"? → Add module to Build.cs
├─ Contains "UCLASS" or "USTRUCT"? → Fix reflection macro
├─ Contains "cannot open include"? → Check include path
├─ Contains "already defined"? → Check for circular includes
├─ Contains "API" or "DLL interface"? → Add MODULE_API export
└─ Contains "PCH" or "precompiled"? → Fix include order
```

## Emergency Reset

If build is completely broken:

```bash
# 1. Close editor
# 2. Delete generated files
rm -rf Main/Intermediate/
rm -rf Main/Binaries/
rm -rf Main/Saved/
rm -rf .vs/

# 3. Regenerate project
GenerateProjectFiles.bat

# 4. Full rebuild
"Engine/Binaries/DotNET/UnrealBuildTool/UnrealBuildTool.exe" ProjectLungfishEditor Win64 Development -Project="<PROJECT_ROOT>/Main/ProjectLungfish.uproject" -clean
```

## Most Common Mistakes

1. **Forgetting module dependency** - Always check Build.cs first
2. **Wrong include path** - Use grep to find correct path
3. **Missing API export** - Add MODULENAME_API to public classes
4. **PCH not first** - First include must be module header
5. **Circular includes** - Use forward declarations in headers

## Prevention Checklist

Before writing new C++ code:
- [ ] Know which module it belongs to
- [ ] Identify required dependencies
- [ ] Plan header includes (use forward declarations)
- [ ] Verify module exists in .uproject
- [ ] Update Build.cs with new dependencies
- [ ] Use correct reflection macros
- [ ] Add API export for public classes
