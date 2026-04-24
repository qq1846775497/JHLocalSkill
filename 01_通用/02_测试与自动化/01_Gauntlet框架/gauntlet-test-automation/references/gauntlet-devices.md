# Gauntlet Device Pool & Reservation

Reference for device management, `DevicePool`, `DeviceDefinition`, validators, and troubleshooting.

---

## DevicePool Singleton

`Framework/Devices/Gauntlet.DevicePool.cs`

`DevicePool.Instance` is the global inventory broker. It holds two collections:
- **UnprovisionedDevices** — `DeviceDefinition` records not yet materialized as `ITargetDevice`
- **AvailableDevices** — provisioned `ITargetDevice` instances ready for assignment
- **ReservedDevices** — devices currently assigned to a running test

Provisioning is **lazy**: a `DeviceDefinition` stays unprovisioned until a test's `IsReadyToStart()` triggers `TryReserveDevices()`.

### Initialization (by TestExecutor)

1. `DevicePool.AddLocalDevices(platforms)` — adds the localhost as an unprovisioned device for each requested platform
2. `-Devices=` CLI arg — additional devices parsed and added as `DeviceDefinition` records
3. Device JSON file (`-DeviceMapFile=`) — bulk device definitions from JSON
4. `IDeviceReservationService` backends — Horde remote pool (invoked lazily on first reservation)

---

## DeviceDefinition Fields

```csharp
class DeviceDefinition
{
    string Name;            // Friendly name (e.g., "TestPhone01")
    string Address;         // Hostname, IP, or ADB serial
    string Platform;        // "Win64", "Android", "IOS", "Linux", "Mac"
    EPerfSpec PerfSpec;     // Minimum / Recommended / High / Unspecified
    string Model;           // Hardware model string for constraint matching
    bool Available;         // Whether device is currently available
    TimeRange AvailableTime; // Window when device is available (null = always)
    string[] Tags;          // Arbitrary labels for tag-based selection
    string DeviceData;      // Platform-specific JSON blob (SSH credentials, etc.)
    bool RemoveOnShutdown;  // Remove from pool after all tests finish
}
```

### JSON Device File Format

```json
[
  {
    "Name": "WinPC01",
    "Address": "192.168.1.10",
    "Platform": "Win64",
    "PerfSpec": "High",
    "Model": "Dell XPS 9700",
    "Tags": ["Desktop", "HighSpec"],
    "Available": true
  },
  {
    "Name": "Pixel7Pro",
    "Address": "emulator-5554",
    "Platform": "Android",
    "PerfSpec": "Recommended",
    "Model": "Pixel 7 Pro",
    "Tags": ["Mobile", "Android13"]
  }
]
```

---

## EPerfSpec — Hardware Mapping Guide

| Value | Meaning | Typical Hardware |
|-------|---------|-----------------|
| `Unspecified` | No performance requirement | Any device |
| `Minimum` | Meets minimum spec requirements | Low-end / QA lab devices |
| `Recommended` | Meets recommended spec | Mid-range consumer hardware |
| `High` | High-end / perf benchmarking | Top-spec devices, perf farms |

Set `PerfSpec` on `UnrealDeviceTargetConstraint` in your `UnrealSessionRole` to filter the pool:

```csharp
Constraint = new UnrealDeviceTargetConstraint(
    UnrealTargetPlatform.Android,
    perfSpec: EPerfSpec.Recommended)
```

---

## Device Tag Matching

Tags allow flexible device selection without hardcoding names:

```csharp
// Require both tags
Constraint = new UnrealDeviceTargetConstraint(
    UnrealTargetPlatform.Win64,
    requiredTags: new[] { "HighSpec", "Desktop" });

// Block a tag
Constraint = new UnrealDeviceTargetConstraint(
    UnrealTargetPlatform.Win64,
    blockedTags: new[] { "Unstable" });
```

CLI: `-Devices=Win64,Tag:HighSpec` — selects Win64 devices that have the "HighSpec" tag.

`UnrealDeviceTargetConstraint.Check(ITargetDevice)` and `Check(DeviceDefinition)` perform the matching. `IsIdentity()` returns true when the constraint matches any device of the platform.

---

## Local Device Pool Setup

For developer machines, devices can be specified via:

**CLI:**
```bash
-Devices=Win64:hostname1,Linux:192.168.1.20
-Devices=Win64    # use local machine for Win64
```

**Environment variable:** `UE_GAUNTLET_DEVICES=Win64:host1,Android:192.168.x.x`

**JSON file:**
```bash
-DeviceMapFile=D:/CI/devices.json
```

`DevicePool.AddLocalMachine()` is called automatically to add `localhost` when the target platform matches the agent's OS.

---

## Remote Reservation (Horde Backend)

`IDeviceReservationService` implementations are discovered via reflection at startup. The Horde implementation:
- `Framework/Devices/Gauntlet.UnrealDeviceReservation.cs`
- `Framework/Devices/Gauntlet.DeviceReservationService.cs`

Reservation flow:
1. `UnrealSession.TryReserveDevices()` calls `DevicePool.CheckAvailableDevices(constraints)`
2. If local devices satisfy constraints → allocate from local pool
3. If not → call `IDeviceReservationService.ReserveDevices(constraints, waitSeconds)`
4. Service issues a REST lease request to the Horde device service
5. Horde returns matching `DeviceDefinition` records
6. `DevicePool` materializes these as `ITargetDevice` instances
7. A heartbeat thread calls `IDeviceReservation.Extend()` every ~60s to keep the lease alive
8. On `CleanupTest()`, `IDeviceReservation.Dispose()` releases the lease

---

## Device Validators

Before a device is assigned to a test, it passes through a chain of `IDeviceValidator` implementations (discovered via reflection):

| Validator | File | What It Checks |
|-----------|------|----------------|
| `DeviceFirmwareValidator` | `Gauntlet.DeviceFirmwareValidator.cs` | Firmware version ≥ minimum required |
| `DeviceLoginValidator` | `Gauntlet.DeviceLoginValidator.cs` | Can log into required online services |
| `DeviceProfileValidator` | `Gauntlet.DeviceProfileValidator.cs` | Device config profile is applied |

### Writing a Custom Validator

```csharp
public class MyDeviceValidator : IDeviceValidator
{
    public bool Validate(ITargetDevice Device, UnrealDeviceTargetConstraint Constraint)
    {
        // Return false to reject the device for this test
        if (Device.Platform == UnrealTargetPlatform.Android)
        {
            // Check for required ADB feature
            return CheckAdbFeature(Device, "MyFeature");
        }
        return true; // platform not relevant, pass through
    }
}
```

Validators are discovered automatically — just implement `IDeviceValidator` in a loaded assembly.

---

## Platform-Specific Device Quirks

### Windows (TargetDeviceWindows)
- Uses local process launch for local devices; RDP for remote
- Sandbox path defaults to `%TEMP%\Gauntlet\<project>\`
- Multiple Windows devices on the same machine possible via different `Address` + sandbox paths
- Build type dispatch: `NativeStagedBuild` → `StagedBuild` → `EditorBuild` → `IWindowsSelfInstallingBuild`

### Linux (TargetDeviceLinux)
- Requires SSH access (`ssh user@host`) with key-based auth or stored credentials in `DeviceData`
- Artifact pull via SCP / SFTP
- `DeviceData` JSON format: `{ "username": "...", "privatekey": "..." }`
- Agent running AutomationTool does **not** need to be Linux — cross-platform SSH from Windows is supported

### Mac (TargetDeviceMac)
- Local: direct process spawn
- Remote: SSH, same credential format as Linux
- `.app` bundle detection; codesign validation on install
- Notarization state checked if `RequireNotarized` flag set in DeviceData

### Android (TargetDeviceAndroid)
- `Address` = ADB serial number (e.g., `emulator-5554`, `R5CT300ABCD`)
- Multiple physical devices: list separate `DeviceDefinition` entries per serial
- Implements `IWithPLMSuspend` (background suspend) and `IWithPLMConstrain` (CPU/RAM constrain)
- OBB files installed separately after APK
- Artifacts pulled via `adb pull`

### iOS (TargetDeviceIOS)
- Requires `libimobiledevice` toolchain on the agent machine
- `Address` = UDID (40-char hex string)
- Must have valid provisioning profile installed on device
- Implements `IWithPLMSuspend` and `IWithPLMConstrain`
- `IOSAppium` integration available for UI-level automation

### Null (TargetDeviceNull)
- Stub device — no actual hardware
- Used for `ERoleModifier.Null` roles (headless server, mock client)
- `InstallBuild()` and `Run()` are no-ops
- Useful in CI configs where one role doesn't need a real device

---

## Troubleshooting: InsufficientDevices

When a test fails with `TestResult.InsufficientDevices`, work through this checklist:

1. **Check the `-Wait=` flag** — default is 300s. If 0, the test fails immediately when no device is free. Set `-Wait=120` to give devices time to become available.

2. **Count devices vs. roles** — each non-Null role needs one device. If your test has `Server + Client` = 2 devices needed but the pool only has 1, it will always fail.

3. **Check platform match** — a Win64 role cannot be satisfied by a Linux device. Verify `DeviceDefinition.Platform` matches the role's `UnrealTargetPlatform`.

4. **Check PerfSpec** — if the role's constraint requires `EPerfSpec.High` but the pool only has `Recommended` devices, no match.

5. **Check tag requirements** — required tags must all be present on the device; blocked tags must all be absent.

6. **Check time windows** — `DeviceDefinition.AvailableTime` may exclude the current time.

7. **Check Horde connectivity** — if using remote reservation, verify the Horde device service endpoint is reachable and the agent has a valid lease token.

8. **Check device validator rejection** — validators can silently reject a device. Enable `-VeryVerbose` to see validation output.

9. **Check device is not stuck reserved** — if a previous test crashed without `CleanupTest()` running, the device may still be marked reserved. Restart the device service or remove the device from the pool JSON and re-add.
