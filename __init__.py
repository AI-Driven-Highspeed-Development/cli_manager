"""cli_manager - Centralized CLI command registration and admin CLI generation."""

# Add path handling to work from the new nested directory structure
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.getcwd()  # Use current working directory as project root
sys.path.insert(0, project_root)

from managers.cli_manager.cli_manager import (
    CLIManager,
    Command,
    CommandArg,
    ModuleRegistration,
)

__all__ = [
    "CLIManager",
    "Command",
    "CommandArg",
    "ModuleRegistration",
]
