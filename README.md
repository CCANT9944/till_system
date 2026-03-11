# Till System

Standalone PyQt6 point-of-sale application with local SQLite storage, bill history, shift reporting, product management, and backup/restore tools.

## What Is In This Repo

- `till/` contains the application code, tests, and module-level documentation.
- `requirements.txt` lists the minimal Python dependencies for running and testing the app.
- Local runtime files such as the SQLite database, backups, cached test output, and machine-specific UI config are intentionally ignored.
- The manager PIN can be supplied through an ignored local settings file or the `TILL_MANAGER_PIN` environment variable, so it does not need to live in the published source.

## Main Features

- Touch-friendly till screen with category and subcategory filtering.
- Product manager flows for add, edit, delete, category editing, color presets, and grid layout control.
- Dedicated `Product Details` tab for searchable catalog browsing and quick product maintenance.
- Bills history with payment-method tracking, bill editing, shift filtering, and end-of-day reporting.
- Local-only data model using SQLite with timestamped backups and restore safety copies.

## Quick Start

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m interface.till.main
```

To override the example manager PIN locally, copy `till/local_settings.example.json` to `till/local_settings.json` and change `manager_pin` before running the app.

If you are already inside the `interface` folder, you can also run:

```bash
python -m till.main
```

## Tests

```bash
pytest till/tests -q
```

## More Detail

The module-by-module breakdown and deeper behavior notes are in [till/README.md](till/README.md).