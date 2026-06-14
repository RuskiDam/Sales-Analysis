import datetime
import textwrap

from sales_analysis.data.sales_data import DisplayFormatter


class SimplePDFDocument:
    """Build a compact text PDF without external runtime dependencies."""

    page_width = 612
    page_height = 792
    margin = 54
    line_height = 16
    body_size = 11
    heading_size = 15
    title_size = 20

    def __init__(self):
        self.pages = []
        self.commands = []
        self.y_position = self.page_height - self.margin
        self.new_page()

    def new_page(self):
        if self.commands:
            self.pages.append("\n".join(self.commands))

        self.commands = []
        self.y_position = self.page_height - self.margin

    def add_title(self, text):
        self.add_text(text, self.title_size, bold=True)
        self.add_gap(10)

    def add_heading(self, text):
        self.add_gap(6)
        self.add_text(text, self.heading_size, bold=True)
        self.add_gap(4)

    def add_paragraph(self, text):
        for line in textwrap.wrap(text, width=82):
            self.add_text(line, self.body_size)
        self.add_gap(4)

    def add_bullet(self, text):
        wrapped_lines = textwrap.wrap(text, width=78)
        if not wrapped_lines:
            return

        self.add_text(f"- {wrapped_lines[0]}", self.body_size)
        for line in wrapped_lines[1:]:
            self.add_text(f"  {line}", self.body_size)

    def add_key_value(self, label, value):
        self.add_text(f"{label}: {value}", self.body_size)

    def add_gap(self, size):
        self.y_position -= size

    def add_text(self, text, size, bold=False):
        if self.y_position < self.margin:
            self.new_page()

        font = "F2" if bold else "F1"
        self.commands.append(
            f"BT /{font} {size} Tf {self.margin} {self.y_position} Td "
            f"({self.escape(text)}) Tj ET"
        )
        self.y_position -= self.line_height

    def bytes(self):
        if self.commands:
            self.pages.append("\n".join(self.commands))
            self.commands = []

        objects = [
            "<< /Type /Catalog /Pages 2 0 R >>",
            self.pages_object(),
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
        ]

        page_object_ids = []
        for content in self.pages:
            content_object_id = len(objects) + 2
            page_object_ids.append(len(objects) + 1)
            objects.append(self.page_object(content_object_id))
            objects.append(self.content_object(content))

        objects[1] = self.pages_object(page_object_ids)
        return self.serialize(objects)

    def pages_object(self, page_object_ids=None):
        page_object_ids = page_object_ids or []
        kids = " ".join(f"{object_id} 0 R" for object_id in page_object_ids)
        return f"<< /Type /Pages /Kids [{kids}] /Count {len(page_object_ids)} >>"

    def page_object(self, content_object_id):
        return (
            "<< /Type /Page /Parent 2 0 R "
            f"/MediaBox [0 0 {self.page_width} {self.page_height}] "
            "/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> "
            f"/Contents {content_object_id} 0 R >>"
        )

    @staticmethod
    def content_object(content):
        encoded = content.encode("latin-1", errors="replace")
        return (
            f"<< /Length {len(encoded)} >>\n"
            "stream\n"
            f"{content}\n"
            "endstream"
        )

    @staticmethod
    def serialize(objects):
        pdf = ["%PDF-1.4\n"]
        offsets = [0]
        for index, body in enumerate(objects, start=1):
            offsets.append(sum(len(part.encode("latin-1")) for part in pdf))
            pdf.append(f"{index} 0 obj\n{body}\nendobj\n")

        xref_position = sum(len(part.encode("latin-1")) for part in pdf)
        pdf.append(f"xref\n0 {len(objects) + 1}\n")
        pdf.append("0000000000 65535 f \n")
        for offset in offsets[1:]:
            pdf.append(f"{offset:010d} 00000 n \n")
        pdf.append(
            "trailer\n"
            f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            "startxref\n"
            f"{xref_position}\n"
            "%%EOF\n"
        )
        return "".join(pdf).encode("latin-1")

    @staticmethod
    def escape(text):
        return str(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


class MonthlyPDFReport:
    def __init__(self, data_store, metrics, finance_policy):
        self.data_store = data_store
        self.metrics = metrics
        self.finance_policy = finance_policy

    def build(self, chat_history=None):
        inventory_rows = self.data_store.load_inventory_rows(
            "simulation/sb_inventory.json"
        )
        sales_rows = self.data_store.load_sales_rows(
            "simulation/sb_sales_log.json"
        )
        report = self.metrics.latest_month_report(
            sales_rows,
            self.finance_policy,
        )
        monthly_rows = self.metrics.monthly_financials(
            sales_rows,
            self.finance_policy,
        )
        if report is None:
            raise ValueError("No sales data available for a monthly report.")

        pdf = SimplePDFDocument()
        self.add_header(pdf, report)
        self.add_executive_summary(pdf, report, inventory_rows, sales_rows)
        self.add_last_two_months(pdf, monthly_rows)
        self.add_recent_chat(pdf, chat_history or [])
        return {
            "file_name": self.file_name(report),
            "data": pdf.bytes(),
            "mime": "application/pdf",
        }

    def add_header(self, pdf, report):
        month_label = self.metrics.month_label(report["year"], report["month"])
        generated_on = datetime.date.today().isoformat()
        pdf.add_title("Monthly Sales/Fiscal Report")
        pdf.add_key_value("Business", "PC parts retailer")
        pdf.add_key_value("Reporting period", month_label)
        pdf.add_key_value("Generated on", generated_on)

    def add_executive_summary(self, pdf, report, inventory_rows, sales_rows):
        finance = report["finance"]
        revenue_change = report["current_revenue"] - report["previous_revenue"]
        pdf.add_heading("Executive Summary")
        pdf.add_bullet(
            f"Revenue was {DisplayFormatter.money(report['current_revenue'])}."
        )
        pdf.add_bullet(
            "MoM revenue change was "
            f"{DisplayFormatter.money(revenue_change)} "
            f"({DisplayFormatter.percent(report['revenue_growth'])})."
        )
        pdf.add_bullet(
            f"Net income was {DisplayFormatter.money(finance['net_income'])}."
        )
        pdf.add_bullet(
            "Profit margin "
            f"{self.baseline_movement(report['profit_margin'])}."
        )
        pdf.add_bullet(
            f"Shipping costs were {DisplayFormatter.money(report['shipping_costs'])}."
        )
        pdf.add_bullet(
            f"Inventory value was "
            f"{DisplayFormatter.money(self.metrics.inventory_value(inventory_rows))}."
        )
        pdf.add_bullet(f"Items sold: {self.metrics.sold_quantity(sales_rows):,d}.")

    def add_last_two_months(self, pdf, monthly_rows):
        recent_rows = monthly_rows[-2:]
        if not recent_rows:
            return

        pdf.add_heading("Last Two Months Profit/Loss")
        for row in recent_rows:
            status = "profit" if row["Profit"] >= 0 else "loss"
            profit_margin = 0.0
            if row["Revenue"]:
                profit_margin = row["Profit"] / row["Revenue"] * 100

            pdf.add_bullet(
                f"{row['Month']}: {status}, net income "
                f"{DisplayFormatter.money(row['Profit'])}, profit margin "
                f"{self.baseline_movement(profit_margin)}."
            )

    def add_recent_chat(self, pdf, chat_history):
        findings = [
            message.get("content", "").strip()
            for message in chat_history[-4:]
            if message.get("role") == "assistant"
            and message.get("content", "").strip()
        ]
        if not findings:
            return

        pdf.add_heading("Recent Chat Findings")
        for finding in findings:
            pdf.add_bullet(finding)

    @classmethod
    def baseline_movement(cls, profit_margin):
        difference = profit_margin - 50.0
        if difference > 0:
            return f"increased by {DisplayFormatter.percent(difference)}"
        if difference < 0:
            return f"decreased by {DisplayFormatter.percent(abs(difference))}"
        return "was flat against baseline"

    def file_name(self, report):
        month = self.metrics.month_label(report["year"], report["month"])
        slug = month.lower().replace(" ", "-")
        return f"monthly-sales-fiscal-report-{slug}.pdf"
