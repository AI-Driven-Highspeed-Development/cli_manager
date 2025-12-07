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

## Template

```python
"""CLI commands and registration for <module_name>."""

import argparse
import sys

from <module_type>.<module_name>.<module_name> import <ModuleClass>
from managers.cli_manager import CLIManager, ModuleRegistration, Command, CommandArg


# ─────────────────────────────────────────────────────────────────────────────
# Handler Functions
# ─────────────────────────────────────────────────────────────────────────────

def example_command(args: argparse.Namespace) -> int:
    """Description of what this command does."""
    # Implementation
    return 0


def command_with_args(args: argparse.Namespace) -> int:
    """Command that uses arguments."""
    print(f"Received: {args.name}")
    return 0


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
