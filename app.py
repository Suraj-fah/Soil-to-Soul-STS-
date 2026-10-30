import os, sqlite3
from contextlib import contextmanager
from flask import Flask, jsonify, request, render_template

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'local-demo-change-this')
DB_URL = os.getenv('DATABASE_URL', '').replace('postgres://', 'postgresql://', 1)
USE_PG = DB_URL.startswith('postgresql://')

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
            conn.rollback(); raise
        finally: conn.close()
    else:
        conn = sqlite3.connect(os.getenv('SQLITE_PATH', 'farmroute.db'))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback(); raise
        finally: conn.close()

def query(sql):
    return sql.replace('?', '%s') if USE_PG else sql

def init_db():
    with db() as c:
        cur = c.cursor()
        idcol = 'SERIAL PRIMARY KEY' if USE_PG else 'INTEGER PRIMARY KEY AUTOINCREMENT'
        cur.execute(f'''CREATE TABLE IF NOT EXISTS products (id {idcol}, farmer TEXT NOT NULL, name TEXT NOT NULL, category TEXT NOT NULL, price REAL NOT NULL, stock REAL NOT NULL, unit TEXT NOT NULL, area TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        cur.execute(f'''CREATE TABLE IF NOT EXISTS orders (id {idcol}, buyer TEXT NOT NULL, product_id INTEGER NOT NULL REFERENCES products(id), quantity REAL NOT NULL, delivery_area TEXT NOT NULL, delivery_window TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Placed', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        cur.execute('SELECT COUNT(*) AS n FROM products')
        row = cur.fetchone(); count = row['n'] if USE_PG else row['n']
        if count == 0:
            samples = [('Ravi Farms','Tomatoes','Vegetables',28,120,'kg','MVP Colony'),('Green Valley','Spinach','Leafy greens',18,70,'bunch','MVP Colony'),('Sita Organic Farm','Bengal Gram','Pulses',92,90,'kg','Seethammadhara'),('Coastal Growers','Bananas','Fruits',45,100,'dozen','Gajuwaka')]
            for p in samples:
                cur.execute(query('INSERT INTO products (farmer,name,category,price,stock,unit,area) VALUES (?,?,?,?,?,?,?)'), p)

@app.get('/')
def home(): return render_template('index.html')

@app.get('/api/health')
def health(): return jsonify(status='ok', database='postgresql' if USE_PG else 'sqlite')

@app.get('/api/products')
def products():
    with db() as c:
        rows = c.execute('SELECT * FROM products ORDER BY created_at DESC, id DESC').fetchall()
        return jsonify([dict(r) for r in rows])

@app.post('/api/products')
def add_product():
    d=request.get_json(silent=True) or {}
    required=['farmer','name','category','price','stock','unit','area']
    if any(d.get(k) in (None,'') for k in required): return jsonify(error='Please complete all product fields.'),400
    try: price=float(d['price']); stock=float(d['stock'])
    except (ValueError,TypeError): return jsonify(error='Price and stock must be numbers.'),400
    if price<=0 or stock<=0: return jsonify(error='Price and stock must be greater than zero.'),400
    with db() as c:
        cur=c.cursor(); cur.execute(query('INSERT INTO products (farmer,name,category,price,stock,unit,area) VALUES (?,?,?,?,?,?,?) RETURNING id'),(d['farmer'],d['name'],d['category'],price,stock,d['unit'],d['area']))
        row=cur.fetchone(); pid=row['id'] if USE_PG else row[0]
        return jsonify(id=pid,message='Product added successfully.'),201

@app.get('/api/orders')
def orders():
    with db() as c:
        rows=c.execute('''SELECT o.*, p.name AS product_name, p.farmer, p.unit, p.price FROM orders o JOIN products p ON p.id=o.product_id ORDER BY o.created_at DESC, o.id DESC''').fetchall()
        return jsonify([dict(r) for r in rows])

@app.post('/api/orders')
def add_order():
    d=request.get_json(silent=True) or {}
    try: pid=int(d.get('product_id')); qty=float(d.get('quantity'))
    except (ValueError,TypeError): return jsonify(error='Choose a product and valid quantity.'),400
    if qty<=0: return jsonify(error='Quantity must be greater than zero.'),400
    buyer=(d.get('buyer') or '').strip(); area=(d.get('delivery_area') or '').strip(); window=(d.get('delivery_window') or '').strip()
    if not all([buyer,area,window]): return jsonify(error='Buyer, delivery area and delivery window are required.'),400
    with db() as c:
        cur=c.cursor(); cur.execute(query('SELECT stock FROM products WHERE id=?'),(pid,)); p=cur.fetchone()
        if not p: return jsonify(error='Product not found.'),404
        stock=p['stock'] if USE_PG else p['stock']
        if qty>stock: return jsonify(error=f'Only {stock:g} available.'),400
        cur.execute(query('UPDATE products SET stock=stock-? WHERE id=?'),(qty,pid))
        cur.execute(query('INSERT INTO orders (buyer,product_id,quantity,delivery_area,delivery_window,status) VALUES (?,?,?,?,?,?) RETURNING id'),(buyer,pid,qty,area,window,'Placed'))
        row=cur.fetchone(); oid=row['id'] if USE_PG else row[0]
        return jsonify(id=oid,message='Order placed and saved.'),201

@app.patch('/api/orders/<int:order_id>')
def update_order(order_id):
    d=request.get_json(silent=True) or {}; status=d.get('status')
    allowed=['Placed','Confirmed','Packed','Out for delivery','Delivered','Cancelled']
    if status not in allowed: return jsonify(error='Invalid order status.'),400
    with db() as c:
        cur=c.cursor(); cur.execute(query('UPDATE orders SET status=? WHERE id=?'),(status,order_id))
        if cur.rowcount==0: return jsonify(error='Order not found.'),404
    return jsonify(message='Order status updated.')

@app.get('/api/delivery-batches')
def batches():
    with db() as c:
        rows=c.execute('''SELECT delivery_area, delivery_window, COUNT(*) AS order_count, SUM(quantity*price) AS order_value FROM orders JOIN products ON products.id=orders.product_id WHERE status NOT IN ('Delivered','Cancelled') GROUP BY delivery_area,delivery_window ORDER BY delivery_area''').fetchall()
        return jsonify([dict(r) for r in rows])

with app.app_context(): init_db()

if __name__ == '__main__': app.run(host='0.0.0.0', port=int(os.getenv('PORT',5000)), debug=False)
