---
name: pr
description: P4 changelist description updater. Generate concise one-line descriptions from diffs and update the changelist in place. Use when user asks to generate or update CL descriptions, including optional changelist number and JIRA reference.
---
# P4 Changelist Description Updater

argument-hint: "[changelist-number] [PL-XXXX|JIRA-URL]"

## Steps
1. **Determine changelist**:
   - Use $1 if provided, otherwise:
     - Extract client: `p4 set | grep P4CLIENT | cut -d'=' -f2 | cut -d' ' -f1`
     - Get most recent: `p4 changes -m 1 -s pending -c <client>`

2. **Process JIRA parameter** (if $2 provided):
   - If $2 contains "http://192.168.2.13:8083/browse/", extract PL-XXXX from URL
   - If $2 starts with "PL-", use as-is
   - Format as markdown link: `[PL-XXXX](http://192.168.2.13:8083/browse/PL-XXXX)`

3. **Preserve PreCheckin tag** (before overwriting description):
   - Read existing description: `p4 change -o [CL]`
   - If description contains pattern `[PreCheckin:OK <hash>]`, extract the full tag
   - Store it to append later (e.g. `PRECHECKIN_TAG="[PreCheckin:OK a3a0ed]"`)

4. **Get file diffs**:
   - Clear custom diff: `p4 set P4DIFF=`
   - Get changelist files: `p4 describe [CL_NUMBER]`
   - **IMPORTANT**: Use `p4 diff //full/depot/path/to/file` for each file (not `p4 diff -c`)

5. **Analyze changes**:
   - Text files: Look for function/class/variable changes, understand the "why" not just "what"
   - Binary files: Focus on file names and paths
   - If unclear, use Read tool for more context
   - p4 Description should maintain the template of "Code/BP/Script - Modified Feature/Module Name - Descriptions" pattern
   - **Description must be written in English** — no Chinese or other languages, use only English words and common ASCII punctuation; no special or Unicode symbols

6. **Generate description**:
   - If JIRA link exists: First line = JIRA link, second line = description
   - Format: "Code/BP/Script - Module/Feature - Brief description"
   - Base on actual changes, not just file names
   - Single line, informative but concise
   - If `PRECHECKIN_TAG` was found in step 3, append it on its own line at the end

7. **Update changelist** (file relay method — `p4 --field` is NOT available here):
   - Export spec: `p4 change -o [CL] > Tools/cl_temp.txt`
   - Edit description with Edit tool (TAB indent, not spaces)
   - Submit: `p4 change -u -i < Tools/cl_temp.txt`
   - Cleanup: `rm Tools/cl_temp.txt`  ← use `rm`, NOT `del` (shell is bash, not CMD)

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `Unknown command. Try 'p4 help'` | `p4 --field` not supported | Use file relay method (Step 6) |
| `del: command not found` | Shell is bash, `del` is CMD-only | Use `rm` to delete temp file |
| `'grep' is not recognized` | Windows CMD has no Unix tools | Run `p4 set` and read output manually |
| `p4 diff` returns nothing for a file | File is `# add` status (no baseline) | Skip diff, infer purpose from file path |
