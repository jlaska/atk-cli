"""atk version and completion commands."""

import typer
from rich.console import Console

from .. import __version__

console = Console()
app = typer.Typer(help="Version and shell completion.", context_settings={"help_option_names": ["-h", "--help"]})


@app.callback(invoke_without_command=True)
def version(ctx: typer.Context) -> None:
    """Show atk-cli version."""
    if ctx.invoked_subcommand is None:
        console.print(f"atk-cli {__version__}")


@app.command()
def completion(
    shell: str = typer.Argument(help="Shell: bash|zsh|fish"),
) -> None:
    """Print shell completion script."""
    shell = shell.lower()
    if shell == "bash":
        script = '_ATK_COMPLETE=bash_source atk'
    elif shell == "zsh":
        script = '_ATK_COMPLETE=zsh_source atk'
    elif shell == "fish":
        script = '_ATK_COMPLETE=fish_source atk'
    else:
        console.print(f"[red]Unsupported shell: {shell}. Use bash, zsh, or fish.[/red]")
        raise typer.Exit(1)

    console.print(f"# Add to your shell rc file:")
    console.print(f'eval "$({script})"')
