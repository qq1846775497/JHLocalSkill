---
name: ue-cli-development
title: ue-cli Development Workflow
description: Development workflow for the Tools/ue-cli Python repository. Use this skill when modifying ue-cli code, adding or refactoring ue-cli domain commands, changing its BAT build/test tooling, updating unit tests, packaging bin/ue-cli.exe, or diagnosing ue-cli development/build/test failures. Do not use this for ordinary ue-cli usage; use the ue-cli-shared/runtime/blueprint/asset skills for calling UE tools.
tags: [UE-CLI, Python, Tooling, Build, Test, SoftUEBridge, Developer-Workflow]
---

# ue-cli Development Workflow

This skill is for maintaining `Tools/ue-cli` itself. It is not the user-facing operation guide for calling Unreal Editor through `ue-cli`.

## 代码变更后编译

修改 `Tools/ue-cli/` 下的 Python 源码后，需重新编译生成 exe：

```powershell
Tools\ue-cli\ue-cli-dev.bat build
```

## Scope

Use this skill when the task is about:

- changing Python source under `Tools/ue-cli/src`
- adding, removing, or refactoring domain commands
- changing `ue-cli-dev.bat`, build behavior, dependency bootstrapping, or exe packaging
- updating unit tests under `Tools/ue-cli/tests`
- troubleshooting `ue-cli-dev.bat test`, `ue-cli-dev.bat build`, or generated `bin/ue-cli.exe`
- keeping this local CLI aligned with SoftUEBridge tool names and schemas

For operating UE through the CLI, prefer the domain usage skills:

- `ue-cli-shared` — 连通性检查、instance.json 发现
- `ue-cli-runtime` — 关卡 Actor 查询、运行时日志
- `ue-cli-blueprint` — Blueprint 查询与编译
- `ue-cli-asset` — 资产查询
- `ue-cli-remote-control` — UE Remote Control API（端口 30010），调用 BlueprintCallable 静态函数

## Repository Layout

`Tools/ue-cli` intentionally keeps the Python package shallow:

```text
Tools/ue-cli/
  ue-cli-dev.bat
  pyproject.toml
  README.md
  SKILL.md
  src/
    __main__.py
    app.py
    core/
      client.py
      discovery.py
      output.py
    domains/
      setup/commands.py
      tools/commands.py
      runtime/commands.py
      blueprint/commands.py
      asset/commands.py
      automation/commands.py
      remote_control/
        __init__.py
        client.py        # RemoteControlClient (stdlib urllib, 无第三方依赖)
        commands.py      # ACTIONS 注册表 + register_remote_control()
  tests/
  bin/ue-cli.exe
  references/
    remote-control.md    # remote-control domain 开发参考
```

Do not reintroduce `src/ue_cli` or `ue_cli` package nesting. The import root is `src`, and direct development execution is `python -m src` through the BAT wrapper.

## Toolchain Rules

Use the repo-local Engine Python through `ue-cli-dev.bat`. Do not add Makefile-based workflows.

```bat
Tools\ue-cli\ue-cli-dev.bat test
Tools\ue-cli\ue-cli-dev.bat build
Tools\ue-cli\ue-cli-dev.bat clean
Tools\ue-cli\ue-cli-dev.bat --help
```

`ue-cli-dev.bat` resolves Python from:

```text
Engine\Binaries\ThirdParty\Python3\Win64\python.exe
```

`ue-cli-dev.bat build` checks for `PyInstaller` and installs it with the bundled Python pip when missing. Keep dependency bootstrapping inside BAT unless there is a clear reason to add a separate script.

## Architecture Rules

Keep the CLI thin. SoftUEBridge remains the source of truth for actual UE behavior.

- `src/app.py` owns global argparse options, top-level parser creation, domain registration, and process exit behavior.
- `src/core/client.py` owns HTTP and JSON-RPC transport only.
- `src/core/discovery.py` owns `.soft-ue-bridge/instance.json` discovery and host/port override resolution.
- `src/core/output.py` owns pretty/json formatting.
- Each domain command must live in its own folder under `src/domains/<domain>/commands.py`.
- Domain wrappers should convert CLI flags into a `client.call_tool(<soft-ue-bridge-tool>, arguments)` call.
- Keep `tools call` as the escape hatch instead of wrapping every SoftUEBridge tool immediately.

## Adding A Domain Command

Follow this sequence when adding or changing a domain command:

1. Confirm the SoftUEBridge tool name and argument schema from `Main/Plugins/SoftUEBridge/SKILL.md` or the plugin source.
2. Add or edit `src/domains/<domain>/commands.py`.
3. Register the domain in `src/app.py` only if it is a new domain.
4. Add or update a unit test in `tests/test_domain_commands.py` that verifies the exact `client.call_tool` name and argument object.
5. Keep optional CLI flags explicit and stable; do not pass unset flags if the bridge expects them omitted.
6. Run `Tools\ue-cli\ue-cli-dev.bat test`.
7. If packaging behavior changed or imports moved, run `Tools\ue-cli\ue-cli-dev.bat build` and then `Tools\ue-cli\bin\ue-cli.exe --help`.

> **`remote-control` domain 例外**：它不调用 `BridgeClient`，使用独立的 `RemoteControlClient`（REST PUT，端口 30010）。
> 添加新调用目标时，只需在 `commands.py` 的 `ACTIONS` 字典中增加一行，无需新增 handler。
> 详见 `references/remote-control.md`。

## Testing Expectations

Every changed module should have a unit test unless the change is documentation-only or pure BAT plumbing.

Preferred test coverage:

- command registration and argument mapping for domain commands
- discovery edge cases for project dir, host override, and port override
- JSON-RPC envelope handling and error handling in `BridgeClient`
- pretty/json output formatting

Use standard library `unittest`; do not add pytest unless the project deliberately migrates.

## Build And Cleanup

Build with:

```bat
Tools\ue-cli\ue-cli-dev.bat build
```

The build output is:

```text
Tools/ue-cli/bin/ue-cli.exe
```

The BAT should remove PyInstaller intermediates after a successful or failed build:

- `Tools/ue-cli/build/`
- `Tools/ue-cli/ue-cli.spec`

Before wrapping up, check that generated cache files are not present or opened in P4:

```powershell
Get-ChildItem Tools/ue-cli -Recurse -Force | Where-Object { $_.FullName -match '__pycache__|\.pyc$|ue-cli\.spec$|\\build(\\|$)|\\ue_cli(\\|$)|Makefile$' }
p4 opened -c 87391 | Select-String -Pattern 'Makefile|__pycache__|\.pyc|build\\|ue-cli\.spec|Tools/ue-cli/ue_cli'
```

Adjust the changelist number to the active task.

## P4 And Index Hygiene

When editing `Tools/ue-cli/SKILL.md`, update `SKILL.index.json` with:

```bat
cmd.exe /c skill_index_gen.bat
```

Keep changed ue-cli files in the task changelist. Verify the default changelist is empty before handoff:

```bat
p4 opened -c default
p4 opened -c <task-cl>
```

Do not submit unless the user explicitly asks for submission.

## Development Checklist

Before final response on ue-cli development tasks:

- Confirm the package root is still `Tools/ue-cli/src`.
- Confirm every domain command is under `src/domains/<domain>/commands.py`.
- Run `Tools\ue-cli\ue-cli-dev.bat test` for source changes.
- Run `Tools\ue-cli\ue-cli-dev.bat build` for packaging or import-layout changes.
- Run `Tools\ue-cli\bin\ue-cli.exe --help` after build.
- Remove `__pycache__`, `.pyc`, `build/`, `ue-cli.spec`, old `ue_cli`, and Makefile remnants.
- Rebuild `SKILL.index.json` if any `SKILL.md` changed.
- Check P4 default changelist is empty and task changelist contains only relevant files.

---

## References

| 文件 | 内容 |
|------|------|
| `references/remote-control.md` | `remote-control` domain 完整开发参考：传输层差异、ACTIONS 注册表、objectPath 格式、shell 路径陷阱、BridgeEditorFunctionLibrary 接口说明 |
