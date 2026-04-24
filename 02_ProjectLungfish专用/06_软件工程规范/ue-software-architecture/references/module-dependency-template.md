# 模块依赖图模板

## 标准 UE 模块依赖（ProjectLungfish 风格）

```
ProjectLungfishEditor
        │
        ▼ (PrivateDependency)
ProjectLungfish
        │
        ├──► Engine/Core
        ├──► Engine/CoreUObject
        ├──► Engine/Engine
        ├──► Engine/InputCore
        ├──► GameplayAbilities
        ├──► GameplayTags
        ├──► GameplayTasks
        │
        ▼ (Plugin dependency)
    PLBehaviorTreeSM
        │
        ▼
    SoftUEBridge
        │
        └──► Engine/EditorScriptingUtilities
```

## .Build.cs 模板

```csharp
using UnrealBuildTool;

public class ProjectLungfish : ModuleRules
{
    public ProjectLungfish(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

        PublicDependencyModuleNames.AddRange(new string[] {
            "Core",
            "CoreUObject",
            "Engine",
            "InputCore",
            "GameplayAbilities",
            "GameplayTags",
            "GameplayTasks",
            "EnhancedInput",
            "UMG",
        });

        PrivateDependencyModuleNames.AddRange(new string[] {
            "Projects",
            "Slate",
            "SlateCore",
        });

        // 插件依赖（条件编译）
        if (Target.bBuildEditor)
        {
            PrivateDependencyModuleNames.Add("UnrealEd");
            PrivateDependencyModuleNames.Add("EditorScriptingUtilities");
        }
    }
}
```

## 模块拆分检查清单

当某个模块的 `.Build.cs` 中 `PublicDependencyModuleNames` 超过 15 个时，考虑拆分：

- [ ] 是否有独立的 gameplay 子系统可以抽成插件？
- [ ] 是否有编辑器-only 代码混在游戏模块中？
- [ ] 是否有第三方库依赖污染了核心模块？

## 新增模块流程

1. 在 `Source/` 下创建 `{ModuleName}/` 目录
2. 创建 `{ModuleName}.Build.cs`
3. 在 `.uproject` 的 `Modules` 数组中添加
4. 运行 UBT 生成项目文件：`GenerateProjectFiles.bat`
5. 编译验证
