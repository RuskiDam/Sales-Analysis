import unittest

from sales_analysis.app_pages import AIPage
from sales_analysis.reports.monthly_pdf import MonthlyPDFReport


class FakeDataStore:
    def load_inventory_rows(self, path):
        return [{"Price": 100.0, "Quantity": 3}]

    def load_sales_rows(self, path):
        return [{"quant": 2}, {"quant": 1}]


class FakeMetrics:
    def latest_month_report(self, sales_rows, finance_policy):
        return {
            "year": 2026,
            "month": 6,
            "current_revenue": 2000.0,
            "previous_revenue": 1500.0,
            "shipping_costs": 100.0,
            "revenue_growth": 33.33,
            "profit_margin": 52.35,
            "finance": {"net_income": 638272.75},
        }

    def monthly_financials(self, sales_rows, finance_policy):
        return [
            {
                "Month": "May 2026",
                "Revenue": 1500.0,
                "Profit": 780.0,
            },
            {
                "Month": "June 2026",
                "Revenue": 2000.0,
                "Profit": 1047.0,
            },
        ]

    def month_label(self, year, month):
        return "June 2026"

    def inventory_value(self, inventory_rows):
        return 300.0

    def sold_quantity(self, sales_rows):
        return 3


class MonthlyPDFReportTest(unittest.TestCase):
    def test_build_returns_pdf_download_payload(self):
        payload = MonthlyPDFReport(
            FakeDataStore(),
            FakeMetrics(),
            object(),
        ).build([{"role": "assistant", "content": "Revenue improved."}])

        self.assertEqual(payload["mime"], "application/pdf")
        self.assertEqual(
            payload["file_name"],
            "monthly-sales-fiscal-report-june-2026.pdf",
        )
        self.assertTrue(payload["data"].startswith(b"%PDF-1.4"))
        self.assertIn(b"Monthly Sales/Fiscal Report", payload["data"])
        self.assertIn(b"profit margin increased by 2.35%", payload["data"])
        self.assertIn(b"Recent Chat Findings", payload["data"])

    def test_baseline_movement(self):
        self.assertEqual(
            MonthlyPDFReport.baseline_movement(52.35),
            "increased by 2.35%",
        )
        self.assertEqual(
            MonthlyPDFReport.baseline_movement(48.2),
            "decreased by 1.80%",
        )
        self.assertEqual(
            MonthlyPDFReport.baseline_movement(50.0),
            "was flat against baseline",
        )

    def test_ai_page_detects_pdf_report_requests(self):
        self.assertTrue(AIPage.is_pdf_report_request("Create a MoM PDF"))
        self.assertTrue(
            AIPage.is_pdf_report_request("Generate a PDF Monthly report")
        )
        self.assertFalse(AIPage.is_pdf_report_request("Were we profitable?"))


if __name__ == "__main__":
    unittest.main()
