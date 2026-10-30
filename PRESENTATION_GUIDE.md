# FarmRoute Direct — Presentation & Demo Guide

## 90-second project explanation
FarmRoute Direct is a farm-to-city marketplace MVP. Farmers publish produce with quantity, price and pickup area. Buyers browse listings and place orders. The application validates stock, reserves the ordered quantity and groups orders by delivery area and delivery window so nearby deliveries can be coordinated.

## Live demo
https://farmroute-direct.onrender.com

The Render free web service may sleep when idle. Open the site a few minutes before presenting so it can wake up.

## Recommended 5–7 minute walkthrough
1. Register a Farmer account with a demo name, email and password.
2. Open My products and list produce with category, price, stock, unit and area.
3. Log out and register a separate Buyer account.
4. Open Marketplace, select the listing and place an order with quantity, delivery area and preferred delivery window.
5. Log back in as the farmer and show the order and reduced stock.
6. Move the order through Placed → Confirmed → Packed → Out for delivery → Delivered. Cancellation before dispatch restores stock.
7. Open Delivery planning and explain the area/time grouping.
8. Sign in with the pre-created Admin account to show summary, team directory and CSV export links.

## Implemented
- Farmer, buyer and administrator accounts with role/ownership controls.
- Password hashing and session authentication.
- Product create, edit and delete; deletion is blocked when order history exists.
- Marketplace, order placement, stock validation and overselling protection.
- Order status workflow and stock restoration on cancellation.
- Delivery grouping by area and delivery window.
- Admin summary, registered-user directory and CSV exports for products, orders and users.
- Demo checkout is explicitly simulated and collects no money.
- SQLite local development and PostgreSQL support through DATABASE_URL.
- Automated API tests and frontend JavaScript syntax checks.

## Limitations to state honestly
- This is a hackathon MVP, not a production payment or logistics platform.
- No real payment processing or settlement.
- No live GPS tracking, road-route optimisation or driver dispatch.
- No SMS, WhatsApp, email or push notifications.
- The language selector does not yet provide a complete Telugu translation; the interface remains English.
- Use fictional demo accounts and sample produce; do not enter real customer or payment information.
- Render free services may have cold starts. The free PostgreSQL database is temporary; download CSV exports before its expiry.

## Presentation fallback
Open the website before the session to allow for cold start. If the live service is slow, explain the workflow using the repository and prepared screenshots. Do not describe unavailable integrations as operational.
