"""
CLI - Command-line interface for Ada
"""

import click
import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

console = Console()


def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stderr)
        ]
    )


@click.group(invoke_without_command=True)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--config", "-c", type=click.Path(exists=True), help="Config file path")
@click.pass_context
def main(ctx: click.Context, verbose: bool, config: Optional[str]):
    """
    Ada - AI Assistant for NebulaOS

    An intelligent assistant that can perceive and control your desktop.
    """
    setup_logging(verbose)

    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["config"] = config

    # If no command specified, start interactive mode
    if ctx.invoked_subcommand is None:
        ctx.invoke(chat)


@main.command()
@click.option("--backend", "-b", type=click.Choice(["ollama", "openai"]), default="ollama", help="LLM backend")
@click.pass_context
def chat(ctx: click.Context, backend: str):
    """Start interactive chat session"""
    console.print(Panel.fit(
        "[bold blue]Ada[/bold blue] - AI Assistant\n"
        "Type your message and press Enter to send.\n"
        "Type /help for commands, /quit to exit.",
        title="Welcome"
    ))

    # Initialize agent
    from ada.core.context import Agent, AgentConfig

    config = AgentConfig()
    agent = Agent(config)

    # Chat loop
    while True:
        try:
            user_input = Prompt.ask("\n[bold green]You[/bold green]")

            if not user_input.strip():
                continue

            # Handle commands
            if user_input.startswith("/"):
                cmd = user_input.lower().strip()

                if cmd in ["/quit", "/exit", "/q"]:
                    console.print("[yellow]Goodbye![/yellow]")
                    break

                elif cmd == "/help":
                    show_help()
                    continue

                elif cmd == "/clear":
                    console.clear()
                    continue

                elif cmd == "/status":
                    show_status(agent)
                    continue

                elif cmd == "/skills":
                    show_skills(agent)
                    continue

                else:
                    console.print(f"[red]Unknown command: {cmd}[/red]")
                    continue

            # Process with agent
            console.print("[dim]Thinking...[/dim]", end="\r")

            result = asyncio.run(agent.process(user_input))

            # Clear "thinking" message
            console.print(" " * 20, end="\r")

            # Show response
            console.print(f"\n[bold blue]Ada[/bold blue]: ", end="")
            console.print(Markdown(result.message))

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Type /quit to exit.[/yellow]")

        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")


def show_help():
    """Show help message"""
    help_text = """
[bold]Commands:[/bold]
  /help     - Show this help message
  /quit     - Exit the chat
  /clear    - Clear the screen
  /status   - Show agent status
  /skills   - List available skills
"""
    console.print(help_text)


def show_status(agent):
    """Show agent status"""
    status_text = f"""
[bold]Agent Status[/bold]
  Mode: {agent.mode.value if hasattr(agent, 'mode') else 'normal'}
  Skills: {len(agent._registry) if hasattr(agent, '_registry') else 0}
"""
    console.print(status_text)


def show_skills(agent):
    """Show available skills"""
    if not hasattr(agent, '_registry'):
        console.print("[red]Skills not loaded[/red]")
        return

    skills = agent._registry.list_skills()

    if not skills:
        console.print("[yellow]No skills available[/yellow]")
        return

    console.print("[bold]Available Skills:[/bold]\n")

    for skill in skills:
        console.print(f"  • {skill.metadata.name}")
        console.print(f"    [dim]{skill.metadata.description}[/dim]")


@main.command()
@click.argument("query")
@click.option("--backend", "-b", type=click.Choice(["ollama", "openai"]), default="ollama")
@click.pass_context
def ask(ctx: click.Context, query: str, backend: str):
    """Send a single query and get response"""
    from ada.core.context import Agent, AgentConfig

    config = AgentConfig()
    agent = Agent(config)

    result = asyncio.run(agent.process(query))

    console.print(result.message)


@main.command()
@click.argument("skill_id")
@click.argument("input_text", required=False)
@click.pass_context
def skill(ctx: click.Context, skill_id: str, input_text: Optional[str]):
    """Execute a skill directly"""
    console.print(f"[yellow]Executing skill: {skill_id}[/yellow]")

    # TODO: Implement skill execution
    console.print("[red]Skill execution not yet implemented[/red]")


@main.command()
@click.pass_context
def skills(ctx: click.Context):
    """List available skills"""
    from ada.skill.registry import SkillRegistry
    from ada.skill.loader import SkillLoader

    registry = SkillRegistry()
    loader = SkillLoader(registry)

    # Load builtin skills
    builtin_path = Path(__file__).parent.parent / "src" / "ada" / "skill" / "builtin"
    if builtin_path.exists():
        loader.load_from_directory(builtin_path, "builtin")

    skills = registry.list_skills()

    if not skills:
        console.print("[yellow]No skills found[/yellow]")
        return

    console.print("[bold]Available Skills:[/bold]\n")

    for skill in skills:
        console.print(f"[green]{skill.metadata.id}[/green]")
        console.print(f"  Name: {skill.metadata.name}")
        console.print(f"  Description: {skill.metadata.description}")
        console.print(f"  Category: {skill.metadata.category}")
        console.print()


@main.command()
@click.pass_context
def daemon(ctx: click.Context):
    """Start as daemon service"""
    console.print("[blue]Starting Ada daemon...[/blue]")

    from ada.core.context import Agent, AgentConfig
    from ada.platform.adapters import AdaDBusService

    config = AgentConfig()
    agent = Agent(config)

    # Start D-Bus service
    service = AdaDBusService(agent)

    async def run():
        if not await service.start():
            console.print("[red]Failed to start D-Bus service[/red]")
            return

        console.print("[green]Daemon started. Press Ctrl+C to stop.[/green]")

        # Keep running
        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            pass
        finally:
            await service.stop()

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Daemon stopped[/yellow]")


@main.command()
@click.option("--force", "-f", is_flag=True, help="Force installation")
@click.pass_context
def install(ctx: click.Context, force: bool):
    """Install system service and integration"""
    from ada.platform.adapters import SystemdIntegration

    systemd = SystemdIntegration()

    console.print("[blue]Installing Ada...[/blue]")

    # Install user service
    exec_path = sys.executable
    working_dir = str(Path.home() / ".local" / "share" / "ada")

    if systemd.install_user_service(exec_path, working_dir):
        console.print("[green]✓ User service installed[/green]")
    else:
        console.print("[red]✗ Failed to install user service[/red]")

    # Enable service
    if systemd.enable_service(user=True):
        console.print("[green]✓ Service enabled[/green]")

    console.print("\n[bold]Installation complete![/bold]")
    console.print("Start with: [cyan]ada daemon[/cyan]")


@main.command()
@click.option("--purge", is_flag=True, help="Also remove user data")
@click.pass_context
def uninstall(ctx: click.Context, purge: bool):
    """Uninstall system service"""
    from ada.platform.adapters import SystemdIntegration

    systemd = SystemdIntegration()

    console.print("[blue]Uninstalling Ada...[/blue]")

    if systemd.uninstall_user_service():
        console.print("[green]✓ User service uninstalled[/green]")

    if purge:
        console.print("[yellow]Removing user data...[/yellow]")
        # TODO: Remove user data


if __name__ == "__main__":
    main()
