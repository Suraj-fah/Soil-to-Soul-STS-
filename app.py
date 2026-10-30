import math
import os
import sqlite3
from contextlib import contextmanager

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "local-demo-change-this")
DB_URL = os.getenv("DATABASE_URL", "").replace("postgres://", "postgresql://", 1)
USE_PG = DB_URL.startswith("postgresql://")

ORDER_STATUSES = ["Placed", "Confirmed", "Packed", "Out for delivery", "Delivered", "Cancelled"]
NEXT_STATUSES = {
    "Placed": {"Confirmed", "Cancelled"},
    "Confirmed": {"Packed", "Cancelled"},
    "Packed": {"Out for delivery", "Cancelled"},
    "Out for delivery": {"Delivered"},
    "Delivered": set(),
    "Cancelled": set(),
}


@contextmanager
def db():
    if USE_PG:
        import psycopg
        from psycopg.rows import dict_row

        conn = psycopg.connect(DB_URL, row_factory=dict_row)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        conn = sqlite3.connect(os.getenv("SQLITE_PATH", "farmroute.db"), timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 15000")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def query(sql):
    return sql.replace("?", "%s") if USE_PG else sql


def init_db():
    with db() as conn:
        cur = conn.cursor()
        id_column = "SERIAL PRIMARY KEY" if USE_PG else "INTEGER PRIMARY KEY AUTOINCREMENT"
        cur.execute(f"""CREATE TABLE IF NOT EXISTS products (
            id {id_column}, farmer TEXT NOT NULL, name TEXT NOT NULL,
            category TEXT NOT NULL, price REAL NOT NULL CHECK(price > 0),
            stock REAL NOT NULL CHECK(stock >= 0), unit TEXT NOT NULL,
            area TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        cur.execute(f"""CREATE TABLE IF NOT EXISTS orders (
            id {id_column}, buyer TEXT NOT NULL,
            product_id INTEGER NOT NULL REFERENCES products(id),
            quantity REAL NOT NULL CHECK(quantity > 0),
            delivery_area TEXT NOT NULL, delivery_window TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Placed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        cur.execute("SELECT COUNT(*) AS n FROM products")
        if cur.fetchone()["n"] == 0:
            samples = [
                ("Ravi Farms", "Tomatoes", "Vegetables", 28, 120, "kg", "MVP Colony"),
                ("Green Valley", "Spinach", "Leafy greens", 18, 70, "bunch", "MVP Colony"),
                ("Sita Organic Farm", "Bengal Gram", "Pulses", 92, 90, "kg", "Seethammadhara"),
                ("Coastal Growers", "Bananas", "Fruits", 45, 100, "dozen", "Gajuwaka"),
            ]
            for product in samples:
                cur.execute(
                    query("""INSERT INTO products
                    (farmer,name,category,price,stock,unit,area)
                    VALUES (?,?,?,?,?,?,?)"""),
                    product,
                )


def clean_text(value, field, max_length=100):
    if not isinstance(value, str):
        raise ValueError(f"{field} is required.")
    value = value.strip()
    if not value:
        raise ValueError(f"{field} is required.")
    if len(value) > max_length:
        raise ValueError(f"{field} must be {max_length} characters or fewer.")
    return value


def positive_number(value, field):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a valid number.")
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{field} must be greater than zero.")
    return number


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/api/health")
def health():
    try:
        with db() as conn:
            conn.execute("SELECT 1").fetchone()
        return jsonify(status="ok", database="postgresql" if USE_PG else "sqlite")
    except Exception:
        app.logger.exception("Health check failed")
        return jsonify(status="error", message="Database connection failed"), 503


@app.get("/api/products")
def products():
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM products ORDER BY created_at DESC, id DESC"
        ).fetchall()
        return jsonify([dict(row) for row in rows])


@app.post("/api/products")
def add_product():
    data = request.get_json(silent=True) or {}
    try:
        farmer = clean_text(data.get("farmer"), "Farmer / farm name")
        name = clean_text(data.get("name"), "Product name")
        category = clean_text(data.get("category"), "Category", 50)
        unit = clean_text(data.get("unit"), "Unit", 20)
        area = clean_text(data.get("area"), "Pickup area")
        price = positive_number(data.get("price"), "Price")
        stock = positive_number(data.get("stock"), "Stock")
    except ValueError as exc:
        return jsonify(error=str(exc)), 400

    with db() as conn:
        cur = conn.cursor()
        cur.execute(
            query("""INSERT INTO products
            (farmer,name,category,price,stock,unit,area)
            VALUES (?,?,?,?,?,?,?) RETURNING id"""),
            (farmer, name, category, price, stock, unit, area),
        )
        product_id = cur.fetchone()["id"] if USE_PG else cur.fetchone()[0]
    return jsonify(id=product_id, message="Product added successfully."), 201


@app.get("/api/orders")
def orders():
    with db() as conn:
        rows = conn.execute("""SELECT o.*, p.name AS product_name,
            p.farmer, p.unit, p.price FROM orders o
            JOIN products p ON p.id=o.product_id
            ORDER BY o.created_at DESC, o.id DESC""").fetchall()
        return jsonify([dict(row) for row in rows])


@app.post("/api/orders")
def add_order():
    data = request.get_json(silent=True) or {}
    try:
        product_id = int(data.get("product_id"))
        quantity = positive_number(data.get("quantity"), "Quantity")
        buyer = clean_text(data.get("buyer"), "Buyer / shop name")
        area = clean_text(data.get("delivery_area"), "Delivery area")
        window = clean_text(data.get("delivery_window"), "Delivery window")
    except (ValueError, TypeError) as exc:
        return jsonify(error=str(exc) or "Choose a product and valid quantity."), 400

    with db() as conn:
        cur = conn.cursor()
        # A conditional update makes stock reservation atomic: simultaneous buyers
        # cannot both purchase the same remaining units.
        cur.execute(
            query("UPDATE products SET stock=stock-? WHERE id=? AND stock>=?"),
            (quantity, product_id, quantity),
        )
        if cur.rowcount == 0:
            exists = conn.execute(
                query("SELECT id FROM products WHERE id=?"), (product_id,)
            ).fetchone()
            if not exists:
                return jsonify(error="Product not found."), 404
            available = conn.execute(
                query("SELECT stock FROM products WHERE id=?"), (product_id,)
            ).fetchone()["stock"]
            return jsonify(error=f"Only {available:g} available."), 400

        cur.execute(
            query("""INSERT INTO orders
            (buyer,product_id,quantity,delivery_area,delivery_window,status)
            VALUES (?,?,?,?,?,?) RETURNING id"""),
            (buyer, product_id, quantity, area, window, "Placed"),
        )
        order_id = cur.fetchone()["id"] if USE_PG else cur.fetchone()[0]
    return jsonify(id=order_id, message="Order placed and saved."), 201


@app.patch("/api/orders/<int:order_id>")
def update_order(order_id):
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    if new_status not in ORDER_STATUSES:
        return jsonify(error="Invalid order status."), 400

    with db() as conn:
        cur = conn.cursor()
        cur.execute(query("SELECT status, product_id, quantity FROM orders WHERE id=?"), (order_id,))
        order = cur.fetchone()
        if not order:
            return jsonify(error="Order not found."), 404

        old_status = order["status"]
        if new_status == old_status:
            return jsonify(message="Order status is unchanged.")
        if new_status not in NEXT_STATUSES.get(old_status, set()):
            return jsonify(error=f"Cannot change an order from {old_status} to {new_status}."), 409

        cur.execute(query("UPDATE orders SET status=? WHERE id=?"), (new_status, order_id))
        if new_status == "Cancelled":
            cur.execute(
                query("UPDATE products SET stock=stock+? WHERE id=?"),
                (order["quantity"], order["product_id"]),
            )

    return jsonify(message="Order status updated.", status=new_status)


@app.get("/api/delivery-batches")
def batches():
    with db() as conn:
        rows = conn.execute("""SELECT delivery_area, delivery_window,
            COUNT(*) AS order_count, SUM(quantity*products.price) AS order_value
            FROM orders JOIN products ON products.id=orders.product_id
            WHERE status NOT IN ('Delivered','Cancelled')
            GROUP BY delivery_area,delivery_window
            ORDER BY delivery_area,delivery_window""").fetchall()
        return jsonify([dict(row) for row in rows])



@app.patch("/api/products/<int:product_id>")
def edit_product(product_id):
    data = request.get_json(silent=True) or {}
    fields = {}
    try:
        for key, label, limit in [
            ("farmer", "Farmer / farm name", 100), ("name", "Product name", 100),
            ("category", "Category", 50), ("unit", "Unit", 20), ("area", "Pickup area", 100)
        ]:
            if key in data:
                fields[key] = clean_text(data[key], label, limit)
        if "price" in data:
            fields["price"] = positive_number(data["price"], "Price")
        if "stock" in data:
            value = float(data["stock"])
            if not math.isfinite(value) or value < 0:
                raise ValueError("Stock must be zero or greater.")
            fields["stock"] = value
    except (ValueError, TypeError) as exc:
        return jsonify(error=str(exc)), 400
    if not fields:
        return jsonify(error="No product fields supplied."), 400
    with db() as conn:
        cur = conn.cursor()
        cur.execute(query("SELECT id FROM products WHERE id=?"), (product_id,))
        if not cur.fetchone():
            return jsonify(error="Product not found."), 404
        assignments = ", ".join(f"{key}=?" for key in fields)
        cur.execute(query(f"UPDATE products SET {assignments} WHERE id=?"),
                    (*fields.values(), product_id))
    return jsonify(message="Product updated.")


@app.delete("/api/products/<int:product_id>")
def delete_product(product_id):
    with db() as conn:
        cur = conn.cursor()
        cur.execute(query("SELECT COUNT(*) AS n FROM products WHERE id=?"), (product_id,))
        if cur.fetchone()["n"] == 0:
            return jsonify(error="Product not found."), 404
        # Keep order history referentially intact. A product with any historical
        # order cannot be hard-deleted; farmers can set its stock to zero instead.
        cur.execute(query("SELECT COUNT(*) AS n FROM orders WHERE product_id=?"), (product_id,))
        if cur.fetchone()["n"]:
            return jsonify(error="This product has order history and cannot be removed. Set available quantity to zero to stop new orders."), 409
        cur.execute(query("DELETE FROM products WHERE id=?"), (product_id,))
    return jsonify(message="Product removed.")


@app.get("/api/admin/summary")
def admin_summary():
    with db() as conn:
        products_count = conn.execute("SELECT COUNT(*) AS n FROM products").fetchone()["n"]
        orders_count = conn.execute("SELECT COUNT(*) AS n FROM orders").fetchone()["n"]
        active_count = conn.execute("SELECT COUNT(*) AS n FROM orders WHERE status NOT IN ('Delivered','Cancelled')").fetchone()["n"]
        delivered_count = conn.execute("SELECT COUNT(*) AS n FROM orders WHERE status='Delivered'").fetchone()["n"]
        value = conn.execute("SELECT COALESCE(SUM(orders.quantity*products.price),0) AS n FROM orders JOIN products ON products.id=orders.product_id").fetchone()["n"]
        areas = conn.execute("""SELECT delivery_area, COUNT(*) AS orders
            FROM orders GROUP BY delivery_area ORDER BY orders DESC LIMIT 5""").fetchall()
    return jsonify(products=products_count, orders=orders_count, active_orders=active_count,
                   delivered_orders=delivered_count, order_value=float(value),
                   top_areas=[dict(row) for row in areas])


@app.post("/api/demo-payment")
def demo_payment():
    data = request.get_json(silent=True) or {}
    try:
        amount = positive_number(data.get("amount"), "Payment amount")
        method = clean_text(data.get("method", "Demo checkout"), "Payment method", 40)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    # This endpoint intentionally simulates payment; it never charges a real account.
    return jsonify(payment_id=f"DEMO-{os.urandom(4).hex().upper()}",
                   amount=amount, method=method, status="Demo payment successful",
                   note="Simulation only. No money was collected."), 200


@app.errorhandler(404)
def not_found(_error):
    if request.path.startswith("/api/"):
        return jsonify(error="API endpoint or record not found."), 404
    return "Page not found", 404


@app.errorhandler(500)
def server_error(_error):
    app.logger.exception("Unhandled application error")
    if request.path.startswith("/api/"):
        return jsonify(error="An unexpected server error occurred."), 500
    return "An unexpected server error occurred.", 500


with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False)
