# Gauntlet RPC Framework

Reference for `Framework/RpcFramework/` — distributed test coordination between Gauntlet and running UE processes.

---

## Overview

The RpcFramework allows Gauntlet (the C# orchestrator) to communicate with **running UE processes** during a test. This enables:

- Sending commands to control test flow inside the game
- Querying game state from the orchestrator without parsing logs
- Coordinating multi-machine tests where different roles need to synchronize

**Files:** `Framework/RpcFramework/`
- `Gauntlet.GauntletHttpClient.cs` — HTTP client for Gauntlet REST API calls
- `Gauntlet.RpcExecutor.cs` — synchronous RPC execution
- `Gauntlet.RpcExecutorAsync.cs` — async RPC execution
- `Gauntlet.RpcLibrary.cs` — registry of available RPC endpoints
- `Gauntlet.RpcTargetRegistry.cs` — maps logical targets to network endpoints

---

## Architecture

```
[Gauntlet C# Orchestrator]
        │
        │  HTTP POST /rpc/<method>
        ▼
[UE Process (game/editor)]
  UGauntletRpcService (C++ plugin)
        │
        │  UFunction dispatch
        ▼
[Test logic inside UE]
```

The UE-side plugin (`UGauntletRpcService`) listens on an HTTP port and dispatches incoming RPC calls to registered handlers. Gauntlet's C# side uses `RpcExecutor` to send calls.

---

## RpcTargetRegistry

Maps logical role names to `(host, port)` pairs:

```csharp
// The registry is populated when UnrealSession launches processes
// Each process reports its RPC listen port via a log line:
// LogGauntlet: GauntletRpc: Listening on port 12345

// After launch, Gauntlet reads this port and registers:
RpcTargetRegistry.Register("Client", new RpcTarget("192.168.1.10", 12345));
RpcTargetRegistry.Register("Server", new RpcTarget("192.168.1.20", 12346));
```

---

## RpcLibrary

Registry of available RPC method signatures:

```csharp
// Gauntlet C# side defines the method contract:
public static class GameRpcMethods
{
    public const string StartBenchmark = "StartBenchmark";
    public const string GetFrameRate    = "GetFrameRate";
    public const string SetMap          = "SetMap";
}

// Method signatures are registered with parameter types:
RpcLibrary.Register(GameRpcMethods.StartBenchmark, typeof(StartBenchmarkRequest));
RpcLibrary.Register(GameRpcMethods.GetFrameRate,   typeof(GetFrameRateResponse));
```

---

## RpcExecutor (Synchronous)

```csharp
var executor = new RpcExecutor(RpcTargetRegistry.Get("Client"));

// Fire-and-forget command:
executor.Call(GameRpcMethods.SetMap, new SetMapRequest { MapName = "TestLevel" });

// Request with response:
var response = executor.Call<GetFrameRateResponse>(GameRpcMethods.GetFrameRate);
float currentFps = response.AverageFPS;
```

⚠️ **Never call synchronous RPC from `TickTest()`** — it blocks the main executor thread and stalls all other tests. Use `RpcExecutorAsync` from `TickTest()`.

---

## RpcExecutorAsync (Async)

```csharp
private RpcExecutorAsync AsyncExecutor;
private Task<GetFrameRateResponse> PendingFpsQuery;

protected override void TickTest(TestExecutionInfo TestInfo)
{
    base.TickTest(TestInfo);

    // Fire async query (non-blocking):
    if (PendingFpsQuery == null)
    {
        AsyncExecutor = new RpcExecutorAsync(RpcTargetRegistry.Get("Client"));
        PendingFpsQuery = AsyncExecutor.CallAsync<GetFrameRateResponse>(
            GameRpcMethods.GetFrameRate);
    }

    // Check if result arrived (non-blocking):
    if (PendingFpsQuery.IsCompleted)
    {
        var fps = PendingFpsQuery.Result.AverageFPS;
        if (fps < 30f)
            AddTestEvent(new UnrealTestEvent(EventSeverity.Warning,
                $"FPS dropped to {fps:F1}"));
        PendingFpsQuery = null; // ready for next query
    }
}
```

---

## Simple Two-Role RPC Handshake Example

**Scenario:** Server starts, waits for client to connect via RPC, then starts the test.

**UE-side (C++):**
```cpp
// Server registers handler:
GauntletRpc->RegisterHandler("ClientReady", [this]() {
    UE_LOG(LogGauntlet, Log, TEXT("Client connected, starting test"));
    StartTest();
});

// Client calls when ready:
GauntletRpc->Call("Server", "ClientReady", {});
```

**Gauntlet C# side (in `TickTest()`):**
```csharp
// After server is up, send "ClientReady" from orchestrator perspective:
if (ServerIsRunning && !ClientReadySent)
{
    var clientExecutor = new RpcExecutorAsync(RpcTargetRegistry.Get("Client"));
    await clientExecutor.CallAsync("NotifyServerClientReady", new {});
    ClientReadySent = true;
}
```

---

## When to Use RPC vs Alternatives

| Approach | When to Use |
|----------|-------------|
| **RPC** | Need real-time control or queries; multi-machine synchronization points |
| **Stdout / log parsing** | One-way signals (heartbeats, completion tokens, perf snapshots); read-only |
| **Shared filesystem** | Async data exchange (perf CSVs, screenshots); not time-critical |
| **ExecCmds** | Simple one-shot commands at launch time; doesn't need response |

RPC adds complexity — only use it when log parsing or `ExecCmds` can't solve the problem.

---

## Known Limitations

- **Latency:** Each RPC round-trip adds HTTP overhead (~1-10ms on LAN). Not suitable for high-frequency queries (>10/second).
- **No ordering guarantee:** Multiple async calls may complete out of order. Use sequence numbers if ordering matters.
- **Port availability:** The UE process must successfully bind its RPC port before queries work. Always wait for the heartbeat `GauntletRpc: Listening on port` log line before making RPC calls.
- **Firewall:** On remote devices (Android via ADB, Linux via SSH), the RPC port must be accessible from the Gauntlet agent. Use `adb forward` or SSH port forwarding if needed.
- **Process restart:** On `WantRetry`, new processes get new ports. `RpcTargetRegistry` must be re-populated after each `StartTest()`.

---

## GauntletHttpClient

Used internally by `RpcExecutor` and also by Horde integration for report submission:

```csharp
var client = new GauntletHttpClient(baseUrl, bearerToken);

// GET request:
var response = await client.GetAsync<MyResponse>("/api/v1/status");

// POST request:
await client.PostAsync("/api/v1/results", myPayload);
```

Handles: retry on transient HTTP errors (429, 503), timeout configuration, JSON serialization.
