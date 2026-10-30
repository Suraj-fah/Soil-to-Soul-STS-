import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as farmroute


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test.db"))
    farmroute.init_db()
    farmroute.app.config.update(TESTING=True)
    with farmroute.app.test_client() as test_client:
        yield test_client


def test_health_and_seeded_products(client):
    assert client.get("/api/health").json["status"] == "ok"
    products = client.get("/api/products").json
    assert len(products) >= 4
    assert all(item["stock"] > 0 for item in products)


def test_add_product_validation_and_creation(client):
    bad = client.post("/api/products", json={"name": "Tomato"})
    assert bad.status_code == 400

    response = client.post("/api/products", json={
        "farmer": "Test Farm", "name": "Carrots", "category": "Vegetables",
        "price": 30, "stock": 25, "unit": "kg", "area": "Central Market"
    })
    assert response.status_code == 201
    product = next(p for p in client.get("/api/products").json if p["id"] == response.json["id"])
    assert product["stock"] == 25


def test_order_reduces_stock_and_creates_delivery_batch(client):
    product = client.get("/api/products").json[0]
    before = product["stock"]
    response = client.post("/api/orders", json={
        "product_id": product["id"], "quantity": 3,
        "buyer": "City Shop", "delivery_area": "MVP Colony",
        "delivery_window": "Tomorrow morning"
    })
    assert response.status_code == 201
    after = next(p for p in client.get("/api/products").json if p["id"] == product["id"])
    assert after["stock"] == pytest.approx(before - 3)
    assert client.get("/api/orders").json[0]["buyer"] == "City Shop"
    batches = client.get("/api/delivery-batches").json
    assert any(b["delivery_area"] == "MVP Colony" for b in batches)


def test_rejects_overselling_and_invalid_order(client):
    product = client.get("/api/products").json[0]
    response = client.post("/api/orders", json={
        "product_id": product["id"], "quantity": product["stock"] + 1,
        "buyer": "Shop", "delivery_area": "Area", "delivery_window": "Morning"
    })
    assert response.status_code == 400
    assert client.post("/api/orders", json={"product_id": product["id"], "quantity": 0}).status_code == 400


def test_order_status_transitions_and_cancellation_restores_stock(client):
    product = client.get("/api/products").json[0]
    initial_stock = product["stock"]
    created = client.post("/api/orders", json={
        "product_id": product["id"], "quantity": 4,
        "buyer": "Shop", "delivery_area": "Area", "delivery_window": "Evening"
    })
    order_id = created.json["id"]
    assert created.status_code == 201

    invalid = client.patch(f"/api/orders/{order_id}", json={"status": "Delivered"})
    assert invalid.status_code == 409

    confirmed = client.patch(f"/api/orders/{order_id}", json={"status": "Confirmed"})
    assert confirmed.status_code == 200
    cancelled = client.patch(f"/api/orders/{order_id}", json={"status": "Cancelled"})
    assert cancelled.status_code == 200

    restored = next(p for p in client.get("/api/products").json if p["id"] == product["id"])
    assert restored["stock"] == pytest.approx(initial_stock)
    repeated = client.patch(f"/api/orders/{order_id}", json={"status": "Cancelled"})
    assert repeated.status_code == 200
    still_restored = next(p for p in client.get("/api/products").json if p["id"] == product["id"])
    assert still_restored["stock"] == pytest.approx(initial_stock)


def test_home_page_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"FarmRoute Direct" in response.data

def test_product_edit_delete_and_admin_summary(client):
    product = client.get("/api/products").json[0]
    edited = client.patch(f"/api/products/{product['id']}", json={"price": 31, "stock": 80})
    assert edited.status_code == 200
    updated = next(p for p in client.get("/api/products").json if p["id"] == product["id"])
    assert updated["price"] == 31
    assert updated["stock"] == 80
    summary = client.get("/api/admin/summary")
    assert summary.status_code == 200
    assert summary.json["products"] >= 4
    removed = client.delete(f"/api/products/{product['id']}")
    assert removed.status_code == 200


def test_demo_payment_is_explicitly_simulated(client):
    response = client.post("/api/demo-payment", json={"amount": 250, "method": "UPI (demo)"})
    assert response.status_code == 200
    assert response.json["status"] == "Demo payment successful"
    assert "No money was collected" in response.json["note"]



def test_product_with_order_history_cannot_be_deleted(client):
    product = client.get("/api/products").json[0]
    created = client.post("/api/orders", json={
        "product_id": product["id"], "quantity": 2,
        "buyer": "History Shop", "delivery_area": "Area",
        "delivery_window": "Morning"
    })
    assert created.status_code == 201
    order_id = created.json["id"]
    cancelled = client.patch(f"/api/orders/{order_id}", json={"status": "Cancelled"})
    assert cancelled.status_code == 200
    response = client.delete(f"/api/products/{product['id']}")
    assert response.status_code == 409
    assert "order history" in response.json["error"]
