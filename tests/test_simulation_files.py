import json
import tempfile
import unittest
from pathlib import Path

from sales_analysis.simulation.simulation_files import SimulationFileManager


class SimulationFileManagerTest(unittest.TestCase):
    def write_json(self, path, data):
        path.write_text(json.dumps(data) + "\n", encoding="utf-8")

    def make_simulation_files(self, temp_dir, inventory_data):
        simulation_path = Path(temp_dir) / "simulation"
        simulation_path.mkdir()
        inventory_file = simulation_path / "sb_inventory.json"
        sales_file = simulation_path / "sb_sales_log.json"
        self.write_json(inventory_file, inventory_data)
        self.write_json(sales_file, [])
        return simulation_path, inventory_file

    def changed_inventory(self, category):
        return {"items": {category: [{"item": "Changed"}]}}

    def test_reset_restores_baseline(self):
        """Reset relinks the active files back to the saved hard-link baseline."""

        original_inventory = {"items": {"GPUs": []}}
        with tempfile.TemporaryDirectory() as temp_dir:
            simulation_path, inventory_file = self.make_simulation_files(
                temp_dir,
                original_inventory,
            )
            manager = SimulationFileManager(simulation_path)
            manager.ensure_baselines()
            mutation_file = manager.prepare_mutation_file("sb_inventory.json")
            self.write_json(mutation_file, self.changed_inventory("GPUs"))

            manager.reset_files()

            restored = json.loads(inventory_file.read_text(encoding="utf-8"))
            self.assertEqual(restored, original_inventory)

    def test_baseline_preserved(self):
        """Mutation must write a copied active file, not the reset baseline."""

        original_inventory = {"items": {"CPUs": []}}
        with tempfile.TemporaryDirectory() as temp_dir:
            simulation_path, inventory_file = self.make_simulation_files(
                temp_dir,
                original_inventory,
            )
            manager = SimulationFileManager(simulation_path)
            manager.ensure_baselines()
            mutation_file = manager.prepare_mutation_file("sb_inventory.json")
            changed_inventory = self.changed_inventory("CPUs")
            self.write_json(mutation_file, changed_inventory)

            baseline_file = (
                simulation_path / "hard_links" / "sb_inventory.json"
            )
            baseline = json.loads(baseline_file.read_text(encoding="utf-8"))
            active = json.loads(inventory_file.read_text(encoding="utf-8"))
            self.assertEqual(baseline, original_inventory)
            self.assertEqual(active, changed_inventory)


if __name__ == "__main__":
    unittest.main()
