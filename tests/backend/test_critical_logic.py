"""
Tests for critical backend business logic.

Covers previously untested code paths: quarter-based date filtering,
quarterly/monthly report aggregations, and backlog→purchase-order joins.
"""
import pytest


class TestCriticalLogic:
    """Test suite for critical backend calculations and data transformations."""

    def test_orders_quarter_filter_aggregates_three_months(self, client):
        """Test that the QUARTER_MAP filter returns exactly the union of its 3 months.

        Exercises filter_by_month's quarter branch (main.py:27-31), which uses
        QUARTER_MAP to expand 'Q1-2025' into ['2025-01', '2025-02', '2025-03']
        and matches via substring against order_date.
        """
        q1_response = client.get("/api/orders?month=Q1-2025")
        assert q1_response.status_code == 200
        q1_orders = q1_response.json()

        # Fetch each constituent month individually
        jan = client.get("/api/orders?month=2025-01").json()
        feb = client.get("/api/orders?month=2025-02").json()
        mar = client.get("/api/orders?month=2025-03").json()

        # Quarter result must equal the sum of its months (no duplicates, no gaps)
        assert len(q1_orders) == len(jan) + len(feb) + len(mar)
        assert len(q1_orders) > 0

        q1_ids = {o["id"] for o in q1_orders}
        month_ids = {o["id"] for o in jan} | {o["id"] for o in feb} | {o["id"] for o in mar}
        assert q1_ids == month_ids

        # Every Q1 order's date must fall within Q1 months
        for order in q1_orders:
            assert any(m in order["order_date"] for m in ["2025-01", "2025-02", "2025-03"])

    def test_quarterly_report_calculations(self, client):
        """Test that avg_order_value and fulfillment_rate are computed correctly.

        Verifies the derived metrics at main.py:292-293:
          - avg_order_value = total_revenue / total_orders
          - fulfillment_rate = (delivered_orders / total_orders) * 100
        """
        response = client.get("/api/reports/quarterly")
        assert response.status_code == 200

        quarters = response.json()
        assert isinstance(quarters, list)
        assert len(quarters) > 0

        for q in quarters:
            assert q["total_orders"] > 0  # endpoint only emits quarters with orders

            # Recompute avg from the raw fields the endpoint also returns
            expected_avg = round(q["total_revenue"] / q["total_orders"], 2)
            assert abs(q["avg_order_value"] - expected_avg) < 0.01

            # Recompute fulfillment rate
            expected_rate = round((q["delivered_orders"] / q["total_orders"]) * 100, 1)
            assert abs(q["fulfillment_rate"] - expected_rate) < 0.01

            # Sanity bounds
            assert 0 <= q["fulfillment_rate"] <= 100
            assert q["delivered_orders"] <= q["total_orders"]

        # Verify sorted ascending by quarter label (main.py:297)
        labels = [q["quarter"] for q in quarters]
        assert labels == sorted(labels)

    def test_monthly_trends_revenue_matches_orders(self, client):
        """Test that monthly-trends aggregates match the raw /api/orders data.

        Cross-validates main.py:300-329, which groups orders by order_date[:7]
        and sums total_value per month. The aggregate must equal an independent
        rollup of the source data.
        """
        trends_response = client.get("/api/reports/monthly-trends")
        assert trends_response.status_code == 200
        trends = trends_response.json()
        assert len(trends) > 0

        orders_response = client.get("/api/orders")
        all_orders = orders_response.json()

        # Independently aggregate orders by YYYY-MM
        expected = {}
        for order in all_orders:
            month = order["order_date"][:7]
            bucket = expected.setdefault(
                month, {"order_count": 0, "revenue": 0.0, "delivered_count": 0}
            )
            bucket["order_count"] += 1
            bucket["revenue"] += order["total_value"]
            if order["status"] == "Delivered":
                bucket["delivered_count"] += 1

        # Every reported month must match our independent rollup
        for trend in trends:
            month = trend["month"]
            assert month in expected, f"Reported month {month} not found in raw orders"
            assert trend["order_count"] == expected[month]["order_count"]
            assert abs(trend["revenue"] - expected[month]["revenue"]) < 0.01
            assert trend["delivered_count"] == expected[month]["delivered_count"]

        # Verify sorted chronologically (main.py:328)
        months = [t["month"] for t in trends]
        assert months == sorted(months)

    def test_backlog_has_purchase_order_flag(self, client):
        """Test that has_purchase_order correctly reflects the purchase_orders join.

        Exercises main.py:201-202: for each backlog item, has_purchase_order is
        True iff some purchase_order.backlog_item_id references it. This test
        verifies the flag against the backend's own purchase_orders list rather
        than hardcoding expectations, so it remains valid as fixture data evolves.
        """
        # Access the authoritative in-memory purchase_orders list the endpoint joins against
        import main
        po_backlog_ids = {po["backlog_item_id"] for po in main.purchase_orders}

        response = client.get("/api/backlog")
        assert response.status_code == 200

        backlog = response.json()
        assert len(backlog) > 0

        for item in backlog:
            assert "has_purchase_order" in item
            assert isinstance(item["has_purchase_order"], bool)

            expected_flag = item["id"] in po_backlog_ids
            assert item["has_purchase_order"] == expected_flag, (
                f"Backlog item {item['id']}: has_purchase_order={item['has_purchase_order']}, "
                f"but purchase_orders {'contains' if expected_flag else 'does not contain'} this id"
            )

    def test_orders_month_filter_isolates_single_month(self, client):
        """Test that month=YYYY-MM returns only orders from that month and excludes others.

        Exercises filter_by_month's direct-match branch (main.py:34) and confirms
        the filtered result is a strict, correct subset of the unfiltered set.
        """
        all_orders = client.get("/api/orders").json()
        assert len(all_orders) > 0

        filtered = client.get("/api/orders?month=2025-01").json()

        # Must return something (fixture data has Jan 2025 orders) but fewer than total
        assert len(filtered) > 0
        assert len(filtered) < len(all_orders)

        # Every returned order is from Jan 2025
        for order in filtered:
            assert "2025-01" in order["order_date"]

        # Completeness: every Jan 2025 order in the full set appears in the filtered set
        expected_ids = {o["id"] for o in all_orders if "2025-01" in o["order_date"]}
        filtered_ids = {o["id"] for o in filtered}
        assert filtered_ids == expected_ids
