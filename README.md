# ERPNext Restaurant Demo Seeder

Git-installable Frappe app for seeding an ERPNext restaurant operations demo.
It creates four restaurant brands/branches that share one Central Store and one
Central Kitchen while tracking branch-wise requisition, stock movement,
production/consumption, delivery, sales, and accounting cost centers.

Use only on a dedicated demo site/company. The script creates submitted stock
and accounting documents.

## Business Flow

The demo follows this operating model:

1. A branch/brand requests finished food items, such as Beef Tehari or Kacchi
   Biryani.
2. Central Kitchen receives the finished-item requisition.
3. Raw materials are transferred internally from Central Store to Central
   Kitchen.
4. BOM-based manufacture consumes raw materials and produces finished food.
5. Finished food is transferred from Central Kitchen to the requesting branch
   outlet warehouse.
6. Delivery Note and Sales Invoice show the sale under the brand cost center.

Raw materials are not the branch requisition. Raw materials are internal kitchen
consumption driven by the recipe/BOM.

## What It Creates

- 4 brands/branches with separate outlet warehouses and POS Profiles
- 1 Central Store and 1 Central Kitchen
- Brand-wise Cost Centers
- Bangladesh menu items and raw material items with `BDREST-` item codes
- BDT selling and buying prices
- Local PNG item thumbnails
- Recipe BOMs
- Opening stock
- Finished-item branch requisitions
- Purchase MR -> Purchase Order -> Purchase Receipt -> Purchase Invoice
- Internal raw material transfer
- Manufacture/consumption Stock Entry
- Finished food transfer to branch
- Delivery Note and Sales Invoice

## Install

Run from the bench directory:

```bash
cd ~/frappe-bench
bench get-app --skip-assets restaurant_demo https://github.com/TechwithZakir/ERPNext-restaurant-demo-seeder.git
bench --site <demo-site> install-app restaurant_demo
bench --site <demo-site> migrate
bench --site <demo-site> clear-cache
```

The app has no frontend assets, so `--skip-assets` avoids an unnecessary build.

## Update

```bash
cd ~/frappe-bench/apps/restaurant_demo
git pull

cd ~/frappe-bench
bench --site <demo-site> migrate
bench --site <demo-site> clear-cache
```

## Seed Demo Data

Dry run:

```bash
bench --site <demo-site> execute restaurant_demo.restaurant_demo_seed.create_full_demo --kwargs "{'cycles': 100, 'dry_run': True}"
```

Smoke test 4 cycles, so all four brands are touched:

```bash
bench --site <demo-site> execute restaurant_demo.restaurant_demo_seed.create_full_demo --kwargs "{'cycles': 4, 'dry_run': False, 'confirm_demo_site': True}"
```

Full demo:

```bash
bench --site <demo-site> execute restaurant_demo.restaurant_demo_seed.create_full_demo --kwargs "{'cycles': 100, 'dry_run': False, 'confirm_demo_site': True}"
```

## Delete/Clean Demo Data

Preview the records selected for cleanup before changing anything:

```bash
bench --site <demo-site> execute restaurant_demo.restaurant_demo_seed.clear_demo_data --kwargs "{'dry_run': True}"
```

For a disposable demo site, hard-delete the seeded transactions, ledger rows,
items, POS Profiles, warehouses, and related masters:

```bash
bench --site <demo-site> execute restaurant_demo.restaurant_demo_seed.clear_demo_data --kwargs "{'dry_run': False, 'hard_delete': True, 'confirm_demo_site': True}"
bench --site <demo-site> clear-cache
```

Hard delete also removes demo-linked stock, GL, and payment ledger rows and
handles archived warehouse names. Never run it on a production site or a
company containing real transactions.

For a non-destructive cleanup attempt, omit `hard_delete`; ERPNext may retain
records blocked by submitted-document or repost-processing locks.

## Demo Checklist

Show these in ERPNext:

- Warehouse: Central Store, Central Kitchen, and 4 outlet warehouses
- Cost Center: 4 brand-wise cost centers
- POS Profile: one profile per brand
- Item: filter `BDREST-` to show menu and ingredient items
- BOM: open a menu item BOM to show recipe/raw material consumption
- Material Request: branch requisition for finished food item
- Stock Entry: raw transfer, manufacture/consumption, finished transfer
- Purchase Order / Purchase Receipt / Purchase Invoice: raw material supply
- Delivery Note: food delivery/challan
- Sales Invoice: brand-wise sale and accounting impact

## Recovery Notes

If a previous install failed and left partial folders:

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
