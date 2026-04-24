# 工作流打印版步骤清单

## C++ 修改闭环

```
□ Step 1: 侦察 — codebase-search 定位文件
□ Step 2: P4 Checkout — p4-workflow 迁出文件
□ Step 3: 规范确认 — ue-software-architecture 检查命名/GAS
□ Step 4: 修改 — unreal-cpp-workflow 编写代码
  └── [CONFIRM] 用户确认修改方案
□ Step 5: 审查 — code-quality-guardian 5-Gate
□ Step 6: 编译 — unreal-build-commands
  └── 失败 → unreal-build-fix → 重试(≤3)
□ Step 7: PIE — ue-cli-runtime / soft-ue-bridge
  └── 失败 → pie-error-fix-notify → 重试(≤3)
□ Step 8: 回归 — code-quality-guardian Gate 3
□ Step 9: 提交 — p4-workflow + pr
  └── [CONFIRM] 用户确认 CL 描述
```

## Blueprint 修改闭环

```
□ Step 1: 侦察 — codebase-search / ue-cli-asset
□ Step 2: P4 Checkout — p4-workflow
□ Step 3: 规范确认 — ue-software-architecture（是否应转 C++？）
□ Step 4: 修改 — ue-cli-blueprint / soft-ue-bridge
  └── [CONFIRM] 用户确认
□ Step 5: 审查 — code-quality-guardian（节点数、Cast）
□ Step 6: 编译 — ue-cli-blueprint
□ Step 7: PIE — ue-cli-runtime
□ Step 8: 回归 — code-quality-guardian
□ Step 9: 提交 — p4-workflow + pr
```

## 配置/数据修改闭环

```
□ Step 1: 侦察 — excel-query / entity-tag-modifier
□ Step 2: P4 Checkout — p4-workflow
□ Step 3: 修改 — entity-tag-modifier / equip-entry-pool-config
  └── [CONFIRM] 用户确认
□ Step 4: 导出验证 — precheckin
□ Step 5: 数据验证 — 检查 DataTable / 游戏内数值
□ Step 6: 提交 — p4-workflow + pr
```

## 资产修改闭环

```
□ Step 1: 侦察 — asset-export / ue-cli-asset
□ Step 2: P4 Checkout — p4-workflow
□ Step 3: 修改 — flowgraph-edit / damage-flow-graph-authoring / soft-ue-bridge
  └── [CONFIRM] 用户确认
□ Step 4: 审查 — code-quality-guardian（引用完整性）
□ Step 5: PIE — ue-cli-runtime
□ Step 6: 提交 — p4-workflow + pr
```

## 调试修复闭环

```
□ Step 1: 侦察 — codebase-search 定位报错源
□ Step 2: 诊断 — core-redirects-debug / pie-error-fix-notify / unreal-build-fix
□ Step 3: P4 Checkout — p4-workflow（如需要修改文件）
□ Step 4: 修复 — 按对应 skill 修复
  └── [CONFIRM] 用户确认修复方案
□ Step 5: 审查 — code-quality-guardian
□ Step 6: 编译 — unreal-build-commands / ue-cli-blueprint
□ Step 7: PIE — ue-cli-runtime
□ Step 8: 提交 — p4-workflow + pr
```

---

## Hard Gate 检查表

| Gate | 触发条件 | 必须人工干预？ |
|------|----------|---------------|
| 编译失败 ≥3 次 | unreal-build-commands 连续失败 | ✅ 是 |
| PIE 崩溃 ≥3 次 | PIE 连续崩溃或报错 | ✅ 是 |
| P4 冲突 | 文件已被他人 checkout | ✅ 是 |
| API 破坏 | 公开 API 签名变更未处理调用方 | ✅ 是 |
| 用户中止 | 用户选择 [D] 中止 | ✅ 是 |
