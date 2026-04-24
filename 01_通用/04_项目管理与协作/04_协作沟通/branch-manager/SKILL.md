---
name: branch-manager
description: Automate operations on the branch management dashboard at http://192.168.2.13/dashboard/branch-conflict. Use this skill when the user wants to check branch status, view build results, check for conflicts, or perform any operations on the branch management system. Trigger when user mentions branch status, build status, merge conflicts, CI/CD pipeline, or asks to check/view/monitor branches.
---

# Branch Manager Skill

This skill automates interactions with the internal branch management dashboard using Playwright.

## System Information

- **Dashboard URL**: http://192.168.2.13/dashboard/branch-conflict
- **Login Credentials**:
  - Username: Administrator
  - Password: Ali@sukaIs1BigwoguaCyancook@sukaIs1Bigwogua

## Available Operations

### 1. Check Branch Status
View the current status of all branches including build and test results.

### 2. View Build Results
Check compilation status for:
- Client builds (客户端编译)
- Client data (客户端数值)
- Server builds (server编译)
- Server data (server数值)
- Editor smoke tests (editor冒烟)

### 3. Check Merge Status
View auto-merge status (自动合并) and branch state (分支状态).

### 4. Resolve Conflicts
Automatically resolve merge conflicts for branches that have conflict issues. The system can trigger conflict resolution through the dashboard interface.

### 5. Monitor Specific Branches
The system tracks these branches:
- 1.0_rel
- 1.0_rel_patch
- Stable
- MainDev

## Implementation Approach

Use the Playwright script template at `scripts/branch-operations.mjs` to:

1. Launch browser (headless or headed based on user preference)
2. Navigate to dashboard and handle login
3. Wait for page load and data population
4. Extract requested information from the table
5. Take screenshots if needed
6. Return formatted results

## Usage Examples

When the user asks:
- "检查分支状态" → Run script to fetch all branch statuses
- "MainDev 分支构建成功了吗" → Check MainDev build status
- "有哪些分支有冲突" → Check merge conflict status
- "截图当前分支状态" → Take screenshot of dashboard

## Output Format

Present results in a clear table format showing:
- Branch name
- Auto-merge status
- Build statuses (client/server)
- Overall branch state
