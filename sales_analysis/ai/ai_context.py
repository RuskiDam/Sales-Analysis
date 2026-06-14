from sales_analysis.data.sales_data import DisplayFormatter


class AIContextBuilder:
    def __init__(
        self,
        data_store,
        metrics,
        finance_policy,
        inventory_path="simulation/sb_inventory.json",
        sales_path="simulation/sb_sales_log.json",
    ):
        self.data_store = data_store
        self.metrics = metrics
        self.finance_policy = finance_policy
        self.inventory_path = inventory_path
        self.sales_path = sales_path

    def build(self):
        """Build a compact sales snapshot for the grounded A.I. prompt."""

        inventory_rows = self.data_store.load_inventory_rows(
            self.inventory_path
        )
        sales_rows = self.data_store.load_sales_rows(self.sales_path)
        context = self.context_values(inventory_rows, sales_rows)

        lines = self.summary_lines(context)
        lines.extend(self.inventory_product_lines(inventory_rows))
        lines.extend(self.latest_month_lines(context["latest_report"]))
        lines.extend(self.last_two_profit_lines(context["last_two_months"]))
        lines.extend(self.recent_month_lines(context["recent_months"]))
        return "\n".join(lines)

    def context_values(self, inventory_rows, sales_rows):
        """Calculate reusable values before formatting prompt text."""

        monthly_rows = self.metrics.monthly_financials(
            sales_rows,
            self.finance_policy,
        )
        return {
            "inventory_count": len(inventory_rows),
            "inventory_quantity": self.inventory_quantity(inventory_rows),
            "available_products": self.available_products(inventory_rows),
            "available_quantity": self.available_quantity(inventory_rows),
            "warehouse_value": self.metrics.inventory_value(inventory_rows),
            "items_sold": self.metrics.sold_quantity(sales_rows),
            "total_revenue": self.metrics.sales_revenue(sales_rows),
            "shipping_costs": self.metrics.shipping_costs(sales_rows),
            "tax_percent": self.finance_policy.tax_rate * 100,
            "latest_report": self.metrics.latest_month_report(
                sales_rows,
                self.finance_policy,
            ),
            "last_two_months": monthly_rows[-2:],
            "recent_months": monthly_rows[-3:],
        }

    def summary_lines(self, context):
        """Format top-level business totals before month-specific details."""

        return [
            "Business: PC parts retailer.",
            f"Inventory products: {context['inventory_count']:,d}.",
            (
                "Inventory quantity remaining: "
                f"{context['inventory_quantity']:,d} units."
            ),
            (
                "Available inventory: "
                f"{context['available_quantity']:,d} units across "
                f"{self.product_count_label(context['available_products'])}."
            ),
            (
                "Warehouse value: "
                f"{DisplayFormatter.money(context['warehouse_value'])}."
            ),
            f"Items sold: {context['items_sold']:,d}.",
            (
                "Total revenue: "
                f"{DisplayFormatter.money(context['total_revenue'])}."
            ),
            (
                "Shipping costs: "
                f"{DisplayFormatter.money(context['shipping_costs'])}."
            ),
            f"Tax rate: {DisplayFormatter.percent(context['tax_percent'])}.",
            self.staff_line(),
            self.health_insurance_line(),
        ]

    def latest_month_lines(self, latest_report):
        if not latest_report:
            return []

        finance = latest_report["finance"]
        revenue_change = (
            latest_report["current_revenue"]
            - latest_report["previous_revenue"]
        )
        return [
            f"Latest month: {self.latest_month_label(latest_report)}.",
            (
                "Latest month revenue: "
                f"{DisplayFormatter.money(latest_report['current_revenue'])}."
            ),
            (
                "Previous month revenue: "
                f"{DisplayFormatter.money(latest_report['previous_revenue'])}."
            ),
            (
                "Latest month MoM revenue change: "
                f"{DisplayFormatter.money(revenue_change)}."
            ),
            self.latest_money_line("net income", finance),
            self.latest_money_line("break-even margin", finance),
            self.latest_percent_line("profit margin", latest_report),
            self.latest_percent_line("MoM revenue growth", latest_report),
        ]

    def inventory_product_lines(self, inventory_rows):
        if not inventory_rows:
            return []

        lines = ["Inventory product rows:"]
        for row in inventory_rows:
            lines.append(
                f"- {row['Item']} ({row['Category']}): "
                f"{row['Quantity']:,d} units, "
                f"price: {DisplayFormatter.money(row['Price'])}."
            )

        return lines

    @staticmethod
    def last_two_profit_lines(monthly_rows):
        if not monthly_rows:
            return []

        lines = ["Last two months profit/loss:"]
        for row in monthly_rows:
            profit_margin = 0.0
            if row["Revenue"]:
                profit_margin = row["Profit"] / row["Revenue"] * 100

            status = "profit"
            if row["Profit"] < 0:
                status = "loss"

            lines.append(
                f"- {row['Month']}: {status}, "
                f"net income {DisplayFormatter.money(row['Profit'])}, "
                f"profit margin {DisplayFormatter.percent(profit_margin)}."
            )

        return lines

    @staticmethod
    def recent_month_lines(recent_months):
        if not recent_months:
            return []

        lines = ["Recent monthly rows:"]
        for row in recent_months:
            lines.append(
                f"- {row['Month']}: "
                f"revenue {DisplayFormatter.money(row['Revenue'])}, "
                f"net income {DisplayFormatter.money(row['Profit'])}, "
                f"orders {row['Orders']:,d}."
            )

        return lines

    def staff_line(self):
        wage = DisplayFormatter.money(self.finance_policy.staff_hourly_wage)
        return (
            f"Staff: {self.finance_policy.staff_count:,d} people "
            f"at {wage}/hr."
        )

    def health_insurance_line(self):
        monthly_cost = DisplayFormatter.money(
            self.finance_policy.monthly_health_insurance_per_staff
        )
        return f"Health insurance: {monthly_cost} per person monthly."

    def latest_month_label(self, report):
        return self.metrics.month_label(report["year"], report["month"])

    @staticmethod
    def latest_money_line(label, finance):
        key = label.replace("-", "_").replace(" ", "_")
        return f"Latest month {label}: {DisplayFormatter.money(finance[key])}."

    @staticmethod
    def latest_percent_line(label, report):
        key = "profit_margin"
        if label == "MoM revenue growth":
            key = "revenue_growth"

        value = DisplayFormatter.percent(report[key])
        return f"Latest month {label}: {value}."

    @staticmethod
    def inventory_quantity(inventory_rows):
        return sum(row["Quantity"] for row in inventory_rows)

    @staticmethod
    def available_products(inventory_rows):
        return sum(1 for row in inventory_rows if row["Available"] == "Y")

    @staticmethod
    def available_quantity(inventory_rows):
        return sum(
            row["Quantity"]
            for row in inventory_rows
            if row["Available"] == "Y"
        )

    @staticmethod
    def product_count_label(count):
        label = "product"
        if count != 1:
            label = "products"

        return f"{count:,d} {label}"
