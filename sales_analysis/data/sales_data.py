import datetime
import json
from collections import defaultdict

from sales_analysis.project_paths import ProjectPaths


class InventoryCatalog:
    def __init__(self, inventory_data):
        self.inventory_data = inventory_data

    def products(self):
        products = []
        for category_products in self.inventory_data["items"].values():
            products.extend(category_products)

        return products

    def category_products(self, category):
        return self.inventory_data["items"].get(category, [])

    def available_products(self, category=None):
        products = self.products()
        if category is not None:
            products = self.category_products(category)

        return [
            product
            for product in products
            if product["status"] == "available" and product["quant"] > 0
        ]

    def find_product(self, item):
        matches = [
            product for product in self.products() if product["item"] == item
        ]
        if matches:
            return matches[0]

        return None


class DisplayFormatter:
    @staticmethod
    def money(value):
        if value < 0:
            return f"-${abs(value):,.2f}"

        return f"${value:,.2f}"

    @staticmethod
    def percent(value):
        return f"{value:.2f}%"

    @staticmethod
    def availability(status):
        if status == "available":
            return "Y"

        return "N"

    @staticmethod
    def availability_style(value):
        if value == "Y":
            return (
                "background-color: #dafbe1; color: #116329; "
                "font-weight: 700;"
            )

        if value == "N":
            return (
                "background-color: #ffebe9; color: #82071e; "
                "font-weight: 700;"
            )

        return ""


class SalesDataStore:
    json_indent = 2
    inventory_fields = ["category", "item", "price", "quant", "status"]
    sales_fields = ["item", "quant", "revenue", "shipping_cost"]

    def load_inventory_rows(self, file_path):
        data = self.load_inventory_data(file_path)
        return [
            self.inventory_row(product)
            for product in InventoryCatalog(data).products()
        ]

    @staticmethod
    def inventory_row(product):
        return {
            "Category": product["category"],
            "Item": product["item"],
            "Price": product["price"],
            "Quantity": product["quant"],
            "Available": DisplayFormatter.availability(product["status"]),
        }

    @staticmethod
    def load_inventory_data(file_path):
        data = json.loads(ProjectPaths.resolve(file_path).read_text())
        SalesDataStore.validate_inventory_data(data)
        return data

    @staticmethod
    def save_inventory_data(file_path, data):
        SalesDataStore.validate_inventory_data(data)
        ProjectPaths.resolve(file_path).write_text(
            json.dumps(data, indent=SalesDataStore.json_indent) + "\n"
        )

    @staticmethod
    def load_sales_rows(file_path):
        rows = json.loads(ProjectPaths.resolve(file_path).read_text())
        SalesDataStore.validate_sales_rows(rows)
        return rows

    @staticmethod
    def save_sales_rows(file_path, rows):
        SalesDataStore.validate_sales_rows(rows)
        ProjectPaths.resolve(file_path).write_text(
            json.dumps(rows, indent=SalesDataStore.json_indent) + "\n"
        )

    @classmethod
    def validate_inventory_data(cls, data):
        """Reject malformed inventory JSON before UI or simulation uses it."""

        if type(data) is not dict or "items" not in data:
            raise ValueError("Inventory data must contain an items object.")

        if type(data["items"]) is not dict:
            raise ValueError("Inventory items must be grouped by category.")

        for category, products in data["items"].items():
            if type(products) is not list:
                raise ValueError(
                    f"Inventory category {category} must be a list."
                )

            for product in products:
                cls.validate_inventory_product(category, product)

    @classmethod
    def validate_inventory_product(cls, category, product):
        if type(product) is not dict:
            raise ValueError(
                f"Inventory category {category} has an invalid product."
            )

        missing_fields = [
            field for field in cls.inventory_fields if field not in product
        ]
        if missing_fields:
            missing_field = missing_fields[0]
            raise ValueError(
                f"Inventory product in {category} is missing {missing_field}."
            )

    @classmethod
    def validate_sales_rows(cls, rows):
        if type(rows) is not list:
            raise ValueError("Sales log must be a list.")

        for index, row in enumerate(rows, start=1):
            cls.validate_sales_row(index, row)

    @classmethod
    def validate_sales_row(cls, index, row):
        if type(row) is not dict:
            raise ValueError(f"Sales row {index} must be an object.")

        missing_fields = [
            field for field in cls.sales_fields if field not in row
        ]
        if missing_fields:
            raise ValueError(
                f"Sales row {index} is missing {missing_fields[0]}."
            )


class SalesMetrics:
    percent_multiplier = 100

    @staticmethod
    def inventory_value(rows):
        return sum(row["Price"] * row["Quantity"] for row in rows)

    @staticmethod
    def sold_quantity(sales_rows):
        return sum(row["quant"] for row in sales_rows)

    @staticmethod
    def sales_revenue(sales_rows):
        return sum(row["revenue"] for row in sales_rows)

    @staticmethod
    def shipping_costs(sales_rows):
        return sum(row["shipping_cost"] for row in sales_rows)

    @staticmethod
    def profit_margin(profit, revenue):
        if revenue == 0:
            return 0.0

        return (profit / revenue) * SalesMetrics.percent_multiplier

    @staticmethod
    def mom_revenue_growth(current_revenue, previous_revenue):
        if previous_revenue == 0:
            return 0.0

        return (
            (current_revenue - previous_revenue)
            / previous_revenue
            * SalesMetrics.percent_multiplier
        )

    @staticmethod
    def sale_datetime(sale):
        if "purchased_at" in sale:
            return datetime.datetime.fromisoformat(sale["purchased_at"])

        sale_date = datetime.date.fromisoformat(sale["date"])
        return datetime.datetime.combine(sale_date, datetime.time())

    @staticmethod
    def previous_month(year, month):
        if month == 1:
            return year - 1, 12

        return year, month - 1

    @staticmethod
    def month_label(year, month):
        month_date = datetime.date(year, month, 1)
        return month_date.strftime("%B %Y")

    def sales_for_month(self, sales_rows, year, month):
        return [
            sale
            for sale in sales_rows
            if self.sale_in_month(sale, year, month)
        ]

    def sale_in_month(self, sale, year, month):
        sale_time = self.sale_datetime(sale)
        return sale_time.year == year and sale_time.month == month

    def latest_sales_month(self, sales_rows):
        sale_times = [self.sale_datetime(sale) for sale in sales_rows]
        if not sale_times:
            return None

        latest_sale_time = max(sale_times)
        return latest_sale_time.year, latest_sale_time.month

    def monthly_totals(self, sales_rows):
        totals = defaultdict(
            lambda: {"Revenue": 0.0, "Shipping Costs": 0.0, "Orders": 0}
        )
        for sale in sales_rows:
            self.add_sale_to_month(totals, sale)

        return [
            self.month_total_row(year, month, totals[(year, month)])
            for year, month in sorted(totals)
        ]

    def add_sale_to_month(self, totals, sale):
        sale_time = self.sale_datetime(sale)
        month_key = sale_time.year, sale_time.month
        totals[month_key]["Revenue"] += sale["revenue"]
        totals[month_key]["Shipping Costs"] += sale["shipping_cost"]
        totals[month_key]["Orders"] += 1

    def month_total_row(self, year, month, month_data):
        revenue = month_data["Revenue"]
        shipping_costs = month_data["Shipping Costs"]
        return {
            "Month": self.month_label(year, month),
            "Revenue": revenue,
            "Profit": revenue - shipping_costs,
            "Shipping Costs": shipping_costs,
            "Orders": month_data["Orders"],
        }

    def monthly_financials(self, sales_rows, finance_policy):
        """Attach company expense and net-income fields to each monthly row."""

        monthly_rows = []
        for month_row in self.monthly_totals(sales_rows):
            finance = finance_policy.financial_summary(
                month_row["Revenue"],
                month_row["Shipping Costs"],
            )
            month_row["Gross Profit"] = finance["gross_profit"]
            month_row["Staff Payroll"] = finance["staff_payroll"]
            month_row["Health Insurance"] = finance["health_insurance"]
            month_row["Break Even Margin"] = finance["break_even_margin"]
            month_row["Taxes"] = finance["taxes"]
            month_row["Profit"] = finance["net_income"]
            monthly_rows.append(month_row)

        return monthly_rows

    def latest_month_report(self, sales_rows, finance_policy):
        """Build the report for the newest month that has at least one sale."""

        latest_month = self.latest_sales_month(sales_rows)
        if latest_month is None:
            return None

        year, month = latest_month
        current_sales = self.sales_for_month(sales_rows, year, month)
        previous_sales = self.previous_month_sales(sales_rows, year, month)
        return self.month_report(
            year,
            month,
            current_sales,
            previous_sales,
            finance_policy,
        )

    def previous_month_sales(self, sales_rows, year, month):
        previous_year, previous_month = self.previous_month(year, month)
        return self.sales_for_month(sales_rows, previous_year, previous_month)

    def month_report(
        self,
        year,
        month,
        current_sales,
        previous_sales,
        finance_policy,
    ):
        """Combine latest-month sales, finance, and comparison rates."""

        values = self.report_values(
            current_sales,
            previous_sales,
            finance_policy,
        )
        report = self.report_summary(year, month, current_sales, values)
        report.update(
            self.report_rates(
                values["finance"],
                values["current_revenue"],
                values["previous_revenue"],
            )
        )
        return report

    @staticmethod
    def report_summary(year, month, current_sales, values):
        return {
            "year": year,
            "month": month,
            "current_sales": current_sales,
            "current_revenue": values["current_revenue"],
            "shipping_costs": values["shipping_costs"],
            "finance": values["finance"],
        }

    def report_values(self, current_sales, previous_sales, finance_policy):
        """Calculate revenue, shipping, and finance values used in reports."""

        current_revenue = self.sales_revenue(current_sales)
        shipping_costs = self.shipping_costs(current_sales)
        return {
            "current_revenue": current_revenue,
            "previous_revenue": self.sales_revenue(previous_sales),
            "shipping_costs": shipping_costs,
            "finance": finance_policy.financial_summary(
                current_revenue,
                shipping_costs,
            ),
        }

    def report_rates(self, finance, current_revenue, previous_revenue):
        return {
            "profit_margin": self.profit_margin(
                finance["net_income"],
                current_revenue,
            ),
            "revenue_growth": self.mom_revenue_growth(
                current_revenue,
                previous_revenue,
            ),
        }
