# Gauntlet Platform Support

Per-platform details for device backends, build sources, and platform-specific quirks.

---

## Platform Summary Table

| Platform | `ITargetDevice` impl | `IFolderBuildSource` impl | Build format | Toolchain |
|----------|---------------------|--------------------------|-------------|----------|
| Win64 | `TargetDeviceWindows` | `WindowsBuildSources` | Staged / Native / Editor | Local process / RDP |
| Linux | `TargetDeviceLinux` | `LinuxBuildSources` | Staged | SSH + SCP |
| Mac | `TargetDeviceMac` | `MacBuildSource` | `.app` bundle | Local process / SSH |
| Android | `TargetDeviceAndroid` | `AndroidBuildSource` | APK + OBB | ADB |
| iOS | `TargetDeviceIOS` | `IOSBuildSource` | IPA | libimobiledevice |
| Null | `TargetDeviceNull` | (none) | (none) | No-op stub |

All implementations live under `Engine/Source/Programs/AutomationTool/Gauntlet/Platform/<OS>/`.

---

## Windows (Win64)

**Files:** `Platform/Windows/Gauntlet.TargetDeviceWindows.cs`, `Gauntlet.WindowsBuildSources.cs`

### Device Connection
- **Local:** Process spawn directly via `System.Diagnostics.Process`
- **Remote:** Not natively supported (use SSH/PSRemoting externally); for remote Windows, provide the agent machine as the "device"

### Build Type Dispatch

`CreateAppInstall()` dispatches based on what the build source provides:

| Build Type | Condition | Install Method |
|-----------|-----------|---------------|
| `NativeStagedBuild` | Staged with native layout | Copy to sandbox |
| `StagedBuild` | Standard staged | Copy to sandbox |
| `EditorBuild` | Editor binary | No install (use in-place) |
| `IWindowsSelfInstallingBuild` | Self-installing package | Run installer |

### Sandbox Layout
Default sandbox: `%TEMP%\Gauntlet\<ProjectName>\<Configuration>\`

Override via `UnrealAppConfig.Sandbox`.

### Build Discovery Paths

`WindowsBuildSources` scans for builds at:
```
<BuildPath>/
  <ProjectName>/Binaries/Win64/          ← NativeStagedBuild
  WindowsClient/ or WindowsNoEditor/    ← StagedBuild
  Engine/Binaries/Win64/                 ← EditorBuild
```

### PGO

`WindowsPGO.cs` — collects and merges MSVC PGO profiles. Invoked via `UnrealPGONode`.

### Self-Tests
`Gauntlet.SelfTest.TestTargetDeviceWindows.cs`, `Gauntlet.SelfTest.TestUnrealInstallAndRunWindows.cs`

---

## Linux

**Files:** `Platform/Linux/Gauntlet.TargetDeviceLinux.cs`, `Gauntlet.LinuxBuildSources.cs`

### Device Connection
- SSH-based. Requires key-based auth or credentials in `DeviceDefinition.DeviceData`:
```json
{
  "username": "testrunner",
  "privatekey": "/path/to/id_rsa"
}
```
- File transfer: SCP / SFTP
- The AutomationTool agent does **not** need to be Linux; Windows agents can SSH to Linux devices

### Artifact Pull
Artifacts are pulled via `scp` from `<sandbox>/Saved/` to the agent's local artifact directory.

### Build Discovery Paths

```
<BuildPath>/
  LinuxClient/ or LinuxNoEditor/    ← StagedBuild
  LinuxServer/                       ← Server build
```

### Cross-Compilation from Windows
Linux builds produced by a Windows agent need the Linux cross-toolchain. Gauntlet itself only *deploys* and *runs* the build; cross-compilation is handled by UBT, not Gauntlet.

### PGO
`LinuxPGO.cs` — LLVM PGO profile collection and `llvm-profdata merge`.

---

## Mac

**Files:** `Platform/Mac/Gauntlet.TargetDeviceMac.cs`, `Gauntlet.MacBuildSource.cs`

### Device Connection
- **Local:** Direct process spawn
- **Remote:** SSH (same credential format as Linux)
- `.app` bundle detection: looks for `<ProjectName>.app` in the staged directory
- Codesign awareness: validates signature before running if `RequireSignedBuild` is set

### Build Discovery Paths

```
<BuildPath>/
  Mac/                    ← Contains <ProjectName>.app
  MacNoEditor/
```

### Notes
- Notarization state can be checked via `DeviceData.RequireNotarized`
- Universal binary (arm64 + x86_64) builds are handled transparently

---

## Android

**Files:** `Platform/Android/Gauntlet.TargetDeviceAndroid.cs`, `Gauntlet.AndroidBuildSource.cs`

### Device Connection
- ADB (Android Debug Bridge)
- `Address` = ADB serial number: e.g., `emulator-5554`, `R5CT300ABCD`, `192.168.1.5:5555` (TCP/IP)
- Requires ADB server running on the agent machine
- Multiple physical devices: one `DeviceDefinition` per serial

### Install Flow
1. `adb install -r <apk>` — install APK
2. `adb push <obb> /sdcard/Android/obb/<package>/` — install OBB data
3. Launch via `adb shell am start ...`

### Log Capture
- `adb logcat -s UE4,UE5` — filtered log stream
- Artifact pull: `adb pull /sdcard/Android/data/<package>/files/Saved/` 

### PLM (Process Lifetime Management)
Implements `IWithPLMSuspend` and `IWithPLMConstrain`:
```csharp
// Suspend app (background it)
(device as IWithPLMSuspend).SuspendApp();

// Constrain CPU/RAM
(device as IWithPLMConstrain).ConstrainApp();
```
Used by `UE.PLMTest`.

### Multi-Device Gotchas
- Two devices on the same host with the same model will have the same `DeviceDefinition.Model` — distinguish them via unique `Name` or `Tags`
- ADB daemon must be running with correct permissions; `adb start-server` on the agent may be needed
- API level mismatch: build targeting API 30 won't install on API 28 device

### Build Discovery Paths
```
<BuildPath>/
  Android_ASTC/    or   Android_ETC2/
    <ProjectName>.apk
    <ProjectName>.obb   (if > 2GB data)
```

### PGO
`AndroidPGO.cs` — LLVM PGO on Android (NDK toolchain).

---

## iOS

**Files:** `Platform/IOS/Gauntlet.TargetDeviceIOS.cs`, `Gauntlet.IOSBuildSource.cs`

### Device Connection
- `libimobiledevice` toolchain: `ideviceinstaller`, `idevicesyslog`, `ideviceinfo`
- `Address` = UDID (40-character hex, e.g., `00008101-000A1234567890`)
- Device must be trusted on the Mac agent machine
- Provisioning profile must be installed on the device

### Install Flow
1. `ideviceinstaller -i <ipa>` — install IPA
2. Launch via `idevicedebug run <bundle-id>`

### Log Capture
`idevicesyslog -u <udid>` — filtered by bundle ID

### Appium Integration
`IOSAppium.cs` — wraps Appium for UI-level automation on top of Gauntlet. Enables simulating taps, swipes, and reading accessibility labels.

### Build Discovery Paths
```
<BuildPath>/
  IOS/
    <ProjectName>.ipa
```

### Notes
- Re-signing IPAs for different provisioning profiles is not handled by Gauntlet — do this in the build pipeline before Gauntlet runs
- iOS 17+ may require device in "Developer Mode" — enable via Settings → Privacy & Security

---

## Null Device

**File:** `Platform/Null/Gauntlet.TargetDeviceNull.cs`

A **stub device** that does nothing.

| Method | Behavior |
|--------|---------|
| `Connect()` | Returns `true` |
| `InstallBuild()` | Returns a no-op `IAppInstall` |
| `Run()` | Returns a no-op `IAppInstance` (immediately "exited" with code 0) |
| `GetArtifacts()` | No-op |

### When to Use Null
- A role in a multi-process test that doesn't need a real device (e.g., a "dummy client" for load simulation)
- `ERoleModifier.Null` automatically uses `TargetDeviceNull`
- Headless CI where you want to test the orchestration logic without real hardware

---

## Build Source Discovery

`UnrealBuildSource.DiscoverBuilds(platform)` discovers `IFolderBuildSource` implementations at runtime via reflection:

```csharp
// Discovers all non-abstract IFolderBuildSource implementations in loaded assemblies
var sources = InterfaceHelpers.FindImplementations<IFolderBuildSource>();
// Filters to those that CanSupportPlatform(platform)
```

This means **adding a new platform** requires only implementing `IFolderBuildSource` in a new class — no central registration needed. The class is auto-discovered on the next run.

---

## Platform Self-Tests

Each desktop platform has co-located self-tests:

| Platform | Self-Test Files |
|----------|----------------|
| Windows | `Gauntlet.SelfTest.TestTargetDeviceWindows.cs`, `TestUnrealInstallAndRunWindows.cs` |
| Linux | `Gauntlet.SelfTest.TestTargetDeviceLinux.cs`, `TestUnrealInstallAndRunLinux.cs` |
| Mac | `Gauntlet.SelfTest.TestTargetDeviceMac.cs`, `TestUnrealInstallAndRunMac.cs` |

These validate the `ITargetDevice` contract and the full install-and-run cycle on each platform. Run via:
```bash
RunUAT TestGauntlet -Group=Platform
```
