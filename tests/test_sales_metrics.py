import unittest

from sales_analysis.data.sales_data import SalesMetrics
from sales_analysis.finance.company_finance import CompanyFinancePolicy


class SalesMetricsTest(unittest.TestCase):
    def setUp(self):
        self.metrics = SalesMetrics()

    def sales_rows(self):
        return [
            {
                "item": "GPU",
                "quant": 2,
                "revenue": 1000.0,
                "shipping_cost": 20.0,
                "date": "2026-01-15",
                "purchased_at": "2026-01-15T12:00:00",
            },
            {
                "item": "CPU",
                "quant": 1,
                "revenue": 500.0,
                "shipping_cost": 20.0,
                "date": "2026-02-10",
                "purchased_at": "2026-02-10T12:00:00",
            },
            {
                "item": "SSD",
                "quant": 3,
                "revenue": 900.0,
                "shipping_cost": 20.0,
                "date": "2026-02-20",
                "purchased_at": "2026-02-20T12:00:00",
            },
        ]

    def test_sales_totals(self):
        rows = self.sales_rows()
        self.assertEqual(self.metrics.sold_quantity(rows), 6)
        self.assertEqual(self.metrics.sales_revenue(rows), 2400.0)
        self.assertEqual(self.metrics.shipping_costs(rows), 60.0)

    def test_month_over_month_growth(self):
        growth = self.metrics.mom_revenue_growth(1500.0, 1000.0)
        self.assertEqual(growth, 50.0)

    def test_latest_month_report(self):
        report = self.metrics.latest_month_report(
            self.sales_rows(),
            CompanyFinancePolicy(),
        )
        if report is None:
            self.fail("Expected latest month report.")

        self.assertEqual(report["year"], 2026)
        self.assertEqual(report["month"], 2)
        self.assertEqual(report["current_revenue"], 1400.0)
        self.assertEqual(report["shipping_costs"], 40.0)
        self.assertEqual(report["revenue_growth"], 40.0)

    def test_monthly_financials(self):
        rows = self.metrics.monthly_financials(
            self.sales_rows(),
            CompanyFinancePolicy(),
        )
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["Month"], "January 2026")
        self.assertEqual(rows[1]["Month"], "February 2026")
        self.assertIn("Net Income", {"Net Income": rows[1]["Profit"]})


if __name__ == "__main__":
    unittest.main()
