import tempfile
import unittest
from pathlib import Path

from sales_analysis.ai.skill_loader import SkillLoader


class SkillLoaderTest(unittest.TestCase):
    def write_skill(self, text):
        temp_dir = tempfile.TemporaryDirectory()
        skill_path = Path(temp_dir.name) / "skill.md"
        skill_path.write_text(text, encoding="utf-8")
        return temp_dir, skill_path

    def test_load_returns_skill_text(self):
        temp_dir, skill_path = self.write_skill("Use short sales answers.")
        with temp_dir:
            skill = SkillLoader(skill_path).load()
            self.assertEqual(skill, "Use short sales answers.")

    def test_missing_skill_fails(self):
        with self.assertRaises(ValueError):
            SkillLoader("missing.md").load()

    def test_empty_skill_fails(self):
        temp_dir, skill_path = self.write_skill(" ")
        with temp_dir:
            with self.assertRaises(ValueError):
                SkillLoader(skill_path).load()

    def test_large_skill_fails(self):
        large_skill = "x" * (SkillLoader.max_skill_chars + 1)
        temp_dir, skill_path = self.write_skill(large_skill)
        with temp_dir:
            with self.assertRaises(ValueError):
                SkillLoader(skill_path).load()


if __name__ == "__main__":
    unittest.main()
