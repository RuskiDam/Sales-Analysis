import os
import shutil

from sales_analysis.project_paths import ProjectPaths


class SimulationFileManager:
    """Manages mutable simulation files while preserving reset baselines.

    Active simulation files start as hard links to baseline files. Before any
    mutation, the active link becomes a normal copy so reset data stays clean.
    """

    def __init__(self, simulation_path=None):
        self.simulation_path = ProjectPaths.resolve(
            simulation_path or ProjectPaths.simulation
        )
        self.baseline_path = self.simulation_path / "hard_links"
        self.file_names = ["sb_inventory.json", "sb_sales_log.json"]

    def ensure_baselines(self):
        """Create missing hard-link baselines or restore missing active files."""

        self.baseline_path.mkdir(parents=True, exist_ok=True)

        for file_name in self.file_names:
            active_file = self.simulation_path / file_name
            baseline_file = self.baseline_path / file_name

            if not active_file.exists() and not baseline_file.exists():
                raise FileNotFoundError(
                    f"Missing simulation file: {active_file}"
                )

            if not active_file.exists() and baseline_file.exists():
                os.link(baseline_file, active_file)
            elif active_file.exists() and not baseline_file.exists():
                os.link(active_file, baseline_file)

    def reset_files(self):
        """Replace changed active files with hard links to baseline files."""

        self.ensure_baselines()

        for file_name in self.file_names:
            active_file = self.simulation_path / file_name
            baseline_file = self.baseline_path / file_name

            active_is_not_baseline = (
                active_file.exists()
                and not active_file.samefile(baseline_file)
            )
            if active_is_not_baseline:
                active_file.unlink()
            elif active_file.exists():
                continue

            os.link(baseline_file, active_file)

    def prepare_mutation_file(self, file_name):
        """Return an active file path that can be changed without touching baseline."""

        self.ensure_baselines()
        active_file = self.simulation_path / file_name
        baseline_file = self.baseline_path / file_name

        # Break the hard link before writes so the baseline remains pristine.
        if active_file.samefile(baseline_file):
            temp_file = active_file.with_suffix(".tmp")
            shutil.copy2(active_file, temp_file)
            os.replace(temp_file, active_file)

        return active_file
