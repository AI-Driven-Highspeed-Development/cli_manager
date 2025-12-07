"""CLI Manager for centralized command registration and admin CLI generation."""

from __future__ import annotations

import argparse
import importlib
import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Optional

from managers.config_manager import ConfigManager
from utils.logger_util import Logger


@dataclass
class CommandArg:
    """Represents a command argument."""
    name: str
    help: str = ""
    short: Optional[str] = None  # e.g., "-v" for --value
    type: str = "str"  # str, int, float, bool
    required: bool = False
    default: Any = None
    nargs: Optional[str] = None  # ?, *, +
    choices: Optional[list] = None
    action: Optional[str] = None  # store_true, store_false, count

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class Command:
    """Represents a CLI subcommand."""
    name: str
    help: str
    handler: str  # module.path:function_name
    args: list[CommandArg] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "help": self.help,
            "handler": self.handler,
            "args": [arg.to_dict() for arg in self.args],
        }


@dataclass
class ModuleRegistration:
    """Represents a module's CLI registration."""
    module_name: str
    short_name: Optional[str] = None
    description: str = ""
    commands: list[Command] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "module_name": self.module_name,
            "short_name": self.short_name,
            "description": self.description,
            "commands": [cmd.to_dict() for cmd in self.commands],
        }


class CLIManager:
    """Manages CLI command registration and parser building for admin CLI."""

    _instance: Optional[CLIManager] = None

    def __new__(cls, *args, **kwargs) -> CLIManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True

        self.logger = Logger(name=__class__.__name__)
        self.config = ConfigManager().config.cli_manager

        self._data_path = Path(self.config.path.data)
        self._registry_file = self._data_path / "commands.json"

        self._ensure_data_dir()

    def _ensure_data_dir(self) -> None:
        """Ensure the data directory exists."""
        self._data_path.mkdir(parents=True, exist_ok=True)
        if not self._registry_file.exists():
            self._save_registry({})

    def _load_registry(self) -> dict[str, dict]:
        """Load the command registry from disk."""
        if not self._registry_file.exists():
            return {}
        try:
            with open(self._registry_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            self.logger.warning(f"Failed to load registry: {e}")
            return {}

    def _save_registry(self, registry: dict[str, dict]) -> None:
        """Save the command registry to disk."""
        try:
            with open(self._registry_file, "w") as f:
                json.dump(registry, f, indent=2)
        except IOError as e:
            self.logger.error(f"Failed to save registry: {e}")

    def register_module(self, registration: ModuleRegistration) -> bool:
        """Register a module's commands. Handles deduplication by module_name."""
        registry = self._load_registry()

        module_key = registration.module_name

        # Check for short_name conflicts
        if registration.short_name:
            for key, existing in registry.items():
                if key != module_key and existing.get("short_name") == registration.short_name:
                    self.logger.warning(
                        f"Short name '{registration.short_name}' already used by "
                        f"'{existing['module_name']}'. Ignoring short_name for '{module_key}'."
                    )
                    registration.short_name = None
                    break

        registry[module_key] = registration.to_dict()
        self._save_registry(registry)
        self.logger.debug(f"Registered module: {module_key}")
        return True

    def unregister_module(self, module_name: str) -> bool:
        """Unregister a module's commands."""
        registry = self._load_registry()
        if module_name in registry:
            del registry[module_name]
            self._save_registry(registry)
            self.logger.debug(f"Unregistered module: {module_name}")
            return True
        return False

    def get_registry(self) -> dict[str, dict]:
        """Get the current command registry."""
        return self._load_registry()

    def list_modules(self) -> list[str]:
        """List all registered module names."""
        return list(self._load_registry().keys())

    def build_parser(
        self,
        prog: str = "admin_cli",
        description: str = "Project Admin CLI",
    ) -> argparse.ArgumentParser:
        """Build an argparse parser from the registry."""
        parser = argparse.ArgumentParser(
            prog=prog,
            description=description,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        subparsers = parser.add_subparsers(
            dest="module",
            title="modules",
            description="Available modules",
            help="Module to invoke",
        )

        registry = self._load_registry()

        for module_key, module_data in registry.items():
            module_name = module_data["module_name"]
            short_name = module_data.get("short_name")
            module_desc = module_data.get("description", "")

            # Create aliases if short_name exists
            aliases = [short_name] if short_name else []

            module_parser = subparsers.add_parser(
                module_name,
                aliases=aliases,
                help=module_desc or f"Commands for {module_name}",
            )

            # Add command subparsers
            cmd_subparsers = module_parser.add_subparsers(
                dest="command",
                title="commands",
                description=f"Available commands for {module_name}",
                help="Command to run",
            )

            for cmd_data in module_data.get("commands", []):
                cmd_parser = cmd_subparsers.add_parser(
                    cmd_data["name"],
                    help=cmd_data.get("help", ""),
                )

                # Add arguments
                for arg_data in cmd_data.get("args", []):
                    self._add_argument(cmd_parser, arg_data)

        return parser

    def _add_argument(self, parser: argparse.ArgumentParser, arg_data: dict) -> None:
        """Add an argument to a parser based on arg_data dict."""
        name = arg_data["name"]
        short = arg_data.get("short")
        is_positional = not name.startswith("-")

        kwargs = {}

        if "help" in arg_data:
            kwargs["help"] = arg_data["help"]

        if "default" in arg_data and arg_data["default"] is not None:
            kwargs["default"] = arg_data["default"]

        if "nargs" in arg_data and arg_data["nargs"]:
            kwargs["nargs"] = arg_data["nargs"]

        if "choices" in arg_data and arg_data["choices"]:
            kwargs["choices"] = arg_data["choices"]

        if "action" in arg_data and arg_data["action"]:
            kwargs["action"] = arg_data["action"]
        else:
            # Handle type conversion
            type_map = {"str": str, "int": int, "float": float, "bool": bool}
            arg_type = arg_data.get("type", "str")
            if arg_type in type_map and "action" not in kwargs:
                kwargs["type"] = type_map[arg_type]

        if not is_positional:
            kwargs["required"] = arg_data.get("required", False)

        if is_positional:
            parser.add_argument(name, **kwargs)
        elif short:
            parser.add_argument(short, name, **kwargs)
        else:
            parser.add_argument(name, **kwargs)

    def resolve_handler(self, handler_path: str) -> Optional[Callable]:
        """Resolve a handler string to a callable.

        Handler format: 'module.path:function_name'
        """
        try:
            module_path, func_name = handler_path.rsplit(":", 1)
            module = importlib.import_module(module_path)
            return getattr(module, func_name)
        except (ValueError, ImportError, AttributeError) as e:
            self.logger.error(f"Failed to resolve handler '{handler_path}': {e}")
            return None

    def dispatch(self, args: argparse.Namespace) -> int:
        """Dispatch parsed args to the appropriate handler.

        Returns exit code (0 for success, non-zero for failure).
        """
        if not args.module:
            return 1

        registry = self._load_registry()

        # Find module by name or short_name
        module_data = None
        for data in registry.values():
            if data["module_name"] == args.module:
                module_data = data
                break
            if data.get("short_name") == args.module:
                module_data = data
                break

        if not module_data:
            self.logger.error(f"Module '{args.module}' not found in registry")
            return 1

        if not args.command:
            return 1

        # Find command
        cmd_data = None
        for cmd in module_data.get("commands", []):
            if cmd["name"] == args.command:
                cmd_data = cmd
                break

        if not cmd_data:
            self.logger.error(f"Command '{args.command}' not found in module '{args.module}'")
            return 1

        handler = self.resolve_handler(cmd_data["handler"])
        if not handler:
            return 1

        try:
            result = handler(args)
            return 0 if result is None else int(result)
        except Exception as e:
            self.logger.error(f"Error executing command: {e}")
            return 1

    def get_admin_cli_path(self) -> Path:
        """Get the configured path for admin_cli.py."""
        output_dir = Path(self.config.admin_cli.output_dir)
        filename = self.config.admin_cli.filename
        return output_dir / filename
