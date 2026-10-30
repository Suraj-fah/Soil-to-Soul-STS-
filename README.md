# FarmRoute Direct

FarmRoute Direct is a professional farm-to-city marketplace and delivery-coordination hackathon MVP. It demonstrates how farmers can list produce, buyers can place orders, and operations users can group open orders by delivery area and preferred time window.

## Implemented in this repository

- Responsive dashboard with a restrained, professional agricultural visual style
- Product marketplace seeded with clearly labelled fictional demo products
- Farmer and buyer account registration, login and logout with hashed passwords
- Role-aware API permissions and account-specific product/order ownership
- Admin registration protected by a private invitation code; admin user directory and dashboard
- Add-product form with price and stock validation
- Edit and remove product listings; products with order history are protected to preserve records
- Buyer order placement with stock checks
- Persistent product and order records
- Order status updates: Placed, Confirmed, Packed, Out for delivery, Delivered and Cancelled
- Delivery batches grouped by area and delivery window
- Stock reservation that prevents orders above available inventory
- Order status transition checks and automatic stock restoration when an eligible order is cancelled
- Automated API and workflow tests
- Dashboard metrics for products, active orders, batches and listed stock value
- Flask JSON API
- SQLite for local development; PostgreSQL support through DATABASE_URL
- English interface; Telugu language selection is a placeholder and translation is not implemented yet

## Run locally

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000.

The database is created automatically and seeded with fictional demonstration products on first run.

## API endpoints

- `GET /api/health` – application and database health
- `POST /api/auth/register` – register as farmer or buyer; admin signup requires the invitation code
- `POST /api/auth/login` and `POST /api/auth/logout` – session authentication
- `GET /api/auth/me` – current signed-in account
- `GET /api/products` – list products
- `POST /api/products` – create a product
- `PATCH /api/products/<id>` – edit a product
- `DELETE /api/products/<id>` – remove a product only when it has no order history
- `GET /api/orders` – list orders
- `POST /api/orders` – place an order and reduce available stock
- `PATCH /api/orders/<id>` – update order status
- `GET /api/delivery-batches` – group open orders by area and delivery window
- `GET /api/admin/summary` and `GET /api/admin/users` – administrator-only summary and account directory
- `POST /api/demo-payment` – simulated checkout only; no money is collected

## Run tests

```bash
pip install pytest
pytest -q
```

The tests use temporary SQLite databases and do not modify your local demo database.

## Deploy to Render

A starter blueprint is included in `render.yaml`.

1. Push this repository to GitHub.
2. In Render, create a new Blueprint deployment and select this repository.
3. Add a managed PostgreSQL database in Render and set the web service's `DATABASE_URL` to its internal connection string.
4. Ensure `SECRET_KEY` is set to a long random value.
5. Deploy, then verify the public site's `/api/health` endpoint.

SQLite is intended for local development only on hosts with ephemeral filesystems. Use PostgreSQL for hosted data. **Free-plan setup:** this project currently uses Render's free web service and free PostgreSQL database. Render free Postgres expires 30 days after creation and has no backups; this database was created on 30 October 2026 and is scheduled to expire on 29 November 2026. Export data before expiry. The free web service may spin down after inactivity and the first request after idle time can be slow. No paid services are required for the current demo, but free-tier limits apply.

## Honest scope and limitations

This is a hackathon MVP, not a production-ready marketplace. It has basic email/password sessions and role-based API permissions, but no email verification, password reset, multi-factor authentication or production security audit. It has no real payment processing, live GPS, road-network route optimisation, SMS notifications or fully translated Telugu interface. Product listings can be edited. A listing can be removed only when no orders reference it; otherwise set its available quantity to zero to stop new orders. Refunds and multi-farmer settlement are not implemented. The buyer order workflow uses an inline form for buyer, quantity, delivery area and preferred delivery window. Delivery batches are grouped by matching area and delivery window; they are not calculated driving routes.

All seeded farms, names, products and orders are fictional examples. Listed-stock value is an arithmetic dashboard metric, not revenue. Do not claim verified transport savings or real farmer adoption from this demonstration.

## Project structure

- `app.py` – Flask application, API, database access and seed data
- `templates/index.html` – application shell
- `static/css/styles.css` – responsive visual system
- `static/js/app.js` – frontend interactions and API integration
- `render.yaml` – deployment blueprint
