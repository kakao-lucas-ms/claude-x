"""Template Registry for managing external template packs.

This module handles:
1. Loading the registry of available template packs
2. Downloading and installing packs from GitHub
3. Managing attributions and licenses
4. Listing installed packs
"""

import json
import shutil
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import yaml


@dataclass
class TemplatePack:
    """Represents a template pack from the registry."""

    id: str
    name: str
    name_ko: Optional[str]
    description: str
    description_ko: Optional[str]
    source: str
    source_type: str = "github"
    branch: str = "main"
    path: str = ""
    license: str = "MIT"
    author: str = ""
    attribution: str = ""
    categories: List[str] = field(default_factory=list)
    template_count: int = 0
    bundled: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "TemplatePack":
        """Create from dictionary."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            name_ko=data.get("name_ko"),
            description=data.get("description", ""),
            description_ko=data.get("description_ko"),
            source=data.get("source", ""),
            source_type=data.get("source_type", "github"),
            branch=data.get("branch", "main"),
            path=data.get("path", ""),
            license=data.get("license", "MIT"),
            author=data.get("author", ""),
            attribution=data.get("attribution", ""),
            categories=data.get("categories", []),
            template_count=data.get("template_count", 0),
            bundled=data.get("bundled", False),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "name_ko": self.name_ko,
            "description": self.description,
            "description_ko": self.description_ko,
            "source": self.source,
            "source_type": self.source_type,
            "branch": self.branch,
            "path": self.path,
            "license": self.license,
            "author": self.author,
            "attribution": self.attribution,
            "categories": self.categories,
            "template_count": self.template_count,
            "bundled": self.bundled,
        }


class TemplateRegistry:
    """Manages template packs installation and updates."""

    def __init__(self):
        """Initialize the registry."""
        self._registry_path = Path(__file__).parent / "best_practices" / "registry.yaml"
        self._user_templates_path = Path.home() / ".claude-x" / "best_practices"
        self._installed_file = self._user_templates_path / "installed.json"
        self._attributions_file = self._user_templates_path / "ATTRIBUTIONS.md"
        self._packs: Dict[str, TemplatePack] = {}
        self._installed: Dict[str, dict] = {}
        self._loaded = False

    def _ensure_user_dir(self):
        """Ensure user templates directory exists."""
        self._user_templates_path.mkdir(parents=True, exist_ok=True)

    def _load_registry(self):
        """Load the registry from YAML file."""
        if self._loaded:
            return

        if self._registry_path.exists():
            with open(self._registry_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            for pack_data in data.get("packs", []):
                pack = TemplatePack.from_dict(pack_data)
                self._packs[pack.id] = pack

        # Load installed packs info
        if self._installed_file.exists():
            with open(self._installed_file, "r", encoding="utf-8") as f:
                self._installed = json.load(f)

        self._loaded = True

    def _save_installed(self):
        """Save installed packs info."""
        self._ensure_user_dir()
        with open(self._installed_file, "w", encoding="utf-8") as f:
            json.dump(self._installed, f, indent=2, ensure_ascii=False)

    def _update_attributions(self):
        """Update the ATTRIBUTIONS.md file."""
        self._ensure_user_dir()

        lines = [
            "# Template Pack Attributions",
            "",
            "This file lists the sources and licenses of installed template packs.",
            "",
        ]

        for pack_id, info in self._installed.items():
            pack = self._packs.get(pack_id)
            if pack:
                lines.extend([
                    f"## {pack.name}",
                    f"- **Source**: {pack.source}",
                    f"- **License**: {pack.license}",
                    f"- **Author**: {pack.author}",
                    f"- **Attribution**: {pack.attribution}",
                    f"- **Installed**: {info.get('installed_at', 'Unknown')}",
                    "",
                ])

        with open(self._attributions_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def list_available(self) -> List[TemplatePack]:
        """List all available packs from registry."""
        self._load_registry()
        return list(self._packs.values())

    def list_installed(self) -> List[dict]:
        """List installed packs with their info."""
        self._load_registry()
        result = []

        # Core is always "installed"
        if "core" in self._packs:
            result.append({
                "pack": self._packs["core"],
                "installed_at": "bundled",
                "path": str(self._registry_path.parent),
            })

        for pack_id, info in self._installed.items():
            if pack_id in self._packs:
                result.append({
                    "pack": self._packs[pack_id],
                    "installed_at": info.get("installed_at"),
                    "path": info.get("path"),
                })

        return result

    def get_pack(self, pack_id: str) -> Optional[TemplatePack]:
        """Get a specific pack by ID."""
        self._load_registry()
        return self._packs.get(pack_id)

    def is_installed(self, pack_id: str) -> bool:
        """Check if a pack is installed."""
        self._load_registry()
        if pack_id == "core":
            return True
        return pack_id in self._installed

    def install(self, pack_id: str, force: bool = False) -> dict:
        """Install a template pack.

        Args:
            pack_id: ID of the pack to install
            force: Force reinstall if already installed

        Returns:
            Installation result with status and details
        """
        self._load_registry()
        self._ensure_user_dir()

        pack = self._packs.get(pack_id)
        if not pack:
            return {
                "success": False,
                "error": f"Pack '{pack_id}' not found in registry",
            }

        if pack.bundled:
            return {
                "success": True,
                "message": f"Pack '{pack_id}' is bundled with claude-x",
                "already_installed": True,
            }

        if self.is_installed(pack_id) and not force:
            return {
                "success": True,
                "message": f"Pack '{pack_id}' is already installed. Use --force to reinstall.",
                "already_installed": True,
            }

        # Download from GitHub
        try:
            result = self._download_github_pack(pack)
            if result["success"]:
                # Record installation
                self._installed[pack_id] = {
                    "installed_at": datetime.now().isoformat(),
                    "path": result["path"],
                    "template_count": result.get("template_count", 0),
                }
                self._save_installed()
                self._update_attributions()

            return result

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to install pack: {str(e)}",
            }

    def _download_github_pack(self, pack: TemplatePack) -> dict:
        """Download templates from a GitHub repository."""
        # Parse GitHub URL
        # Format: https://github.com/owner/repo
        parts = pack.source.replace("https://github.com/", "").split("/")
        if len(parts) < 2:
            return {"success": False, "error": "Invalid GitHub URL"}

        owner, repo = parts[0], parts[1]

        # Create pack directory
        pack_dir = self._user_templates_path / pack.id
        if pack_dir.exists():
            shutil.rmtree(pack_dir)
        pack_dir.mkdir(parents=True)

        # Download README or main content
        readme_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{pack.branch}/README.md"
        try:
            self._download_file(readme_url, pack_dir / "README.md")
        except Exception:
            pass  # README is optional

        # Save pack metadata
        metadata = {
            "id": pack.id,
            "name": pack.name,
            "source": pack.source,
            "license": pack.license,
            "author": pack.author,
            "attribution": pack.attribution,
            "downloaded_at": datetime.now().isoformat(),
        }
        with open(pack_dir / "metadata.yaml", "w", encoding="utf-8") as f:
            yaml.dump(metadata, f, allow_unicode=True)

        # Try to download prompts/templates
        # This is a simplified version - real implementation would parse the repo structure
        templates_downloaded = self._download_repo_templates(owner, repo, pack, pack_dir)

        return {
            "success": True,
            "message": f"Installed {pack.name}",
            "path": str(pack_dir),
            "template_count": templates_downloaded,
            "attribution": pack.attribution,
        }

    def _download_file(self, url: str, dest: Path):
        """Download a file from URL."""
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "claude-x/0.6.0"}
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            with open(dest, "wb") as f:
                f.write(response.read())

    def _download_repo_templates(
        self, owner: str, repo: str, pack: TemplatePack, dest_dir: Path
    ) -> int:
        """Download templates from a GitHub repository.

        This is a simplified implementation that downloads the raw content.
        A full implementation would use the GitHub API to list files.
        """
        templates_count = 0

        # Try to get the repo contents via GitHub API (unauthenticated)
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{pack.path}"

        try:
            req = urllib.request.Request(
                api_url,
                headers={
                    "User-Agent": "claude-x/0.6.0",
                    "Accept": "application/vnd.github.v3+json",
                }
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                contents = json.loads(response.read().decode("utf-8"))

                if isinstance(contents, list):
                    for item in contents[:50]:  # Limit to 50 files
                        if item.get("type") == "file":
                            name = item.get("name", "")
                            if name.endswith((".md", ".txt", ".yaml", ".yml", ".json")):
                                download_url = item.get("download_url")
                                if download_url:
                                    try:
                                        self._download_file(
                                            download_url,
                                            dest_dir / name
                                        )
                                        templates_count += 1
                                    except Exception:
                                        pass  # Skip failed downloads

        except urllib.error.HTTPError as e:
            if e.code == 404:
                # Path doesn't exist, try root
                pass
            else:
                raise
        except Exception:
            pass

        # If no templates found via API, create a placeholder
        if templates_count == 0:
            placeholder = dest_dir / "templates.yaml"
            with open(placeholder, "w", encoding="utf-8") as f:
                yaml.dump({
                    "version": "1.0",
                    "source": pack.source,
                    "note": "Visit the source repository to see available templates",
                    "templates": [],
                }, f, allow_unicode=True)
            templates_count = 1

        return templates_count

    def uninstall(self, pack_id: str) -> dict:
        """Uninstall a template pack.

        Args:
            pack_id: ID of the pack to uninstall

        Returns:
            Uninstallation result
        """
        self._load_registry()

        pack = self._packs.get(pack_id)
        if not pack:
            return {"success": False, "error": f"Pack '{pack_id}' not found"}

        if pack.bundled:
            return {"success": False, "error": "Cannot uninstall bundled pack"}

        if not self.is_installed(pack_id):
            return {"success": False, "error": f"Pack '{pack_id}' is not installed"}

        # Remove directory
        pack_dir = self._user_templates_path / pack_id
        if pack_dir.exists():
            shutil.rmtree(pack_dir)

        # Remove from installed list
        del self._installed[pack_id]
        self._save_installed()
        self._update_attributions()

        return {
            "success": True,
            "message": f"Uninstalled {pack.name}",
        }


# Singleton instance
_registry: Optional[TemplateRegistry] = None


def get_registry() -> TemplateRegistry:
    """Get the singleton TemplateRegistry instance."""
    global _registry
    if _registry is None:
        _registry = TemplateRegistry()
    return _registry


def list_available_packs() -> List[TemplatePack]:
    """List all available template packs."""
    return get_registry().list_available()


def list_installed_packs() -> List[dict]:
    """List installed template packs."""
    return get_registry().list_installed()


def install_pack(pack_id: str, force: bool = False) -> dict:
    """Install a template pack."""
    return get_registry().install(pack_id, force)


def uninstall_pack(pack_id: str) -> dict:
    """Uninstall a template pack."""
    return get_registry().uninstall(pack_id)


def is_pack_installed(pack_id: str) -> bool:
    """Check if a pack is installed."""
    return get_registry().is_installed(pack_id)
