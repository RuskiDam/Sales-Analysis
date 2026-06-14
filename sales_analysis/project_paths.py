from pathlib import Path


class ProjectPaths:
    """Routes package assets, root docs, root logs, and `.env` consistently."""

    package_root = Path(__file__).resolve().parent
    project_root = package_root.parent
    root = package_root
    data = package_root / "data"
    simulation = package_root / "simulation"
    logs = project_root / "logs"
    skills = package_root / "skills"
    docs = project_root / "docs"

    @classmethod
    def resolve(cls, path):
        """Resolve package-relative paths while keeping `.env` and docs at root."""

        resolved_path = Path(path)
        if resolved_path.is_absolute():
            return resolved_path

        if resolved_path.parts and resolved_path.parts[0] == "docs":
            return cls.project_root / resolved_path

        if resolved_path == Path(".env"):
            return cls.project_root / resolved_path

        return cls.root / resolved_path
