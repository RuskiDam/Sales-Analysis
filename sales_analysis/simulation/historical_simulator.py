import datetime
import random

from sales_analysis.data.sales_data import InventoryCatalog
from sales_analysis.finance.shipping_policy import ShippingPolicy


class HistoricalSalesSimulator:
    monthly_order_count = 500
    minimum_purchase_quantity = 1
    maximum_purchase_quantity = 4
    first_month_day = 1
    midday_hour = 12

    def __init__(self, simulation_manager, data_store, seed=None):
        self.simulation_manager = simulation_manager
        self.data_store = data_store
        self.random = random.Random(seed)

    def run(self, month_count):
        """Generate monthly sales, mutate simulation inventory, persist both files."""

        inventory_file = self.simulation_manager.prepare_mutation_file(
            "sb_inventory.json"
        )
        sales_log_file = self.simulation_manager.prepare_mutation_file(
            "sb_sales_log.json"
        )
        inventory_data = self.data_store.load_inventory_data(inventory_file)
        sales_rows = self.data_store.load_sales_rows(sales_log_file)
        generated_rows = []

        for month_start in self.month_starts(month_count):
            month_rows = self.monthly_sales(inventory_data, month_start)
            generated_rows.extend(month_rows)

        if not generated_rows:
            raise ValueError("Products no longer available!")

        sales_rows.extend(generated_rows)
        self.data_store.save_inventory_data(inventory_file, inventory_data)
        self.data_store.save_sales_rows(sales_log_file, sales_rows)
        return self.summary(generated_rows)

    def month_starts(self, month_count):
        """Return month starts for the requested window ending this month."""

        today = datetime.date.today()
        start_year, start_month = self.shift_month(
            today.year,
            today.month,
            -(month_count - 1),
        )
        return [
            datetime.date(year, month, self.first_month_day)
            for year, month in (
                self.shift_month(start_year, start_month, offset)
                for offset in range(month_count)
            )
        ]

    def monthly_sales(self, inventory_data, month_start):
        """Create one month of sales while reducing available inventory."""

        rows = []
        for _ in range(self.monthly_order_count):
            product = self.random_product(inventory_data)
            if product is None:
                break

            quantity = self.purchase_quantity(product)
            product["quant"] -= quantity
            if product["quant"] == 0:
                product["status"] = "not available"

            rows.append(self.sales_record(product, quantity, month_start))

        return rows

    def random_product(self, inventory_data):
        products = InventoryCatalog(inventory_data).available_products()
        if not products:
            return None

        return self.random.choice(products)

    def purchase_quantity(self, product):
        return self.random.randint(
            self.minimum_purchase_quantity,
            min(self.maximum_purchase_quantity, product["quant"]),
        )

    def sales_record(self, product, quantity, month_start):
        """Build one persisted sale row from the chosen product and date."""

        purchased_at = self.purchase_time(month_start)
        return {
            "item": product["item"],
            "price": product["price"],
            "quant": quantity,
            "shipping_cost": ShippingPolicy.company_shipping_cost,
            "status": "success",
            "date": purchased_at.date().isoformat(),
            "purchased_at": purchased_at.isoformat(timespec="seconds"),
            "simulation_month": month_start.strftime("%Y-%m"),
            "revenue": product["price"] * quantity,
        }

    def purchase_time(self, month_start):
        day = self.random.randint(
            self.first_month_day,
            self.last_month_day(month_start),
        )
        purchase_date = month_start.replace(day=day)
        return datetime.datetime.combine(
            purchase_date,
            datetime.time(self.midday_hour),
        )

    @staticmethod
    def shift_month(year, month, offset):
        month_index = year * 12 + month - 1 + offset
        return month_index // 12, month_index % 12 + 1

    @staticmethod
    def last_month_day(month_start):
        next_year, next_month = HistoricalSalesSimulator.shift_month(
            month_start.year,
            month_start.month,
            1,
        )
        next_month_start = datetime.date(next_year, next_month, 1)
        return (next_month_start - datetime.timedelta(days=1)).day

    @staticmethod
    def summary(rows):
        return {
            "orders": len(rows),
            "items": sum(row["quant"] for row in rows),
            "revenue": sum(row["revenue"] for row in rows),
        }
