"""
Tests for restocking order API endpoints.
"""
import pytest
from datetime import datetime, timedelta


@pytest.fixture(autouse=True)
def reset_restocking_orders():
    """Reset the in-memory restocking_orders list before each test.

    The list is module-level and persists across tests, so we clear it
    to ensure test isolation.
    """
    import main
    main.restocking_orders.clear()
    yield
    main.restocking_orders.clear()


@pytest.fixture
def sample_restocking_items():
    """Sample restocking order items for testing."""
    return [
        {
            "sku": "PCB-001",
            "name": "Single Layer PCB Assembly",
            "quantity": 150,
            "unit_cost": 24.99
        },
        {
            "sku": "MCU-401",
            "name": "8-bit Microcontroller",
            "quantity": 150,
            "unit_cost": 8.25
        }
    ]


class TestRestockingOrdersEndpoints:
    """Test suite for restocking order-related endpoints."""

    def test_get_restocking_orders_empty(self, client):
        """Test GET returns empty list initially."""
        response = client.get("/api/restocking-orders")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_create_restocking_order_success(self, client, sample_restocking_items):
        """Test POST with valid items returns 201 with proper order fields."""
        response = client.post(
            "/api/restocking-orders",
            json={"items": sample_restocking_items}
        )
        assert response.status_code == 201

        order = response.json()

        # Verify structure
        assert "id" in order
        assert "order_number" in order
        assert "items" in order
        assert "total_value" in order
        assert "submitted_date" in order
        assert "lead_time_days" in order
        assert "expected_arrival" in order
        assert "status" in order

        # Verify fixed 14-day lead time
        assert order["lead_time_days"] == 14

        # Verify expected_arrival is 14 days after submitted_date
        submitted = datetime.fromisoformat(order["submitted_date"])
        expected_arrival = datetime.fromisoformat(order["expected_arrival"])
        delta = expected_arrival - submitted
        assert delta == timedelta(days=14)

        # Verify order number format: RST-YYYY-NNNN
        assert order["order_number"].startswith("RST-")
        assert order["order_number"].endswith("-0001")

        # Verify status
        assert order["status"] == "Submitted"

        # Verify items preserved
        assert len(order["items"]) == 2

    def test_create_restocking_order_empty_items(self, client):
        """Test POST with empty items list returns 400."""
        response = client.post(
            "/api/restocking-orders",
            json={"items": []}
        )
        assert response.status_code == 400

        data = response.json()
        assert "detail" in data
        assert "at least one item" in data["detail"].lower()

    def test_create_restocking_order_validation(self, client):
        """Test POST with missing required field returns 422."""
        # Missing 'sku' field
        response = client.post(
            "/api/restocking-orders",
            json={
                "items": [
                    {
                        "name": "Missing SKU Item",
                        "quantity": 10,
                        "unit_cost": 5.00
                    }
                ]
            }
        )
        assert response.status_code == 422

    def test_restocking_order_appears_in_list(self, client, sample_restocking_items):
        """Test that created order appears in GET list."""
        # Create an order
        create_response = client.post(
            "/api/restocking-orders",
            json={"items": sample_restocking_items}
        )
        assert create_response.status_code == 201
        created_order = create_response.json()

        # Fetch the list
        list_response = client.get("/api/restocking-orders")
        assert list_response.status_code == 200

        orders = list_response.json()
        assert len(orders) == 1
        assert orders[0]["id"] == created_order["id"]
        assert orders[0]["order_number"] == created_order["order_number"]

    def test_order_number_sequential(self, client, sample_restocking_items):
        """Test that order numbers increment sequentially."""
        # Create first order
        response1 = client.post(
            "/api/restocking-orders",
            json={"items": sample_restocking_items}
        )
        assert response1.status_code == 201
        order1 = response1.json()

        # Create second order
        response2 = client.post(
            "/api/restocking-orders",
            json={"items": sample_restocking_items}
        )
        assert response2.status_code == 201
        order2 = response2.json()

        # Extract sequential numbers (last 4 digits)
        seq1 = order1["order_number"].split("-")[-1]
        seq2 = order2["order_number"].split("-")[-1]

        assert seq1 == "0001"
        assert seq2 == "0002"

        # Year should match current year
        current_year = datetime.now().year
        assert f"RST-{current_year}-" in order1["order_number"]
        assert f"RST-{current_year}-" in order2["order_number"]

    def test_total_value_computed(self, client):
        """Test that server-side total matches sum(qty × cost)."""
        items = [
            {"sku": "A", "name": "Item A", "quantity": 10, "unit_cost": 2.50},
            {"sku": "B", "name": "Item B", "quantity": 5, "unit_cost": 4.00},
        ]
        expected_total = (10 * 2.50) + (5 * 4.00)  # 25.00 + 20.00 = 45.00

        response = client.post("/api/restocking-orders", json={"items": items})
        assert response.status_code == 201

        order = response.json()
        assert isinstance(order["total_value"], (int, float))
        # Allow small floating point tolerance
        assert abs(order["total_value"] - expected_total) < 0.01
