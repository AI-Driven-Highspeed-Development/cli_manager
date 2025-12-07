"""Refresh script for cli_manager.

Copies admin_cli.txt to configured location. If the target filename changed
but an old file exists, creates new file without deleting old one.
"""

import os
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = Path.cwd()

sys.path.insert(0, str(PROJECT_ROOT))

from managers.config_manager import ConfigManager
from utils.logger_util import Logger


def refresh() -> None:
    """Copy admin_cli.txt to configured location."""
    logger = Logger(name="cli_manager.refresh")
    cm = ConfigManager()
    config = cm.config.cli_manager

    # Source template
    source = SCRIPT_DIR / "data" / "admin_cli.txt"
    if not source.exists():
        logger.error(f"Template not found: {source}")
        return

    # Target location from config
    output_dir = Path(config.admin_cli.output_dir)
    filename = config.admin_cli.filename
    target = output_dir / filename

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Check if target exists with different content
    if target.exists():
        with open(source, "r") as f:
            source_content = f.read()
        with open(target, "r") as f:
            target_content = f.read()

        if source_content == target_content:
            logger.debug(f"Admin CLI already up to date: {target}")
            return

        logger.info(f"Updating admin CLI: {target}")

    # Copy the file
    shutil.copy2(source, target)

    # Make executable on POSIX
    if os.name == "posix":
        os.chmod(target, 0o755)

    logger.info(f"Admin CLI created: {target}")

    # Ensure data directory exists
    data_path = Path(config.path.data)
    data_path.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    refresh()
