# SWE-Dev

A [pyRevit](https://github.com/eirannejad/pyRevit) extension developed by **Systems West Engineers (SWE)** for internal Revit workflow automation. The extension adds a **SWE Dev** tab to the Revit ribbon with a production-ready sheet management panel and a suite of beta tools covering coordination tracking, electrical parameter management, workshared model sync queuing, and more.

---

## Requirements

| Dependency | Minimum Version |
|---|---|
| Autodesk Revit | 2022+ |
| pyRevit | 4.8+ |
| Python (IronPython) | Bundled with pyRevit |

A `config.py` file must exist at the extension root and must define `PROJECTS_ROOT` — the path to the firm's project directory on the network or local drive. See [Configuration](#configuration) below.

---

## Installation

1. Clone or download this repository to your local machine.
2. In pyRevit settings, add the repository root as a custom extension directory.
3. Reload pyRevit. The **SWE Dev** tab will appear in the Revit ribbon.
4. Create a `config.py` file at the extension root (see [Configuration](#configuration)).

---

## Configuration

A `config.py` file is required at the extension root alongside `SWE_Dev.tab/`, `hooks/`, and `lib/`. This file is **not** committed to the repository (see `.gitignore`).

**Minimum required content:**

```python
# config.py
PROJECTS_ROOT = r"\\server\Projects"   # Path to the root projects directory
```

`lib/project_paths.py` reads this file at runtime and uses `PROJECTS_ROOT` to resolve per-project CAD folders and JSON data storage paths based on the **SWE Project Number** parameter stored in each Revit model's Project Information.

---

## Repository Structure

```
SWE-Dev/
├── config.py                        ← Local only, not committed (define PROJECTS_ROOT)
├── SWE_Dev.tab/
│   ├── ManageSheets.panel/
│   │   └── print_sheets.pushbutton/ ← Print Sheets tool (production)
│   └── __beta__.panel/              ← Beta tools (in development)
│       ├── Add to Family.pushbutton/
│       ├── BAS_points.pushbutton/
│       ├── Coordination Dashboard.pushbutton/
│       ├── ElectricalConnector.pushbutton/
│       ├── Manage Keynotes.pushbutton/
│       ├── New Schedule.pushbutton/
│       ├── Sum WFU.pushbutton/
│       ├── Sync Queue.pushbutton/
│       └── Update.pushbutton/
├── hooks/
│   ├── app-init.py                  ← Registers Sync Queue dockable pane on startup
│   └── doc-synced.py                ← Removes user from sync queue after model sync
└── lib/
    ├── project_paths.py             ← Resolves project folder paths from config
    ├── sync_queue.py                ← Sync queue read/write logic (JSON-backed)
    └── sync_queue_panel.py          ← WPF dockable panel UI for the Sync Queue
```

---

## Tools

### Production

#### Print Sheets — `ManageSheets.panel`
Manages sheet printing workflows from within Revit. Accessible from the **Manage Sheets** panel in the SWE Dev tab.

---

### Beta — `__beta__.panel`

> Tools in this panel are under active development and may change behavior between updates.

#### Electrical Connector — `ElectricalConnector.pushbutton`
Adds electrical shared parameters and connectors to Revit families in batch. Reads `AUTO_ADD_PARAMS` and `SCHEDULE_PARAMETERS` from the shared parameter file configured in Revit.

- **Script:** `elec_connect_script.py`
- **Requirements:** A configured Revit shared parameter file containing the expected parameter names.
- **Usage:** Open a project or family, run the script, select a family, choose connector type and options, then click **Add Shared Parameters**.

#### Coordination Dashboard — `Coordination Dashboard.pushbutton`
Launches an HTML-based coordination dashboard (`coordination_dashboard.html`) embedded in a WPF viewer. Tracks project stages and revision status, persisting data to a JSON file in the project's `10 CAD` folder.

- **Script:** `dashboard_script.py`

#### Sync Queue — `Sync Queue.pushbutton`
A dockable panel that manages a shared model sync queue for workshared Revit projects. Users join the queue before syncing and are automatically removed via the `doc-synced` event hook upon a successful sync.

- **Library:** `lib/sync_queue.py`, `lib/sync_queue_panel.py`
- **Hook:** `hooks/doc-synced.py` — fires on the `doc-synced` pyRevit event to call `sq.leave_queue()`
- **Storage:** JSON file written to the project's `10 CAD` folder (resolved via `project_paths.py`)

#### Sum WFU — `Sum WFU.pushbutton`
Calculates and summarizes Water Fixture Units (WFU) for plumbing design within the active Revit model.

#### Add to Family — `Add to Family.pushbutton`
Adds parameters or data to Revit families in batch.

#### BAS Points — `BAS_points.pushbutton`
Tools for Building Automation System (BAS) point tagging or scheduling within Revit models.

#### Manage Keynotes — `Manage Keynotes.pushbutton`
Provides keynote management utilities for Revit projects.

#### New Schedule — `New Schedule.pushbutton`
Automates creation or styling of Revit schedules.

#### Update — `Update.pushbutton`
Utility for updating extension components or refreshing cached data.

---

## Hooks

| File | Event | Purpose |
|---|---|---|
| `hooks/app-init.py` | pyRevit startup | Registers the **Sync Queue** dockable pane with Revit's UI framework and initializes the external sync event handler |
| `hooks/doc-synced.py` | `doc-synced` | Calls `sync_queue.leave_queue()` to remove the current user from the sync queue after a workshared model sync completes |

---

## Shared Libraries (`lib/`)

| Module | Purpose |
|---|---|
| `project_paths.py` | Loads `config.py`, resolves `PROJECTS_ROOT`, and provides helper functions to locate per-project CAD folders and JSON data files from the model's **SWE Project Number** parameter |
| `sync_queue.py` | JSON-backed read/write logic for the sync queue (join, leave, list) |
| `sync_queue_panel.py` | WPF dockable panel implementation for the Sync Queue UI, including the external event handler and Revit `IDockablePaneProvider` interface |

---

## Development Notes

- All scripts use **IronPython** as bundled with pyRevit. Standard CPython libraries are not available.
- `config.py` is excluded from version control via `.gitignore`. Each developer must create their own local copy.
- Beta tools (`__beta__.panel`) are in active development. Stability and API compatibility are not guaranteed between commits.
- Log output from `app-init.py` is written to `%USERPROFILE%\pyRevitSyncLogs\sync_queue_startup_debug.txt` for debugging startup issues.

---

## License

Distributed under the terms of the [LICENSE](LICENSE) file included in this repository.

---

*Developed and maintained by [Systems West Engineers](https://www.systemswestengineers.com/) — Oregon.*
