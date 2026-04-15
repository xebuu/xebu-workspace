# AGENTS.md

## Purpose

This repository is a local-first PySide6 desktop application for project and task management. Use this guide as the first orientation point before making changes.

The codebase is small, but it already has a few mixed patterns:

- Newer persistence code uses SQLite repositories under `app/database/`.
- Bitacora still uses CSV through `app/utility/database.py`.
- UI is split across tabs, windows, and widgets, with a large amount of feature logic living directly in Qt classes.

When changing behavior, prefer understanding the full feature path first: UI event -> in-memory mutation -> repository write -> rerender.

## High-Level Architecture

Entry path:

- `main.py` imports `run()` from `app.ui.main_window`.
- `app/ui/main_window.py` creates `QApplication`, builds `MainWindow`, and lazily instantiates the three main tabs.

Primary UI shell:

- `ProjectManagerTab` in `app/ui/tabs/tab_projects.py`
- `CalendarTab` in `app/ui/tabs/tab_calendar.py`
- `ConfiguracionTab` in `app/ui/tabs/tab_configuracion.py`
- Secondary windows launched from the shell:
  - `TasksWindow`
  - `BitacoraWindow`
  - `ArchivedProjectWindow`
  - `NewProjectWindow`
  - `ProjectViewWindow`

Persistence:

- `app/database/connection.py` opens SQLite connections against the AppData database path.
- `app/database/schema.py` defines the DDL.
- `app/database/migrations.py` applies versioned schema creation.
- Repositories are thin wrappers that mostly store JSON payloads in SQLite tables.

Data model:

- `app/models/project_models.py` defines `ProcessDef` plus nested `ScriptItem`, `LinkItem`, and `CopierItem`.
- Projects are stored as serialized JSON blobs, not normalized relational rows.
- Tasks are also stored as JSON blobs, even though they live in SQLite.

Theming:

- `app/core/theme.py` exposes a module-level `theme_manager`.
- Settings persist the selected theme through `SettingsRepository`.
- Some screens react to theme changes, but styling is still partly hardcoded in widgets and partly in `app/assets/style.qss`.

## Repository Map

Top level:

- `main.py`: current application entrypoint.
- `README.md`: product-level overview.
- `TODO.md`: useful source of intended direction and known issues.
- `XebuWorkspace.spec`: PyInstaller build config.
- `requirements.txt`: currently only `PySide6>=6.5`.

Application package:

- `app/__init__.py`: exposes `initialize_application()`, which initializes schema and applies saved theme.
- `app/core/`: paths, theme state, generic helpers.
- `app/database/`: SQLite connection, schema, migrations, repositories.
- `app/models/`: project dataclasses.
- `app/ui/`: main shell, tabs, widgets, feature windows.
- `app/utility/`: legacy CSV persistence for bitacora.
- `app/assets/style.qss`: shared stylesheet loaded by the main window.

## Important Paths And Storage

App data resolution lives in `app/core/paths.py`.

Persistent user data is intended to live under Qt AppData:

- `get_app_data_dir()`
- `ensure_app_data_dir()`
- `get_db_path()`

If that location is not writable, the app falls back to:

- `app/.appdata/Xebu/XebuWorkspace/`

Current persistent files:

- SQLite DB: `get_db_path("xebu_workspace.db")`
- Archived tasks CSV seed file: `ARCHIVED_TASKS_CSV`
- Bitacora CSV: `BITACORA_CSV`

Code/assets paths:

- Repo app root: `APP_DIR`
- Stylesheet: `app/assets/style.qss`

## Startup Reality

There is an architectural intent and a current runtime path, and they are not fully the same.

Intended startup:

- `app.initialize_application()` should initialize the SQLite schema and apply the saved theme.

Current startup:

- `main.py` directly calls `app.ui.main_window.run()`.
- `run()` builds the UI without calling `initialize_application()`.
- In practice, repositories self-heal by creating tables on demand, so the app still works.

Implication:

- Do not assume the whole schema is created eagerly at startup.
- Do not assume the saved theme is applied before the first window is shown.
- If you refactor startup, verify whether `initialize_application()` should be invoked centrally.

## Feature Ownership By Module

Projects:

- `app/ui/tabs/tab_projects.py` lists, searches, pins, archives, creates, edits, and deletes projects.
- `app/ui/windows/w_new_project.py` edits basic project metadata.
- `app/ui/windows/w_ProjectViewer.py` is the detailed project view and handles:
  - description editing
  - project-specific links/scripts/copiers
  - a quick task panel

Tasks:

- `app/ui/windows/w_tasks.py` is the main task manager.
- `app/ui/tabs/tab_calendar.py` presents tasks by `deadline`.
- `app/database/tasks_repository.py` persists the full task list.
- `app/database/archived_tasks_repository.py` stores archived tasks in SQLite and can seed from legacy CSV.

Toolbar shortcuts:

- Main window shortcuts are stored in `app/database/toolbar_repository.py`.
- Project-specific access actions are held inside `ProcessDef` and edited in `ProjectViewWindow`.

Bitacora:

- `app/ui/windows/w_bitacora.py`
- `app/utility/database.py`

Settings/theme:

- `app/ui/tabs/tab_configuracion.py`
- `app/database/settings_repository.py`
- `app/core/theme.py`

## Data Flow Patterns

Projects:

1. UI mutates a `ProcessDef` in memory.
2. `ProjectsRepository.save()` serializes it to JSON.
3. The full object is stored in the `projects` table as a single `payload`.

Tasks:

1. UI loads all tasks into memory.
2. Actions mutate task dictionaries directly.
3. `TasksRepository.save_all()` deletes all rows and rewrites the entire task table.

Toolbar items:

1. UI loads rows from `ToolbarRepository`.
2. Actions update one item at a time through insert/update/delete calls.

Bitacora:

1. UI appends rows to `bitacora.csv`.
2. No SQLite repository exists yet for this feature.

## Conventions That Matter

- The codebase mixes English file/module names with many Spanish UI strings and some Spanish variable names. Preserve the existing local style within the file you touch.
- Most features keep logic inside widget classes rather than pushing it into service layers. Keep changes scoped unless you are intentionally refactoring.
- Repositories are intentionally thin. Business rules often live in UI classes.
- `ProcessDef` remains the project model name even though the product language increasingly says "project". Renaming it would be a broader refactor.
- Styling is split between inline `setStyleSheet(...)`, theme manager colors, and `style.qss`. Check all three before assuming a color or widget style is centralized.

## Known Architectural Sharp Edges

These are worth checking before and after edits:

- `ProjectViewWindow` includes methods that appear misplaced inside `_MiniTaskRow` at the bottom of `app/ui/windows/w_ProjectViewer.py`, including `_open()` and `_runner_copy()`. The repo TODO also mentions broken link opening there.
- `main.py` bypasses `app.initialize_application()`.
- Tasks are not consistently updated by unique ID everywhere:
  - `CalendarTab` toggles/deletes by matching task text (`tarea`), which can affect duplicate task names.
  - `TasksWindow` often mutates in-memory objects directly and relies on object identity in the widget map.
- `TasksRepository.save_all()` rewrites the whole tasks table every time.
- `ArchivedTasksRepository.append_task()` always returns `(True, "")` after insert; error handling is minimal.
- `BitacoraWindow` still depends on the legacy CSV repo under `app/utility/`.
- Some files contain mojibake in UI strings. Be careful with file encodings and avoid making accidental encoding churn.

## Working Safely In This Repo

Before editing:

- Read the whole feature path, not just the first file that mentions the widget.
- Search for the repository and model used by that screen.
- Check `TODO.md` for explicit known bugs that may overlap with your change.

When changing persistence:

- Update both repository behavior and the UI assumptions that call it.
- Be careful with legacy CSV compatibility for bitacora and archived tasks.
- Preserve current payload shapes unless you are also handling migration.

When changing tasks:

- Prefer using task `id` consistently if you touch task selection, deletion, toggling, or cross-view sync.
- Verify both `TasksWindow` and `CalendarTab`, because they share the same underlying task store with different assumptions.

When changing projects:

- Verify both `ProjectManagerTab` and `ProjectViewWindow`.
- Remember that project links/scripts/copiers are stored inside the serialized `ProcessDef` payload.

When changing startup/theme:

- Check `main.py`, `app/__init__.py`, `app/core/theme.py`, and `ConfiguracionTab` together.

## Suggested Development Workflow

Run locally:

```powershell
pip install -r requirements.txt
python main.py
```

Package:

```powershell
pyinstaller --noconfirm --clean XebuWorkspace.spec
```

There are currently no repo-local tests in this checkout, All CI/CD ocurrs in Github.

## Manual Verification Checklist

For project changes:

- Open the app.
- Create/edit/delete a project.
- Open `ProjectViewWindow`.
- Verify description save behavior.
- Verify links/scripts/copiers toolbar actions.

For task changes:

- Test in both `TasksWindow` and `CalendarTab`.
- Verify daily reset behavior.
- Verify duplicate task names do not produce regressions.
- Verify archive/delete/toggle flows.

For settings/theme changes:

- Change theme in settings.
- Restart the app.
- Confirm whether the selected theme is restored.

For storage/path changes:

- Confirm the database and CSV files appear in the expected AppData location.
- If you touch fallback behavior, test with unwritable or missing app-data directories only if you can do so safely.

## Good First Refactors

If you need to improve the codebase without changing product scope too much, these are high-value targets:

- Centralize startup around `initialize_application()`.
- Fix `ProjectViewWindow` toolbar action ownership and the misplaced `_MiniTaskRow` methods.
- Normalize task operations around unique task IDs across all views.
- Move bitacora from CSV into SQLite, matching the rest of the app.
- Reduce duplicated task rendering/manipulation logic between `TasksWindow` and `CalendarTab`.

## Files To Read First For Most Tasks

- `main.py`
- `app/ui/main_window.py`
- `app/core/paths.py`
- `app/database/connection.py`
- `app/database/migrations.py`
- `app/ui/tabs/tab_projects.py`
- `app/ui/windows/w_ProjectViewer.py`
- `app/ui/windows/w_tasks.py`
- `app/ui/tabs/tab_calendar.py`
- `TODO.md`

