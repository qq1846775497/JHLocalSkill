# Gauntlet Built-In Test Nodes

All located in `Engine/Source/Programs/AutomationTool/Gauntlet/Unreal/Automation/` and related directories.

Invoke via: `RunUAT RunUnreal -Tests=<NodeName> -Project=MyGame -Platform=Win64 -Build=Staged`

---

## UE.BootTest

**File:** `Unreal/Automation/UE.BootTest.cs` (or `Unreal/Game/UnrealGame.DefaultNode.cs`)
**Purpose:** Verify the engine boots to the main menu and exits cleanly.

**What it does:**
1. Launches a client process with `-unattended -nullrhi` (or specified RHI)
2. Waits for `EngineInitialized` sentinel in the log
3. Waits a configurable duration at idle
4. Sends a clean quit command
5. Passes if process exits with code 0

**Key config params:**

| `[AutoParam]` | CLI | Default | Notes |
|---------------|-----|---------|-------|
| `BootDuration` | `-bootduration=` | 60 | Seconds to wait after init before quitting |

**Example:**
```bash
RunUAT RunUnreal -Project=MyGame -Platform=Win64 -Configuration=Development \
  -Build=Staged -Tests=UE.BootTest -bootduration=30
```

**Typical failures:** Missing DLLs (`InitializationFailure`), crash on startup (`EncounteredFatalError`), log shows `RequestedExit` before `EngineInitialized`.

---

## UE.Automation (EngineTest)

**File:** `Unreal/Engine/UnrealTests.cs` — class `EngineTest`
**Entry:** `RunUAT RunUnrealTests` (which sets `DefaultTestName=EngineTest`)
**Purpose:** Run UE's built-in in-engine automation suite via the editor.

**What it does:**
1. Launches the editor with `-ExecCmds="Automation RunTests <filter>; Quit"`
2. Streams the editor log watching `LogAutomationController` output
3. Parses per-test pass/fail/skip via `AutomationLogParser`
4. Fails if any test failed or zero tests ran
5. Generates HTML report + links to the automation report file

**Key config params:**

| `[AutoParam]` | CLI | Default | Notes |
|---------------|-----|---------|-------|
| `UseEditor` | `-useeditor` | true | Run via editor (vs game client) |
| `TestFilter` | `-testfilter=` | `""` | Filter expression passed to automation |
| `ReportOutputPath` | `-reportoutputpath=` | `""` | Where to write the HTML report |

**Example:**
```bash
RunUAT RunUnrealTests -Project=MyGame -Platform=Win64 -Build=Editor \
  -testfilter="MyGame." -ReportOutputPath=D:/TestOutput
```

**Idle detection:** If `LogAutomationController` produces no output for 30 minutes, the editor is considered hung and the test is aborted.

**Typical failures:** Test filter matches nothing (zero tests = fail), editor crashes mid-suite, individual test assertions failed.

---

## UE.CookByTheBook

**File:** `Unreal/Automation/UE.CookByTheBook.cs` (plus 9 variant files)
**Purpose:** Verify content cooking via the editor's cook-by-the-book pipeline.

**Base class behavior:**
1. Launches the editor with `-run=cook -targetplatform=<Platform> -map=...`
2. Monitors the cook log for progress and errors
3. Passes when the cook completes with exit code 0

**Cook variants:**

| Node Name | File | Variant Behavior |
|-----------|------|-----------------|
| `UE.CookByTheBook` | `UE.CookByTheBook.cs` | Standard cook from current DDC state |
| `UE.CookByTheBook.Cold` | `UE.ColdCookByTheBook.cs` | Force-clears DDC before cooking (worst-case cache miss) |
| `UE.CookByTheBook.Fast` | `UE.FastCookByTheBook.cs` | Pre-warm DDC then cook (best-case) |
| `UE.CookByTheBook.Incremental` | (inline) | Cook only assets changed since last cook |
| `UE.CookByTheBook.Iterative` | (inline) | Two-pass iterative cook validation |
| `UE.CookByTheBook.Interrupted` | `UE.InterruptedCookByTheBook.cs` | Interrupt mid-cook, resume, verify completeness |
| `UE.CookByTheBook.Unversioned` | `UE.UnversionedCookByTheBook.cs` | Cook without asset version stamps |
| `UE.CookByTheBook.SinglePackage` | `UE.CookSinglePackageByTheBook.cs` | Cook a single package in isolation |
| `UE.CookByTheBook.DLC` | (inline) | Cook a DLC chunk |
| `UE.CookByTheBook.CacheSettings` | `UE.CookByTheBookCacheSettings.cs` | Validate DDC cache settings |

**Key config params:**

| `[AutoParam]` | CLI | Default | Notes |
|---------------|-----|---------|-------|
| `CookPlatform` | `-cookplatform=` | (role platform) | Target cook platform |
| `MapsToCook` | `-map=` | `""` | Comma-separated map list |
| `CookArgs` | `-cookargs=` | `""` | Extra cook commandline |
| `NumCookIterations` | `-cookiterations=` | 2 | For Iterative variant |

**Example:**
```bash
RunUAT RunUnreal -Project=MyGame -Platform=Win64 -Build=Editor \
  -Tests=UE.CookByTheBook.Cold -cookplatform=Android
```

---

## UE.Networking

**File:** `Unreal/Automation/UE.Networking.cs` (if present) or via `DefaultTest` with `-server`
**Purpose:** Verify a client can connect to a dedicated server.

**What it does:**
1. Launches a server role on one device
2. Waits for server to be ready (listens for log pattern)
3. Launches a client role that connects to the server
4. Verifies both processes run for a minimum duration and exit cleanly

**Example:**
```bash
RunUAT RunUnreal -Project=MyGame -Platform=Win64 -Build=Staged \
  -Tests=MyGame.DefaultTest -server -numclients=2 \
  -Devices=Win64:server-host,Win64:client-host
```

---

## UE.PLMTest

**File:** `Unreal/Automation/UE.PLMTest.cs`
**Purpose:** Test mobile Process Lifecycle Management (suspend/resume/constrain) transitions.

**What it does:**
1. Launches the game on a mobile device
2. Sends PLM commands via `IWithPLMSuspend` / `IWithPLMConstrain` interface
3. Verifies the process survives suspend/resume correctly
4. Checks for ensure violations or crashes

**Requires:** Android or iOS device with PLM support.

---

## UE.ZenLoaderTest / UE.ZenStreaming

**Files:** `Unreal/Automation/UE.ZenLoaderTest.cs`, `UE.ZenStreaming.cs`
**Purpose:** Validate Zen I/O async asset streaming under load.

- **ZenLoaderTest** — verifies that the Zen asset I/O scheduler correctly loads assets asynchronously without hitches
- **ZenStreaming** — stress-tests the streaming system with concurrent asset requests

---

## UE.ErrorTest

**File:** `Unreal/Automation/UE.ErrorTest.cs`
**Purpose:** Intentionally trigger engine errors to verify the Gauntlet detection pipeline works.

**What it does:**
1. Launches a game with `-ExecCmds="GauntletSelfTest Crash"` (or similar)
2. Expects the process to produce a fatal error log line
3. **Passes** when `UnrealLogParser` detects `EncounteredFatalError`
4. **Fails** if the process exits cleanly (detection pipeline broken)

Useful for CI health checks: if `UE.ErrorTest` passes, error detection is working.

---

## UE.InstallOnly

**File:** `Unreal/Automation/UE.InstallOnly.cs`
**Purpose:** Install a build onto a device without launching it. Smoke-tests packaging.

**What it does:**
1. All session roles have `ERoleModifier.Dummy` (install but don't run)
2. Verifies `IAppInstall` completes without errors
3. Passes if installation succeeds

Useful for: verifying a packaged build is installable before investing in full run tests.

---

## ElementalDemoTest (Sample)

**File:** `Unreal/Game/Samples/ElementalDemoTest.cs`
**Purpose:** Reference implementation of a game-specific test. Demonstrates:
- Reading perf snapshots via `UnrealSnapshotSummary<UnrealHealthSnapshot>`
- Zipping FPS chart CSVs from `Profiling/FPSChartStats/`
- Uploading to `-uploadfolder=`

---

## FortGPUTestbedPerfTest (Sample)

**File:** `Unreal/Game/Samples/FortGPUTestbedPerfTest.cs`
**Purpose:** Performance benchmark test. Demonstrates:
- Streaming the log via `UnrealLogStreamParser` during `TickTest()`
- Watching for a custom completion token (`"FortGPUTestbedPerfTest Finished"`)
- Signaling pass from within `TickTest()` rather than waiting for process exit

---

## DefaultTest (UnrealGame.DefaultNode)

**File:** `Unreal/Game/UnrealGame.DefaultNode.cs`
**Purpose:** Configurable generic test. Reads from CLI:
- `-numclients=N` → add N client roles
- `-server` → add a server role
- `-editor` → add an editor role

Used as the base for simple "just launch the game" tests without writing a custom node.

---

## EditorTest.BootTest

**File:** `Editor/EditorTest.BootTest.cs`
**Purpose:** Verify the Unreal Editor boots and exits cleanly. Similar to `UE.BootTest` but for the editor binary.

---

## CookUtils/ Helpers

**Files:** `Unreal/Automation/CookUtils/`

| Class | Purpose |
|-------|---------|
| `ContentFolder` | Represents a directory of cooked content |
| `ContentFolderReader` | Reads and compares content folder structure |
| `ContentFolderEqualityComparer` | Compares two content folders for diff |
| `Checker` | Validates cooked content against expected state |

Used internally by cook test variants to verify incremental cook correctness.

---

## Quick Reference Table

| Node | Roles | Build Required | Key Use Case |
|------|-------|---------------|-------------|
| `UE.BootTest` | Client | Staged | CI smoke test |
| `UE.Automation` (EngineTest) | Editor | Editor | In-engine test suite |
| `UE.CookByTheBook` | Editor | Editor | Cook validation |
| `UE.CookByTheBook.Cold` | Editor | Editor | Worst-case cook perf |
| `UE.Networking` | Server + Client | Staged | Multiplayer smoke |
| `UE.PLMTest` | Client (mobile) | Staged | Mobile lifecycle |
| `UE.ZenLoaderTest` | Client | Staged | Streaming correctness |
| `UE.ErrorTest` | Client | Staged | Detection pipeline health |
| `UE.InstallOnly` | Any (Dummy) | Staged | Packaging smoke |
| `DefaultTest` | Configurable | Staged | Quick custom runs |
