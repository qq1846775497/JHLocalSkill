---
name: core-redirects-debug
description: Diagnose and fix Unreal Engine CoreRedirects errors in ProjectLungfish. Use when user sees "AddRedirect failed", "invalid characters", "redirect not working", "CoreRedirects error", "UObjectRedirector", "资产重定向失效", or asset redirect warnings after renaming/moving assets. Provides a prioritized 6-solution decision tree from cache clearing to code-level debugging.
---

# CoreRedirects Debug Workflow

## Problem Signature

```
LogCoreRedirects: Error: AddRedirect(AddKnownMissing) failed to add redirect from
'/Game/...' with invalid characters!
```

Most common cause: asset path contains illegal characters (single quote `'`, or others from `"',|&!~@#(){}[]=;^%$``)

---

## Solution Priority Order

### ⭐ Solution 1 — Clear Cache (Fastest, ~5 min)

```bash
# From project root
cd Main
rmdir /S /Q DerivedDataCache
rmdir /S /Q Intermediate
rmdir /S /Q Saved/ShaderDebugInfo
rmdir /S /Q Saved/Cooked
```

Then:
1. `GenerateProjectFiles.bat`
2. Recompile in Visual Studio
3. Launch editor — check if error gone

**Why it works**: Forces engine to re-scan all assets and redirects, purging corrupt cached data.

---

### ⭐ Solution 2 — Fix Asset References in Editor (~15-30 min)

1. Open **Content Browser** → search for the problem asset
2. Right-click → **Reference Viewer** → check Referencers and Dependencies
3. Check if asset exists at two paths (moved/copied without cleanup):
   - Identify the correct version
   - Reroute all referencers to correct asset
   - Delete the duplicate
4. If asset data is corrupt: find original Excel in `Main/RawData/`, fix any stray quotes, re-import DataTable
5. **Fix Up Redirectors**: Content Browser → right-click empty area → **Fix Up Redirectors in Folder** → select `/Game/`
6. Save All

---

### Solution 3 — Enable Verbose Logging (Diagnostic, ~1-2h)

Add to `Main/Config/DefaultEngine.ini`:
```ini
[Core.Log]
LogCoreRedirects=VeryVerbose
LogLinker=Verbose
LogAssetRegistry=Verbose
LogLoad=Verbose
```

Restart editor, reproduce the error, then check **Output Log** for:
- Which asset triggered the error
- Redirect type (Package/Class/Property/Function)
- Call stack

---

### Solution 4 — Code-Level Debugging

Set conditional breakpoint in Visual Studio:

File: `Engine/Source/Runtime/CoreUObject/Private/UObject/CoreRedirects.cpp` line ~2723

```cpp
// Breakpoint condition:
NewRedirect.OldName.ToString().Contains("YourAssetName")
```

Watch window:
```
NewRedirect.OldName
NewRedirect.OldName.ToString()
```

---

### Solution 5 — Clean Editor Settings

Backup and edit `Main/Saved/Config/WindowsEditor/EditorPerProjectUserSettings.ini`:

Remove lines containing the problem asset path (MRUItem entries, recent files, etc.), then restart editor.

---

### Solution 6 — Inspect Python Data Pipeline

If redirects originate from Python-generated paths, check `Main/Plugins/PLPythonPipeline/Content/Python/`:

```python
# Common bug — extra quotes:
asset_path = f"'{package_name}.{asset_name}'"   # WRONG
asset_path = f"{package_name}.{asset_name}"      # CORRECT

# Sanitize helper:
def sanitize_asset_path(path: str) -> str:
    invalid_chars = '"\'|&!~@#(){}[]=;^%$`'
    for char in invalid_chars:
        path = path.replace(char, '')
    return path.strip()
```

---

## Verify Fix

After applying any solution, confirm:

1. Editor starts with no `invalid characters` errors in Output Log
2. Problem asset opens and loads all rows
3. Content Browser search for "UObjectRedirector" returns nothing (or fix remaining redirectors)

---

## Prevention

Add path validation to C++ DataTable import code:

```cpp
static bool ValidatePath(const FString& AssetPath, FString& OutError)
{
    static const FString InvalidChars = TEXT("\"',|&!~\n\r\t@#(){}[]=;^%$`");
    for (const TCHAR Ch : InvalidChars)
    {
        if (AssetPath.Contains(FString::Chr(Ch)))
        {
            OutError = FString::Printf(TEXT("Invalid char '%c' in: %s"), Ch, *AssetPath);
            return false;
        }
    }
    return true;
}
```

---

## Quick Decision Tree

```
CoreRedirects error?
    ↓
Try Solution 1 (clear cache) first — 5 min
    ↓ still failing?
Check for duplicate asset paths (Solution 2)
    ↓ still failing?
Enable verbose logging (Solution 3) to identify source
    ↓ source found?
  → Python script generating bad paths → Solution 6
  → Editor settings → Solution 5
  → Need deeper analysis → Solution 4
```
