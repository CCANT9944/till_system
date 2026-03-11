# Till System

Simple point-of-sale application using PyQt6 and SQLite.

## Structure

- `models.py` – data classes for product, cart items, and transactions.
- `db.py` – SQLite database layer with product and transaction tables.
- `backup_service.py` – backup/restore storage, rotation, and restore helpers for the SQLite database.
- `controller.py` – business logic for inventory and cart operations.
- `bills_mixin.py` – Bills tab UI, reports, and backup/restore actions shared by the main window.
- `product_details_mixin.py` – Product Details tab UI for searchable catalog browsing, touch-friendly table layout, and reused product add/edit/delete actions.
- `grid_layout.py` – persistent grid layout presets for the till and rearrange screens.
- `button_rows.py` – shared helpers for category/subcategory button rows.
- `dialog_helpers.py` – reusable picker and manager utility dialogs.
- `category_editor_dialog.py` – category/subcategory editor dialog logic.
- `color_preset_dialog.py` – color preset editor dialog logic.
- `grid_reorder_dialog.py` – rearrange-grid dialog shell.
- `grid_widgets.py` – reusable product-grid placement and drag/drop widgets.
- `manager_dialog.py` – reusable manager section dialog UI.
- `app_settings.py` – local manager-PIN loading from environment variables and ignored local config.
- `product_dialogs.py` – add/edit product dialog helpers.
- `views.py` – main till window and feature wiring for the PyQt6 GUI.
- `main.py` – entry point for launching the application.
- `tests/` – pytest unit tests for models and controllers.

## Getting Started

1. Create and activate a Python virtual environment (see parent `requirements.txt`).
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Optional but recommended: copy `local_settings.example.json` to `local_settings.json` and change `manager_pin` so the manager PIN is stored only in your ignored local file.
4. Run the application:
   ```bash
   # from the standalone repository root
   python -m till.main

   # if this package lives inside a larger parent workspace
   python -m interface.till.main

   # or, if you `cd` into the till directory, run
   cd till
   python main.py
   ```

> the `interface` folder is now a proper Python package (contains `__init__.py`), and
> `main.py` will automatically insert the workspace root into `sys.path` so the
> `interface.till` imports resolve correctly when invoked directly.

> The manager PIN is loaded in this order: `TILL_MANAGER_PIN` environment variable,
> ignored `local_settings.json`, then the tracked `local_settings.example.json` template.

## Features

- Add products to inventory with a category (beer, spirits, hot drinks, cocktails, wines, or custom).
- Filter inventory by category using the square buttons at the top of the window. For some categories (e.g. beer) a second row of subcategory buttons will appear (draught / bottled). Products are only shown after you choose both a category and a subcategory; before selecting the sub‑row the list displays a placeholder.
- The categories available are beer, spirits, hot drinks, cocktails, wines and snacks. Snacks currently have no subcategories.
- Item colors are assigned automatically from category-specific presets, with subcategory overrides where needed (for example beer draught vs bottled).
- The **Manager** button now opens a small manager screen split into **Product** and **Design** sections.
- Under **Product**: `Add Product`, `Edit Product`, `Delete Product`.
- Under **Product** there is also `Edit Categories`, which lets you add, rename, delete, and reorder the main category list used by the till, plus manage subcategories for each category in the same screen.
- `Edit Product` opens a searchable list of all products so any item can be found and edited, not just the one currently visible on screen.
- `Delete Product` also opens a searchable list of all products before asking for confirmation.
- Under **Design**: `Color Presets`, `Adjust Product Font`.
- Under **Design** there is now `Grid Layout`, which lets you switch between `6 x 6`, `5 x 6`, and `4 x 6` product grid presets.
- Under **Design** there is also `Rearrange Grid Items`, which lets you drag and drop the products shown in the current category/subcategory grid into exact row and column slots.
- Products are presented as large, touch‑friendly buttons arranged in a grid rather than a plain list. Buttons are now **square** in shape, compact, and the grid starts at the top of the view. Click a product button to select it (highlighted in green), then press **Add to cart** or use the Manager menu for protected actions.
- The product area now uses a matching `6 x 6` layout style for both the main till grid and the rearrange screen, so placement is consistent while editing positions.
- The chosen grid preset is saved and reused the next time the till starts.
- Manager actions (add/delete products) have been grouped under a **Manager** button; selecting either option requires entering a PIN.
- The cart now lives on the right side of the screen at the same vertical height as the product area, with the total displayed below the cart items.
- Add items from inventory to cart.
- View cart and total; remove items.
- Checkout now opens a payment selector with `Cash`, `Visa`, `Mastercard`, and `Amex` buttons, and the chosen method is shown on saved bills, receipts, and reports.
- A `Bills` tab shows recent completed transactions, bill details, and a simple daily totals summary for the current day.
- Receipt history is built from stored transaction snapshots, so historical bills keep the original item names and prices even if products are edited later.
- Bills history now lets you edit a saved bill, including correcting its timestamp, and edited bills stay highlighted in the history list while those changes flow through to the bill details, payment totals, bill ordering, and shift reports.
- Transactions are now linked to shifts, and the Bills tab can `Close Day` to end the current shift and start a new one without deleting bill history.
- The Bills tab can also filter by shift, so a single closed day can be inspected on its own without mixing it with the current open shift.
- The Bills tab now includes an `End Of Day Report` view for the selected shift, and closing the day immediately opens a report for the shift that was just closed, including separate `Visa`, `Mastercard`, and `Amex` totals alongside cash and combined card totals.
- Multi-step database writes now run atomically for checkout, bill edits, and shift closing, so failed writes roll back instead of leaving partial bill or shift data behind.
- The app now closes the SQLite connection cleanly on shutdown to reduce the chance of stale or half-open database state on restart.
- The Bills tab now includes `Backup Data` and `Restore Backup` actions, both PIN-protected, so staff can create a timestamped copy of the live till database before risky changes or at the end of a shift.
- Every successful checkout and every successful `Close Day` action now also create an automatic timestamped backup in the background, so each completed sale and each day close leave behind a recent recovery point even if staff never press the manual backup button.
- Restoring from a backup creates a fresh safety backup of the current live database first, then reloads the till data in place so bills, totals, and products refresh against the restored copy.

## Testing

Run:
```bash
pytest interface/till/tests
```

## Notes

- Database file `till.db` is located inside the `till` package directory.
- Local manager settings can be kept in `local_settings.json`, which is ignored by Git; the tracked `local_settings.example.json` file exists only as a template.
- Timestamped backups are stored next to the live database under `interface/till/backups/manual/` for manual backups, `interface/till/backups/auto/` for automatic backups, and `interface/till/backups/restore-safety/` for the safety copy created before a restore overwrites live data.
- Each backup file is a full snapshot of the whole till database at that moment in time, including products, saved bills, transaction items, payment methods, shift history, edited bill markers, and other stored till data.
- Designed as a starting point; additional features can be added such as receipts,
user authentication, and reporting.
