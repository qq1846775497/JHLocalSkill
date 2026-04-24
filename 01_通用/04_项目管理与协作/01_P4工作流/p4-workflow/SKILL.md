---
name: p4-workflow
title: Perforce (P4) 版本控制工作流
description: Perforce (P4) version control workflow for the ProjectLungfish Unreal Engine project. Use when user mentions "p4", "perforce", "edit", "checkout", "changelist", "submit", or encounters read-only file errors. Use when creating/modifying files in version control, organizing changes into changelists, moving/renaming files while preserving history, or preparing changes for submission. Essential for all P4 operations including changelist management and pre-submit verification. Use proactively whenever a file appears read-only during code modification, whenever the user has finished making changes and needs to commit or save them to version control, or when any Perforce-related error appears. Also trigger when user says "push", "pull", "sync", "save my work", "commit my changes", or "ready to submit" in the ProjectLungfish context, as these map to P4 operations even without explicit "p4" mentions.
tags: [Perforce, P4, Changelist, Version-Control, File-Management, Submit-Workflow, Checkout]
---

# Perforce (P4) Workflow

## Overview

This skill handles all Perforce version control operations for the ProjectLungfish project, including file checkout, changelist management, history-preserving moves, and submission workflows.

## Quick Reference

### Create Changelist
```bash
# Recommended: Use temp file method (most reliable)
cat > /tmp/p4_changelist.txt << 'EOF'
Change: new

Client: [CLIENT_NAME]

User: [USER_NAME]

Status: new

Description:
	WIP - [Task Name]

Files:
EOF
p4 change -i < /tmp/p4_changelist.txt

# IMPORTANT: Get client/user with:
# p4 info | grep "Client name"
# p4 info | grep "User name"
```

### Check Out and Organize
```bash
p4 edit "file.cpp"
p4 reopen -c [CL_NUM] "file.cpp"
```

### Verify Before Submit
```bash
p4 opened -c default        # Must be empty
p4 opened -c [CL_NUM]      # Only your files
```

### Submit
```bash
p4 submit -c [CL_NUM]      # NEVER without -c flag!
```

### Description Format
`"Code/BP/Script - Feature/Module - Brief description"` (1-2 lines)

## Core Workflow

### Step 1: Create Changelist (START of ANY task)

**Always create a new changelist before modifying any files.**

```bash
# Get client and user info
p4 info | grep "Client name"  # e.g., SunLaibing_MainDev_9897
p4 info | grep "User name"    # e.g., sunlaibing

# Create changelist using temp file (most reliable)
cat > /tmp/p4_changelist.txt << 'EOF'
Change: new

Client: SunLaibing_MainDev_9897

User: sunlaibing

Status: new

Description:
	Code - AssetScanner - Add clang-tidy source code scanner

Files:
EOF

p4 change -i < /tmp/p4_changelist.txt
# Returns: Change 12345 created
```

**Key Points:**
- Use actual client/user names from `p4 info`
- Use temp file method to avoid shell escaping issues
- Description should follow format: "Code/BP/Script - Module - Brief description"

### Step 2: Check Out and Organize Files IMMEDIATELY

**CRITICAL**: Move files to your changelist immediately after checkout/add.

```bash
# Check out existing file
p4 edit "Main/Source/MyClass.cpp"
p4 reopen -c 12345 "Main/Source/MyClass.cpp"

# Add new file
p4 add "ClaudeTasks/Building/MyTask.md"
p4 reopen -c 12345 "ClaudeTasks/Building/MyTask.md"
```

### Step 3: Verify Changelist Contents

```bash
# Check default is empty
p4 opened -c default
# MUST return: "File(s) not opened on this client."

# Check your changelist
p4 opened -c 12345
# Should list ONLY files for this task

# Detailed view
p4 describe -s 12345
```

### Step 4: Update Description

**Use proper format before submit:**

```bash
# Recommended method (direct field update):
p4 --field "Description=Code - Modified MyClass - Added new feature" change -o 12345 | p4 change -i

# Or file editor method:
p4 change -o 12345 > temp.txt
# Edit temp.txt
p4 change -i < temp.txt
rm temp.txt
```

**Description Format Pattern:**
- `"Code - Modified Feature - Brief description"`
- `"BP - SystemName - What changed"`
- `"Script - ComponentName - Action taken"`
- Keep to 1-2 lines total

### Step 5: MANDATORY Pre-Submit Verification

**NEVER skip these checks:**

```bash
# 1. Verify default is empty
p4 opened -c default
# MUST show: "File(s) not opened on this client."

# 2. Verify only your files
p4 opened -c 12345
# Should list ONLY files for this task

# 3. Count and verify
p4 opened -c 12345 | wc -l
```

**If ANY unrelated files appear, STOP and reorganize!**

### Step 6: Submit Changelist

**CRITICAL RULES:**
- **DO NOT submit before user explicitly says "submit"** — but ALWAYS complete steps 1–5
- **ALWAYS complete steps 1-5 first**
- **NEVER use `p4 submit` without `-c` flag**
- **Always include `ClaudeTasks/*.md` documentation in the same changelist as code changes**

```bash
# Correct:
p4 submit -c 12345

# DANGEROUS (never do):
p4 submit              # Submits ALL changes
p4 submit -d "msg"     # Without -c flag
```

## P4 Move (Preserve History)

**Use `p4 move` instead of delete+add to preserve file history.**

### Single File Move

```bash
# 1. Backup modifications
cp "target/file" /tmp/file.backup

# 2. Revert any delete+add operations
p4 revert "source/file" "target/file"

# 3. Remove local target (avoids overwrite error)
rm -f "target/file"

# 4. Execute move (edit first!)
p4 edit "source/file"
p4 move "source/file" "target/file"

# 5. Organize to changelist
p4 reopen -c 12345 "source/file" "target/file"

# 6. Restore modifications
cp /tmp/file.backup "target/file"

# 7. Verify
p4 opened -c 12345 | grep "move/"     # Shows move/delete and move/add
p4 filelog "target/file"               # Shows "move from" history
```

### Key Principles
- **ALWAYS backup before reverting**
- **Use `p4 edit` before `p4 move`** (required)
- **Remove target file** before move
- **Reopen immediately** to correct changelist
- **Restore from backup** after move
- **NEVER use delete+add** - you lose history!

## Common Commands

### File Operations
```bash
p4 edit "file"              # Check out
p4 add "file"               # Add new
p4 delete "file"            # Mark for deletion
p4 revert "file"            # Revert changes
p4 revert -a "file"         # Revert only if unchanged (safe cleanup)
p4 move "src" "dest"        # Move/rename
p4 sync "file"              # Update to latest
p4 diff "file"              # Show differences
```

### Changelist Operations
```bash
p4 change                   # Create/edit CL
p4 changes -m 10            # Last 10 CLs
p4 describe -s [CL]         # Describe CL
p4 opened -c [CL]           # Files in CL
p4 reopen -c [CL] "file"    # Move file to CL
p4 submit -c [CL]           # Submit CL
```

### Status Operations
```bash
p4 info                     # Client/user info
p4 opened                   # All opened files
p4 opened -c default        # Default CL files
p4 fstat "file"             # File status
p4 filelog "file"           # File history
```

## Update Submitted CL Description

```bash
# Most reliable method:
p4 --field "Description=New description here" change -o [CL] | p4 change -u -i
```

Note: `p4 change -u` alone opens GUI editor (not usable in CLI).

## Integration with Other Skills

### Read-Only File Detection
When file cannot be modified:
1. Check: `ls -la "file"`
2. Checkout: `p4 edit "file"`
3. Organize: `p4 reopen -c [CL] "file"`

### Unreal C++ Workflow
**Before build:**
- Checkout all modified files
- Organize into changelist
- Update ClaudeTasks documentation

**After build:**
- Verify changelist contents
- Update description
- Run pre-submit verification

## Best Practices

### Changelist Organization
- One changelist per logical task
- Group related files together
- Keep unrelated changes separate
- Include ClaudeTasks/*.md documentation

### Safety Checks
- Always verify default CL is empty before submit
- Count files in changelist
- Review `p4 opened -c [CL]` output
- Never skip pre-submit verification

### History Preservation
- Use `p4 move` for file relocations
- Never use delete+add for moves
- Preserve file history for blame/annotate

## Common Errors and Solutions

### Error: "Missing required field 'Change'"

**Symptom**: `p4 change -i` fails with "Missing required field 'Change'"

**Cause**: Incorrect format when using `printf` or `echo` to create changelist

**Solution**: Use temp file method instead:
```bash
cat > /tmp/p4_changelist.txt << 'EOF'
Change: new

Client: [CLIENT_NAME]

User: [USER_NAME]

Status: new

Description:
	[Your description]

Files:
EOF

p4 change -i < /tmp/p4_changelist.txt
```

### Error: "Error in change specification. Change description missing"

**Symptom**: `p4 change` opens editor but fails on save

**Cause**: Interactive editor cannot be used in command-line mode

**Solution**: Always use temp file method with `p4 change -i < file`

### Error: Submitting unrelated files

**Symptom**: `p4 submit` submits files from other tasks

**Cause**: Files not moved to correct changelist, or using `p4 submit` without `-c` flag

**Solution**:
1. Always use `p4 submit -c [CL_NUM]`
2. Verify before submit:
   ```bash
   p4 opened -c default     # Must be empty
   p4 opened -c [CL_NUM]    # Only your files
   ```

## Advanced Topics

For detailed information on batch move operations, see [references/batch-moves.md](references/batch-moves.md).

## Quick Workflow Example

```bash
# Complete workflow from start to submit

# 1. Get P4 info
p4 info | grep "Client name"
p4 info | grep "User name"

# 2. Create CL using temp file
cat > /tmp/p4_changelist.txt << 'EOF'
Change: new

Client: SunLaibing_MainDev_9897

User: sunlaibing

Status: new

Description:
	Code - MyClass - Added feature

Files:
EOF

p4 change -i < /tmp/p4_changelist.txt
# Output: Change 12345 created

# 3. Check out and organize files
p4 edit "Main/Source/MyClass.cpp"
p4 reopen -c 12345 "Main/Source/MyClass.cpp"
p4 add "ClaudeTasks/Building/MyTask.md"
p4 reopen -c 12345 "ClaudeTasks/Building/MyTask.md"

# 4. Make changes, build, test...

# 5. Update description if needed
p4 --field "Description=Code - MyClass - Added advanced feature" change -o 12345 | p4 change -i

# 6. MANDATORY verification before submit
p4 opened -c default        # MUST show: File(s) not opened on this client
p4 opened -c 12345          # Verify only your files
p4 describe -s 12345        # Review changelist

# 7. Wait for user to explicitly say "submit"
p4 submit -c 12345
```
