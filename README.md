# XebuWorkspace (Alpha)

XebuWorkspace is a **desktop application built with Python and PySide6**,
designed as a **modular local workspace** to organize technical utilities,
automate local processes, and manage personal tasks in a single UI.

⚠️ **Status: ALPHA**
This project is under active development.  
Features, structure, and data formats may change at any time.

---

## ⚙️ Features

- **Process Manager**
  - Run local Python scripts
  - Quick access links (files, folders, URLs)
  - File copiers with optional history handling

- **Task Manager**
  - Persistent local task storage
  - Daily tasks with automatic reset
  - Deadlines and priorities
  - Task archiving to CSV

- **Daily Log (Bitácora)**
  - Simple daily notes stored locally as CSV

- **Custom UI**
  - PySide6-based interface
  - Custom QSS themes
  - Modular tab-based layout

---

## 🧠 Philosophy

XebuWorkspace is intentionally **local-first**:
- No cloud
- No accounts
- No telemetry
- No external services

All user data (tasks, processes, logs) is stored **locally** in the system's
AppData directory.

---

## ⚠️ Security Notice

XebuWorkspace allows executing **local Python scripts** and opening
local files/paths **by design**.

- Only use scripts you trust.
- Do not share your local configuration files (`files.json`, `tasks.json`, etc.).
- This application is **not sandboxed**.

---

## 🧪 Alpha Limitations

- No installer (run from source)
- Limited error handling
- No backward compatibility guarantees for local data
- UI and APIs may change without notice

---

## 🛠️ Installation

### Requirements
- Python 3.10+
- Windows (primary target, macOS/Linux untested)

### Setup
```bash
pip install -r requirements.txt
python main.py
