import unittest

from sales_analysis.ai.ai_context import AIContextBuilder
from sales_analysis.finance.company_finance import CompanyFinancePolicy


class FakeDataStore:
    def load_inventory_rows(self, path):
        return []

    def load_sales_rows(self, path):
        return []


class FakeMetrics:
    def monthly_financials(self, sales_rows, finance_policy):
        return [
            {
                "Month": "May 2026",
                "Revenue": 1500.0,
                "Profit": 200.0,
                "Gross Profit": 1400.0,
                "Shipping Costs": 100.0,
                "Staff Payroll": 700.0,
                "Health Insurance": 200.0,
                "Break Even Margin": 1000.0,
                "Taxes": 50.0,
                "Orders": 10,
            },
            {
                "Month": "June 2026",
                "Revenue": 2000.0,
                "Profit": 400.0,
                "Gross Profit": 1900.0,
                "Shipping Costs": 100.0,
                "Staff Payroll": 700.0,
                "Health Insurance": 200.0,
                "Break Even Margin": 1000.0,
                "Taxes": 100.0,
                "Orders": 12,
            },
        ]

    def inventory_value(self, inventory_rows):
        return 0.0

    def sold_quantity(self, sales_rows):
        return 0

    def sales_revenue(self, sales_rows):
        return 0.0

    def shipping_costs(self, sales_rows):
        return 0.0

    def latest_month_report(self, sales_rows, finance_policy):
        return {
            "year": 2026,
            "month": 6,
            "current_revenue": 2000.0,
            "previous_revenue": 1500.0,
            "profit_margin": 54.98,
            "revenue_growth": 0.0,
            "finance": {
                "net_income": 100.0,
                "break_even_margin": 50.0,
            },
        }

    def month_label(self, year, month):
        return "June 2026"


class AIContextBuilderTest(unittest.TestCase):
    def test_profit_margin_baseline_delta_is_in_context(self):
        context = AIContextBuilder(
            FakeDataStore(),
            FakeMetrics(),
            CompanyFinancePolicy(),
        ).build()

        self.assertIn("Profit margin baseline: 50.00%.", context)
        self.assertIn(
            "Latest month profit margin vs baseline: "
            "4.98% above baseline, which is a 4.98% increase.",
            context,
        )
        self.assertIn("Latest month MoM revenue change: $500.00.", context)


if __name__ == "__main__":
    unittest.main()
