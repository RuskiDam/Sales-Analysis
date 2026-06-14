import json
import tempfile
import unittest
from pathlib import Path

from sales_analysis.data.sales_data import SalesDataStore
from sales_analysis.finance.shipping_policy import ShippingPolicy
from sales_analysis.simulation.historical_simulator import (
    HistoricalSalesSimulator,
)
from sales_analysis.simulation.simulation_files import SimulationFileManager


class HistoricalSalesSimulatorTest(unittest.TestCase):
    def write_json(self, path, data):
        path.write_text(json.dumps(data) + "\n", encoding="utf-8")

    def make_simulation_files(self, temp_dir):
        simulation_path = Path(temp_dir) / "simulation"
        simulation_path.mkdir()
        inventory_file = simulation_path / "sb_inventory.json"
        sales_file = simulation_path / "sb_sales_log.json"
        self.write_json(inventory_file, self.make_inventory())
        self.write_json(sales_file, [])
        return simulation_path, inventory_file, sales_file

    def make_inventory(self):
        return {
            "items": {
                "GPUs": [
                    {
                        "category": "GPUs",
                        "item": "Test GPU",
                        "price": 100.0,
                        "quant": 20,
                        "status": "available",
                    }
                ]
            }
        }

    def test_run_updates_sales(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            simulation_path, inventory_file, sales_file = (
                self.make_simulation_files(temp_dir)
            )
            manager = SimulationFileManager(simulation_path)
            simulator = HistoricalSalesSimulator(
                manager,
                SalesDataStore(),
                seed=1,
            )
            simulator.monthly_order_count = 3

            summary = simulator.run(1)

            sales_rows = json.loads(sales_file.read_text(encoding="utf-8"))
            inventory_data = json.loads(
                inventory_file.read_text(encoding="utf-8")
            )
            product = inventory_data["items"]["GPUs"][0]
            self.assertEqual(summary["orders"], 3)
            self.assertEqual(len(sales_rows), 3)
            self.assertEqual(
                sales_rows[0]["shipping_cost"],
                ShippingPolicy.company_shipping_cost,
            )
            self.assertLess(product["quant"], 20)


if __name__ == "__main__":
    unittest.main()
