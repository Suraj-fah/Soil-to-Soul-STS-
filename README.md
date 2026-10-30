# FarmRoute Direct

A professional, multilingual-ready farm-to-city marketplace and delivery coordination MVP.

## What this MVP includes
- Farmer and buyer demo workspaces
- Product catalogue and inventory management
- Order creation and status updates
- Delivery batch grouping by area and delivery window
- Illustrative grouped-delivery cost comparison
- English and Telugu interface labels
- SQLite persistence for local development
- Flask JSON API and responsive web interface

## Run locally

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000.

The app seeds clearly labelled demonstration data on first run. Use the demo role switcher to explore farmer, buyer and operations views. This is a hackathon MVP, not a production marketplace: payments, live GPS, verified identity, real route optimisation and production-grade authentication are not included.

## Deployment

A Render blueprint is provided in `render.yaml`. Set `SECRET_KEY` to a long random value. For persistent hosted data, configure a PostgreSQL database and `DATABASE_URL`; without it, SQLite is suitable only for local/demo use and may not persist on ephemeral hosting filesystems.

## Project structure

- `app.py` – Flask application, API, SQLite/PostgreSQL data access and seed data
- `templates/index.html` – application shell
- `static/css/styles.css` – visual system and responsive layouts
- `static/js/app.js` – frontend interactions and API integration
- `render.yaml` – deployment blueprint

## Responsible demo notes

All seeded names, farms, products and orders are fictional examples. Delivery cost figures are assumptions for demonstrating the calculation, not verified savings. Grouping is area/time-window based and is not road-network route optimisation. Translation strings should be reviewed by fluent speakers before real-world use.
