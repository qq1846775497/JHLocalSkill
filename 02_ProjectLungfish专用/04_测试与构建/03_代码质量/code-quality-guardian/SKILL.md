---
name: code-quality-guardian
description: >
  代码修改后的质量守护 Skill。强制 5-Gate 检查清单（编译验证 → 测试验证 → 回归检查
  → P4 版本控制 → 代码审查自检），确保任何代码修改都可编译、可测试、不破坏现有功能。
  在**任何代码/配置/资产修改完成后**必须触发，绝不声明任务完成直到所有 Gate 通过。
trigger_when: >
  用户说"完成了"、"改好了"、"搞定了"、"Done"、"Finished"、"写完了"、
  "提交吧"、"ready to submit"、"commit"，或任何暗示代码修改已结束的话语。
  也在编译失败、测试失败、PIE 报错时被动触发，用于引导修复流程。
  任何 C++ / Blueprint / 配置 / 资产修改后自动激活。
---

# 代码质量守护（5-Gate 检查清单）

> ⚠️ **红规：绝不声明任务完成直到所有 Gate 通过。**
> ⚠️ **如果编译失败，修复是最高优先级，不继续其他工作。**

## 何时运行

- 任何代码/配置/资产修改完成后
- 用户说"完成了"、"改好了"、"提交吧"
- 编译/测试/PIE 报错时（引导修复）

---

## Gate 1: 编译验证（Compile Gate）

**目标**：确保修改后的代码能编译通过。

### C++ 修改
- [ ] 触发 `unreal-build-commands` skill 执行 UBT 编译
- [ ] 如果编译失败：
  1. 读取错误日志前 30 行
  2. 触发 `unreal-build-fix` skill 诊断
  3. 修复错误后重新编译
  4. **循环直到编译通过**
- [ ] 编译警告：评估是否为新增警告，如果是则修复

### Blueprint 修改
- [ ] 触发 `ue-cli-blueprint` 编译验证
- [ ] 或使用 `soft-ue-bridge` 在编辑器内编译
- [ ] 检查是否有断开的节点（orphaned nodes）

### 配置/数据修改
- [ ] 触发 `precheckin` 导出验证（Excel → DataTable）
- [ ] 检查导出的 `.json` / `.uasset` 是否有效

### 强制规则
```
❌ 未编译通过的代码 = 未完成
❌ 不允许用户"先提交再修"（除非明确记录技术债务）
```

---

## Gate 2: 测试验证（Test Gate）

**目标**：验证修改没有破坏现有功能。

### PIE 验证
- [ ] 如果是 gameplay 修改，询问用户是否需要运行 PIE 验证
- [ ] 如果用户同意，通过 `soft-ue-bridge` 或 `ue-cli-runtime` 启动 PIE
- [ ] 如果出现 PIE 报错，触发 `pie-error-fix-notify` skill

### 自动化测试
- [ ] 如果修改区域有自动化测试覆盖，运行 `ue-cli-automation`
- [ ] 检查测试是否全部通过
- [ ] 如果测试失败，评估是否为 flaky test（已知不稳定）

### 数据验证
- [ ] 如果是配置/配表修改，检查游戏内数值是否正确生效
- [ ] 如果是词条/实体修改，检查 `entity-tag-modifier` 导出结果

### 强制规则
```
⚠️ 如果用户说"先不管测试"，必须：
   1. 明确记录技术债务（"以下测试未验证：..."）
   2. 告知风险（"未测试的修改可能导致回归"）
   3. 在回复中标注 [未验证]
```

---

## Gate 3: 回归检查（Regression Gate）

**目标**：确保修改不影响相邻代码和 API 兼容性。

### 调用点检查
- [ ] 用 `Grep` 搜索被修改函数/类的所有调用点
- [ ] 检查是否有调用方依赖了被修改的行为
- [ ] 如果函数签名变更，确认所有调用方已同步更新

### API 兼容性
- [ ] 公开 API（`UFUNCTION(BlueprintCallable)` / `UPROPERTY`）变更 = 破坏性变更
- [ ] 破坏性变更需要：
  1. 搜索所有 Blueprint 调用方（`ue-cli-blueprint`）
  2. 搜索所有 C++ 调用方（`Grep`）
  3. 提供迁移说明或保持向后兼容

### File-Skill 历史联动（新增）
- [ ] 检查被修改文件的 File-Skill 档案（如存在）
- [ ] 查看 `history` 中是否有 `regression_detected: true` 的记录
- [ ] 避免重复过去已标记的回归错误模式
- [ ] 如果本次发现 regression，在 File-Skill 对应 history 记录中标记 `regression_detected: true`

### 规则合规
- [ ] 检查是否违反 `native-class-derivation` 规则（禁止直接使用 UE 原生类）
- [ ] 检查是否符合 `ue-software-architecture` 命名规范
- [ ] 检查 Asset 是否符合项目派生类要求

### 强制规则
```
❌ 不能破坏现有 API 而不告知用户
❌ 不能修改核心函数而不检查调用方
❌ 不能重复 File-Skill 中已标记的回归错误
```

---

## Gate 4: 版本控制（VCS Gate）

**目标**：确保修改正确纳入版本控制。

### P4 状态
- [ ] 所有修改的文件是否已 `p4 edit`（`p4-workflow`）
- [ ] 新增文件是否已 `p4 add`
- [ ] 是否有 read-only 文件被修改但未 checkout（检查错误日志）

### Changelist 描述
- [ ] 触发 `pr` skill 生成简洁的 CL 描述
- [ ] 描述是否包含：修改内容 + 原因 + 影响范围
- [ ] 是否关联 JIRA ticket（如有）

### 文件干净度
- [ ] 不包含临时文件：`.tmp`, `.log`, `.user`, `.suo`
- [ ] 不包含生成的二进制：`Binaries/`, `Intermediate/`
- [ ] 不包含调试输出：大型 `.hprof`, 截图等

### 强制规则
```
❌ 不能提交未 checkout 的文件
❌ 不能提交无描述的 changelist
```

---

## Gate 5: 代码审查自检（Self-Review Gate）

**目标**：在提交前做一次自我代码审查。

### 调试代码清理
- [ ] 没有残留的 `UE_LOG(LogTemp, Warning, ...)` 调试日志
- [ ] 没有 `PrintString` 或 `DrawDebug` 临时可视化
- [ ] 没有注释掉的代码块（>3 行）
- [ ] 没有临时断点或 `ensure()` 调试断言

### 代码质量
- [ ] 没有硬编码魔法数字（应定义为 `constexpr` 或 UPROPERTY）
- [ ] 没有硬编码路径字符串（应使用 `FPaths` 或配置）
- [ ] 没有未处理的错误分支（每个 `if` 都有 `else`，每个 `Cast` 都有校验）

### 内存安全
- [ ] 所有 `UObject*` 指针都有 `UPROPERTY()` 标记（防止 GC）
- [ ] 所有 `TWeakObjectPtr` 使用前检查 `IsValid()`
- [ ] 没有裸 `new` / `delete`（使用 UE 内存管理）

### 性能
- [ ] Tick 函数中没有重计算（考虑缓存）
- [ ] 没有每帧的 `FindObject` / `GetAllActorsOfClass`
- [ ] 蓝图中没有每帧的复杂 Cast

### 强制规则
```
⚠️ 如果用户说"先不清理"，记录技术债务并标注 [调试代码残留]
```

---

## 快速决策流

```
修改完成？
  ├─ C++ 代码？
  │   ├─ 编译通过？ → Gate 2 → Gate 3 → Gate 4 → Gate 5 → ✅ 完成
  │   └─ 编译失败？ → unreal-build-fix → 修复 → 重新编译
  │
  ├─ Blueprint？
  │   ├─ 编译通过？ → PIE 验证？ → Gate 3 → Gate 4 → Gate 5 → ✅ 完成
  │   └─ 节点断开？ → 修复 → 重新编译
  │
  ├─ 配置/数据？
  │   └─ precheckin 导出？ → 数据验证 → Gate 4 → ✅ 完成
  │
  └─ 其他？
      └─ Gate 3 → Gate 4 → Gate 5 → ✅ 完成
```

---

## 与现有 Skill 的调用链

| 本 Gate | 调用的 Skill | 原因 |
|---------|-------------|------|
| Gate 1 | `unreal-build-commands` | UBT 编译 |
| Gate 1 | `unreal-build-fix` | 编译错误诊断 |
| Gate 1 | `ue-cli-blueprint` | Blueprint 编译 |
| Gate 1 | `precheckin` | 配置导出验证 |
| Gate 2 | `ue-cli-automation` | 自动化测试 |
| Gate 2 | `pie-error-fix-notify` | PIE 错误修复 |
| Gate 2 | `ue-cli-runtime` | PIE 运行时验证 |
| Gate 3 | `native-class-derivation` | 派生类规则检查 |
| Gate 3 | `ue-software-architecture` | 命名规范检查 |
| Gate 4 | `p4-workflow` | 版本控制操作 |
| Gate 4 | `pr` | CL 描述生成 |

## 参考
- 完整预提交检查表（可打印）：`references/pre-submit-checklist.md`
