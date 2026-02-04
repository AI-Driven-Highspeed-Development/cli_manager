"""Tests for CLI Manager command registration and handler loading.

This validates the new cli_manager module for centralized command registration.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from cli_manager import (
    CLIManager,
    Command,
    CommandArg,
    ModuleRegistration,
)


class TestCommandArgDataclass:
    """Test CommandArg dataclass."""

    def test_command_arg_minimal(self):
        """CommandArg with just name should work."""
        arg = CommandArg(name="--value")
        assert arg.name == "--value"
        assert arg.help == ""
        assert arg.type == "str"
        assert arg.required is False

    def test_command_arg_full(self):
        """CommandArg with all fields should work."""
        arg = CommandArg(
            name="--count",
            help="Number of items",
            short="-c",
            type="int",
            required=True,
            default=10,
            nargs="+",
            choices=[1, 5, 10],
            action=None,
        )
        assert arg.name == "--count"
        assert arg.short == "-c"
        assert arg.type == "int"
        assert arg.required is True
        assert arg.default == 10

    def test_command_arg_to_dict(self):
        """to_dict should return non-None values only."""
        arg = CommandArg(name="--value", help="A value", type="str")
        d = arg.to_dict()
        
        assert d["name"] == "--value"
        assert d["help"] == "A value"
        assert d["type"] == "str"
        # None values should be excluded
        assert "action" not in d or d["action"] is not None


class TestCommandDataclass:
    """Test Command dataclass."""

    def test_command_minimal(self):
        """Command with required fields should work."""
        cmd = Command(
            name="run",
            help="Run the task",
            handler="mymodule:run_handler",
        )
        assert cmd.name == "run"
        assert cmd.handler == "mymodule:run_handler"
        assert cmd.args == []

    def test_command_with_args(self):
        """Command with arguments should work."""
        cmd = Command(
            name="build",
            help="Build the project",
            handler="mymodule:build_handler",
            args=[
                CommandArg(name="--target", help="Build target"),
                CommandArg(name="--verbose", short="-v", action="store_true"),
            ],
        )
        assert len(cmd.args) == 2

    def test_command_to_dict(self):
        """to_dict should serialize command and args."""
        cmd = Command(
            name="test",
            help="Run tests",
            handler="tests:run",
            args=[CommandArg(name="--filter")],
        )
        d = cmd.to_dict()
        
        assert d["name"] == "test"
        assert d["help"] == "Run tests"
        assert d["handler"] == "tests:run"
        assert len(d["args"]) == 1


class TestModuleRegistrationDataclass:
    """Test ModuleRegistration dataclass."""

    def test_module_registration_minimal(self):
        """ModuleRegistration with just module_name should work."""
        reg = ModuleRegistration(module_name="my_module")
        assert reg.module_name == "my_module"
        assert reg.short_name is None
        assert reg.commands == []

    def test_module_registration_full(self):
        """ModuleRegistration with all fields should work."""
        reg = ModuleRegistration(
            module_name="config_manager",
            short_name="cfg",
            description="Configuration management",
            commands=[
                Command(name="show", help="Show config", handler="config:show"),
            ],
        )
        assert reg.module_name == "config_manager"
        assert reg.short_name == "cfg"
        assert len(reg.commands) == 1

    def test_module_registration_to_dict(self):
        """to_dict should serialize registration completely."""
        reg = ModuleRegistration(
            module_name="test_module",
            short_name="tm",
            description="Test module",
            commands=[
                Command(name="run", help="Run", handler="test:run"),
            ],
        )
        d = reg.to_dict()
        
        assert d["module_name"] == "test_module"
        assert d["short_name"] == "tm"
        assert d["description"] == "Test module"
        assert len(d["commands"]) == 1


class TestCLIManagerSingleton:
    """Test CLIManager singleton behavior."""

    def test_cli_manager_is_singleton(self):
        """CLIManager should return same instance."""
        # Reset singleton for test
        CLIManager._instance = None
        
        with patch.object(CLIManager, '_ensure_data_dir'):
            m1 = CLIManager()
            m2 = CLIManager()
        
        assert m1 is m2

    def test_cli_manager_reinit_safe(self):
        """Multiple __init__ calls should be safe."""
        CLIManager._instance = None
        
        with patch.object(CLIManager, '_ensure_data_dir'):
            m = CLIManager()
            # Second init should not fail
            m.__init__()


class TestCLIManagerRegistry:
    """Test command registry operations."""

    @pytest.fixture
    def cli_manager(self, tmp_path: Path) -> CLIManager:
        """Create a CLIManager with isolated data directory."""
        CLIManager._instance = None
        
        # Mock ConfigManager to return test path
        mock_config = MagicMock()
        mock_config.config.cli_manager.path.data = str(tmp_path / "data")
        
        with patch('cli_manager.cli_manager.ConfigManager', return_value=mock_config):
            manager = CLIManager()
        
        return manager

    def test_register_module(self, cli_manager: CLIManager):
        """register_module should add module to registry."""
        reg = ModuleRegistration(
            module_name="test_module",
            description="Test",
            commands=[
                Command(name="run", help="Run", handler="test:run"),
            ],
        )
        
        result = cli_manager.register_module(reg)
        assert result is True
        
        registry = cli_manager.get_registry()
        assert "test_module" in registry

    def test_register_module_overwrites_existing(self, cli_manager: CLIManager):
        """Registering same module should overwrite."""
        reg1 = ModuleRegistration(
            module_name="test_module",
            description="Version 1",
        )
        reg2 = ModuleRegistration(
            module_name="test_module",
            description="Version 2",
        )
        
        cli_manager.register_module(reg1)
        cli_manager.register_module(reg2)
        
        registry = cli_manager.get_registry()
        assert registry["test_module"]["description"] == "Version 2"

    def test_unregister_module(self, cli_manager: CLIManager):
        """unregister_module should remove module from registry."""
        reg = ModuleRegistration(module_name="to_remove")
        cli_manager.register_module(reg)
        
        result = cli_manager.unregister_module("to_remove")
        assert result is True
        
        registry = cli_manager.get_registry()
        assert "to_remove" not in registry

    def test_unregister_nonexistent_returns_false(self, cli_manager: CLIManager):
        """unregister_module for nonexistent module should return False."""
        result = cli_manager.unregister_module("nonexistent")
        assert result is False

    def test_list_modules(self, cli_manager: CLIManager):
        """list_modules should return all registered module names."""
        # Clear any existing registry first
        cli_manager._save_registry({})
        
        cli_manager.register_module(ModuleRegistration(module_name="mod1"))
        cli_manager.register_module(ModuleRegistration(module_name="mod2"))
        
        modules = cli_manager.list_modules()
        assert set(modules) == {"mod1", "mod2"}

    def test_short_name_conflict_warning(self, cli_manager: CLIManager):
        """Conflicting short_name should be ignored with warning."""
        reg1 = ModuleRegistration(module_name="mod1", short_name="m")
        reg2 = ModuleRegistration(module_name="mod2", short_name="m")
        
        cli_manager.register_module(reg1)
        cli_manager.register_module(reg2)
        
        registry = cli_manager.get_registry()
        # First keeps short_name, second should have it cleared
        assert registry["mod1"]["short_name"] == "m"
        assert registry["mod2"]["short_name"] is None


class TestCLIManagerParserBuilding:
    """Test argparse parser building."""

    @pytest.fixture
    def cli_manager(self, tmp_path: Path) -> CLIManager:
        """Create a CLIManager with isolated data directory."""
        CLIManager._instance = None
        
        mock_config = MagicMock()
        mock_config.config.cli_manager.path.data = str(tmp_path / "data")
        
        with patch('cli_manager.cli_manager.ConfigManager', return_value=mock_config):
            manager = CLIManager()
        
        return manager

    def test_build_parser_with_no_modules(self, cli_manager: CLIManager):
        """build_parser should work with empty registry."""
        parser = cli_manager.build_parser()
        
        assert parser is not None
        assert parser.prog == "admin_cli"

    def test_build_parser_with_module(self, cli_manager: CLIManager):
        """build_parser should include registered modules as subparsers."""
        reg = ModuleRegistration(
            module_name="test_mod",
            description="Test module",
            commands=[
                Command(name="run", help="Run command", handler="test:run"),
            ],
        )
        cli_manager.register_module(reg)
        
        parser = cli_manager.build_parser()
        
        # Parse args to test structure
        args = parser.parse_args(["test_mod", "run"])
        assert args.module == "test_mod"
        assert args.command == "run"

    def test_build_parser_with_short_name(self, cli_manager: CLIManager):
        """Parser should support short_name aliases."""
        reg = ModuleRegistration(
            module_name="config_manager",
            short_name="cfg",
            commands=[
                Command(name="show", help="Show config", handler="config:show"),
            ],
        )
        cli_manager.register_module(reg)
        
        parser = cli_manager.build_parser()
        
        # Should work with both full name and short name
        args1 = parser.parse_args(["config_manager", "show"])
        args2 = parser.parse_args(["cfg", "show"])
        
        assert args1._cli_module == "config_manager"
        assert args2._cli_module == "config_manager"

    def test_build_parser_with_command_args(self, cli_manager: CLIManager):
        """Parser should handle command arguments correctly."""
        reg = ModuleRegistration(
            module_name="test_mod",
            commands=[
                Command(
                    name="process",
                    help="Process files",
                    handler="test:process",
                    args=[
                        CommandArg(name="--count", short="-c", type="int", default=1),
                        CommandArg(name="--verbose", short="-v", action="store_true"),
                    ],
                ),
            ],
        )
        cli_manager.register_module(reg)
        
        parser = cli_manager.build_parser()
        
        args = parser.parse_args(["test_mod", "process", "-c", "5", "-v"])
        assert args.count == 5
        assert args.verbose is True

    def test_build_parser_custom_prog(self, cli_manager: CLIManager):
        """build_parser should accept custom prog name."""
        parser = cli_manager.build_parser(prog="my_cli", description="My CLI")
        
        assert parser.prog == "my_cli"
        assert "My CLI" in parser.description


class TestHandlerLoading:
    """Test handler function loading from handler strings."""

    @pytest.fixture
    def cli_manager(self, tmp_path: Path) -> CLIManager:
        """Create a CLIManager with isolated data directory."""
        CLIManager._instance = None
        
        mock_config = MagicMock()
        mock_config.config.cli_manager.path.data = str(tmp_path / "data")
        
        with patch('cli_manager.cli_manager.ConfigManager', return_value=mock_config):
            manager = CLIManager()
        
        return manager

    def test_resolve_handler_valid_format(self, cli_manager: CLIManager):
        """resolve_handler should load function from 'module:function' format."""
        # Using a real stdlib module for testing
        handler = cli_manager.resolve_handler("json:dumps")
        assert handler is json.dumps

    def test_resolve_handler_nested_module(self, cli_manager: CLIManager):
        """resolve_handler should work with nested module paths."""
        handler = cli_manager.resolve_handler("os.path:join")
        import os.path
        assert handler is os.path.join

    def test_resolve_handler_invalid_format_returns_none(self, cli_manager: CLIManager):
        """resolve_handler should return None for invalid handler format."""
        # The implementation logs error and returns None instead of raising
        result = cli_manager.resolve_handler("invalid_no_colon")
        assert result is None

    def test_resolve_handler_missing_module_returns_none(self, cli_manager: CLIManager):
        """resolve_handler should return None for non-existent module."""
        result = cli_manager.resolve_handler("nonexistent_module_12345:func")
        assert result is None

    def test_resolve_handler_missing_function_returns_none(self, cli_manager: CLIManager):
        """resolve_handler should return None for non-existent function."""
        result = cli_manager.resolve_handler("json:nonexistent_func_12345")
        assert result is None
