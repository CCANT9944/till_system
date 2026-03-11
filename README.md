# Till System

[![Tests](https://github.com/CCANT9944/till_system/actions/workflows/tests.yml/badge.svg)](https://github.com/CCANT9944/till_system/actions/workflows/tests.yml)

Standalone PyQt6 point-of-sale application with local SQLite storage, bill history, shift reporting, product management, and backup/restore tools.

## Overview

This repository contains a desktop till / POS application built with PyQt6 and SQLite. It is aimed at small local setups where inventory, bills, reports, and backup snapshots all stay on the machine instead of depending on a cloud service.

## Highlights

- Product till grid with category and subcategory filtering
- Product Details tab for searchable catalog browsing and maintenance
- Bills history with editable transactions and shift-based reporting
- Backup and restore flows for the local SQLite database
- Manager PIN that can stay outside Git via ignored local settings or an environment variable

## Repo Layout

- `till/` contains the application code, tests, and module-level documentation.
- `requirements.txt` lists the minimal Python dependencies for running and testing the app.
- Local runtime files such as the SQLite database, backups, cached test output, and machine-specific UI config are intentionally ignored.
- The manager PIN can be supplied through an ignored local settings file or the `TILL_MANAGER_PIN` environment variable, so it does not need to live in the published source.

## Screenshots

No screenshots are committed yet, but the repo is ready for them. Add images under [docs/screenshots/README.md](docs/screenshots/README.md) using the suggested filenames and they can be linked here without changing the structure again.

## Quick Start

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m till.main
```

To override the example manager PIN locally, copy `till/local_settings.example.json` to `till/local_settings.json` and change `manager_pin` before running the app.

If this package is being used from a larger parent workspace that contains an `interface/` directory, you can also run:

```bash
python -m interface.till.main
```

## Tests

```bash
pytest till/tests -q
```

The same test command now runs automatically on GitHub Actions for pushes and pull requests to `main`.

## More Detail

The module-by-module breakdown and deeper behavior notes are in [till/README.md](till/README.md).