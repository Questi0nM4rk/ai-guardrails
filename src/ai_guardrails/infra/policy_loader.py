"""PolicyLoader — load org and team governance policies from TOML files."""

from __future__ import annotations

from pathlib import Path
import tomllib

from ai_guardrails.models.governance import OrgPolicy, TeamPolicy

_DEFAULT_ORG_CONFIG = Path.home() / ".guardrails" / "org.toml"
_TEAM_CONFIG_NAME = ".guardrails-team.toml"


def load_org_policy(*, org_config_path: Path | None = None) -> OrgPolicy | None:
    """Load org-level policy from ~/.guardrails/org.toml.

    Returns None if the file does not exist.
    """
    path = org_config_path or _DEFAULT_ORG_CONFIG
    if not path.exists():
        return None
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    return OrgPolicy.from_dict(data)


def load_team_policy(
    project_dir: Path,
    *,
    git_root: Path | None = None,
) -> TeamPolicy | None:
    """Walk up from project_dir to git_root looking for .guardrails-team.toml.

    Returns the policy from the closest ancestor that contains the file,
    or None if not found.
    """
    root = (git_root or _find_git_root(project_dir) or project_dir).resolve()
    current = project_dir.resolve()

    while True:
        candidate = current / _TEAM_CONFIG_NAME
        if candidate.exists():
            with candidate.open("rb") as fh:
                data = tomllib.load(fh)
            return TeamPolicy.from_dict(data)
        if current in {root, current.parent}:
            break
        current = current.parent

    return None


def _find_git_root(path: Path) -> Path | None:
    current = path.resolve()
    while True:
        if (current / ".git").exists():
            return current
        if current.parent == current:
            return None
        current = current.parent
