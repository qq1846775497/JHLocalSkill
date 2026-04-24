# 常见代码库侦察模式

## 模式 A：定位某个函数/类的实现

```
1. Grep "void MyFunction" --glob="*.cpp" → files_with_matches
2. Grep "class AMyActor" --glob="*.h" → files_with_matches
3. 并行 ReadFile 最高匹配度的 2-3 个文件（line_offset 精确到函数/类声明）
4. 如需调用链，Grep "MyFunction(" 搜索所有调用点
```

## 模式 B：理解某个子系统的架构

```
1. Glob "Source/SubsystemName/**/*.h" → 获取所有公共头文件
2. 并行 ReadFile 每个头文件的类声明（前 50 行）
3. 绘制类关系图（谁继承谁、谁包含谁）
4. Grep "#include \"SubsystemName" 找跨模块依赖
```

## 模式 C：查找配置/数据表定义

```
1. Glob "Config/**/*.ini" + "**/*.json" + "**/*.csv"
2. Grep "ConfigKeyName" --glob="*.ini" → 定位配置段
3. ReadFile 相关 section
4. 追踪到代码中的读取点：Grep "ConfigKeyName" --glob="*.cpp"
```

## 模式 D：追踪 Blueprint 引用

```
1. Grep "/Game/Path/BP_Name" --glob="*.cpp" --glob="*.h" --glob="*.json"
2. 如果 Blueprint 已导出 JSON，ReadFile 导出的 JSON 获取变量/函数列表
3. 用 ue-cli-blueprint 查询运行时信息
```

## 模式 E：分析修改影响范围

```
1. 确定被修改的符号（函数名、类名、配置键）
2. Grep 搜索所有引用点（C++ + Blueprint JSON + 配置）
3. 分类影响：直接调用方 / 间接调用方 / 数据依赖
4. 输出影响范围报告
```

## 性能基准

| 操作 | 预估时间 | Token 消耗 |
|------|----------|-----------|
| Glob 扫描 | 2-5s | ~200 |
| Grep files_with_matches | 3-8s | ~100 |
| Grep content (-C 2, head 20) | 5-10s | ~500 |
| ReadFile 1 个文件（100 行）| 2-4s | ~800 |
| 并行 ReadFile 5 个文件 | 3-6s | ~4000 |
| 无侦察直接 ReadFile 20 个文件 | 40-80s | ~16000+ |

> 侦察协议 vs 盲目读取：**节省 80% 时间和 75% token**
