from sales_analysis.project_paths import ProjectPaths


class SkillLoader:
    skill_path = ProjectPaths.skills / "sales_analysis_skill.md"
    max_skill_chars = 4000

    def __init__(self, skill_path=None):
        if skill_path:
            self.path = ProjectPaths.resolve(skill_path)
        else:
            self.path = self.skill_path

    def load(self):
        """Read the fixed internal skill and reject missing or oversized files."""

        if not self.path.exists():
            raise ValueError("Missing internal A.I. skill file.")

        skill_text = self.path.read_text(encoding="utf-8").strip()
        if not skill_text:
            raise ValueError("Internal A.I. skill file is empty.")

        if len(skill_text) > self.max_skill_chars:
            raise ValueError("Internal A.I. skill file is too large.")

        return skill_text
