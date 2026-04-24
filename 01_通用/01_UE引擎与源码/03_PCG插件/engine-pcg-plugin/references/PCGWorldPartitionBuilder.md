# PCGWorldPartitionBuilder — 使用方式与原理参考

> 文件路径: `Engine/Plugins/PCG/Source/PCGEditor/Private/WorldPartitionBuilder/PCGWorldPartitionBuilder.h/.cpp`

---

## 目录

1. [定位与职责](#1-定位与职责)
2. [核心类型速览](#2-核心类型速览)
3. [触发方式](#3-触发方式)
4. [命令行参数完整列表](#4-命令行参数完整列表)
5. [UPCGBuilderSettings 数据资产](#5-upcgbuildersettings-数据资产)
6. [执行流程（生命周期）](#6-执行流程生命周期)
7. [两种加载模式详解](#7-两种加载模式详解)
8. [组件筛选逻辑](#8-组件筛选逻辑)
9. [关键内部机制](#9-关键内部机制)
10. [扩展点与集成](#10-扩展点与集成)
11. [常见陷阱与注意事项](#11-常见陷阱与注意事项)

---

## 1. 定位与职责

`UPCGWorldPartitionBuilder` 继承自 `UWorldPartitionBuilder`，是 UE5 World Partition Builder Commandlet 框架下的一个具体实现。

**职责：**
- 遍历世界中所有符合条件的 `UPCGComponent`
- 对每个 component 触发 `Generate`（离线烘焙）
- 收集生成过程中被标脏的 Package
- 将脏 Package 存档/提交到 Source Control

**不负责：**
- 图节点执行逻辑（由 `UPCGSubsystem` / Graph Executor 负责）
- PCG 数据类型处理

---

## 2. 核心类型速览

### `FPCGWorldPartitionCommandlineArgs`
从命令行/UWorldPartitionBuilder 基类参数解析出的原始可选值（`TOptional<T>`），优先级最高。

### `FPCGWorldPartitionBuilderArgs`
最终生效的参数结构体，由 `InitializeFrom()` 合并 `UPCGBuilderSettings` 和 `CommandlineArgs` 得到。命令行覆盖 Settings Asset。

```cpp
struct FPCGWorldPartitionBuilderArgs {
    bool bGenerateEditingModeLoadAsPreviewComponents = true;  // 默认只烘 LoadAsPreview
    bool bGenerateEditingModeNormalComponents = false;
    bool bGenerateEditingModePreviewComponents = false;
    TArray<FString> IncludeGraphNames;          // 为空 = 所有图
    TArray<TSoftObjectPtr<UPCGGraphInterface>> IncludeGraphs; // Settings asset 指定
    bool bOneComponentAtATime = false;          // 串行生成，适合调试
    TArray<FString> IncludeActorIDs;            // 为空 = 所有 Actor
    bool bIgnoreGenerationErrors = false;
    bool bIterativeCellLoading = false;         // 大地图分 Cell 加载
    int32 IterativeCellSize = 25600;            // 最小 12800
    bool bLoadEditorOnlyDataLayers = true;
    bool bLoadActivatedRuntimeDataLayers = true;
    TArray<TObjectPtr<UDataLayerAsset>> IncludedDataLayers;
    TArray<TObjectPtr<UDataLayerAsset>> ExcludedDataLayers;
    bool bRevertUnchangedActors = false;        // 实验性：未变更 Actor 回滚
    TArray<FString> OutputsToIgnoreForRevert;
};
```

### `UPCGWorldPartitionBuilder` (UCLASS)
继承链：`UPCGWorldPartitionBuilder` → `UWorldPartitionBuilder`

关键 override：
```cpp
virtual bool RequiresCommandletRendering() const override { return true; }
// GPU 需要，GetTextureData 等 Node 依赖 GPU fallback

virtual ELoadingMode GetLoadingMode() const override {
    return Args.bIterativeCellLoading ? ELoadingMode::IterativeCells2D : ELoadingMode::EntireWorld;
}

virtual bool CanProcessNonPartitionedWorlds() const override { return true; }
// 非 WP 世界也能运行
```

### `UPCGWorldPartitionBuilderHelper` (UCLASS, BlueprintFunctionLibrary)
```cpp
UFUNCTION(BlueprintCallable, Category = "PCG|Builder")
static void AddAssetToSubmitAllowList(const TSoftObjectPtr<UObject>& InPath);
```
在 PCG Graph 节点中调用此函数，可将非 Actor 资产（如 DataAsset）加入提交许可列表，使 Builder 在 PostRun 时一并提交。

---

## 3. 触发方式

### 方式 A：Commandlet（CI/CD 推荐）

```bat
UnrealEditor.exe ProjectName MapPath -Unattended -AllowCommandletRendering ^
    -run=WorldPartitionBuilderCommandlet ^
    -Builder=PCGWorldPartitionBuilder ^
    -SCCProvider=Perforce ^
    -AllowSoftwareRendering ^
    -AssetGatherAll=true ^
    -GenerateComponentEditingModeLoadAsPreview ^
    -PCGBuilderSettings=/Game/Path/BuilderSettingsAssetName
```

### 方式 B：Editor 菜单（交互式）

Build 菜单 → "Build PCG" → 弹出 `SPCGBuilderDialog` 对话框，选择 `UPCGBuilderSettings` asset 后执行。

内部调用：
```cpp
IWorldPartitionEditorModule::Get().RunBuilder(Params);
// Params.BuilderClass = UPCGWorldPartitionBuilder::StaticClass()
```

### 方式 C：Console Command（Editor 内快速测试）

```
pcg.BuildComponents [-IncludeGraphNames=PCG_A;PCG_B] [-IterativeCellLoading] ...
// 多值用 ; 分隔
```

运行在当前 `GEditor->GetEditorWorldContext().World()`。

---

## 4. 命令行参数完整列表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `-PCGBuilderSettings=/Game/Path/Name` | string | none | Settings Asset 路径，覆盖所有其他默认值 |
| `-IncludeGraphNames=A;B` | string (`;`分隔) | all | 只生成名称匹配的图，按序分组执行 |
| `-GenerateComponentEditingModeLoadAsPreview` | flag/bool | true | 生成 LoadAsPreview 模式的组件 |
| `-GenerateComponentEditingModeNormal` | flag/bool | false | 生成 Normal 模式的组件 |
| `-GenerateComponentEditingModePreview` | flag/bool | false | 生成 Preview 模式的组件 |
| `-IgnoreGenerationErrors` | flag/bool | false | 生成出错时仍保存 Package |
| `-IncludeActorIDs=Actor1_UAID;Actor2_UAID` | string (`;`分隔) | all | 只处理指定 Actor（使用 `Actor->GetName()`） |
| `-OneComponentAtATime` | flag/bool | false | 串行等待每个组件完成后再处理下一个 |
| `-IterativeCellLoading` | flag/bool | false | 分 Cell 迭代加载（大地图省内存） |
| `-IterativeCellSize=25600` | int | 25600 | Cell 大小（最小 12800） |

**参数优先级：** Commandline > PCGBuilderSettings Asset > 默认值

**Bool 参数格式：** 支持 `-FlagName`（=true）或 `-FlagName=false`

---

## 5. UPCGBuilderSettings 数据资产

`UPCGBuilderSettings` 是一个编辑器数据资产（`UObject`），路径在 Project Settings 中 `DefaultBuilderSetting` 指定，或通过 `-PCGBuilderSettings=` 传入。

```cpp
// Engine/Plugins/PCG/Source/PCGEditor/Private/WorldPartitionBuilder/PCGBuilderSettings.h
class UPCGBuilderSettings : public UObject {
    TArray<TSoftObjectPtr<UPCGGraphInterface>> Graphs;  // 空=所有图
    TArray<EPCGEditorDirtyMode> EditingModes;
    TArray<FString> FilterByActorNames;
    bool bLoadEditorOnlyDataLayers = true;
    bool bLoadActivatedRuntimeDataLayers = true;
    TArray<TObjectPtr<UDataLayerAsset>> IncludedDataLayers;
    TArray<TObjectPtr<UDataLayerAsset>> ExcludedDataLayers;
    bool bIterativeCellLoading = false;
    int32 IterativeCellSize = 25600;
    bool bIgnoreGenerationErrors = false;
    bool bOneComponentAtATime = false;          // RevertUnchangedActors 开时自动启用
    bool bRevertUnchangedActors = false;        // 实验性
    TArray<FString> OutputsToIgnoreForRevert;
};
```

**注意：**  
- `Graphs` 和命令行 `-IncludeGraphNames` 互斥：命令行指定时会清空 `IncludeGraphs`，改用名称匹配。
- `bRevertUnchangedActors=true` 时会强制 `bOneComponentAtATime=true`（因为串行才能正确计算 CRC）。

---

## 6. 执行流程（生命周期）

Builder 由 `UWorldPartitionBuilder` 基类框架驱动，关键 override 依次调用：

```
PreWorldInitialization(World, PackageHelper)
    └─ SetDisablePartitionActorCreationForWorld(true)   // 禁止 PA 自动创建

PreRun(World, PackageHelper)
    ├─ FPCGWorldPartitionBuilderArgs::InitializeFrom(CommandlineArgs, Args)
    ├─ SetChainedDispatchToLocalComponents(World, bRevertUnchangedActors)
    └─ 配置 DataLayers、IterativeCellSize 等

RunInternal(World, CellInfo, PackageHelper)   // ← 可能多次调用（IterativeCells 模式）
    ├─ [EntireWorld] RunEntireWorld()
    └─ [IterativeCells2D] RunPerCell()

PostRun(World, PackageHelper, bSuccess)
    ├─ 日志输出最终 new/modified/deleted/reverted 统计
    ├─ [EntireWorld] 无需额外 SCC 操作（已在 RunEntireWorld 中处理）
    └─ [IterativeCells2D] 重建 SCC Provider → checkout/add/delete 文件 → 提交
```

---

## 7. 两种加载模式详解

### EntireWorld 模式（默认）

```
1. CollectComponentsToGenerate()       // 一次性收集所有 UCPGComponent
2. ResetPackageDirtyFlags()            // 清除加载时产生的脏标记
3. GetRevertableActors (pre-gen CRC)  // 可选：记录生成前状态
4. CreatePartitionedActors()           // 为 Partitioned 组件创建缺失的 PA
5. UpdatePartitionedActors()           // 更新 Original→Local 映射
6. GroupComponentsToGenerate()         // 按 IncludeGraphNames 分组顺序执行
7. GenerateComponents()                // 触发生成，等待完成
8. WaitOnGraphExecutor()
9. GetDirtyPackages()                  // 收集脏 Package（过滤非 WP External Package）
10. RevertUnchangedActors()            // 可选
11. SaveEntireWorldPackages()          // save/delete + OnFilesModified (SCC)
```

### IterativeCells2D 模式（大地图）

- 基类逐 Cell 调用 `RunInternal()` → 转发到 `RunPerCell()`
- **PreRun 时禁用 SCC**（避免 Cell 间文件锁冲突）；**PostRun 时重建 SCC 并批量操作**
- 每个 Cell 结束调用 `FWorldPartitionHelpers::DoCollectGarbage()` 释放内存
- 使用 `FLoaderAdapterShape` 按需扩展加载范围（`ExpandLoadedBoundsIfNeeded`）
- 跨 Cell 追踪已生成的组件（`GeneratedComponents` TSet），避免重复生成

**Cell 流程：**
```
LoadPartitionedActorDependencies()     // 加载 PA 依赖的 Original Actor 和 Managed Actor
ResetPackageDirtyFlags()
GetRevertablePartitionActors()         // 记录 PA 状态（pre-gen）
CreatePartitionedActors() / UpdatePartitionedActors()
CollectComponentsToGenerate()          // 过滤：组件中心在 Cell 内且未生成过
ExpandLoadedBoundsIfNeeded()           // 扩展加载区域以覆盖组件完整 bounds
CollectSubGridComponentsToGenerate()   // 收集子网格 PA 组件（HiGen）
GenerateComponents()
WaitOnGraphExecutor()
SavePerCellPackages()                  // 追踪 new/modified/deleted 到 PostRun 用
```

---

## 8. 组件筛选逻辑

`CollectComponentsToGenerate()` 过滤条件（AND 逻辑）：

1. **Actor ID 过滤**：`IncludeActorIDs` 非空时，`Component->GetOwner()->GetName()` 必须在列表中
2. **EditingMode 过滤**：`Component->GetSerializedEditingMode()` 必须匹配启用的 mode 标志
3. **图名称过滤**：`IncludeGraphNames` 非空时，`Graph->GetName()` 必须匹配；或 `IncludeGraphs` 非空时 soft ptr 匹配
4. **Activated 标志**：`Component->bActivated == true`
5. **RuntimeGen 排除**：`Component->IsManagedByRuntimeGenSystem() == false`
6. **自定义 ComponentFilter**：调用方传入的额外 lambda（如 EntireWorld 模式排除 Local Component）

### HiGen 子网格顺序

`CollectSubGridComponentsToGenerate()` 递归收集多层 Grid 的 PA 局部组件，并建立依赖关系：
- 较大 Grid 的 PA 优先生成（作为较小 Grid 的依赖）
- `GroupComponentsToGenerate()` 在 `bOneComponentAtATime=true` 下确保依赖组件的 TaskId 传递

---

## 9. 关键内部机制

### Package 脏状态追踪

```
FPCGDetectDirtyPackageInScope    // 检测生命周期内是否有 Package 被脏（用于判断 cell 是否有变更）
FPCGDetectDeletedActorInScope    // 监听 OnLevelActorDeleted，记录被删 Actor 的 Package 名
FPCGDetectErrorsInScope          // 挂载 GLog OutputDevice，捕获 Error 级别日志
```

### GetDirtyPackages 过滤规则

- **WP 世界**：只允许当前世界的 External Package（Actor Package）和 AllowedAssetPackages 中的资产
- **非 WP 世界**：只允许 umap 本身和 AllowedAssetPackages
- 世界 Package 本身（`.umap`）在 WP 模式下不可保存（除非显式 allow）

### RevertUnchangedActors（实验性）

原理：CRC 比较 Actor 在生成前后的状态（`bGenerated` + `LastGeneratedBounds` + `ManagedResource CRCs` + Output TaggedData CRCs），如果完全一致则从脏列表移除该 Actor 的 Package，避免不必要的 SCC 提交。

限制：只对 `IsPackageExternal() == true` 的 Actor 有效，Actor 不能有非默认子对象。

### FPCGDisableClearResults

生成批次执行期间，临时禁止 `UPCGSubsystem` 清理执行结果（防止依赖链中前置结果被回收），批次结束自动恢复。

### AddAssetToSubmitAllowList

PCG Graph 节点内（如生成 DataAsset 的节点）调用：
```cpp
UPCGWorldPartitionBuilderHelper::AddAssetToSubmitAllowList(SoftObjectPtr);
```
通过 `TObjectIterator<UPCGWorldPartitionBuilder>` 找到运行中的 Builder 实例并注册。允许该资产在 PostRun 时被 checkout/add。

---

## 10. 扩展点与集成

### 从 C++ 以编程方式触发 Builder

```cpp
// 在 Editor 世界内触发（适合 Editor 插件/工具）
IWorldPartitionEditorModule::FRunBuilderParams Params;
Params.BuilderClass = UPCGWorldPartitionBuilder::StaticClass();
Params.World = GEditor->GetEditorWorldContext().World();
Params.OperationDescription = FText::FromString("Generating PCG...");
Params.ExtraArgs = TEXT("-AllowCommandletRendering -AllowSoftwareRendering -AssetGatherAll=true");
Params.ExtraArgs += TEXT(" -PCGBuilderSettings=/Game/MySettings");
IWorldPartitionEditorModule::Get().RunBuilder(Params);
```

### 在 PCG Graph 节点中注册非 Actor 资产

```cpp
// 在 UPCGElement 的 ExecuteInternal 中（仅 Editor 构建时）
#if WITH_EDITOR
if (bIsBuilderRunning) {
    UPCGWorldPartitionBuilderHelper::AddAssetToSubmitAllowList(
        TSoftObjectPtr<UObject>(MyDataAsset)
    );
}
#endif
```

### 自定义 UPCGBuilderSettings 默认值

在 Project Settings (`UPCGEditorProjectSettings::DefaultBuilderSetting`) 指定默认的 Settings Asset 路径，无需每次传命令行参数。

---

## 11. 常见陷阱与注意事项

| 问题 | 原因 | 解法 |
|------|------|------|
| Builder 不处理某组件 | `EditingMode != LoadAsPreview` | 确认组件的 `EditingMode` 设置，或增加对应 flag |
| Component 被跳过，日志提示 `IsManagedByRuntimeGenSystem` | 生成触发器设为运行时 | 改为 Editor 触发或调整生成模式 |
| IterativeCellLoading 下内存未下降 | CellSize 太大 | 减小 `IterativeCellSize`（最小 12800） |
| 非 Actor 资产未被提交 | 未调用 `AddAssetToSubmitAllowList` | 在图节点中主动注册资产 |
| WP 世界下 umap 被意外脏 | 某节点写入了世界级 Package | 检查是否有非 External 写入 |
| `bRevertUnchangedActors` 无效 | Actor 含非默认子对象 | 确认 Actor 只有 PCGComponent 无其他运行时组件 |
| IterativeCells 模式下 SCC 失败 | PostRun SCC 重建连接失败 | 检查网络/P4 配置；日志 `Failed to initialize source control provider` |
| Unbounded 分区组件未生成 | 按 PA 而非原始组件遍历时跳过了 unbounded | 框架内部已处理：unbounded 分区组件在 per-cell 模式下特殊排序优先生成 |

---

## 文件位置快速参考

```
Engine/Plugins/PCG/Source/PCGEditor/Private/WorldPartitionBuilder/
    PCGWorldPartitionBuilder.h      ← 类声明、参数结构体、UFUNCTION
    PCGWorldPartitionBuilder.cpp    ← 完整实现（2200 行）
    PCGBuilderSettings.h            ← UPCGBuilderSettings 属性定义
    SPCGBuilderDialog.h/cpp         ← Editor UI 对话框
```
