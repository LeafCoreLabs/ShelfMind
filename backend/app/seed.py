"""Seed demo stores, ML data, AI recommendations, alerts, and users."""

import csv
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import func, select

from app.core.security import hash_password
from app.db.session import SyncSessionLocal
from app.models.admin import AlertEvent, AlertRule, AuditLog, ForecastAccuracySnapshot
from app.models.commerce import Customer, Invoice, InvoiceLine, Payment, PurchaseLine, PurchaseOrder, Vendor, hsn_for_category, split_gst
from app.models.store import ExternalSignal, Product, Recommendation, Store, Transaction
from app.models.user import User
from app.services.collaborative import generate_peer_benchmarks
from app.services.forecast import run_all_forecasts
from app.tasks.signal_tasks import _save_signals

PRODUCTS = [
    ("SKU-UMB-001", "Compact Umbrella", "Rain Gear", 299),
    ("SKU-BEV-001", "Cold Beverage 500ml", "Beverages", 40),
    ("SKU-BEV-002", "Energy Drink 250ml", "Beverages", 55),
    ("SKU-NOD-001", "Instant Noodles Pack", "Snacks", 25),
    ("SKU-SNK-001", "Potato Chips 50g", "Snacks", 20),
    ("SKU-DAI-001", "Fresh Milk 1L", "Dairy", 60),
    ("SKU-BRD-001", "Whole Wheat Bread", "Bakery", 45),
    ("SKU-FRT-001", "Seasonal Fruit Pack", "Produce", 80),
]

DEMO_STORES = [
    ("ShelfMind Demo Store", "Mumbai, IN", 19.0760, 72.8777, "owner@shelfmind.com", "Demo Store Owner", 42),
    ("ShelfMind Pune Central", "Pune, IN", 18.5204, 73.8567, "owner.pune@shelfmind.com", "Pune Store Owner", 17),
    ("ShelfMind Delhi Market", "Delhi, IN", 28.6139, 77.2090, "owner.delhi@shelfmind.com", "Delhi Store Owner", 88),
    ("ShelfMind Bangalore Hub", "Bangalore, IN", 12.9716, 77.5946, "owner.blr@shelfmind.com", "Bangalore Store Owner", 55),
]

HOURLY_WEIGHTS = {
    "Beverages": {10: 1.2, 11: 1.5, 12: 2.0, 13: 1.8, 14: 1.3, 15: 1.4, 16: 1.6, 17: 2.2, 18: 2.5, 19: 2.0, 20: 1.5},
    "Snacks": {11: 1.3, 12: 1.8, 13: 1.5, 17: 2.0, 18: 2.3, 19: 2.1, 20: 1.7, 21: 1.4},
    "Rain Gear": {7: 1.5, 8: 2.0, 9: 1.8, 17: 1.6, 18: 2.2},
    "Dairy": {7: 1.8, 8: 2.5, 9: 1.5, 18: 1.6, 19: 1.4},
}


def _ensure_store(session, name: str, location: str, lat: float, lon: float) -> Store:
    store = session.execute(select(Store).where(Store.name == name)).scalar_one_or_none()
    if store:
        if not store.preferences or not store.preferences.get("gstin"):
            city = location.split(",")[0].strip() if location else "IN"
            store.preferences = {
                **(store.preferences or {}),
                "gstin": f"27AABCU{store.id:04d}A1Z5",
                "place_of_supply": city,
            }
            session.commit()
        return store
    store = Store(name=name, location=location, lat=lat, lon=lon, salary_cycle_day=1, business_type="Retail")
    session.add(store)
    session.commit()
    session.refresh(store)
    city = location.split(",")[0].strip() if location else "IN"
    store.preferences = {
        "gstin": f"27AABCU{store.id:04d}A1Z5",
        "place_of_supply": city,
    }
    session.commit()
    return store


def _ensure_products(session, store_id: int) -> list[Product]:
    existing = session.execute(select(Product).where(Product.store_id == store_id)).scalars().all()
    if existing:
        _apply_product_commerce(session, existing)
        return list(existing)
    products: list[Product] = []
    rng = random.Random(store_id)
    for sku, pname, category, list_price in PRODUCTS:
        cost = round(list_price * 0.65, 2)
        stock = rng.randint(15, 120)
        reorder = max(5, int(stock * 0.15))
        p = Product(
            store_id=store_id,
            sku=sku,
            name=pname,
            category=category,
            list_price=list_price,
            cost_price=cost,
            stock_on_hand=stock,
            reorder_level=reorder,
        )
        session.add(p)
        products.append(p)
    session.commit()
    return list(session.execute(select(Product).where(Product.store_id == store_id)).scalars().all())


def _apply_product_commerce(session, products: list[Product]) -> None:
    rng = random.Random(products[0].store_id if products else 1)
    changed = False
    for product in products:
        list_price = next((p[3] for p in PRODUCTS if p[0] == product.sku), product.list_price or 50)
        if not product.list_price:
            product.list_price = list_price
            changed = True
        if not product.cost_price:
            product.cost_price = round(list_price * 0.65, 2)
            changed = True
        if product.stock_on_hand == 0 and product.reorder_level == 5:
            product.stock_on_hand = rng.randint(15, 120)
            product.reorder_level = max(5, int(product.stock_on_hand * 0.15))
            changed = True
    if changed:
        session.commit()


def _generate_transactions(session, store_id: int, products: list[Product], seed: int) -> int:
    if session.execute(select(func.count(Transaction.id)).where(Transaction.store_id == store_id)).scalar():
        return 0

    count = 0
    base = datetime.now(timezone.utc) - timedelta(days=90)
    rng = random.Random(seed)

    for day in range(90):
        current = base + timedelta(days=day)
        is_weekend = current.weekday() >= 5
        for product in products:
            base_qty = rng.randint(2, 8)
            if product.category == "Rain Gear" and day > 60:
                base_qty = int(base_qty * 1.5)
            if product.category == "Beverages" and is_weekend:
                base_qty = int(base_qty * 1.8)
            if product.category == "Snacks" and day > 75:
                base_qty = max(1, int(base_qty * 0.6))

            weights = HOURLY_WEIGHTS.get(product.category, {12: 1.5, 18: 2.0})
            for hour, weight in weights.items():
                qty = max(1, int(base_qty * weight * rng.uniform(0.7, 1.3)))
                sold_at = current.replace(hour=hour, minute=rng.randint(0, 59), second=0, microsecond=0)
                session.add(
                    Transaction(
                        store_id=store_id,
                        product_id=product.id,
                        quantity=qty,
                        unit_price=next(p[3] for p in PRODUCTS if p[0] == product.sku),
                        sold_at=sold_at,
                    )
                )
                count += 1
    session.commit()
    return count


def _import_csv_for_store(session, store_id: int) -> int:
    if session.execute(select(func.count(Transaction.id)).where(Transaction.store_id == store_id)).scalar():
        return 0

    csv_path = Path("/app/data/sample_pos.csv")
    if not csv_path.exists():
        csv_path = Path(__file__).resolve().parents[2] / "data" / "sample_pos.csv"
    if not csv_path.exists():
        return 0

    sku_cache: dict[str, Product] = {}
    for p in session.execute(select(Product).where(Product.store_id == store_id)).scalars().all():
        sku_cache[p.sku] = p

    count = 0
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sku = row["sku"].strip()
            product = sku_cache.get(sku)
            if not product:
                product = Product(store_id=store_id, sku=sku, name=row["product_name"], category=row["category"])
                session.add(product)
                session.flush()
                sku_cache[sku] = product
            sold_at = datetime.fromisoformat(row["sold_at"].replace("Z", "+00:00"))
            session.add(
                Transaction(
                    store_id=store_id,
                    product_id=product.id,
                    quantity=int(row["quantity"]),
                    unit_price=float(row["unit_price"]),
                    sold_at=sold_at,
                )
            )
            count += 1
    session.commit()
    return count


def _seed_users(session) -> None:
    if session.execute(select(User).where(User.email == "admin@shelfmind.com")).scalar_one_or_none():
        pass
    else:
        session.add(
            User(
                email="admin@shelfmind.com",
                hashed_password=hash_password("admin123"),
                full_name="Platform Admin",
                role="admin",
                store_id=None,
            )
        )

    for name, _, _, _, email, full_name, _ in DEMO_STORES:
        store = session.execute(select(Store).where(Store.name == name)).scalar_one_or_none()
        if not store:
            continue
        if session.execute(select(User).where(User.email == email)).scalar_one_or_none():
            continue
        session.add(
            User(
                email=email,
                hashed_password=hash_password("user123"),
                full_name=full_name,
                role="user",
                store_id=store.id,
            )
        )
    session.commit()


def _seed_recommendations(session) -> None:
    if session.execute(select(func.count(Recommendation.id))).scalar():
        return

    stores = session.execute(select(Store).limit(4)).scalars().all()
    samples = [
        ("What should I stock this weekend?", "SKU-UMB-001", "Compact Umbrella", "increase", 340, "Monsoon signal — umbrella demand spike", 0.91),
        ("Which beverages need restocking?", "SKU-BEV-001", "Cold Beverage 500ml", "increase", 100, "Heatwave forecast — double cold drinks", 0.87),
        ("What to cut back on?", "SKU-NOD-001", "Instant Noodles Pack", "decrease", -35, "College hostel closed — lower snack demand", 0.84),
        ("Weekend stocking plan", "SKU-BEV-002", "Energy Drink 250ml", "increase", 65, "Weekend footfall + peer benchmark lift", 0.82),
    ]
    for i, store in enumerate(stores):
        q, sku, pname, action, delta, rationale, conf = samples[i % len(samples)]
        session.add(
            Recommendation(
                store_id=store.id,
                query=q,
                sku=sku,
                product_name=pname,
                action=action,
                delta_pct=delta,
                rationale=rationale,
                confidence=conf,
            )
        )
    session.add(
        Recommendation(
            store_id=stores[0].id if stores else 1,
            query="[ADMIN] Which stores risk stockout on beverages?",
            sku="PLATFORM",
            product_name="Admin Copilot",
            action="insight",
            delta_pct=0,
            rationale="3 stores show elevated beverage demand driven by heatwave signals across the network.",
            confidence=0.88,
        )
    )
    session.commit()


def _seed_customers(session) -> None:
    if session.execute(select(func.count(Customer.id))).scalar():
        return

    segments = ["Regular", "VIP", "New"]
    first_names = ["Aarav", "Priya", "Rohan", "Ananya", "Vikram", "Neha", "Karan", "Isha", "Arjun", "Meera"]
    stores = session.execute(select(Store)).scalars().all()
    for store in stores:
        rng = random.Random(store.id * 31)
        for i in range(20):
            fname = rng.choice(first_names)
            lname = rng.choice(["Sharma", "Patel", "Reddy", "Khan", "Das", "Nair"])
            name = f"{fname} {lname}"
            session.add(
                Customer(
                    store_id=store.id,
                    name=name,
                    email=f"{fname.lower()}.{lname.lower()}{i}@example.com",
                    phone=f"+91{rng.randint(7000000000, 9999999999)}",
                    segment=rng.choice(segments),
                    total_spent=0,
                )
            )
    session.commit()


def _link_transactions_to_customers(session) -> None:
    stores = session.execute(select(Store)).scalars().all()
    for store in stores:
        customers = session.execute(select(Customer).where(Customer.store_id == store.id)).scalars().all()
        if not customers:
            continue
        txns = (
            session.execute(
                select(Transaction)
                .where(Transaction.store_id == store.id, Transaction.customer_id.is_(None))
                .limit(500)
            )
            .scalars()
            .all()
        )
        if not txns:
            continue
        rng = random.Random(store.id + 7)
        for txn in txns:
            customer = rng.choice(customers)
            txn.customer_id = customer.id
            customer.total_spent += txn.quantity * txn.unit_price
            if not customer.last_purchase_at or txn.sold_at > customer.last_purchase_at:
                customer.last_purchase_at = txn.sold_at
    session.commit()


def _seed_invoices(session) -> None:
    if session.execute(select(func.count(Invoice.id))).scalar():
        return

    stores = session.execute(select(Store)).scalars().all()
    for store in stores:
        customers = session.execute(select(Customer).where(Customer.store_id == store.id)).scalars().all()
        products = session.execute(select(Product).where(Product.store_id == store.id)).scalars().all()
        if not customers or not products:
            continue
        rng = random.Random(store.id * 13)
        for i in range(8):
            customer = rng.choice(customers)
            product = rng.choice(products)
            qty = rng.randint(1, 5)
            subtotal = round(qty * product.list_price, 2)
            tax, cgst, sgst, igst = split_gst(subtotal)
            total = subtotal + tax
            status = rng.choice(["paid", "sent", "overdue"])
            city = store.location.split(",")[0].strip() if store.location else "India"
            inv = Invoice(
                store_id=store.id,
                customer_id=customer.id,
                invoice_number=f"INV-{store.id}-{i + 1:04d}",
                status=status,
                subtotal=subtotal,
                tax_amount=tax,
                cgst_amount=cgst,
                sgst_amount=sgst,
                igst_amount=igst,
                place_of_supply=city,
                total=total,
                issued_at=datetime.now(timezone.utc) - timedelta(days=rng.randint(1, 45)),
                due_at=datetime.now(timezone.utc) + timedelta(days=7),
            )
            session.add(inv)
            session.flush()
            session.add(
                InvoiceLine(
                    invoice_id=inv.id,
                    product_id=product.id,
                    description=product.name,
                    hsn_code=hsn_for_category(product.category),
                    quantity=qty,
                    unit_price=product.list_price,
                    line_total=subtotal,
                )
            )
            if status == "paid":
                session.add(
                    Payment(
                        invoice_id=inv.id,
                        amount=total,
                        method=rng.choice(["cash", "upi", "card"]),
                        reference=f"TXN{rng.randint(100000, 999999)}",
                    )
                )
            elif status == "sent":
                session.add(
                    Payment(
                        invoice_id=inv.id,
                        amount=round(total * 0.5, 2),
                        method="upi",
                        reference=f"TXN{rng.randint(100000, 999999)}",
                    )
                )
    session.commit()


def _seed_vendors_purchases(session) -> None:
    if session.execute(select(func.count(Vendor.id))).scalar():
        return

    vendor_names = [
        ("Fresh Foods Wholesale", "+919876543210", "27AABCF1234A1Z5"),
        ("Metro Beverages Supply", "+919876543211", "27AABCM5678B2Z6"),
        ("City Snacks Distributors", "+919876543212", "27AABCS9012C3Z7"),
    ]
    stores = session.execute(select(Store)).scalars().all()
    for store in stores:
        products = session.execute(select(Product).where(Product.store_id == store.id)).scalars().all()
        if not products:
            continue
        rng = random.Random(store.id * 17)
        vendors: list[Vendor] = []
        for vname, phone, gstin in vendor_names:
            v = Vendor(store_id=store.id, name=vname, phone=phone, gstin=gstin, email=f"orders@{vname.split()[0].lower()}.in")
            session.add(v)
            vendors.append(v)
        session.flush()

        for po_idx in range(2):
            vendor = vendors[po_idx % len(vendors)]
            picked = rng.sample(products, min(3, len(products)))
            subtotal = 0.0
            lines_data: list[tuple[Product, int, float, float]] = []
            for product in picked:
                qty = rng.randint(10, 40)
                unit_cost = product.cost_price
                line_total = round(qty * unit_cost, 2)
                subtotal += line_total
                lines_data.append((product, qty, unit_cost, line_total))
            tax = round(subtotal * 0.18, 2)
            total = round(subtotal + tax, 2)
            status = "received" if po_idx == 0 else "ordered"
            po = PurchaseOrder(
                store_id=store.id,
                vendor_id=vendor.id,
                status=status,
                subtotal=subtotal,
                tax=tax,
                total=total,
                ordered_at=datetime.now(timezone.utc) - timedelta(days=rng.randint(3, 20)),
            )
            if status == "received":
                po.received_at = datetime.now(timezone.utc) - timedelta(days=rng.randint(1, 5))
            session.add(po)
            session.flush()
            for product, qty, unit_cost, line_total in lines_data:
                session.add(
                    PurchaseLine(
                        po_id=po.id,
                        product_id=product.id,
                        qty=qty,
                        unit_cost=unit_cost,
                        line_total=line_total,
                    )
                )
                if status == "received":
                    product.stock_on_hand += qty
    session.commit()


def _ensure_low_stock_demo(session) -> None:
    """Force a few SKUs below reorder level so Today/Stock pages show urgency."""
    stores = session.execute(select(Store)).scalars().all()
    for store in stores:
        products = list(session.execute(select(Product).where(Product.store_id == store.id)).scalars().all())
        if not products:
            continue
        rng = random.Random(store.id + 101)
        for p in rng.sample(products, min(3, len(products))):
            p.stock_on_hand = max(0, p.reorder_level - rng.randint(1, 4))
    session.commit()


def _boost_vip_sales(session) -> None:
    """Link recent sales to VIP regulars for believable purchase history."""
    stores = session.execute(select(Store)).scalars().all()
    for store in stores:
        vips = list(
            session.execute(select(Customer).where(Customer.store_id == store.id, Customer.segment == "VIP")).scalars().all()
        )
        if not vips:
            continue
        recent = (
            session.execute(
                select(Transaction)
                .where(Transaction.store_id == store.id)
                .order_by(Transaction.sold_at.desc())
                .limit(40)
            )
            .scalars()
            .all()
        )
        for i, txn in enumerate(recent):
            vip = vips[i % len(vips)]
            if txn.customer_id == vip.id:
                continue
            if txn.customer_id:
                old = session.get(Customer, txn.customer_id)
                if old:
                    old.total_spent = max(0, old.total_spent - txn.quantity * txn.unit_price)
            txn.customer_id = vip.id
            vip.total_spent += txn.quantity * txn.unit_price
            if not vip.last_purchase_at or txn.sold_at > vip.last_purchase_at:
                vip.last_purchase_at = txn.sold_at
    session.commit()


def _seed_store_alerts(session) -> None:
    """Add store-scoped alerts for all demo stores with city names."""
    stores = session.execute(select(Store)).scalars().all()
    if not stores:
        return
    rule = session.execute(select(AlertRule).limit(1)).scalar_one_or_none()
    if not rule:
        return
    per_store = {
        row[0]: row[1]
        for row in session.execute(
            select(AlertEvent.store_id, func.count(AlertEvent.id))
            .where(AlertEvent.store_id.isnot(None))
            .group_by(AlertEvent.store_id)
        ).all()
    }
    for store in stores:
        if per_store.get(store.id, 0) >= 2:
            continue
        city = store.location.split(",")[0].strip() if store.location else store.name
        templates = [
            ("warning", f"Low stock — {city} beverages", f"Cold drinks below reorder level; weekend footfall expected in {city}"),
            ("warning", f"VIP regular inactive — {city}", "Top customer has not visited in 14 days — consider a call"),
            ("critical", f"Monsoon spike — {city} rain gear", f"Umbrella demand 2.4× above forecast for {city} shops"),
        ]
        rng = random.Random(store.id)
        for severity, title, message in rng.sample(templates, 2):
            session.add(
                AlertEvent(rule_id=rule.id, severity=severity, title=title, message=message, store_id=store.id)
            )
    session.commit()


def _seed_alerts(session) -> None:
    if session.execute(select(func.count(AlertRule.id))).scalar():
        return

    rules = [
        ("Demand spike >200%", "demand_spike", 200.0),
        ("Forecast confidence <0.6", "low_confidence", 0.6),
        ("Store inactive 7 days", "store_inactive", 7.0),
    ]
    rule_objs = []
    for name, rtype, threshold in rules:
        r = AlertRule(name=name, rule_type=rtype, threshold=threshold)
        session.add(r)
        rule_objs.append(r)
    session.flush()

    stores = session.execute(select(Store).limit(3)).scalars().all()
    events = [
        (rule_objs[0].id, "warning", "Umbrella demand spike +340%", "Network-wide monsoon signal detected across 3 stores", stores[0].id if stores else None),
        (rule_objs[0].id, "critical", "Beverage surge in Pune", "Cold beverage sales 2.1x above Prophet forecast", stores[1].id if len(stores) > 1 else None),
        (rule_objs[1].id, "warning", "Low forecast confidence — Snacks", "MAPE exceeded 35% for instant noodles category", stores[0].id if stores else None),
    ]
    for rule_id, severity, title, message, store_id in events:
        session.add(AlertEvent(rule_id=rule_id, severity=severity, title=title, message=message, store_id=store_id))
    session.commit()


def _seed_audit(session) -> None:
    if session.execute(select(func.count(AuditLog.id))).scalar():
        return

    logs = [
        ("admin@shelfmind.com", "create", "store", {"name": "ShelfMind Pune Central"}),
        ("admin@shelfmind.com", "create", "user", {"email": "owner.pune@shelfmind.com"}),
        ("admin@shelfmind.com", "trigger", "job", {"job": "forecasts"}),
        ("admin@shelfmind.com", "trigger", "job", {"job": "signals"}),
    ]
    for actor, action, resource, detail in logs:
        session.add(AuditLog(actor_email=actor, action=action, resource=resource, detail=detail))
    session.commit()


def _seed_accuracy_snapshots(session) -> None:
    if session.execute(select(func.count(ForecastAccuracySnapshot.id))).scalar():
        return

    stores = session.execute(select(Store).limit(4)).scalars().all()
    today = date.today()
    for store in stores:
        for cat, mape, mae in [("all", 12.4, 2.1), ("Beverages", 9.8, 1.4), ("Rain Gear", 18.2, 3.2)]:
            session.add(
                ForecastAccuracySnapshot(
                    store_id=store.id,
                    category=cat,
                    mape=mape,
                    mae=mae,
                    sample_size=120,
                    snapshot_date=today,
                )
            )
    session.commit()


def seed() -> None:
    session = SyncSessionLocal()
    try:
        primary_store = None
        for i, (name, location, lat, lon, _email, _owner, seed_val) in enumerate(DEMO_STORES):
            store = _ensure_store(session, name, location, lat, lon)
            if i == 0:
                primary_store = store
            products = _ensure_products(session, store.id)
            if i == 0:
                imported = _import_csv_for_store(session, store.id)
                if not imported:
                    _generate_transactions(session, store.id, products, seed_val)
            else:
                _generate_transactions(session, store.id, products, seed_val)

        _save_signals()
        generate_peer_benchmarks(session)
        try:
            run_all_forecasts(session, top_n=40)
        except Exception as exc:
            print(f"Forecast seed warning: {exc}")

        _seed_users(session)
        _seed_recommendations(session)
        _seed_alerts(session)
        _seed_customers(session)
        _link_transactions_to_customers(session)
        _boost_vip_sales(session)
        _seed_invoices(session)
        _seed_vendors_purchases(session)
        _ensure_low_stock_demo(session)
        _seed_store_alerts(session)
        _seed_audit(session)
        _seed_accuracy_snapshots(session)
        print(f"Seed complete — {len(DEMO_STORES)} demo stores, commerce data, ML forecasts, signals, alerts, and AI history.")
    finally:
        session.close()


if __name__ == "__main__":
    seed()
