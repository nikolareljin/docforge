"""Scan a repository and extract structured context for documentation generation."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional


# Maximum bytes to read from any single file to avoid runaway context.
_FILE_READ_LIMIT = 32 * 1024  # 32 KB

# File patterns mapped to section names.
_MANIFEST_NAMES = {
    "package.json",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "go.mod",
    "Cargo.toml",
    "composer.json",
    "Gemfile",
    "requirements.txt",
    "pom.xml",
    "build.gradle",
}

_ROUTE_PATTERNS = [
    "@app.route",
    "@router.",
    "@app.get",
    "@app.post",
    "@app.put",
    "@app.patch",
    "@app.delete",
    "router.GET",
    "router.POST",
    "router.PUT",
    "router.DELETE",
    "app.get(",
    "app.post(",
    "app.put(",
    "app.delete(",
]

_CLI_PATTERNS = [
    "@click.command",
    "@click.group",
    "cmd.AddCommand",
    "cobra.Command",
    "argparse.ArgumentParser",
    "add_argument(",
    "add_parser(",
    "Cli::new",
    "#[command]",
    "#[arg]",
]

_SKIP_DIRS = {
    ".git",
    ".github",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    ".env",
    "vendor",
    "dist",
    "build",
    ".next",
    ".nuxt",
    "target",
    "bin",
    "obj",
}

_SKIP_EXTS = {
    ".pyc",
    ".pyo",
    ".class",
    ".o",
    ".so",
    ".dll",
    ".exe",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".mp4",
    ".mp3",
    ".zip",
    ".tar",
    ".gz",
    ".lock",
    ".sum",
}


def _read_file(path: Path) -> str:
    """Read a file, truncating at _FILE_READ_LIMIT bytes."""
    try:
        raw = path.read_bytes()
        if len(raw) > _FILE_READ_LIMIT:
            raw = raw[:_FILE_READ_LIMIT]
            return raw.decode("utf-8", errors="replace") + "\n... [truncated]"
        return raw.decode("utf-8", errors="replace")
    except OSError:
        return ""


def _find_files_with_pattern(
    root: Path, patterns: list[str], exts: set[str]
) -> list[Path]:
    """Walk the repo and return files containing any of the given patterns."""
    matches: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for name in filenames:
            if Path(name).suffix in _SKIP_EXTS:
                continue
            if Path(name).suffix not in exts and exts:
                continue
            fpath = Path(dirpath) / name
            try:
                text = fpath.read_text(encoding="utf-8", errors="replace")
                if any(p in text for p in patterns):
                    matches.append(fpath)
            except OSError:
                continue
    return matches


class RepoAnalyzer:
    def __init__(self, repo_path: str) -> None:
        self.root = Path(repo_path).resolve()

    # ── Individual section extractors ────────────────────────────────────────

    def get_readme(self) -> Optional[str]:
        for name in ("README.md", "README.rst", "README.txt", "README"):
            p = self.root / name
            if p.exists():
                return f"## {name}\n\n{_read_file(p)}"
        return None

    def get_manifests(self) -> Optional[str]:
        parts: list[str] = []
        for name in _MANIFEST_NAMES:
            p = self.root / name
            if p.exists():
                parts.append(f"### {name}\n\n```\n{_read_file(p)}\n```")
        return "\n\n".join(parts) if parts else None

    def get_routes(self) -> Optional[str]:
        code_exts = {".py", ".ts", ".js", ".go", ".rb", ".php", ".rs", ".java", ".cs"}
        files = _find_files_with_pattern(self.root, _ROUTE_PATTERNS, code_exts)
        if not files:
            return None
        parts: list[str] = []
        for f in files[:10]:
            rel = f.relative_to(self.root)
            parts.append(
                f"### {rel}\n\n```{f.suffix.lstrip('.')}\n{_read_file(f)}\n```"
            )
        return "\n\n".join(parts)

    def get_cli(self) -> Optional[str]:
        code_exts = {".py", ".go", ".ts", ".js", ".rs", ".rb"}
        files = _find_files_with_pattern(self.root, _CLI_PATTERNS, code_exts)
        if not files:
            return None
        parts: list[str] = []
        for f in files[:8]:
            rel = f.relative_to(self.root)
            parts.append(
                f"### {rel}\n\n```{f.suffix.lstrip('.')}\n{_read_file(f)}\n```"
            )
        return "\n\n".join(parts)

    def get_config(self) -> Optional[str]:
        candidates = [
            ".env.example",
            ".env.sample",
            "config.example.yml",
            "config.example.yaml",
            "config.yml",
            "config.yaml",
            "settings.py",
            "config.py",
            "configuration.py",
        ]
        parts: list[str] = []
        for name in candidates:
            p = self.root / name
            if p.exists():
                parts.append(f"### {name}\n\n```\n{_read_file(p)}\n```")
        return "\n\n".join(parts) if parts else None

    def get_tests(self) -> Optional[str]:
        test_dirs = []
        for candidate in ("tests", "test", "spec", "__tests__", "e2e"):
            p = self.root / candidate
            if p.is_dir():
                test_dirs.append(p)

        if not test_dirs:
            return None

        parts: list[str] = []
        count = 0
        for tdir in test_dirs:
            for fpath in sorted(tdir.rglob("*"))[:5]:
                if fpath.is_file() and fpath.suffix not in _SKIP_EXTS:
                    rel = fpath.relative_to(self.root)
                    parts.append(
                        f"### {rel}\n\n```{fpath.suffix.lstrip('.')}\n{_read_file(fpath)}\n```"
                    )
                    count += 1
                    if count >= 5:
                        break
            if count >= 5:
                break
        return "\n\n".join(parts) if parts else None

    def get_docker(self) -> Optional[str]:
        parts: list[str] = []
        for name in (
            "Dockerfile",
            "docker-compose.yml",
            "docker-compose.yaml",
            "docker-compose.dev.yml",
        ):
            p = self.root / name
            if p.exists():
                ext = (
                    "yaml"
                    if name.endswith(".yml") or name.endswith(".yaml")
                    else "dockerfile"
                )
                parts.append(f"### {name}\n\n```{ext}\n{_read_file(p)}\n```")
        return "\n\n".join(parts) if parts else None

    def get_makefile(self) -> Optional[str]:
        p = self.root / "Makefile"
        if not p.exists():
            return None
        return f"### Makefile\n\n```makefile\n{_read_file(p)}\n```"

    def get_scripts(self) -> Optional[str]:
        scripts_dir = self.root / "scripts"
        if not scripts_dir.is_dir():
            return None
        parts: list[str] = []
        for fpath in sorted(scripts_dir.iterdir())[:6]:
            if fpath.is_file() and fpath.suffix in (".sh", ".bash", ".zsh", ""):
                rel = fpath.relative_to(self.root)
                parts.append(f"### {rel}\n\n```bash\n{_read_file(fpath)}\n```")
        return "\n\n".join(parts) if parts else None

    def get_git_log(self) -> Optional[str]:
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "-30"],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                return f"### Recent Git History\n\n```\n{result.stdout.strip()}\n```"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return None

    # ── Main entry point ─────────────────────────────────────────────────────

    def extract(self, sections: list[str]) -> dict[str, Optional[str]]:
        """Extract all requested sections and return a mapping of section → content."""
        extractors = {
            "readme": self.get_readme,
            "manifests": self.get_manifests,
            "routes": self.get_routes,
            "cli": self.get_cli,
            "config": self.get_config,
            "tests": self.get_tests,
            "docker": self.get_docker,
            "makefile": self.get_makefile,
            "scripts": self.get_scripts,
            "git_log": self.get_git_log,
        }
        result: dict[str, Optional[str]] = {}
        for section in sections:
            fn = extractors.get(section)
            if fn is not None:
                result[section] = fn()
        return result
