# ERPNext Restaurant Demo Seeder

This is a Git-installable Frappe app containing the demo data seeder. It prepares
four restaurant brands, POS profiles, menu items with generated local
image thumbnails, recipes/BOMs, stock, and repeatable full transaction cycles.

## Version alignment

Use the same Frappe and ERPNext major branch already used by your bench, such as
`version-15` or `version-16`. Do not mix branches. ERPNext includes its standard
Point of Sale; this app does not need a separate POS repository. If your site
uses a third-party POS app, install that app from its own compatible Git repo.

Install the app from that Git repository, from the bench directory:

```bash
bench get-app restaurant_demo https://github.com/TechwithZakir/ERPNext-restaurant-demo-seeder.git
bench --site <demo-site> install-app restaurant_demo
```

Your bench must already have Frappe and ERPNext installed on that same branch.
Bench `get-app` fetches an app from Git; `install-app` installs it on a site.
The `restaurant_demo` name before the Git URL tells bench to clone the repo
directly into `apps/restaurant_demo`.

If `bench get-app` fails with `Directory not empty` while renaming
`apps/ERPNext-restaurant-demo-seeder` to `apps/restaurant_demo`, the app folder
already exists in that bench. Do not run `get-app` again; update the existing
app instead:

```bash
cd ~/frappe-bench
git -C apps/restaurant_demo pull
bench --site <demo-site> migrate
bench --site <demo-site> clear-cache
```

## Dry run

```bash
bench --site <demo-site> execute restaurant_demo.restaurant_demo_seed.create_full_demo --cycles 100 --dry_run true
```

## Create the demo records

Start with 10 cycles on a dedicated demo site, inspect the result, then run 100:

```bash
bench --site <demo-site> execute restaurant_demo.restaurant_demo_seed.create_full_demo --cycles 10 --dry_run false --confirm_demo_site true
bench --site <demo-site> execute restaurant_demo.restaurant_demo_seed.create_full_demo --cycles 100 --dry_run false --confirm_demo_site true
```

Each cycle creates a brand requisition, raw-material transfer, BOM-based
manufacturing/consumption entry, finished-goods transfer, Delivery Note, and
Sales Invoice. A shared Purchase Material Request → Purchase Order → Purchase
Receipt → Purchase Invoice chain supplies the raw materials. Sales invoices are
submitted and left unpaid. The script does not create payment entries.

The script is repeatable for fully completed cycles. If a cycle is only partly
created, it stops and asks you to inspect the documents instead of creating
duplicates. Submitted stock and accounting documents affect inventory and
ledgers; use a disposable demo site/company.
