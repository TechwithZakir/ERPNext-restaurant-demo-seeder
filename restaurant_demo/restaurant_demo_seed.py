"""Seed a Bangladesh restaurant demo in an existing ERPNext/Frappe site.

Install
-------
Copy this file into an installed custom app, for example:

    apps/restaurant_demo/restaurant_demo/restaurant_demo_seed.py

Then run from the bench directory:

    bench --site <demo-site> execute restaurant_demo.restaurant_demo_seed.create_demo_setup --kwargs "{'dry_run': True}"
    bench --site <demo-site> execute restaurant_demo.restaurant_demo_seed.create_demo_setup --kwargs "{'dry_run': False, 'confirm_demo_site': True}"
    bench --site <demo-site> execute restaurant_demo.restaurant_demo_seed.create_full_demo --kwargs "{'cycles': 100, 'dry_run': True}"
    bench --site <demo-site> execute restaurant_demo.restaurant_demo_seed.create_full_demo --kwargs "{'cycles': 100, 'dry_run': False, 'confirm_demo_site': True}"
    bench --site <demo-site> execute restaurant_demo.restaurant_demo_seed.update_demo_item_names --kwargs "{'dry_run': False, 'confirm_demo_site': True}"

The setup command creates demo masters, local menu thumbnails, recipes (BOMs),
opening stock, POS profiles, and draft requisitions. The full-demo command
additionally creates linked procurement, requisition, transfer, manufacturing,
delivery-note and sales-invoice documents. Neither command deletes records.
Use a dedicated demo site/company: opening stock and submitted stock
reconciliations affect inventory valuation and accounting.

The script uses only Python's standard library plus Frappe/ERPNext. It makes
local PNG illustrations so POS item images do not depend on an external image
host. Replace them with the restaurant's own photos before a client demo.
"""

from __future__ import annotations

import math
import random
import struct
import zlib

import frappe
from frappe.utils import today


DEMO_PREFIX = "DEMO - BD Restaurant"

# Names are intentionally generic and fictional. Prices are sample BDT prices,
# not a tax or menu-price recommendation.
BRANDS = [
    {"key": "B01", "name": "Brand 01 - Kacchi & Biryani", "color": (172, 78, 42)},
    {"key": "B02", "name": "Brand 02 - Bangla Meals", "color": (77, 119, 67)},
    {"key": "B03", "name": "Brand 03 - Grill & Kebabs", "color": (155, 75, 50)},
    {"key": "B04", "name": "Brand 04 - Cafe & Snacks", "color": (94, 105, 150)},
]

INGREDIENTS = [
    ("RICE", "Basmati Rice", "Kg", 100, 95),
    ("CHICKEN", "Chicken", "Kg", 60, 260),
    ("BEEF", "Beef", "Kg", 45, 780),
    ("MUTTON", "Mutton", "Kg", 25, 980),
    ("POTATO", "Potato", "Kg", 50, 45),
    ("ONION", "Onion", "Kg", 35, 95),
    ("OIL", "Cooking Oil", "Litre", 25, 175),
    ("YOGURT", "Yogurt", "Kg", 20, 180),
    ("FLOUR", "Flour", "Kg", 30, 65),
    ("LENTIL", "Masoor Dal", "Kg", 20, 145),
    ("SPICE", "Bangla Spice Mix", "Kg", 12, 850),
    ("CHICKPEA", "Chickpeas", "Kg", 15, 125),
    ("TAMARIND", "Tamarind", "Kg", 8, 220),
    ("MINT", "Mint Syrup", "Litre", 12, 260),
    ("LEMON", "Lemon", "Kg", 12, 180),
    ("BREAD", "Sandwich Bread", "Nos", 50, 75),
]

# Per serving recipe quantities are illustrative. Ingredient UOMs are kept
# simple for the demo; production recipes should be checked with the chef.
MENUS = [
    ("B01", "Kacchi Biryani", 350, (220, 166, 104), [("RICE", 0.18), ("MUTTON", 0.20), ("POTATO", 0.08), ("ONION", 0.025), ("OIL", 0.025), ("SPICE", 0.012)]),
    ("B01", "Beef Tehari", 280, (198, 144, 82), [("RICE", 0.18), ("BEEF", 0.16), ("ONION", 0.03), ("OIL", 0.02), ("SPICE", 0.012)]),
    ("B01", "Borhani", 90, (166, 193, 127), [("YOGURT", 0.20), ("MINT", 0.02), ("SPICE", 0.004)]),
    ("B02", "Chicken Roast", 190, (191, 118, 75), [("CHICKEN", 0.22), ("YOGURT", 0.04), ("ONION", 0.035), ("OIL", 0.02), ("SPICE", 0.01)]),
    ("B02", "Bhuna Khichuri", 220, (195, 148, 85), [("RICE", 0.12), ("LENTIL", 0.08), ("ONION", 0.025), ("OIL", 0.02), ("SPICE", 0.01)]),
    ("B02", "Masoor Dal", 80, (205, 155, 72), [("LENTIL", 0.10), ("ONION", 0.015), ("OIL", 0.012), ("SPICE", 0.004)]),
    ("B03", "Mezbani Beef", 340, (147, 81, 55), [("BEEF", 0.20), ("ONION", 0.04), ("OIL", 0.02), ("SPICE", 0.014)]),
    ("B03", "Chicken Grill", 290, (182, 97, 58), [("CHICKEN", 0.24), ("YOGURT", 0.035), ("LEMON", 0.015), ("SPICE", 0.012)]),
    ("B03", "Paratha", 40, (218, 179, 103), [("FLOUR", 0.08), ("OIL", 0.01)]),
    ("B04", "Chicken Sandwich", 230, (206, 164, 111), [("BREAD", 2), ("CHICKEN", 0.10), ("YOGURT", 0.015)]),
    ("B04", "Fuchka - 8 Pieces", 140, (206, 159, 77), [("FLOUR", 0.06), ("CHICKPEA", 0.05), ("TAMARIND", 0.02), ("SPICE", 0.005)]),
    ("B04", "Lemon Mint Cooler", 120, (135, 182, 126), [("MINT", 0.04), ("LEMON", 0.025)]),
]


def _has_field(doctype, fieldname):
    return frappe.get_meta(doctype).has_field(fieldname)


def _set(doc, fieldname, value):
    if value is not None and _has_field(doc.doctype, fieldname):
        doc.set(fieldname, value)


def _get_demo_doc(doctype, marker, docstatus=None, title=None, title_like=None):
    filters = {}
    if docstatus is not None:
        filters["docstatus"] = docstatus
    if _has_field(doctype, "remarks"):
        filters["remarks"] = marker
    elif title and _has_field(doctype, "title"):
        filters["title"] = title
    elif title_like and _has_field(doctype, "title"):
        filters["title"] = ["like", title_like]
    else:
        return None
    return frappe.db.get_value(doctype, filters, "name")


def _demo_name_filters(doctype):
    filters = []
    if _has_field(doctype, "remarks"):
        filters.append({"remarks": ["like", DEMO_PREFIX + "%"]})
    if _has_field(doctype, "title"):
        filters.append({"title": ["like", DEMO_PREFIX + "%"]})
    if _has_field(doctype, "item_code"):
        filters.append({"item_code": ["like", "BDREST-%"]})
    if _has_field(doctype, "item_name"):
        filters.append({"item_name": ["like", DEMO_PREFIX + "%"]})
    label_fields = {
        "POS Profile": "name",
        "Warehouse": "warehouse_name",
        "Cost Center": "cost_center_name",
        "Item Group": "item_group_name",
        "Price List": "price_list_name",
        "Customer": "customer_name",
        "Supplier": "supplier_name",
        "BOM": "item",
        "File": "file_name",
    }
    label_field = label_fields.get(doctype)
    if label_field and _has_field(doctype, label_field):
        if doctype == "BOM":
            filters.append({label_field: ["like", "BDREST-%"]})
        elif doctype == "File":
            filters.append({label_field: ["like", "demo_restaurant_%"]})
        else:
            filters.append({label_field: ["like", "DEMO -%"]})
    if doctype in ("Warehouse", "Cost Center", "POS Profile"):
        filters.append({"name": ["like", "DEMO -%"]})
    if doctype == "Warehouse" and _has_field(doctype, "warehouse_name"):
        filters.append({"warehouse_name": ["like", "ARCHIVED - DEMO -%"]})
    return filters


def _demo_doc_names(doctype):
    names = []
    seen = set()

    def add(name):
        if name and name not in seen:
            seen.add(name)
            names.append(name)

    for filters in _demo_name_filters(doctype):
        for name in frappe.get_all(doctype, filters=filters, pluck="name", limit=10000):
            add(name)

    child_tables = {
        "Material Request": "Material Request Item",
        "Stock Entry": "Stock Entry Detail",
        "Delivery Note": "Delivery Note Item",
        "Sales Invoice": "Sales Invoice Item",
        "Purchase Order": "Purchase Order Item",
        "Purchase Receipt": "Purchase Receipt Item",
        "Purchase Invoice": "Purchase Invoice Item",
        "Stock Reconciliation": "Stock Reconciliation Item",
    }
    child_doctype = child_tables.get(doctype)
    if child_doctype and frappe.db.exists("DocType", child_doctype):
        for fieldname, pattern in (("item_code", "BDREST-%"), ("warehouse", "DEMO -%"), ("s_warehouse", "DEMO -%"), ("t_warehouse", "DEMO -%")):
            if _has_field(child_doctype, fieldname):
                for row in frappe.get_all(
                    child_doctype,
                    filters={fieldname: ["like", pattern]},
                    fields=["parent"],
                    limit=10000,
                ):
                    add(row.parent)

    if doctype == "Bin":
        for name in frappe.get_all(
            "Bin",
            filters={"item_code": ["like", "BDREST-%"]},
            pluck="name",
            limit=10000,
        ):
            add(name)
        for name in frappe.get_all(
            "Bin",
            filters={"warehouse": ["like", "DEMO -%"]},
            pluck="name",
            limit=10000,
        ):
            add(name)

    if doctype == "Repost Item Valuation":
        for fieldname in ("item_code", "warehouse"):
            if _has_field(doctype, fieldname):
                pattern = "BDREST-%" if fieldname == "item_code" else "DEMO -%"
                for name in frappe.get_all(doctype, filters={fieldname: ["like", pattern]}, pluck="name", limit=10000):
                    add(name)

    if doctype == "POS Profile":
        for fieldname in ("warehouse", "name", "title"):
            if _has_field(doctype, fieldname):
                for name in frappe.get_all(doctype, filters={fieldname: ["like", "DEMO -%"]}, pluck="name", limit=10000):
                    add(name)
        for child_doctype, fieldname in (("POS Profile Item Group", "item_group"),):
            if frappe.db.exists("DocType", child_doctype) and _has_field(child_doctype, fieldname):
                for row in frappe.get_all(child_doctype, filters={fieldname: ["like", "DEMO -%"]}, fields=["parent"], limit=10000):
                    add(row.parent)
    return names


def _disable_demo_doc(doctype, name):
    if not frappe.db.exists(doctype, name) or not _has_field(doctype, "disabled"):
        return False
    doc = frappe.get_doc(doctype, name)
    doc.disabled = 1
    if doctype == "Warehouse" and _has_field("Warehouse", "warehouse_name") and not (doc.warehouse_name or "").startswith("ARCHIVED - "):
        doc.warehouse_name = "ARCHIVED - " + doc.warehouse_name
    doc.save(ignore_permissions=True)
    return True


def _apply_fields(doc, fields):
    for fieldname, value in fields.items():
        _set(doc, fieldname, value)
    return doc


def _upsert_named(doctype, name, fields):
    """Insert/update a demo-owned record whose document name is stable."""
    if frappe.db.exists(doctype, name):
        doc = frappe.get_doc(doctype, name)
        _apply_fields(doc, fields)
        doc.save(ignore_permissions=True)
    else:
        doc = frappe.new_doc(doctype)
        doc.name = name
        _apply_fields(doc, fields)
        doc.insert(ignore_permissions=True)
    return doc


def _upsert_by_field(doctype, fieldname, value, fields, extra_filters=None):
    filters = {fieldname: value}
    if extra_filters:
        filters.update(extra_filters)
    existing = frappe.db.get_value(doctype, filters, "name")
    if existing:
        doc = frappe.get_doc(doctype, existing)
        _apply_fields(doc, fields)
        doc.save(ignore_permissions=True)
    else:
        doc = frappe.new_doc(doctype)
        _apply_fields(doc, {fieldname: value, **fields})
        doc.insert(ignore_permissions=True)
    return doc


def _find_group_root(doctype, company=None):
    filters = {"is_group": 1}
    if company and _has_field(doctype, "company"):
        filters["company"] = company
    fields = ["name"]
    if _has_field(doctype, "parent_warehouse"):
        fields.append("parent_warehouse")
    if _has_field(doctype, "parent_cost_center"):
        fields.append("parent_cost_center")
    if _has_field(doctype, "parent_item_group"):
        fields.append("parent_item_group")
    roots = frappe.get_all(doctype, filters=filters, fields=fields, limit=100)
    parent_field = {
        "Warehouse": "parent_warehouse",
        "Cost Center": "parent_cost_center",
        "Item Group": "parent_item_group",
    }.get(doctype)
    for row in roots:
        if not parent_field or not row.get(parent_field):
            return row.name
    if roots:
        return roots[0].name
    return None


def _ensure_uom(name, whole_number=False):
    if frappe.db.exists("UOM", name):
        return name
    doc = frappe.new_doc("UOM")
    doc.uom_name = name
    _set(doc, "must_be_whole_number", 1 if whole_number else 0)
    doc.insert(ignore_permissions=True)
    return doc.name


def _make_png(width, height, seed, food_color):
    """Create a small plate-style food illustration PNG without dependencies."""
    rng = random.Random(seed)
    bg1 = (248, 239, 220)
    bg2 = (233, 218, 190)
    pixels = [[(0, 0, 0) for _ in range(width)] for _ in range(height)]

    def blend(a, b, t):
        return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))

    for y in range(height):
        for x in range(width):
            pixels[y][x] = blend(bg1, bg2, y / max(1, height - 1))

    def ellipse(cx, cy, rx, ry, color):
        y0, y1 = max(0, cy - ry), min(height, cy + ry + 1)
        x0, x1 = max(0, cx - rx), min(width, cx + rx + 1)
        for yy in range(y0, y1):
            for xx in range(x0, x1):
                if ((xx - cx) / max(1, rx)) ** 2 + ((yy - cy) / max(1, ry)) ** 2 <= 1:
                    pixels[yy][xx] = color

    # Plate, rice/base, and a subtle rim.
    ellipse(width // 2, height // 2 + 6, 140, 100, (213, 199, 172))
    ellipse(width // 2, height // 2, 134, 95, (255, 253, 246))
    ellipse(width // 2, height // 2, 108, 69, (244, 229, 187))
    ellipse(width // 2, height // 2, 99, 61, food_color)

    # Rice / garnish flecks and browned or green components make each tile
    # visually distinct while keeping the asset self-contained.
    flecks = [
        tuple(min(255, c + d) for c in food_color) for d in (18, 30, 44)
    ] + [(70, 111, 55), (76, 132, 64), (245, 204, 89), (164, 67, 43)]
    for _ in range(95):
        angle = rng.random() * math.tau
        radius = math.sqrt(rng.random())
        cx = width // 2 + int(math.cos(angle) * 88 * radius)
        cy = height // 2 + int(math.sin(angle) * 50 * radius)
        r = rng.choice((2, 3, 4, 6, 8))
        ellipse(cx, cy, r, max(2, r // 2), rng.choice(flecks))

    # PNG rows use filter byte 0; RGB color type, 8-bit depth.
    raw = bytearray()
    for row in pixels:
        raw.append(0)
        for r, g, b in row:
            raw.extend((r, g, b))

    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">2I5B", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(raw), 8))
        + chunk(b"IEND", b"")
    )


def _attach_item_image(item, seed, color):
    filename = "demo_restaurant_%s.png" % frappe.scrub(item.item_code).lower()
    file_url = frappe.db.get_value(
        "File",
        {"attached_to_doctype": "Item", "attached_to_name": item.name, "file_name": filename},
        "file_url",
    )
    if not file_url:
        from frappe.utils.file_manager import save_file

        file_doc = save_file(
            filename,
            _make_png(320, 230, seed, color),
            "Item",
            item.name,
            is_private=0,
        )
        file_url = file_doc.file_url
    if _has_field("Item", "image") and item.image != file_url:
        item.image = file_url
        item.save(ignore_permissions=True)


def _ensure_tree_record(doctype, label_field, label, parent_field, parent, company=None):
    filters = {label_field: label}
    if company and _has_field(doctype, "company"):
        filters["company"] = company
    existing = frappe.db.get_value(doctype, filters, "name")

    # Cleanup can archive a demo tree record by changing its visible label,
    # while ERPNext keeps the original document name. Reuse that record so a
    # later seed remains idempotent and does not collide on the primary key.
    if not existing:
        candidate_names = [label]
        if company and doctype in ("Warehouse", "Cost Center"):
            company_abbr = frappe.db.get_value("Company", company, "abbr")
            if company_abbr:
                candidate_names.append("%s - %s" % (label, company_abbr))
        for candidate in candidate_names:
            if frappe.db.exists(doctype, candidate):
                existing = candidate
                break

    if existing:
        doc = frappe.get_doc(doctype, existing)
        _set(doc, label_field, label)
        _set(doc, parent_field, parent)
        _set(doc, "is_group", 0)
        _set(doc, "disabled", 0)
        if company:
            _set(doc, "company", company)
        doc.save(ignore_permissions=True)
        return doc
    doc = frappe.new_doc(doctype)
    _set(doc, label_field, label)
    _set(doc, parent_field, parent)
    _set(doc, "is_group", 0)
    if company:
        _set(doc, "company", company)
    doc.insert(ignore_permissions=True)
    return doc


def _company_for_demo(company=None):
    company = company or frappe.defaults.get_global_default("company")
    if not company:
        rows = frappe.get_all("Company", pluck="name", limit=1)
        company = rows[0] if rows else None
    if not company or not frappe.db.exists("Company", company):
        frappe.throw("Create a Bangladesh Company in ERPNext first, then rerun this seed script.")
    currency = frappe.db.get_value("Company", company, "default_currency")
    if currency != "BDT":
        frappe.throw("This Bangladesh demo uses BDT sample prices. Select a Company whose default currency is BDT.")
    return company


def _cash_account(company):
    return frappe.db.get_value(
        "Account",
        {"company": company, "account_type": "Cash", "is_group": 0, "disabled": 0},
        "name",
    )


def _opening_stock_difference_account(company):
    """Return a Balance Sheet account accepted by opening Stock Reconciliation."""
    company_doc = frappe.get_doc("Company", company)
    for account in (
        getattr(company_doc, "default_inventory_account", None),
        getattr(company_doc, "stock_received_but_not_billed", None),
    ):
        if account and frappe.db.get_value(
            "Account",
            {"name": account, "company": company, "is_group": 0, "disabled": 0, "root_type": ["in", ["Asset", "Liability"]]},
            "name",
        ):
            return account

    for filters in (
        {"company": company, "account_type": "Stock", "is_group": 0, "disabled": 0, "root_type": "Asset"},
        {"company": company, "is_group": 0, "disabled": 0, "root_type": ["in", ["Asset", "Liability"]]},
    ):
        account = frappe.db.get_value("Account", filters, "name", order_by="lft asc")
        if account:
            return account
    return None


def _ensure_mode_of_payment(label, mode_type, company, account):
    mode = _upsert_by_field("Mode of Payment", "mode_of_payment", label, {"type": mode_type, "enabled": 1})
    if _has_field("Mode of Payment", "accounts") and account:
        rows = [row for row in mode.get("accounts", []) if row.company == company]
        if rows:
            rows[0].default_account = account
        else:
            row = mode.append("accounts", {})
            _set(row, "company", company)
            _set(row, "default_account", account)
        mode.save(ignore_permissions=True)
    return mode


def _ensure_payment_modes(company, cash_account):
    modes = [_ensure_mode_of_payment("Cash", "Cash", company, cash_account).name]
    accounts = frappe.get_all(
        "Account",
        filters={"company": company, "is_group": 0, "disabled": 0},
        fields=["name", "account_name"],
    )
    # Add mobile wallets only if matching company ledgers already exist. This
    # prevents bKash/Nagad receipts from being silently posted to a Cash ledger.
    for label in ("bKash", "Nagad"):
        account = next((a.name for a in accounts if label.lower() in (a.account_name or a.name).lower()), None)
        if account:
            modes.append(_ensure_mode_of_payment(label, "Bank", company, account).name)
    return modes


def _ensure_master_records(company):
    abbr = frappe.db.get_value("Company", company, "abbr")
    if not abbr:
        frappe.throw("The selected Company needs a Company Abbreviation before setup can continue.")

    warehouse_root = _find_group_root("Warehouse", company)
    cost_center_root = _find_group_root("Cost Center", company)
    item_group_root = frappe.db.get_value("Item Group", {"is_group": 1, "parent_item_group": ["is", "not set"]}, "name")
    if not warehouse_root or not cost_center_root or not item_group_root:
        frappe.throw("ERPNext setup is incomplete: a root Warehouse, Cost Center and Item Group are required.")

    # UOMs used in recipe quantities and menu portions.
    for uom in ("Kg", "Litre", "Nos"):
        _ensure_uom(uom, whole_number=(uom == "Nos"))

    warehouses = {}
    warehouses["central_store"] = _ensure_tree_record(
        "Warehouse", "warehouse_name", "DEMO - Central Store", "parent_warehouse", warehouse_root, company
    ).name
    warehouses["central_kitchen"] = _ensure_tree_record(
        "Warehouse", "warehouse_name", "DEMO - Central Kitchen", "parent_warehouse", warehouse_root, company
    ).name
    cost_centers = {}
    cost_centers["shared"] = _ensure_tree_record(
        "Cost Center", "cost_center_name", "DEMO - Central Kitchen & Shared Ops", "parent_cost_center", cost_center_root, company
    ).name

    brand_groups = {}
    for brand in BRANDS:
        group_label = "DEMO - %s Menu" % brand["key"]
        group = _ensure_tree_record("Item Group", "item_group_name", group_label, "parent_item_group", item_group_root)
        brand["item_group"] = group.name

        outlet = _ensure_tree_record(
            "Warehouse", "warehouse_name", "DEMO - %s Outlet" % brand["key"], "parent_warehouse", warehouse_root, company
        )
        warehouses[brand["key"]] = outlet.name

        cc = _ensure_tree_record(
            "Cost Center", "cost_center_name", "DEMO - %s" % brand["name"], "parent_cost_center", cost_center_root, company
        )
        cost_centers[brand["key"]] = cc.name
        brand_groups[brand["key"]] = group.name

    ingredient_group = _ensure_tree_record(
        "Item Group", "item_group_name", "DEMO - Shared Ingredients", "parent_item_group", item_group_root
    ).name

    return abbr, warehouses, cost_centers, brand_groups, ingredient_group


def _ensure_price_list(name="DEMO - Restaurant BDT", selling=True):
    price_list = _upsert_by_field(
        "Price List",
        "price_list_name",
        name,
        {"currency": "BDT", "selling": 1 if selling else 0, "buying": 0 if selling else 1, "enabled": 1},
    )
    return price_list.name


def _ensure_item(code, label, uom, group, warehouse, standard_rate, is_stock_item=True, is_menu=True):
    fields = {
        "item_name": label,
        "item_group": group,
        "stock_uom": uom,
        "is_stock_item": 1 if is_stock_item else 0,
        "is_sales_item": 1 if is_menu else 0,
        "is_purchase_item": 1 if group.endswith("Shared Ingredients") else 0,
        "include_item_in_manufacturing": 1 if is_stock_item else 0,
        "standard_rate": standard_rate,
        "default_warehouse": warehouse,
        "description": "Bangladesh restaurant demo item; replace sample details before production use.",
    }
    if frappe.db.exists("Item", code):
        item = frappe.get_doc("Item", code)
        _apply_fields(item, fields)
        item.save(ignore_permissions=True)
    else:
        item = frappe.new_doc("Item")
        item.item_code = code
        _apply_fields(item, fields)
        item.insert(ignore_permissions=True)
    return item


def _demo_item_labels():
    labels = {"BDREST-%s" % code: label for code, label, *_rest in INGREDIENTS}
    labels.update(
        {
            "BDREST-%s-M%02d" % (brand_key, index): label
            for index, (brand_key, label, _price, _color, _components) in enumerate(MENUS, start=1)
        }
    )
    return labels


def update_demo_item_names(dry_run=True, confirm_demo_site=False):
    """Update existing demo item names while preserving stable item codes."""
    if not dry_run and not confirm_demo_site:
        frappe.throw("Refusing to update demo items without confirm_demo_site=True. Use a dedicated demo site.")

    changes = []
    for item_code, expected_name in _demo_item_labels().items():
        if not frappe.db.exists("Item", item_code):
            continue
        current_name = frappe.db.get_value("Item", item_code, "item_name")
        if current_name == expected_name:
            continue
        changes.append({"item_code": item_code, "from": current_name, "to": expected_name})
        if not dry_run:
            # Some ERPNext versions normalize Item fields during save and can
            # restore the code as the visible name. Update the field directly
            # so this one-time migration persists across versions.
            frappe.db.set_value("Item", item_code, "item_name", expected_name, update_modified=True)

    if not dry_run:
        frappe.db.commit()
    return {"writes": not dry_run, "updated": len(changes), "changes": changes}


def _ensure_item_price(item_code, price_list, rate, uom, selling=True):
    filters = {
        "item_code": item_code,
        "price_list": price_list,
        "selling": 1 if selling else 0,
        "buying": 0 if selling else 1,
    }
    name = frappe.db.get_value("Item Price", filters, "name")
    if name:
        doc = frappe.get_doc("Item Price", name)
        _apply_fields(doc, {"price_list_rate": rate, "currency": "BDT", "uom": uom})
        doc.save(ignore_permissions=True)
    else:
        doc = frappe.new_doc("Item Price")
        _apply_fields(doc, {**filters, "price_list_rate": rate, "currency": "BDT", "uom": uom})
        doc.insert(ignore_permissions=True)


def _ensure_customer():
    settings = frappe.get_single("Selling Settings")
    customer_group = getattr(settings, "customer_group", None)
    territory = getattr(settings, "territory", None)
    if not customer_group:
        customer_group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
    if not territory:
        territory = frappe.db.get_value("Territory", {"is_group": 0}, "name")
    if not customer_group or not territory:
        frappe.throw("Set a default Customer Group and Territory in Selling Settings before running the demo setup.")
    existing = frappe.db.get_value("Customer", {"customer_name": "DEMO - Walk-in Customer"}, "name")
    fields = {"customer_name": "DEMO - Walk-in Customer", "customer_type": "Individual", "customer_group": customer_group, "territory": territory}
    if existing:
        doc = frappe.get_doc("Customer", existing)
        _apply_fields(doc, fields)
        doc.save(ignore_permissions=True)
        return doc.name
    doc = frappe.new_doc("Customer")
    _apply_fields(doc, fields)
    doc.insert(ignore_permissions=True)
    return doc.name


def _ensure_supplier():
    settings = frappe.get_single("Buying Settings")
    supplier_group = getattr(settings, "supplier_group", None)
    if not supplier_group:
        supplier_group = frappe.db.get_value("Supplier Group", {"is_group": 0}, "name")
    if not supplier_group:
        frappe.throw("Set a default Supplier Group in Buying Settings before running the demo setup.")
    fields = {
        "supplier_name": "DEMO - Dhaka Fresh Foods",
        "supplier_group": supplier_group,
        "supplier_type": "Company",
        "country": "Bangladesh",
    }
    existing = frappe.db.get_value("Supplier", {"supplier_name": fields["supplier_name"]}, "name")
    if existing:
        doc = frappe.get_doc("Supplier", existing)
        _apply_fields(doc, fields)
        doc.save(ignore_permissions=True)
        return doc.name
    doc = frappe.new_doc("Supplier")
    _apply_fields(doc, fields)
    doc.insert(ignore_permissions=True)
    return doc.name


def _ensure_pos_profile(name, company, warehouse, cost_center, customer, price_list, item_group, payment_modes):
    if frappe.db.exists("POS Profile", name):
        doc = frappe.get_doc("POS Profile", name)
    else:
        doc = frappe.new_doc("POS Profile")
        doc.name = name
    company_doc = frappe.get_doc("Company", company)
    fields = {
        "company": company,
        "warehouse": warehouse,
        "cost_center": cost_center,
        "write_off_cost_center": cost_center,
        "customer": customer,
        "selling_price_list": price_list,
        "price_list": price_list,
        "currency": "BDT",
        "income_account": getattr(company_doc, "default_income_account", None),
        "expense_account": getattr(company_doc, "default_expense_account", None),
        "write_off_account": getattr(company_doc, "round_off_account", None),
        "write_off_limit": 1,
        "hide_images": 0,
        "hide_unavailable_items": 0,
        "validate_stock_on_save": 1,
        "allow_user_to_edit_rate": 0,
        "allow_user_to_edit_discount": 0,
    }
    _apply_fields(doc, fields)

    if _has_field("POS Profile", "payments"):
        doc.set("payments", [])
        for index, payment_mode in enumerate(payment_modes):
            payment = doc.append("payments", {})
            _set(payment, "mode_of_payment", payment_mode)
            _set(payment, "default", 1 if index == 0 else 0)
    if _has_field("POS Profile", "item_groups"):
        doc.set("item_groups", [])
        row = doc.append("item_groups", {})
        _set(row, "item_group", item_group)

    if doc.is_new():
        doc.insert(ignore_permissions=True)
    else:
        doc.save(ignore_permissions=True)
    return doc.name


def _ensure_bom(menu_item_code, company, components, central_kitchen):
    existing = frappe.db.get_value("BOM", {"item": menu_item_code, "is_active": 1, "is_default": 1}, "name")
    if existing:
        return existing
    if not frappe.db.exists("DocType", "BOM"):
        return None
    bom = frappe.new_doc("BOM")
    _set(bom, "item", menu_item_code)
    _set(bom, "item_code", menu_item_code)
    _set(bom, "company", company)
    _set(bom, "quantity", 1)
    _set(bom, "uom", "Nos")
    _set(bom, "is_active", 1)
    _set(bom, "is_default", 1)
    for ingredient_code, qty in components:
        row = bom.append("items", {})
        _set(row, "item_code", ingredient_code)
        _set(row, "qty", qty)
        _set(row, "uom", frappe.db.get_value("Item", ingredient_code, "stock_uom"))
        _set(row, "source_warehouse", central_kitchen)
        _set(row, "include_item_in_manufacturing", 1)
    bom.insert(ignore_permissions=True)
    bom.submit()
    return bom.name


def _create_opening_stock(company, balances):
    """Submit one opening Stock Reconciliation per warehouse, once only."""
    created = []
    difference_account = _opening_stock_difference_account(company)
    if not difference_account:
        frappe.throw("No leaf Asset or Liability account was found for opening stock difference accounting.")
    for warehouse, lines in balances.items():
        if not lines:
            continue
        marker = "%s opening stock %s" % (DEMO_PREFIX, warehouse)
        exists = _get_demo_doc("Stock Reconciliation", marker, docstatus=1)
        if exists:
            continue
        changed_lines = []
        for item_code, qty, valuation_rate in lines:
            current_qty = frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "actual_qty") or 0
            if abs(float(current_qty) - float(qty)) > 0.0001:
                changed_lines.append((item_code, qty, valuation_rate))
        if not changed_lines:
            continue
        doc = frappe.new_doc("Stock Reconciliation")
        _set(doc, "company", company)
        _set(doc, "purpose", "Opening Stock")
        _set(doc, "posting_date", today())
        _set(doc, "remarks", marker)
        _set(doc, "expense_account", difference_account)
        for item_code, qty, valuation_rate in changed_lines:
            row = doc.append("items", {})
            _set(row, "item_code", item_code)
            _set(row, "warehouse", warehouse)
            _set(row, "qty", qty)
            _set(row, "valuation_rate", valuation_rate)
        doc.insert(ignore_permissions=True)
        doc.submit()
        created.append(doc.name)
    return created


def _create_draft_request(company, purpose, title, rows):
    marker = "%s %s" % (DEMO_PREFIX, title)
    existing = _get_demo_doc("Material Request", marker, docstatus=0, title=title)
    if existing:
        return existing
    doc = frappe.new_doc("Material Request")
    _set(doc, "company", company)
    _set(doc, "purpose", purpose)
    _set(doc, "material_request_type", purpose)
    _set(doc, "transaction_date", today())
    _set(doc, "schedule_date", today())
    _set(doc, "title", title)
    _set(doc, "remarks", marker)
    for item_code, qty, target_warehouse in rows:
        row = doc.append("items", {})
        _set(row, "item_code", item_code)
        _set(row, "qty", qty)
        _set(row, "schedule_date", today())
        _set(row, "warehouse", target_warehouse)
        _set(row, "target_warehouse", target_warehouse)
    doc.insert(ignore_permissions=True)
    return doc.name


def _preflight(company):
    blockers = []
    for doctype in ("POS Profile", "Item", "Item Price", "Material Request", "Stock Reconciliation", "BOM"):
        if not frappe.db.exists("DocType", doctype):
            blockers.append("Required ERPNext DocType is unavailable: %s" % doctype)
    if not _cash_account(company):
        blockers.append("No non-group Cash account is configured for %s." % company)
    if not _opening_stock_difference_account(company):
        blockers.append("No leaf Asset or Liability account is available for opening stock difference accounting.")
    selling = frappe.get_single("Selling Settings")
    customer_group = getattr(selling, "customer_group", None) or frappe.db.get_value(
        "Customer Group", {"is_group": 0}, "name"
    )
    territory = getattr(selling, "territory", None) or frappe.db.get_value(
        "Territory", {"is_group": 0}, "name"
    )
    if not customer_group:
        blockers.append("No default Customer Group is available.")
    if not territory:
        blockers.append("No default Territory is available.")
    buying = frappe.get_single("Buying Settings")
    supplier_group = getattr(buying, "supplier_group", None) or frappe.db.get_value(
        "Supplier Group", {"is_group": 0}, "name"
    )
    if not supplier_group:
        blockers.append("No default Supplier Group is available.")
    for doctype in ("Warehouse", "Cost Center", "Item Group"):
        if not _find_group_root(doctype, company if doctype != "Item Group" else None):
            blockers.append("Root %s is missing." % doctype)
    return blockers


def create_demo_setup(dry_run=True, confirm_demo_site=False, company=None):
    """Create demo masters and seed records; safe preview is the default.

    Args:
        dry_run: True prints/returns the plan without writing anything.
        confirm_demo_site: Required for writes because opening stock and recipes
            are demo data. Set True only on a dedicated demo site/company.
        company: Optional exact ERPNext Company name. Must use BDT currency.
    """
    company = _company_for_demo(company)
    blockers = _preflight(company)
    if blockers:
        frappe.throw("Demo setup prerequisites are missing:\n- " + "\n- ".join(blockers))
    if not dry_run and not confirm_demo_site:
        frappe.throw("Refusing to write demo data without confirm_demo_site=True. Use a dedicated demo site.")

    plan = {
        "company": company,
        "currency": "BDT",
        "brands": [brand["name"] for brand in BRANDS],
        "warehouses": ["Central Store", "Central Kitchen/WIP"] + ["Outlet " + brand["key"] for brand in BRANDS],
        "cost_centers": [brand["name"] for brand in BRANDS] + ["Central Kitchen & Shared Ops"],
        "ingredients": len(INGREDIENTS),
        "menu_items_with_images_and_prices": len(MENUS),
        "recipe_boms": len(MENUS),
        "pos_profiles": len(BRANDS),
        "draft_material_requests": 3,
        "opening_stock": "Central ingredients and sample menu stock in each outlet",
        "sample_payment_modes": "Cash, plus bKash/Nagad when matching ledger accounts already exist",
        "sample_item_images": "Locally generated illustrated PNG thumbnails; replace with actual food photos",
        "writes": not bool(dry_run),
    }
    if dry_run:
        return plan

    cash_account = _cash_account(company)
    if not cash_account:
        frappe.throw("No Cash account was found for this Company. Create/verify a Cash account before enabling POS checkout.")

    abbr, warehouses, cost_centers, brand_groups, ingredient_group = _ensure_master_records(company)
    payment_modes = _ensure_payment_modes(company, cash_account)
    price_list = _ensure_price_list("DEMO - Restaurant BDT", selling=True)
    buying_price_list = _ensure_price_list("DEMO - Restaurant BDT Buying", selling=False)
    walk_in_customer = _ensure_customer()
    demo_supplier = _ensure_supplier()

    # Reconcile just the sample masters' initial quantities. Re-running skips
    # the same marked submitted document, so it will not replenish stock.
    opening = {}
    for ingredient_idx, (code, label, uom, opening_qty, buy_rate) in enumerate(INGREDIENTS, start=1):
        item_code = "BDREST-%s" % code
        item = _ensure_item(
            item_code,
            label,
            uom,
            ingredient_group,
            warehouses["central_store"],
            buy_rate,
            is_menu=False,
        )
        _attach_item_image(item, 100 + ingredient_idx, (194, 143, 92))
        opening.setdefault(warehouses["central_store"], []).append((item_code, opening_qty, buy_rate))
        _ensure_item_price(item_code, buying_price_list, buy_rate, uom, selling=False)

    menu_item_codes = {}
    for idx, (brand_key, label, price, color, components) in enumerate(MENUS, start=1):
        item_code = "BDREST-%s-M%02d" % (brand_key, idx)
        item = _ensure_item(
            item_code,
            label,
            "Nos",
            brand_groups[brand_key],
            warehouses[brand_key],
            price,
            is_stock_item=True,
            is_menu=True,
        )
        _attach_item_image(item, idx, color)
        _ensure_item_price(item_code, price_list, price, "Nos")
        _ensure_bom(item_code, company, [("BDREST-%s" % code, qty) for code, qty in components], warehouses["central_kitchen"])
        opening.setdefault(warehouses[brand_key], []).append((item_code, 20, price * 0.55))
        menu_item_codes.setdefault(brand_key, []).append(item_code)

    # Attach stock/account defaults to Items when the current version exposes
    # the standard Item Defaults table.
    for item_code, default_warehouse, brand_key in [
        ("BDREST-%s" % code, warehouses["central_store"], None) for code, *_ in INGREDIENTS
    ] + [
        (item_code, warehouses[brand_key], brand_key)
        for brand_key, item_codes in menu_item_codes.items()
        for item_code in item_codes
    ]:
        item = frappe.get_doc("Item", item_code)
        if _has_field("Item", "item_defaults"):
            existing = next((row for row in item.item_defaults if row.company == company), None)
            row = existing or item.append("item_defaults", {})
            _set(row, "company", company)
            _set(row, "default_warehouse", default_warehouse)
            if brand_key and _has_field("Item Default", "selling_cost_center"):
                _set(row, "selling_cost_center", cost_centers[brand_key])
            item.save(ignore_permissions=True)

    pos_profiles = {}
    for brand in BRANDS:
        profile_name = "%s POS %s" % (DEMO_PREFIX, brand["key"])
        pos_profiles[brand["key"]] = _ensure_pos_profile(
            profile_name,
            company,
            warehouses[brand["key"]],
            cost_centers[brand["key"]],
            walk_in_customer,
            price_list,
            brand_groups[brand["key"]],
            payment_modes,
        )

    opening_docs = _create_opening_stock(company, opening)

    # Draft requests are ready for the salesperson to review and submit during
    # the demo; they do not move stock until fulfilled by a Stock Entry.
    brand_one = BRANDS[0]["key"]
    chicken = "BDREST-CHICKEN"
    rice = "BDREST-RICE"
    transfer_request = _create_draft_request(
        company,
        "Material Transfer",
        "Brand 01 Daily Requisition",
        [(chicken, 5, warehouses[brand_one]), (rice, 8, warehouses[brand_one])],
    )
    purchase_request = _create_draft_request(
        company,
        "Purchase",
        "Central Store Replenishment",
        [(rice, 50, warehouses["central_store"])],
    )
    kitchen_request = _create_draft_request(
        company,
        "Material Transfer",
        "Central Kitchen Prep Requisition",
        [(chicken, 20, warehouses["central_kitchen"]), (rice, 15, warehouses["central_kitchen"])],
    )

    return {
        **plan,
        "writes": True,
        "company_abbr": abbr,
        "supplier": demo_supplier,
        "payment_modes": payment_modes,
        "pos_profiles": pos_profiles,
        "opening_stock_reconciliations": opening_docs,
        "draft_transfer_request": transfer_request,
        "draft_purchase_request": purchase_request,
        "draft_kitchen_request": kitchen_request,
        "next_steps": [
            "Open POS and choose one of the DEMO POS profiles; item thumbnails and BDT prices are ready.",
            "Review and submit the Brand 01 Daily Requisition, then create a Material Transfer Stock Entry from Central Store to the outlet.",
            "Review the Central Kitchen Prep Requisition, transfer its ingredients into Central Kitchen, then open a menu item's BOM and demonstrate recipe ingredients.",
            "Create a Work Order/Manufacture entry if you want to show production live; its BOM source warehouse is Central Kitchen.",
            "Run POS sales live to populate sales and brand Cost Center reporting.",
        ],
    }


def _lifecycle_selections(cycles):
    selections = []
    demand = {}
    for index in range(cycles):
        menu_index = index % len(MENUS)
        brand_key, label, price, color, components = MENUS[menu_index]
        portions = 1 + index % 3
        menu_code = "BDREST-%s-M%02d" % (brand_key, menu_index + 1)
        lines = []
        for ingredient_key, per_portion in components:
            item_code = "BDREST-%s" % ingredient_key
            qty = round(per_portion * portions, 3)
            lines.append((item_code, qty))
            demand[ingredient_key] = demand.get(ingredient_key, 0) + qty
        selections.append(
            {
                "index": index + 1,
                "brand": brand_key,
                "menu_code": menu_code,
                "menu_name": label,
                "price": price,
                "portions": portions,
                "components": lines,
            }
        )
    return selections, demand


def _create_procurement_cycle(company, supplier, central_store, demand):
    """Create one linked Purchase MR -> PO -> Purchase Receipt -> Invoice chain."""
    marker = "%s CYCLES PROCUREMENT" % DEMO_PREFIX
    title = "DEMO - Raw Material Procurement for Lifecycle Dataset"
    existing_po = _get_demo_doc("Purchase Order", marker, docstatus=1)
    if existing_po:
        pr_name = _get_demo_doc("Purchase Receipt", marker, docstatus=1)
        if not pr_name:
            pr_name = _create_purchase_receipt_from_po(existing_po, marker, title)
        pi_name = _get_demo_doc("Purchase Invoice", marker, docstatus=1)
        if not pi_name:
            pi_name = _create_purchase_invoice_from_receipt(pr_name, marker, title)
        return {
            "purchase_order": existing_po,
            "purchase_receipt": pr_name,
            "purchase_invoice": pi_name,
            "created": False,
        }
    existing_mr = _get_demo_doc("Material Request", marker, docstatus=1, title=title)
    if existing_mr:
        frappe.throw("The demo procurement Material Request already exists without a complete submitted PO/receipt/invoice chain (%s). Inspect it before rerunning." % existing_mr)

    amounts = {key: max(1, math.ceil(qty * 1.10)) for key, qty in demand.items()}
    rates = {key: rate for key, _label, _uom, _opening, rate in INGREDIENTS}
    uoms = {key: uom for key, _label, uom, _opening, _rate in INGREDIENTS}

    mr = frappe.new_doc("Material Request")
    _set(mr, "company", company)
    _set(mr, "purpose", "Purchase")
    _set(mr, "material_request_type", "Purchase")
    _set(mr, "transaction_date", today())
    _set(mr, "schedule_date", today())
    _set(mr, "title", title)
    _set(mr, "remarks", marker)
    for key, qty in sorted(amounts.items()):
        row = mr.append("items", {})
        _set(row, "item_code", "BDREST-%s" % key)
        _set(row, "qty", qty)
        _set(row, "warehouse", central_store)
        _set(row, "schedule_date", today())
    mr.insert(ignore_permissions=True)
    mr.submit()

    po = frappe.new_doc("Purchase Order")
    _set(po, "company", company)
    _set(po, "supplier", supplier)
    _set(po, "transaction_date", today())
    _set(po, "schedule_date", today())
    _set(po, "currency", "BDT")
    _set(po, "title", title)
    _set(po, "buying_price_list", "DEMO - Restaurant BDT Buying")
    _set(po, "price_list_currency", "BDT")
    _set(po, "conversion_rate", 1)
    _set(po, "conversion_factor", 1)
    _set(po, "set_warehouse", central_store)
    _set(po, "remarks", marker)
    for mr_row in mr.items:
        key = mr_row.item_code.replace("BDREST-", "")
        row = po.append("items", {})
        _set(row, "item_code", mr_row.item_code)
        _set(row, "qty", mr_row.qty)
        _set(row, "rate", rates[key])
        _set(row, "uom", uoms[key])
        _set(row, "warehouse", central_store)
        _set(row, "schedule_date", today())
        _set(row, "material_request", mr.name)
        _set(row, "material_request_item", mr_row.name)
    if hasattr(po, "set_missing_values"):
        po.set_missing_values()
    if hasattr(po, "calculate_taxes_and_totals"):
        po.calculate_taxes_and_totals()
    po.insert(ignore_permissions=True)
    po.submit()

    pr_name = _create_purchase_receipt_from_po(po.name, marker, title)
    pi_name = _create_purchase_invoice_from_receipt(pr_name, marker, title)

    return {"material_request": mr.name, "purchase_order": po.name, "purchase_receipt": pr_name, "purchase_invoice": pi_name, "created": True}


def _create_purchase_receipt_from_po(po_name, marker, title):
    try:
        from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt

        pr = make_purchase_receipt(po_name)
    except ImportError:
        po = frappe.get_doc("Purchase Order", po_name)
        pr = frappe.new_doc("Purchase Receipt")
        _set(pr, "company", po.company)
        _set(pr, "supplier", po.supplier)
        _set(pr, "posting_date", today())
        _set(pr, "set_warehouse", getattr(po, "set_warehouse", None))
        _set(pr, "currency", getattr(po, "currency", None))
        _set(pr, "buying_price_list", getattr(po, "buying_price_list", None))
        _set(pr, "price_list_currency", getattr(po, "price_list_currency", None))
        _set(pr, "conversion_rate", getattr(po, "conversion_rate", 1))
        for po_item in po.get("items", []):
            pending_qty = float(getattr(po_item, "qty", 0) or 0) - float(getattr(po_item, "received_qty", 0) or 0)
            if pending_qty <= 0:
                continue
            row = pr.append("items", {})
            _set(row, "item_code", po_item.item_code)
            _set(row, "qty", pending_qty)
            _set(row, "uom", getattr(po_item, "uom", None))
            _set(row, "stock_uom", getattr(po_item, "stock_uom", None))
            _set(row, "conversion_factor", getattr(po_item, "conversion_factor", 1))
            _set(row, "rate", getattr(po_item, "rate", None))
            _set(row, "warehouse", getattr(po_item, "warehouse", None) or getattr(po, "set_warehouse", None))
            _set(row, "purchase_order", po.name)
            _set(row, "purchase_order_item", po_item.name)
            _set(row, "material_request", getattr(po_item, "material_request", None))
            _set(row, "material_request_item", getattr(po_item, "material_request_item", None))
    _set(pr, "posting_date", today())
    _set(pr, "title", title)
    _set(pr, "remarks", marker)
    if hasattr(pr, "set_missing_values"):
        pr.set_missing_values()
    if hasattr(pr, "calculate_taxes_and_totals"):
        pr.calculate_taxes_and_totals()
    pr.insert(ignore_permissions=True)
    pr.submit()
    return pr.name


def _create_purchase_invoice_from_receipt(pr_name, marker, title):
    try:
        from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice

        pi = make_purchase_invoice(pr_name)
    except ImportError:
        pr = frappe.get_doc("Purchase Receipt", pr_name)
        pi = frappe.new_doc("Purchase Invoice")
        _set(pi, "company", pr.company)
        _set(pi, "supplier", pr.supplier)
        _set(pi, "posting_date", today())
        _set(pi, "currency", getattr(pr, "currency", None))
        _set(pi, "buying_price_list", getattr(pr, "buying_price_list", None))
        _set(pi, "price_list_currency", getattr(pr, "price_list_currency", None))
        _set(pi, "conversion_rate", getattr(pr, "conversion_rate", 1))
        for pr_item in pr.get("items", []):
            row = pi.append("items", {})
            _set(row, "item_code", pr_item.item_code)
            _set(row, "qty", getattr(pr_item, "qty", None))
            _set(row, "uom", getattr(pr_item, "uom", None))
            _set(row, "rate", getattr(pr_item, "rate", None))
            _set(row, "warehouse", getattr(pr_item, "warehouse", None))
            _set(row, "purchase_receipt", pr.name)
            _set(row, "pr_detail", pr_item.name)
            _set(row, "purchase_order", getattr(pr_item, "purchase_order", None))
            _set(row, "purchase_order_item", getattr(pr_item, "purchase_order_item", None))
    _set(pi, "title", title)
    _set(pi, "remarks", marker)
    if hasattr(pi, "set_missing_values"):
        pi.set_missing_values()
    if hasattr(pi, "calculate_taxes_and_totals"):
        pi.calculate_taxes_and_totals()
    pi.insert(ignore_permissions=True)
    pi.submit()
    return pi.name


def _create_cycle_request(company, brand, cost_center, outlet, selection, marker):
    title = "%s | %s | %s | Finished Item Request" % (marker, brand, selection["menu_name"])
    existing = _get_demo_doc("Material Request", marker, title=title)
    if existing:
        return frappe.get_doc("Material Request", existing)

    mr = frappe.new_doc("Material Request")
    _set(mr, "company", company)
    _set(mr, "purpose", "Material Transfer")
    _set(mr, "material_request_type", "Material Transfer")
    _set(mr, "transaction_date", today())
    _set(mr, "schedule_date", today())
    _set(mr, "title", title)
    _set(mr, "remarks", marker)
    _set(mr, "cost_center", cost_center)
    row = mr.append("items", {})
    _set(row, "item_code", selection["menu_code"])
    _set(row, "qty", selection["portions"])
    _set(row, "warehouse", outlet)
    _set(row, "target_warehouse", outlet)
    _set(row, "schedule_date", today())
    _set(row, "cost_center", cost_center)
    mr.insert(ignore_permissions=True)
    mr.submit()
    return mr


def _create_transfer(company, source, target, cost_center, lines, marker, material_request=None):
    entry = frappe.new_doc("Stock Entry")
    _set(entry, "company", company)
    _set(entry, "purpose", "Material Transfer")
    _set(entry, "stock_entry_type", "Material Transfer")
    _set(entry, "from_warehouse", source)
    _set(entry, "to_warehouse", target)
    _set(entry, "posting_date", today())
    _set(entry, "remarks", marker)
    _set(entry, "cost_center", cost_center)
    for item_code, qty, request_row in lines:
        row = entry.append("items", {})
        _set(row, "item_code", item_code)
        _set(row, "qty", qty)
        _set(row, "s_warehouse", source)
        _set(row, "t_warehouse", target)
        _set(row, "cost_center", cost_center)
        if material_request:
            _set(row, "material_request", material_request.name)
        if request_row:
            _set(row, "material_request_item", request_row.name)
    entry.insert(ignore_permissions=True)
    entry.submit()
    return entry


def _create_manufacture(company, cost_center, kitchen, selection, marker):
    item_code = selection["menu_code"]
    bom = frappe.db.get_value("BOM", {"item": item_code, "is_active": 1, "is_default": 1}, "name")
    if not bom:
        frappe.throw("No active default BOM found for %s." % item_code)
    entry = frappe.new_doc("Stock Entry")
    _set(entry, "company", company)
    _set(entry, "purpose", "Manufacture")
    _set(entry, "stock_entry_type", "Manufacture")
    _set(entry, "from_bom", 1)
    _set(entry, "bom_no", bom)
    _set(entry, "fg_completed_qty", selection["portions"])
    _set(entry, "to_warehouse", kitchen)
    _set(entry, "posting_date", today())
    _set(entry, "remarks", marker)
    _set(entry, "cost_center", cost_center)
    if hasattr(entry, "get_items"):
        entry.get_items()
    finished = []
    for row in entry.get("items", []):
        _set(row, "cost_center", cost_center)
        if row.item_code == item_code or getattr(row, "is_finished_item", 0):
            _set(row, "item_code", item_code)
            _set(row, "qty", selection["portions"])
            _set(row, "is_finished_item", 1)
            _set(row, "t_warehouse", kitchen)
            finished.append(row)
        else:
            _set(row, "s_warehouse", kitchen)
    if not finished:
        for ingredient_code, qty in selection["components"]:
            row = next((r for r in entry.get("items", []) if r.item_code == ingredient_code), None)
            if not row:
                row = entry.append("items", {})
                _set(row, "item_code", ingredient_code)
                _set(row, "qty", qty)
            _set(row, "s_warehouse", kitchen)
            _set(row, "cost_center", cost_center)
        row = entry.append("items", {})
        _set(row, "item_code", item_code)
        _set(row, "qty", selection["portions"])
        _set(row, "is_finished_item", 1)
        _set(row, "t_warehouse", kitchen)
        _set(row, "cost_center", cost_center)
    entry.insert(ignore_permissions=True)
    entry.submit()
    return entry


def _create_delivery_invoice(company, customer, cost_center, warehouse, price_list, selection, marker):
    dn = frappe.new_doc("Delivery Note")
    _set(dn, "company", company)
    _set(dn, "customer", customer)
    _set(dn, "posting_date", today())
    _set(dn, "set_warehouse", warehouse)
    _set(dn, "selling_price_list", price_list)
    _set(dn, "currency", "BDT")
    _set(dn, "cost_center", cost_center)
    _set(dn, "remarks", marker)
    row = dn.append("items", {})
    _set(row, "item_code", selection["menu_code"])
    _set(row, "qty", selection["portions"])
    _set(row, "uom", "Nos")
    _set(row, "warehouse", warehouse)
    _set(row, "rate", selection["price"])
    _set(row, "cost_center", cost_center)
    if hasattr(dn, "set_missing_values"):
        dn.set_missing_values()
    if hasattr(dn, "calculate_taxes_and_totals"):
        dn.calculate_taxes_and_totals()
    dn.insert(ignore_permissions=True)
    dn.submit()

    # Standard mapper keeps the Sales Invoice linked to its Delivery Note and
    # avoids deducting the same menu stock twice.
    try:
        from erpnext.stock.doctype.delivery_note.mapper import make_sales_invoice
    except ImportError:
        from erpnext.stock.doctype.delivery_note.delivery_note import make_sales_invoice

    invoice = make_sales_invoice(dn.name)
    _set(invoice, "remarks", marker)
    _set(invoice, "cost_center", cost_center)
    for item in invoice.get("items", []):
        _set(item, "cost_center", cost_center)
    if hasattr(invoice, "set_missing_values"):
        invoice.set_missing_values()
    if hasattr(invoice, "calculate_taxes_and_totals"):
        invoice.calculate_taxes_and_totals()
    invoice.insert(ignore_permissions=True)
    invoice.submit()
    return dn, invoice


def create_full_demo(cycles=100, dry_run=True, confirm_demo_site=False, company=None):
    """Create repeatable full-cycle transactions; dry-run is the default.

    Each cycle creates a brand-tagged finished-item Material Request, internal
    raw material transfer, BOM-based Manufacture Stock Entry, finished-product
    transfer to the branch outlet, Delivery Note and linked Sales Invoice. One
    Purchase MR -> PO -> PR -> PI chain supplies a 10% buffer above the selected
    cycles' recipe demand.
    """
    cycles = int(cycles)
    if cycles < 1 or cycles > 500:
        frappe.throw("cycles must be between 1 and 500.")
    company = _company_for_demo(company)
    if dry_run:
        setup_plan = create_demo_setup(dry_run=True, company=company)
        selections, demand = _lifecycle_selections(cycles)
        return {
            "company": company,
            "cycles_requested": cycles,
            "expected_total_lifecycle_documents": cycles * 6 + 4,
            "expected_documents": {
                "Material Request": cycles + 1,
                "Purchase Order": 1,
                "Purchase Receipt": 1,
                "Purchase Invoice": 1,
                "Stock Entry": cycles * 3,
                "Delivery Note": cycles,
                "Sales Invoice": cycles,
            },
            "unique_menu_items_used": len(set(s["menu_code"] for s in selections)),
            "raw_material_types_used": len(demand),
            "setup_preview": setup_plan,
            "writes": False,
        }
    if not confirm_demo_site:
        frappe.throw("Refusing to create hundreds of submitted documents without confirm_demo_site=True. Use a dedicated demo site.")

    setup = create_demo_setup(dry_run=False, confirm_demo_site=True, company=company)
    _abbr, warehouses, cost_centers, _groups, _ingredients = _ensure_master_records(company)
    selections, demand = _lifecycle_selections(cycles)
    procurement = _create_procurement_cycle(company, setup["supplier"], warehouses["central_store"], demand)
    customer = _ensure_customer()
    price_list = "DEMO - Restaurant BDT"

    counts = {"Material Request": 0, "Stock Entry": 0, "Delivery Note": 0, "Sales Invoice": 0}
    completed = 0
    skipped = 0
    examples = []
    for selection in selections:
        index = selection["index"]
        brand = selection["brand"]
        marker = "%s CYCLE %03d" % (DEMO_PREFIX, index)
        if _get_demo_doc("Sales Invoice", marker, docstatus=1):
            skipped += 1
            continue
        finished_request_title = "%s | %s | %s | Finished Item Request" % (marker, brand, selection["menu_name"])
        partial = _get_demo_doc("Material Request", marker, title=finished_request_title)
        if partial:
            frappe.throw("Cycle %03d has a requisition but no submitted invoice (%s). Inspect it before rerunning." % (index, partial))

        cost_center = cost_centers[brand]
        kitchen = warehouses["central_kitchen"]
        outlet = warehouses[brand]
        request = _create_cycle_request(company, brand, cost_center, outlet, selection, marker)
        counts["Material Request"] += 1
        raw_lines = [(code, qty, None) for code, qty in selection["components"]]
        raw_transfer = _create_transfer(
            company, warehouses["central_store"], kitchen, cost_center, raw_lines, marker + " raw transfer"
        )
        counts["Stock Entry"] += 1
        manufacture = _create_manufacture(company, cost_center, kitchen, selection, marker + " BOM consumption")
        counts["Stock Entry"] += 1
        finished_transfer = _create_transfer(
            company,
            kitchen,
            outlet,
            cost_center,
            [(selection["menu_code"], selection["portions"], request.items[0] if request.items else None)],
            marker + " finished goods transfer",
            request,
        )
        counts["Stock Entry"] += 1
        dn, invoice = _create_delivery_invoice(
            company, customer, cost_center, outlet, price_list, selection, marker
        )
        counts["Delivery Note"] += 1
        counts["Sales Invoice"] += 1
        completed += 1
        if len(examples) < 3:
            examples.append(
                {
                    "cycle": index,
                    "brand": brand,
                    "material_request": request.name,
                    "raw_transfer": raw_transfer.name,
                    "manufacture": manufacture.name,
                    "finished_transfer": finished_transfer.name,
                    "delivery_note": dn.name,
                    "sales_invoice": invoice.name,
                }
            )

    return {
        "company": company,
        "cycles_requested": cycles,
        "cycles_created": completed,
        "cycles_skipped_as_already_complete": skipped,
        "procurement_chain": procurement,
        "created_documents": counts,
        "first_created_cycles": examples,
        "note": "Invoices are submitted and receivable remains open. Stock transfers, recipe consumption and sales accounting are posted; no cash Payment Entries are created.",
    }


def _hard_delete_doc(doctype, name):
    """Remove one demo document even when ERPNext blocks normal cancellation."""
    if not frappe.db.exists(doctype, name):
        return False

    # Try Frappe's delete first so hooks and file cleanup still run when
    # possible. Submitted documents may still be blocked, so the SQL fallback
    # is deliberately limited to records already selected as demo-owned.
    try:
        frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)
        return True
    except Exception:
        meta = frappe.get_meta(doctype)
        for table_field in meta.get_table_fields():
            child_doctype = table_field.options
            if child_doctype and frappe.db.exists("DocType", child_doctype):
                frappe.db.sql(
                    "delete from `tab%s` where parent = %%s" % child_doctype.replace("`", ""),
                    name,
                )
        frappe.db.sql(
            "delete from `tab%s` where name = %%s" % doctype.replace("`", ""),
            name,
        )
        return True


def _hard_delete_demo_ledgers(plan):
    """Delete ledger rows belonging only to this demo's selected records."""
    voucher_pairs = []
    for doctype, names in plan.items():
        for name in names:
            voucher_pairs.append((doctype, name))

    for ledger_doctype in ("Stock Ledger Entry", "GL Entry", "Payment Ledger Entry"):
        if not frappe.db.exists("DocType", ledger_doctype):
            continue
        meta = frappe.get_meta(ledger_doctype)
        if _has_field(ledger_doctype, "voucher_type") and _has_field(ledger_doctype, "voucher_no"):
            for voucher_type, voucher_no in voucher_pairs:
                frappe.db.delete(
                    ledger_doctype,
                    {"voucher_type": voucher_type, "voucher_no": voucher_no},
                )
        if ledger_doctype == "Stock Ledger Entry":
            conditions = []
            if _has_field(ledger_doctype, "item_code"):
                conditions.append("item_code like 'BDREST-%%'")
            if _has_field(ledger_doctype, "warehouse"):
                conditions.append("warehouse like 'DEMO -%%'")
            if conditions:
                frappe.db.sql(
                    "delete from `tabStock Ledger Entry` where %s" % " or ".join(conditions)
                )


def clear_demo_data(dry_run=True, confirm_demo_site=False, hard_delete=False):
    """Cancel/delete records created by this demo seeder.

    This targets only demo-prefixed records and BDREST items. Use on a dedicated
    demo site; cancelled/deleted stock and accounting documents affect ledgers.
    Set hard_delete=True only when the demo site must be completely reset.
    """
    if not dry_run and not confirm_demo_site:
        frappe.throw("Refusing to clear demo data without confirm_demo_site=True. Use a dedicated demo site.")

    submitted_order = [
        "Repost Item Valuation",
        "Sales Invoice",
        "Delivery Note",
        "Stock Entry",
        "Purchase Invoice",
        "Purchase Receipt",
        "Purchase Order",
        "Material Request",
        "Stock Reconciliation",
        "BOM",
    ]
    draft_order = submitted_order + [
        "POS Profile",
        "Item Price",
        "File",
        "Bin",
        "Item",
        "Price List",
        "Customer",
        "Supplier",
        "Warehouse",
        "Cost Center",
        "Item Group",
    ]

    plan = {}
    for doctype in draft_order:
        if frappe.db.exists("DocType", doctype):
            names = _demo_doc_names(doctype)
            if doctype == "Warehouse":
                # Delete outlet/child warehouses before their parent nodes.
                names.sort(key=lambda name: frappe.db.get_value("Warehouse", name, "lft") or 0, reverse=True)
            if names:
                plan[doctype] = names
    if dry_run:
        return {"writes": False, "records": {doctype: len(names) for doctype, names in plan.items()}, "names": plan}

    result = {"cancelled": {}, "deleted": {}, "disabled": {}, "hard_deleted": {}, "pending_retry": {}, "skipped": {}}
    if hard_delete:
        _hard_delete_demo_ledgers(plan)
    cancel_failed = set()
    for doctype in submitted_order:
        for name in plan.get(doctype, []):
            try:
                if hard_delete:
                    continue
                doc = frappe.get_doc(doctype, name)
                if getattr(doc, "docstatus", 0) == 1:
                    doc.cancel()
                    result["cancelled"].setdefault(doctype, []).append(name)
            except Exception as exc:
                cancel_failed.add((doctype, name))
                message = str(exc)
                if doctype == "Repost Item Valuation" and "try again in an hour" in message.lower():
                    result["pending_retry"].setdefault(doctype, []).append("%s: %s" % (name, message))
                else:
                    result["skipped"].setdefault(doctype, []).append("%s: %s" % (name, message))

    for doctype in draft_order:
        for name in plan.get(doctype, []):
            try:
                if frappe.db.exists(doctype, name):
                    if hard_delete:
                        if _hard_delete_doc(doctype, name):
                            result["hard_deleted"].setdefault(doctype, []).append(name)
                        continue
                    if (doctype, name) in cancel_failed and (frappe.db.get_value(doctype, name, "docstatus") or 0) == 1:
                        continue
                    frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)
                    result["deleted"].setdefault(doctype, []).append(name)
            except Exception as exc:
                if _disable_demo_doc(doctype, name):
                    result["disabled"].setdefault(doctype, []).append(name)
                else:
                    result["skipped"].setdefault(doctype, []).append("%s: %s" % (name, exc))
    frappe.db.commit()
    return {
        "writes": True,
        "cancelled": {doctype: len(names) for doctype, names in result["cancelled"].items()},
        "deleted": {doctype: len(names) for doctype, names in result["deleted"].items()},
        "hard_deleted": {doctype: len(names) for doctype, names in result["hard_deleted"].items()},
        "disabled": {doctype: len(names) for doctype, names in result["disabled"].items()},
        "pending_retry": result["pending_retry"],
        "skipped": result["skipped"],
    }
