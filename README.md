# CLI Manager

Centralized CLI command registration and admin CLI generation for ADHD projects.

## Overview

- Modules register their CLI commands via `CLIManager.register_module()`
- Commands are stored in `./project/data/cli_manager/commands.json`
- `admin_cli.py` is copied to project root on refresh
- Supports module short names (aliases) for convenience
- Deduplication by module name; short_name conflicts are warned

## Features

- Dataclass-based command/argument definitions
- Singleton pattern for consistent state
- Dynamic handler resolution via `module.path:function_name`
- Argparse integration with nested subparsers
- Configurable admin CLI filename and output directory

## Quickstart

### 1. Register Commands (in your module)

Create a `cli_commands.py` in your module:

```python
from managers.cli_manager import CLIManager, ModuleRegistration, Command, CommandArg

def register_cli():
    cli = CLIManager()
    cli.register_module(ModuleRegistration(
        module_name="secret_manager",
        short_name="sm",
        description="Manage secrets securely",
        commands=[
            Command(
                name="list",
                help="List all secret keys",
                handler="managers.secret_manager.secret_cli:list_secrets",
            ),
            Command(
                name="get",
                help="Get a secret value",
                handler="managers.secret_manager.secret_cli:get_secret",
                args=[
                    CommandArg(name="key", help="The secret key"),
                ],
            ),
            Command(
                name="set",
                help="Set a secret value",
                handler="managers.secret_manager.secret_cli:set_secret",
                args=[
                    CommandArg(name="key", help="The secret key"),
                    CommandArg(name="--value", short="-v", help="Value (prompts if omitted)"),
                ],
            ),
        ],
    ))
```

Then call it from your module's `refresh.py`:

```python
from .cli_commands import register_cli
register_cli()
```

### 2. Run Refresh

```bash
python adhd_framework.py refresh
```

This:
- Copies `admin_cli.py` to project root
- Modules register their commands to `commands.json`

### 3. Use Admin CLI

```bash
# Full module name
python admin_cli.py secret_manager list
python admin_cli.py secret_manager get MY_KEY

# Short name alias
python admin_cli.py sm list
```

## API

```python
class CLIManager:
    def register_module(self, registration: ModuleRegistration) -> bool: ...
    def unregister_module(self, module_name: str) -> bool: ...
    def get_registry(self) -> dict[str, dict]: ...
    def list_modules(self) -> list[str]: ...
    def build_parser(self, prog: str, description: str) -> ArgumentParser: ...
    def dispatch(self, args: Namespace) -> int: ...
    def resolve_handler(self, handler_path: str) -> Callable | None: ...
    def get_admin_cli_path(self) -> Path: ...

@dataclass
class ModuleRegistration:
    module_name: str
    short_name: str | None = None
    description: str = ""
    commands: list[Command] = field(default_factory=list)

@dataclass
class Command:
    name: str
    help: str
    handler: str  # "module.path:function_name"
    args: list[CommandArg] = field(default_factory=list)

@dataclass
class CommandArg:
    name: str
    help: str = ""
    short: str | None = None  # e.g., "-v" for --value
    type: str = "str"  # str, int, float, bool
    required: bool = False
    default: Any = None
    nargs: str | None = None  # ?, *, +
    choices: list | None = None
    action: str | None = None  # store_true, store_false, count
```

## Configuration

In `.config`:

```json
{
  "cli_manager": {
    "path": {
      "data": "./project/data/cli_manager"
    },
    "admin_cli": {
      "filename": "admin_cli.py",
      "output_dir": "./"
    }
  }
}
```

## Handler Function Signature

Handler functions receive the parsed `argparse.Namespace`:

```python
def list_secrets(args: argparse.Namespace) -> int | None:
    """List all secrets. Return 0 or None for success, non-zero for error."""
    sm = SecretManager()
    for key in sm.list_secrets():
        print(f"  - {key}")
    return 0
```

## Data Structure

`./project/data/cli_manager/commands.json`:

```json
{
  "secret_manager": {
    "module_name": "secret_manager",
    "short_name": "sm",
    "description": "Manage secrets securely",
    "commands": [
      {
        "name": "list",
        "help": "List all secret keys",
        "handler": "managers.secret_manager.secret_cli:list_secrets",
        "args": []
      }
    ]
  }
}
```
