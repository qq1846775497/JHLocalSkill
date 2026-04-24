---
name: unreal-build-commands
title: Unreal Engine Build Commands
description: 修改任何C++代码后必须主动调用此skill进行编译验证。包含UBT编译命令、项目文件生成、Development/Shipping配置、多目标构建系统。用于验证代码正确性和构建完整性。
tags: [Unreal-Engine, Build-System, UBT, Compilation]
---

# Unreal Engine Build Commands

C++代码修改后的编译验证命令集。

<memory category="core-rules">
**修改C++代码后必做**: 执行UBT编译命令验证代码正确性，修复编译错误后再提交。

**工作目录**: 必须在项目根目录（包含Engine/和Main/的目录）执行所有构建命令。

**路径要求**: -Project参数使用绝对路径，避免路径解析错误。
</memory>

## 快速参考

<memory category="common-patterns">
### 最常用命令

```bash
# 1. 生成项目文件（修改.Build.cs/.Target.cs后必须执行）
GenerateProjectFiles.bat

# 2. 编译Development Editor（日常开发）
"Engine/Binaries/DotNET/UnrealBuildTool/UnrealBuildTool.exe" ProjectLungfishEditor Win64 Development -Project="D:/MainDev/Main/ProjectLungfish.uproject"
```

</memory>

## C++代码修改后的标准流程

<memory category="workflow">
### 编译验证工作流

1. **修改C++代码**（.cpp/.h文件）
2. **检出P4文件**（如果是只读文件）
   ```bash
   p4 edit <file_path>
   ```
3. **执行UBT编译**
   ```bash
   "Engine/Binaries/DotNET/UnrealBuildTool/UnrealBuildTool.exe" ProjectLungfishEditor Win64 Development -Project="D:/MainDev/Main/ProjectLungfish.uproject"
   ```
4. **检查编译结果**
   - 编译成功 → 继续测试
   - 编译失败 → 修复错误 → 返回步骤3
5. **更新文档**（如果有新模式或重要发现）
6. **提交P4 changelist**

### 修改.Build.cs或.Target.cs后

```bash
# 必须先重新生成项目文件
GenerateProjectFiles.bat

# 然后编译
"Engine/Binaries/DotNET/UnrealBuildTool/UnrealBuildTool.exe" ProjectLungfishEditor Win64 Development -Project="D:/MainDev/Main/ProjectLungfish.uproject"
```
</memory>

## Troubleshooting

<memory category="debug-commands">
### 常见编译问题

**路径错误**:
```
错误: "Project file not found"
解决: 使用绝对路径 -Project="D:/MainDev/Main/ProjectLungfish.uproject"
```

**模块编译失败**:
```bash
# 单独编译问题模块以隔离错误
"Engine/Binaries/DotNET/UnrealBuildTool/UnrealBuildTool.exe" ProjectLungfishEditor Win64 Development -Module=<ModuleName> -Project="D:/MainDev/Main/ProjectLungfish.uproject"
```

**权限错误**:
```
错误: 无法写入输出目录
解决: 检查P4文件是否已检出
命令: p4 edit <file_path>
```

**增量编译问题**:
```bash
# 使用Clean强制完整重建
-Clean
```

### 构建性能优化

- UBT自动使用多核并行编译
- 避免不必要的-Clean（增量编译更快）
- 使用-Module参数只编译修改的模块
- 推荐硬件: 16GB+ RAM, SSD存储
</memory>

## Related Documentation

- **P4 Workflow**: `.claude/skills/p4-workflow/SKILL.md` - 文件检出和changelist管理
- **Engine Modifications**: `.claude/skills/engine-modification-standards/SKILL.md` - 引擎代码修改规范
- **Build Fix**: `.claude/skills/unreal-build-fix/SKILL.md` - 编译错误诊断
