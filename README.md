# ERPNext Restaurant Demo Seeder

This is a Git-installable Frappe app containing the demo data seeder. It prepares
four restaurant brands, POS profiles, menu items with generated local
image thumbnails, recipes/BOMs, stock, and repeatable full transaction cycles.

## Version alignment

Use the same Frappe and ERPNext major branch already used by your bench, such as
`version-15` or `version-16`. Do not mix branches. ERPNext includes its standard
Point of Sale; this app does not need a separate POS repository. If your site
uses a third-party POS app, install that app from its own compatible Git repo.

## Clean install

Install the app from the bench directory. This app has no frontend assets, so
use `--skip-assets` to avoid running an unnecessary Frappe asset build.

```bash
cd ~/frappe-bench
bench get-app --skip-assets restaurant_demo https://github.com/TechwithZakir/ERPNext-restaurant-demo-seeder.git
bench --site <demo-site> install-app restaurant_demo
bench --site <demo-site> migrate
bench --site <demo-site> clear-cache
```

Your bench must already have Frappe and ERPNext installed on that same branch.
Bench `get-app` fetches an app from Git; `install-app` installs it on a site.
The `restaurant_demo` name before the Git URL tells bench to clone the repo
directly into `apps/restaurant_demo`.

## Recover a partial install

If an earlier install failed, clean the partial app folders first, then run the
clean install commands again:

```bash
cd ~/frappe-bench
rm -rf apps/restaurant_demo
rm -rf apps/ERPNext-restaurant-demo-seeder
sed -i '/^restaurant_demo$/d' sites/apps.txt
bench get-app --skip-assets restaurant_demo https://github.com/TechwithZakir/ERPNext-restaurant-demo-seeder.git
bench --site <demo-site> install-app restaurant_demo
bench --site <demo-site> migrate
bench --site <demo-site> clear-cache
```

If `sites/apps.txt` was edited manually, make sure each app is on its own line.
For example, fix a joined line such as `telephonyrestaurant_demo` before running
bench commands:

```bash
sed -i 's/telephonyrestaurant_demo/telephony\nrestaurant_demo/' sites/apps.txt
```

## Update an existing install

If `apps/restaurant_demo` already exists and is the installed app folder, do not
run `get-app` again. Pull the existing app and migrate:

```bash
cd ~/frappe-bench
git -C apps/restaurant_demo pull
bench --site <demo-site> migrate
bench --site <demo-site> clear-cache
```

## Dry run

```bash
bench --site <demo-site> execute restaurant_demo.restaurant_demo_seed.create_full_demo --kwargs "{'cycles': 100, 'dry_run': True}"
```

## Clear demo data

Preview what will be cancelled/deleted:

```bash
bench --site <demo-site> execute restaurant_demo.restaurant_demo_seed.clear_demo_data --kwargs "{'dry_run': True}"
```

Clear only demo-prefixed records and `BDREST-` items from a dedicated demo site:

```bash
bench --site <demo-site> execute restaurant_demo.restaurant_demo_seed.clear_demo_data --kwargs "{'dry_run': False, 'confirm_demo_site': True}"
bench --site <demo-site> clear-cache
```

## Create the demo records

Start with a 2-cycle smoke test on a dedicated demo site, inspect the result,
then run 100:

```bash
bench --site <demo-site> execute restaurant_demo.restaurant_demo_seed.create_full_demo --kwargs "{'cycles': 2, 'dry_run': False, 'confirm_demo_site': True}"
bench --site <demo-site> execute restaurant_demo.restaurant_demo_seed.create_full_demo --kwargs "{'cycles': 100, 'dry_run': False, 'confirm_demo_site': True}"
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
