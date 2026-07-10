# 🛠️ Telegram Scraper Development Guidelines

This document outlines the standards and patterns for adding new scripts to this project. Following these rules ensures a consistent, beautiful, and robust user experience.

## 📁 Project Structure

- **`sessions/`**: All `.session` files (including temporary ones) MUST be stored here.
- **`[Number]_data/`**: Output data for script `[Number]` should be stored in its own dedicated directory.
- **`ui_utils.py`**: Centralized UI logic. Do NOT import `rich` directly into new scripts; use this wrapper instead.

## 🔑 Configuration & Env Vars

Always load credentials from `.env` using these specific keys:

- `MAIN_API_ID`: Your Telegram API ID.
- `MAIN_API_HASH`: Your Telegram API Hash.
- `DEFAULT_SESSION`: The path (e.g., `sessions/YourName`) of the active account.

## 🎨 Using the UI (Beautiful Terminal)

We use the `ui_utils` module to maintain a professional look.

### 1. Basic Imports

```python
from utils import ui_utils
from ui_utils import console
```

### 2. Standard Elements

- **Header**: `ui_utils.print_header("Your Title")`
- **Success**: `ui_utils.print_success("Operation completed")`
- **Error**: `ui_utils.print_error("Something went wrong")`

### 3. Tables

Instead of printing plain text, use the table builder:

```python
table = ui_utils.create_table("Results", ["Column 1", "Column 2"])
table.add_row("Data 1", "Data 2")
console.print(table)
```

### 4. Progress Bars

For scrapers or long tasks, use the specialized progress bar:

```python
with ui_utils.get_progress() as progress:
    task = progress.add_task("Processing...", total=100)
    for item in items:
        # ... do work ...
        progress.advance(task)
```

## 🚀 Script Requirements

1. **Clean Exits**: Always wrap your `asyncio.run()` in a try/except to catch `KeyboardInterrupt` and `EOFError`.
2. **CSV Only**: Do not save `.txt` result files. Use `.csv` for all data outputs to keep the folders tidy.
3. **Session Safety**: When creating new login scripts, prefix the session name with `sessions/` and ensure the directory exists.
4. **Integration**: Add your new script to the menu in `run.py` so others can find it easily.

---

_Created on 2026-02-08_
