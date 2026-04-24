# Batch P4 Move Operations

## Overview

Guide for moving multiple files while preserving P4 history using batch scripts.

## Batch Move Script Pattern

```bash
# Move multiple component files preserving history
COMPONENTS=("PLArrowComponent" "PLBillboardComponent" "PLBoxComponent")
SOURCE_BASE="Plugins/OldPlugin/Source/OldPlugin"
TARGET_BASE="Plugins/NewPlugin/Source/NewPlugin"
CL=12345

for comp in "${COMPONENTS[@]}"; do
  for ext in h cpp; do
    for dir_pair in "Public:Public" "Private:Private"; do
      IFS=':' read -r src_dir tgt_dir <<< "$dir_pair"

      SRC="${SOURCE_BASE}/${src_dir}/Components/${comp}.${ext}"
      TGT="${TARGET_BASE}/${tgt_dir}/Components/${comp}.${ext}"

      # Backup, revert, remove, move, restore
      cp "$TGT" "/tmp/${comp}.${ext}.bak" 2>/dev/null
      p4 revert "$SRC" "$TGT" 2>/dev/null
      rm -f "$TGT"
      p4 edit "$SRC"
      p4 move "$SRC" "$TGT"
      p4 reopen -c $CL "$SRC" "$TGT"
      cp "/tmp/${comp}.${ext}.bak" "$TGT" 2>/dev/null
    done
  done
done
```

## Multi-File Migration Example

```bash
#!/bin/bash
# Migrate entire module preserving history

CL=12345
SOURCE_DIR="Plugins/OldModule/Source/OldModule"
TARGET_DIR="Plugins/NewModule/Source/NewModule"

# File list
FILES=(
  "Public/MyClass.h"
  "Private/MyClass.cpp"
  "Public/AnotherClass.h"
  "Private/AnotherClass.cpp"
)

for file in "${FILES[@]}"; do
  SRC="${SOURCE_DIR}/${file}"
  TGT="${TARGET_DIR}/${file}"

  echo "Moving: $SRC -> $TGT"

  # Backup if target exists
  if [ -f "$TGT" ]; then
    cp "$TGT" "/tmp/$(basename $TGT).backup"
  fi

  # Revert any previous operations
  p4 revert "$SRC" 2>/dev/null
  p4 revert "$TGT" 2>/dev/null

  # Remove target
  rm -f "$TGT"

  # Create target directory
  mkdir -p "$(dirname $TGT)"

  # Execute move
  p4 edit "$SRC"
  p4 move "$SRC" "$TGT"
  p4 reopen -c $CL "$SRC" "$TGT"

  # Restore backup if it existed
  if [ -f "/tmp/$(basename $TGT).backup" ]; then
    cp "/tmp/$(basename $TGT).backup" "$TGT"
    rm "/tmp/$(basename $TGT).backup"
  fi

  echo "Completed: $file"
done

echo "Batch move complete. Verifying..."
p4 opened -c $CL | grep "move/"
```

## Directory Structure Migration

```bash
#!/bin/bash
# Move entire directory structure

CL=12345
SOURCE_BASE="Plugins/OldPlugin"
TARGET_BASE="Plugins/NewPlugin"

# Find all .h and .cpp files
find "$SOURCE_BASE" -type f \( -name "*.h" -o -name "*.cpp" \) | while read src_file; do
  # Calculate target path
  rel_path="${src_file#$SOURCE_BASE/}"
  tgt_file="${TARGET_BASE}/${rel_path}"

  echo "Processing: $src_file"

  # Backup modifications
  if [ -f "$tgt_file" ]; then
    cp "$tgt_file" "${tgt_file}.backup"
  fi

  # Revert
  p4 revert "$src_file" 2>/dev/null
  p4 revert "$tgt_file" 2>/dev/null

  # Remove target
  rm -f "$tgt_file"

  # Create directory
  mkdir -p "$(dirname $tgt_file)"

  # Move
  p4 edit "$src_file"
  p4 move "$src_file" "$tgt_file"
  p4 reopen -c $CL "$src_file" "$tgt_file"

  # Restore
  if [ -f "${tgt_file}.backup" ]; then
    cp "${tgt_file}.backup" "$tgt_file"
    rm "${tgt_file}.backup"
  fi
done

echo "Migration complete!"
p4 opened -c $CL
```

## Verification Script

```bash
#!/bin/bash
# Verify all moves preserved history

CL=$1

if [ -z "$CL" ]; then
  echo "Usage: $0 <changelist_number>"
  exit 1
fi

echo "Checking changelist $CL for move operations..."

# Get all files in changelist
p4 opened -c $CL | while read line; do
  # Extract file path and action
  file=$(echo $line | awk '{print $1}' | sed 's/#.*//')
  action=$(echo $line | grep -o 'move/[a-z]*')

  if [ -n "$action" ]; then
    echo "File: $file"
    echo "Action: $action"

    # Check history
    echo "History:"
    p4 filelog -m 1 "$file"

    # Check diff still works
    echo "Diff check:"
    p4 diff "$file" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
      echo "✓ Diff works"
    else
      echo "✗ Diff failed"
    fi

    echo "---"
  fi
done
```

## Common Patterns

### Pattern 1: Component Migration
Move all component files (header + implementation):

```bash
COMPONENTS=("MyComponent" "AnotherComponent")
for comp in "${COMPONENTS[@]}"; do
  p4 edit "Old/Public/${comp}.h"
  p4 move "Old/Public/${comp}.h" "New/Public/${comp}.h"
  p4 edit "Old/Private/${comp}.cpp"
  p4 move "Old/Private/${comp}.cpp" "New/Private/${comp}.cpp"
  p4 reopen -c $CL "Old/Public/${comp}.h" "New/Public/${comp}.h"
  p4 reopen -c $CL "Old/Private/${comp}.cpp" "New/Private/${comp}.cpp"
done
```

### Pattern 2: Rename with History
Rename files while preserving history:

```bash
OLD_NAME="OldClassName"
NEW_NAME="NewClassName"

for ext in h cpp; do
  p4 edit "Source/Public/${OLD_NAME}.${ext}"
  p4 move "Source/Public/${OLD_NAME}.${ext}" "Source/Public/${NEW_NAME}.${ext}"
  p4 reopen -c $CL "Source/Public/${OLD_NAME}.${ext}" "Source/Public/${NEW_NAME}.${ext}"
done
```

### Pattern 3: Cross-Plugin Migration
Move files between plugins:

```bash
FILES=("ClassA" "ClassB" "ClassC")
SRC_PLUGIN="Plugins/Plugin1/Source/Plugin1"
TGT_PLUGIN="Plugins/Plugin2/Source/Plugin2"

for file in "${FILES[@]}"; do
  for ext in h cpp; do
    SRC="${SRC_PLUGIN}/Public/${file}.${ext}"
    TGT="${TGT_PLUGIN}/Public/${file}.${ext}"

    p4 edit "$SRC"
    p4 move "$SRC" "$TGT"
    p4 reopen -c $CL "$SRC" "$TGT"
  done
done
```

## Best Practices

1. **Always backup before batch operations**
   ```bash
   tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz Source/
   ```

2. **Test with small subset first**
   - Run script on 1-2 files
   - Verify history preserved
   - Then run full batch

3. **Use dry-run mode**
   ```bash
   # Add DRY_RUN variable to script
   DRY_RUN=true
   if [ "$DRY_RUN" = true ]; then
     echo "Would execute: p4 move $SRC $TGT"
   else
     p4 move "$SRC" "$TGT"
   fi
   ```

4. **Verify after completion**
   ```bash
   p4 opened -c $CL | grep "move/"
   p4 filelog <moved_file>
   ```

5. **Handle errors gracefully**
   ```bash
   if ! p4 move "$SRC" "$TGT"; then
     echo "ERROR: Failed to move $SRC"
     # Log error and continue or exit
   fi
   ```
