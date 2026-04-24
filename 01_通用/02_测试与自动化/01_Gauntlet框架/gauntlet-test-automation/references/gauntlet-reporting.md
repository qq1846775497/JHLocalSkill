# Gauntlet Reporting Pipeline

Reference for `ITestReport`, Horde reports, HTML/Markdown builders, and the telemetry CSV pipeline.

---

## ITestReport

`Framework/Base/Gauntlet.TestReport.cs`

The output contract all report implementations satisfy.

### API Surface

```csharp
interface ITestReport
{
    string Type { get; }   // Format identifier, e.g. "SimpleHordeReport"

    // Key-value metadata (displayed in Horde test dashboard)
    void SetProperty(string Name, string Value);
    void SetMetadata(string Name, string Value);

    // Attach a structured event
    void AddEvent(EventType Type, string Message);
    // EventType: Unknown | Info | Warning | Error

    // Associate a file artifact
    void AttachArtifact(string FilePath, string Name = null);

    // Supplementary files the report depends on (e.g., artifact manifests)
    IReadOnlyDictionary<string, object> GetReportDependencies();

    // Write/submit the report
    void FinalizeReport();
}

interface ITelemetryReport
{
    void AddTelemetry(
        string TestName,
        string DataPoint,
        double Measurement,
        string Context = null,
        string Unit = null,
        double? Baseline = null);

    IEnumerable<TelemetryData> GetAllTelemetryData();
}
```

### BaseTestReport

Abstract base providing:
- `Dictionary<string, string> Metadata` — backing store for `SetMetadata()`
- `List<TelemetryData> TelemetryItems` — backing store for `AddTelemetry()`
- Both `ITestReport` and `ITelemetryReport` implemented

---

## HordeReport

`Framework/Utils/Gauntlet.HordeReport.cs`

Two format versions.

### v1: SimpleTestReport

Lightweight. Used when `UnrealTestConfiguration.SimpleHordeReport == true` (default).

```csharp
var report = new HordeReport.SimpleTestReport();
report.SetMetadata("Project", "MyGame");
report.SetMetadata("Platform", "Win64");
report.AddEvent(EventType.Error, "Crash at frame 1234");
report.AttachArtifact("D:/Artifacts/log.txt", "ClientLog");
report.FinalizeReport(); // writes to disk / submits to Horde
```

Written to: `<ArtifactPath>/<TestName>.TestData.json`

### v2: AutomatedTestSessionData

Full phase/step structure for complex multi-step tests. Contains:
- `PhaseQueue` — ordered list of test phases
- `Phase` — individual phase with name, status, and events
- `TestState` — per-phase state (`Unknown / NotRun / InProcess / Fail / Success / Skipped`)

```csharp
var report = new HordeReport.AutomatedTestSessionData();
var phase = report.AddPhase("Boot");
phase.AddEvent(EventType.Info, "Engine started");
phase.SetState(TestStateType.Success);

var phase2 = report.AddPhase("GameplayTest");
phase2.AddEvent(EventType.Error, "Frame rate dropped below threshold");
phase2.SetState(TestStateType.Fail);

report.FinalizeReport();
```

---

## HtmlBuilder

`Framework/Utils/Gauntlet.HtmlBuilder.cs`

Fluent builder for local HTML reports.

```csharp
var html = new HtmlBuilder();

html.H1("Test Results: MyGame.SoakTest");
html.H2("Summary");
html.Paragraph("Ran for 300 seconds with 0 errors.");

// Table
html.StartBuildingTable(new[] { "Metric", "Value", "Status" });
html.StartRow();
html.AddNewCell("FPS Average");
html.AddNewCell("58.3");
html.AddNewCell("PASS", TextOptions.Green | TextOptions.Bold);
html.FinalizeTable();

// List
html.H2("Errors");
html.StartBuildingList(ordered: false);
html.AddListItem("No errors detected");
html.FinalizeList();

// Write to file
File.WriteAllText("report.html", html.ToString());
```

### TextOptions (bitfield)
`Bold | Italic | Green | Red | Yellow | Blue | Hyperlink`

### Hyperlinks
```csharp
html.Hyperlink("View automation report", reportUrl);
html.AddNewCell("Report", TextOptions.Hyperlink, url: reportUrl);
```

---

## MarkdownBuilder

`Framework/Utils/Gauntlet.MarkdownBuilder.cs`

Parallel fluent builder for Markdown output (used in console summaries and Slack integrations).

```csharp
var md = new MarkdownBuilder();
md.H1("Test Summary");
md.HorizontalRule();
md.H2("Results");
md.Paragraph("All 5 tests passed.");
md.StartBuildingList();
md.AddListItem("UE.BootTest: PASS (12.3s)");
md.AddListItem("MyGame.SoakTest: PASS (305s)");
md.FinalizeList();

Console.WriteLine(md.ToString());
```

---

## UnrealTelemetry — CSV Pipeline

`Unreal/Utils/Gauntlet.UnrealTelemetry.cs`

Gauntlet can ingest performance CSV files produced by UE processes and submit them to a telemetry database.

### CSV Format

Expected columns (order flexible; column names configurable):

| Column | Required | Notes |
|--------|----------|-------|
| `TestName` | Yes | Test identifier |
| `DataPoint` | Yes | Metric name (e.g., `"FPS"`, `"MemoryUsageMB"`) |
| `Measurement` | Yes | Numeric value |
| `Context` | No | Sub-context string (e.g., map name, config) |
| `Unit` | No | Unit string (e.g., `"fps"`, `"ms"`) |
| `Baseline` | No | Expected/target value for comparison |

Example CSV:
```csv
TestName,DataPoint,Measurement,Context,Unit,Baseline
MyGame.SoakTest,FPS,58.3,TestLevel,fps,60.0
MyGame.SoakTest,MemoryUsageMB,1842.5,TestLevel,MB,2048.0
MyGame.SoakTest,DrawCalls,1234,TestLevel,,
```

### Loading CSVs into a Report

```csharp
// After test completes, scan artifact dir for CSV files:
UnrealAutomationTelemetry.LoadOutputsIntoReport(
    artifactDir,
    telemetryReport,
    columnMapping: null  // or Dict<string,string> to remap column names
);
```

### Publishing Telemetry (UAT Command)

```bash
RunUAT PublishUnrealAutomationTelemetry \
  -CSVDirectory=D:/Artifacts/Telemetry \
  -Project=MyGame \
  -Platform=Win64 \
  -Branch=//MyProject/Main \
  -Changelist=12345678 \
  -TelemetryConfig=horde  # points to DB config
```

### Fetching Historical Telemetry

```bash
RunUAT FetchUnrealAutomationTelemetry \
  -CSVFile=D:/Output/history.csv \
  -Since=1month \
  -TestName=MyGame.SoakTest \
  -DataPoint=FPS
```

`-Since=` accepts: `Nd` (days), `Nw` (weeks), `Nmonth`, `Ny` (years). Example: `2w`, `3d`, `1month`.

---

## Artifact Attachment Conventions

```csharp
// In StopTest() or CreateReport():
report.AttachArtifact("D:/Artifacts/client.log", "ClientLog");
report.AttachArtifact("D:/Artifacts/crash.dmp", "CrashDump");
report.AttachArtifact("D:/Artifacts/screenshots/frame1234.png", "FrameCapture");
```

Horde displays attached artifacts as clickable links in the test detail view.

**Standard artifact names used by base class:**

| Artifact Name | Content |
|--------------|---------|
| `ClientLog` | Client process log |
| `ServerLog` | Server process log |
| `EditorLog` | Editor process log |
| `CrashDump` | Platform crash dump |
| `Callstack` | Extracted callstack text |
| `Screenshots` | Screenshot directory |

---

## SetMetadata — Horde Dashboard Integration

Metadata keys that Horde recognizes:

| Key | Effect in Horde |
|-----|----------------|
| `Project` | Shown in test list |
| `Platform` | Platform column |
| `Configuration` | Config column |
| `Branch` | Branch filter |
| `Changelist` | CL link |
| `ReportURL` | "View Report" link in test details |
| `ReportPath` | Local report path |
| `AutomationReportURL` | "Automation Report" link |

```csharp
report.SetMetadata("Project", cfg.ProjectName);
report.SetMetadata("Platform", role.Platform.ToString());
report.SetMetadata("ReportURL", hordeReportUrl);
```

---

## Report Generation in UnrealTestNode

The base class `UnrealTestNode` calls `CreateReport()` from `StopTest()`. Default behavior:

```
CreateReport()
  ├── If WriteTestResultsForHorde:
  │     Write <ArtifactPath>/<TestName>.TestData.json
  ├── If SimpleHordeReport (default):
  │     CreateSimpleReportForHorde()
  │     → new HordeReport.SimpleTestReport()
  │     → AddEvent() for each error/warning in RoleResults
  │     → AttachArtifact() for each log file
  │     → SetMetadata() for project, platform, CL, branch
  │     → FinalizeReport()
  └── Else:
        CreateUnrealEngineTestPassReport(ReportPath, ReportURL)
        → HtmlBuilder for local HTML
        + HordeReport.AutomatedTestSessionData
```

Override `CreateReport()` to add game-specific content:

```csharp
protected override void CreateReport()
{
    base.CreateReport();  // generates standard report

    // Add custom perf section
    var perfData = ReadPerfData(ArtifactPath);
    // Attach CSV to existing report:
    Report?.AttachArtifact(perfData.CsvPath, "PerfData");
}
```

---

## DeviceUsageReporter

`Unreal/Utils/Gauntlet.DeviceUsageReporter.cs`

Tracks device utilization metrics. Concrete reporters are discovered via reflection; implement `IDeviceUsageReporter`:

```csharp
public abstract class IDeviceUsageReporter
{
    enum EventType { Device, Install, Test, SavingArtifacts }

    abstract void RecordStart(EventType Type, string DeviceName, string Info);
    abstract void RecordEnd(EventType Type, string DeviceName, string Info);
    abstract void RecordComment(string DeviceName, string Comment);
}
```

Static dispatch methods: `IDeviceUsageReporter.RecordStart(...)`, etc.
