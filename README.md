# XebuWorkspace (Alpha)

**XebuWorkspace** is a **desktop application** for **managing projects and tasks locally**.  
It is written in Python using PySide6 and provides a single interface for
running local processes, organizing projects and keeping personal tasks.

**Status: ALPHA**

This project is under active development.  
Features, structure, and data formats may change at any time.

---

## Features

### Project Management
- Run Python scripts
- Open files, folders or URLs
- Copy files with optional history tracking

### Task Management
- Local task storage
- Daily task lists with automatic reset
- Deadlines and priority indicators
- CSV archiving

### Productivity Tools
- Daily log saved as CSV
- Custom PySide6 interface with theming

### Calendar
  - Visualize tasks in a calendar view
  - Add/Delete Tasks 

## Planned Features

- **Settings** ~March 2026
  - Theme selection
  - Dark / Light mode
  - Manage user data 

---

## Philosophy

XebuWorkspace is intentionally **local-first**.

All user data is stored **locally** in the system's AppData directory
and can be managed, exported, or deleted entirely by the user.

## Security Notice

Please note:

XebuWorkspace allows executing **local Python scripts** and opening
local files or paths **by design**.

Please keep in mind:

- Only run scripts you trust
- Do not share your local configuration files (`files.json`, `tasks.json`, etc.)
- This application is **not sandboxed**

---

## Installation

### Requirements
- Python 3.10+
- Windows (macOS being tested, Linux untested)

### Setup
```bash
pip install -r requirements.txt
python main.py
```
### Quick Start

```bash
git clone https://github.com/xebuu/xebu-workspace.git
cd xebu-workspace
pip install -r requirements.txt
python main.py
```
## Contributing

Bug reports and feature suggestions are welcome.
Please open an issue before submitting major changes.

## License
MIT License.  
This project uses PySide6, which is licensed under the LGPL v3.
