---
applyTo: "managers/**/*_cli.py, plugins/**/*_cli.py, utils/**/*_cli.py, mcps/**/*_cli.py"
---

# CLI Registration Script Guidelines

## Goals
- Standardize CLI command registration across all modules.
- Ensure all `*_cli.py` files integrate with the centralized `CLIManager`.
- Enable unified access via `admin_cli.py <module> <command>`.

## Rules

1. **File Structure**: Every `*_cli.py` MUST contain:
   - Handler functions that accept `argparse.Namespace` and return `int`
   - A `register_cli()` function that registers commands with `CLIManager`

2. **Handler Signature**: Each handler function MUST:
   - Accept `args: argparse.Namespace` as parameter
   - Return `int` (0 for success, non-zero for error)
   - Access arguments via `args.<argname>` (e.g., `args.key`)

3. **Handler Path Format**: Use `"<module_type>.<module_name>.<filename>:<function_name>"`:
   - Example: `"managers.secret_manager.secret_cli:list_secrets"`

4. **Registration Function**: MUST define `register_cli() -> None`:
   - Import `CLIManager, ModuleRegistration, Command, CommandArg` from `managers.cli_manager`
   - Use `CLIManager().register_module(ModuleRegistration(...))` to register

5. **Refresh Integration**: The module's `refresh.py` MUST call `register_cli()`:
   ```python
   from .<module>_cli import register_cli
   register_cli()
   ```

6. **Short Name**: Choose a concise, unique 2-4 letter alias for the module.

7. **User Feedback**: CLI handlers MUST provide output to the user:
   - Silent commands are NOT acceptable. Users need confirmation of what happened.
   - Use the `_print_result()` helper for consistent JSON output.
   - Handlers MUST return `_print_result(result)` where `result` is a dict with at least `{"success": bool}`.
   - Additional fields like `message`, `data`, or `error` are encouraged.

8. **Reserved Argument Names**: CLI commands MUST NOT use these argument names (they collide with argparse namespace):
   - `module` - reserved for module routing
   - `command` - reserved for command routing
   
   Use alternative names like `target_module`, `module_name`, `target_command`, `cmd_name`, etc.

## Template

```python
"""CLI commands and registration for <module_name>."""

from __future__ import annotations

import argparse
import json

from <module_type>.<module_name>.<module_name> import <ModuleClass>
from managers.cli_manager import CLIManager, ModuleRegistration, Command, CommandArg


# ─────────────────────────────────────────────────────────────────────────────
# Controller Access
# ─────────────────────────────────────────────────────────────────────────────

_controller: <ModuleClass> | None = None


def _get_controller() -> <ModuleClass>:
    """Get or create the controller instance."""
    global _controller
    if _controller is None:
        _controller = <ModuleClass>()
    return _controller


def _print_result(result: dict) -> int:
    """Print result as JSON and return exit code."""
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("success", True) else 1


# ─────────────────────────────────────────────────────────────────────────────
# Handler Functions
# ─────────────────────────────────────────────────────────────────────────────

def example_command(args: argparse.Namespace) -> int:
    """Description of what this command does."""
    result = _get_controller().do_something()
    return _print_result(result)


def command_with_args(args: argparse.Namespace) -> int:
    """Command that uses arguments."""
    result = _get_controller().process(name=args.name)
    return _print_result(result)


# ─────────────────────────────────────────────────────────────────────────────
# CLI Registration
# ─────────────────────────────────────────────────────────────────────────────

def register_cli() -> None:
    """Register <module_name> commands with CLIManager."""
    cli = CLIManager()
    cli.register_module(ModuleRegistration(
        module_name="<module_name>",
        short_name="<2-4 letter alias>",
        description="<Brief module description>",
        commands=[
            Command(
                name="example",
                help="Description of example command",
                handler="<module_type>.<module_name>.<module_name>_cli:example_command",
            ),
            Command(
                name="with-args",
                help="Command with arguments",
                handler="<module_type>.<module_name>.<module_name>_cli:command_with_args",
                args=[
                    CommandArg(name="name", help="Positional argument"),
                    CommandArg(name="--flag", short="-f", help="Optional flag", action="store_true"),
                    CommandArg(name="--count", short="-c", help="Integer option", type="int", default=1),
                ],
            ),
        ],
    ))
```

## CommandArg Reference

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Argument name. Positional if no `-`, optional if starts with `--` |
| `help` | str | Help text shown in `--help` |
| `short` | str | Short flag alias (e.g., `"-v"` for `--value`) |
| `type` | str | `"str"`, `"int"`, `"float"`, `"bool"` |
| `required` | bool | For optional args, whether required |
| `default` | Any | Default value if not provided |
| `nargs` | str | `"?"` (0 or 1), `"*"` (0+), `"+"` (1+) |
| `choices` | list | Restrict to specific values |
| `action` | str | `"store_true"`, `"store_false"`, `"count"` |

## Example: Complete Registration

```python
Command(
    name="download",
    help="Download a file",
    handler="managers.download_manager.download_cli:download_file",
    args=[
        CommandArg(name="url", help="URL to download"),
        CommandArg(name="--output", short="-o", help="Output path"),
        CommandArg(name="--quiet", short="-q", action="store_true", help="Suppress output"),
        CommandArg(name="--retries", type="int", default=3, help="Number of retries"),
    ],
)
```
