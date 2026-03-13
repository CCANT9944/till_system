# Till System

Simple point-of-sale application using PyQt6 and SQLite.

## Structure

- `models.py` – data classes for product, cart items, transactions, shifts, and reporting summaries.
- `db.py` – SQLite database layer with product, transaction, shift, backup, and reporting queries.
- `backup_service.py` – backup/restore storage, rotation, and restore helpers for the SQLite database.
- `controller.py` – business logic for inventory and cart operations.
- `bill_audit.py` – shared helpers for comparing saved bill revisions and rendering audit entries.
- `bills_mixin.py` – Bills tab UI, saved-bill audit history, reports, and backup/restore actions shared by the main window.
- `database_inspector_dialog.py` – read-only manager dialog for reviewing live database records, counts, and saved bill audits.
- `product_details_mixin.py` – Product Details tab UI for searchable catalog browsing and reused product add/edit/delete actions.
- `reports_mixin.py` – Reports tab UI for session/date filtering and item-sales summaries.
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
- `bill_dialogs.py` – saved-bill edit dialog helpers, including searchable item insertion and live change highlighting.
- `views.py` – main till window and feature wiring for the PyQt6 GUI.
- `main.py` – entry point for launching the application.
- `tests/` – pytest coverage for controller flows, bills editing, backups, reports, and PyQt UI regressions.

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
- Under **Product** there is also a read-only `Database Inspector`, which shows live product, transaction, transaction-item, shift, backup, and saved bill audit counts plus recent database records, edit-history snapshots, and a dedicated `Audit` tab for review.
- The `Product Details` tab also lets you add a product directly without changing the Till tab's current category filter first; when adding from there, category and subcategory can be left blank and filled in later, and blank-category products stay hidden from the Till tab until you categorise them yourself.
- `Edit Product` opens a searchable list of all products so any item can be found and edited, not just the one currently visible on screen.
- `Delete Product` also opens a searchable list of all products before asking for confirmation.
- Under **Design**: `Color Presets`, `Adjust Product Font`.
- Under **Design** there is now `Grid Layout`, which lets you switch between `6 x 6`, `5 x 6`, and `4 x 6` product grid presets.
- Under **Design** there is also `Rearrange Grid Items`, which lets you drag and drop the products shown in the current category/subcategory grid into exact row and column slots.
- Products are presented as square buttons arranged in a compact grid rather than a plain list. The grid starts at the top of the view, and the category and subcategory rows are sized to match the visible product board. Click a product button to select it (highlighted in green), then press **Add to cart** or use the Manager menu for protected actions.
- The product area now uses a matching `6 x 6` layout style for both the main till grid and the rearrange screen, so placement is consistent while editing positions.
- The chosen grid preset is saved and reused the next time the till starts.
- Manager actions (add/delete products) have been grouped under a **Manager** button; selecting either option requires entering a PIN.
- The **Manager** button now sits in the top-right corner of the main tab bar so the Till tab keeps more vertical room for the working area.
- The Till tab now uses a more compact layout overall, including tighter typography, smaller action buttons, and narrower supporting panels so the whole window fits comfortably at a smaller default size.
- The cart now lives in a dedicated right-hand panel separated from the product area by a vertical divider, with the total displayed below the cart items and the `Add to cart`, `Remove from cart`, and `Checkout` actions stacked directly beneath it.
- Add items from inventory to cart.
- View cart and total; remove items.
- Checkout now opens a payment selector with `Cash`, `Visa`, `Mastercard`, and `Amex` buttons, and the chosen method is shown on saved bills, receipts, and reports.
- A `Bills` tab shows recent completed transactions, bill details, and a simple daily totals summary for the current day.
- Receipt history is built from stored transaction snapshots, so historical bills keep the original item names and prices even if products are edited later.
- Bills history now lets you edit a saved bill, including correcting its timestamp, and edited bills stay highlighted in the history list while those changes flow through to the bill details, payment totals, bill ordering, shift reports, and a saved edit audit trail that keeps removed items visible later.
- The Bills detail panel now keeps receipt text separate from a lower `Saved edits` section, and that audit section can be collapsed when you only want the final bill view.
- Transactions are now linked to shifts, and the Bills tab can `Close Day` to end the current shift and start a new one without deleting bill history.
- The Bills tab can also filter by shift, so a single closed day can be inspected on its own without mixing it with the current open shift.
- The Bills tab now includes an `End Of Day Report` view for the selected shift, and closing the day immediately opens a report for the shift that was just closed, including separate `Visa`, `Mastercard`, and `Amex` totals alongside cash and combined card totals.
- A `Reports` tab shows per-item sales summaries, including quantity sold and revenue, with filters for one or more sessions and optional date/time ranges.
- Reports default to the current open session when no manual filters are selected, and they refresh automatically after checkout, bill edits, restores, and day-close actions.
- Multi-step database writes now run atomically for checkout, bill edits, and shift closing, so failed writes roll back instead of leaving partial bill or shift data behind.
- The app now closes the SQLite connection cleanly on shutdown to reduce the chance of stale or half-open database state on restart.
- The Bills tab now includes `Backup Data` and `Restore Backup` actions, both PIN-protected, so staff can create a timestamped copy of the live till database before risky changes or at the end of a shift.
- Every successful checkout and every successful `Close Day` action now also create an automatic timestamped backup in the background, so each completed sale and each day close leave behind a recent recovery point even if staff never press the manual backup button.
- Restoring from a backup creates a fresh safety backup of the current live database first, then reloads the till data in place so bills, totals, and products refresh against the restored copy.

## Product Details Workflow

- Use the `Product Details` tab when you want to browse the full catalog without changing the Till tab's current category/subcategory view.
- The Product Details search matches product name, price, category, and subcategory.
- The Product Details category dropdown can narrow the table to `All categories`, any configured category, or `Uncategorised`.
- Adding or editing a product from `Product Details` allows category and subcategory to be left blank for later cleanup.
- Blank-category products remain hidden from the Till tab until they are assigned to a visible category.
- Adding a product from the manager `Add Product` action still follows the stricter category-first flow.

## Saved Bill Audit Workflow

1. Open the `Bills` tab and select a completed transaction.
2. Use `Edit` to correct the saved bill, including item rows, payment method, or timestamp.
3. When the edit is saved, the previous version is stored as a revision before the live transaction is updated.
4. The selected bill keeps showing the final receipt in the main detail area, while the lower `Saved edits` section shows what changed between versions.
5. Added, changed, and removed lines stay available later, so deleted items remain visible even after the edit has been saved and the app has been reopened.
6. The same saved revision history also appears in the manager-only `Database Inspector` under the `Audit` tab for admin review.

## Admin Review Guide

- Use `Bills` history when you want to inspect one bill in context, review its final receipt, and read the saved edits attached to that specific transaction.
- Use the lower `Saved edits` section in `Bills` when the goal is to answer "what changed on this bill" without leaving the normal cashier workflow.
- Use `Database Inspector` when you want a read-only admin overview across the whole database, including record counts, recent transactions, transaction items, shifts, backups, and cross-bill audit snapshots.
- Use the `Audit` tab inside `Database Inspector` when you need to scan multiple edited bills quickly instead of opening them one by one from the Bills list.
- In short: `Bills` is transaction-focused and cashier-friendly; `Database Inspector` is database-focused and admin-oriented.

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
