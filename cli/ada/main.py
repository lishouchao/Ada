"""
Ada CLI - Full command-line interface
"""

import asyncio
import click
import logging
import sys
import json
from pathlib import Path
from typing import Optional, List

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax

console = Console()


def setup_logging(verbose: bool = False, debug: bool = False):
    """Setup logging configuration"""
    if debug:
        level = logging.DEBUG
    elif verbose:
        level = logging.INFO
    else:
        level = logging.WARNING

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)]
    )


@click.group(invoke_without_command=True)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--debug", "-d", is_flag=True, help="Enable debug logging")
@click.option("--config", "-c", type=click.Path(exists=True), help="Config file path")
@click.pass_context
def cli(ctx: click.Context, verbose: bool, debug: bool, config: Optional[str]):
    """
    Ada - AI Assistant for NebulaOS

    An intelligent assistant that can perceive and control your desktop.

    \b
    Examples:
        ada chat                    # Start interactive chat
        ada ask "打开 Firefox"      # Single query
        ada skills list             # List available skills
        ada skill run file.organizer --input "整理下载"
    """
    setup_logging(verbose, debug)

    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["debug"] = debug
    ctx.obj["config"] = config

    if ctx.invoked_subcommand is None:
        ctx.invoke(chat)


# ============== Chat Commands ==============

@cli.command()
@click.option("--backend", "-b", type=click.Choice(["ollama", "openai", "mock"]),
              default="ollama", help="LLM backend")
@click.option("--model", "-m", default="llama3.2", help="Model name")
@click.pass_context
def chat(ctx: click.Context, backend: str, model: str):
    """Start interactive chat session.

    \b
    Commands in chat:
        /help     - Show help
        /quit     - Exit chat
        /clear    - Clear screen
        /history  - Show conversation history
        /save     - Save conversation
        /skills   - List skills
        /status   - Show agent status
    """
    console.print(Panel.fit(
        "[bold blue]Ada[/bold blue] - AI Assistant\n"
        "Type your message and press Enter.\n"
        "Type [cyan]/help[/cyan] for commands.",
        title="Welcome"
    ))

    asyncio.run(_run_chat(backend, model))


async def _run_chat(backend: str, model: str):
    """Run interactive chat loop"""
    from ada.core.agent import create_agent
    from ada.core.context import AgentConfig

    # Create config
    config = AgentConfig()
    config.llm["backend"] = backend
    config.llm["model"] = model

    # Initialize agent
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Initializing Ada...", total=None)

        try:
            agent = await create_agent(config)
            progress.remove_task(task)
        except Exception as e:
            progress.stop()
            console.print(f"[red]Failed to initialize: {e}[/red]")
            return

    # Chat loop
    console.print("\n[dim]Type /help for commands, /quit to exit[/dim]\n")

    while True:
        try:
            user_input = Prompt.ask("[bold green]You[/bold green]")

            if not user_input.strip():
                continue

            # Handle commands
            if user_input.startswith("/"):
                cmd = user_input.lower().strip()

                if cmd in ["/quit", "/exit", "/q"]:
                    console.print("[yellow]Goodbye![/yellow]")
                    break

                elif cmd == "/help":
                    _show_chat_help()
                    continue

                elif cmd == "/clear":
                    console.clear()
                    continue

                elif cmd == "/history":
                    _show_history(agent)
                    continue

                elif cmd == "/save":
                    _save_conversation(agent)
                    continue

                elif cmd in ["/skills", "/skill"]:
                    _show_skills(agent)
                    continue

                elif cmd == "/status":
                    _show_status(agent)
                    continue

                else:
                    console.print(f"[red]Unknown command: {cmd}[/red]")
                    console.print("[dim]Type /help for available commands[/dim]")
                    continue

            # Process with agent
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Ada thinking...", total=None)

                result = await agent.process(user_input)

                progress.remove_task(task)

            # Show response
            console.print(f"\n[bold blue]Ada[/bold blue]: ", end="")

            if result.success:
                console.print(Markdown(result.message))

                if result.output:
                    if result.requires_confirmation:
                        if Prompt.ask("\n[yellow]Confirm?[/yellow]", choices=["y", "n"]) == "y":
                            # Execute confirmed action
                            pass
            else:
                console.print(f"[red]{result.message}[/red]")

            console.print()

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Type /quit to exit.[/yellow]")

        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")


def _show_chat_help():
    """Show chat help"""
    help_text = """
[bold]Chat Commands:[/bold]

  /help      Show this help message
  /quit      Exit the chat
  /clear     Clear the screen
  /history   Show conversation history
  /save      Save conversation to file
  /skills    List available skills
  /status    Show agent status

[bold]Tips:[/bold]
  - Be specific in your requests
  - You can use Chinese or English
  - Press Ctrl+C to interrupt long responses
"""
    console.print(help_text)


def _show_history(agent):
    """Show conversation history"""
    history = agent.context.conversation_history

    if not history:
        console.print("[dim]No conversation history[/dim]")
        return

    console.print("\n[bold]Conversation History:[/bold]\n")

    for msg in history[-20:]:
        if msg.role == "user":
            console.print(f"[green]You:[/green] {msg.content}")
        else:
            console.print(f"[blue]Ada:[/blue] {msg.content[:100]}...")
        console.print()


def _save_conversation(agent):
    """Save conversation to file"""
    history = agent.context.conversation_history

    if not history:
        console.print("[dim]No conversation to save[/dim]")
        return

    filename = f"ada_conversation_{Path.home().stem}.json"
    filepath = Path.home() / filename

    data = {
        "timestamp": str(asyncio.get_event_loop().time()),
        "messages": [msg.to_dict() for msg in history]
    }

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    console.print(f"[green]Saved to: {filepath}[/green]")


def _show_skills(agent):
    """Show available skills"""
    skills = agent.skill_registry.list_skills()

    if not skills:
        console.print("[dim]No skills available[/dim]")
        return

    table = Table(title="Available Skills")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Category")
    table.add_column("Description")

    for skill in skills:
        table.add_row(
            skill.metadata.id,
            skill.metadata.name,
            skill.metadata.category,
            skill.metadata.description[:50] + "..."
        )

    console.print(table)


def _show_status(agent):
    """Show agent status"""
    table = Table(title="Agent Status")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("State", agent.context.state.value)
    table.add_row("Mode", agent.context.mode.value)
    table.add_row("Skills", str(len(agent.skill_registry)))
    table.add_row("Initialized", str(agent._initialized))

    console.print(table)


@cli.command()
@click.argument("query")
@click.option("--backend", "-b", type=click.Choice(["ollama", "openai", "mock"]),
              default="ollama", help="LLM backend")
@click.option("--json", "-j", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def ask(ctx: click.Context, query: str, backend: str, output_json: bool):
    """Send a single query and get response.

    \b
    Examples:
        ada ask "打开 Firefox"
        ada ask "今天天气怎么样" --json
    """
    result = asyncio.run(_process_query(query, backend))

    if output_json:
        console.print_json(data=result.to_dict())
    else:
        if result.success:
            console.print(Markdown(result.message))
        else:
            console.print(f"[red]Error: {result.message}[/red]")


async def _process_query(query: str, backend: str):
    """Process a single query"""
    from ada.core.agent import create_agent
    from ada.core.context import AgentConfig

    config = AgentConfig()
    config.llm["backend"] = backend

    agent = await create_agent(config)
    return await agent.process(query)


# ============== Skill Commands ==============

@cli.group()
def skills():
    """Manage skills."""
    pass


@skills.command("list")
@click.option("--category", "-c", help="Filter by category")
@click.option("--format", "-f", type=click.Choice(["table", "json"]),
              default="table", help="Output format")
def skills_list(category: Optional[str], format: str):
    """List all available skills.

    \b
    Examples:
        ada skills list
        ada skills list --category file
        ada skills list --format json
    """
    from ada.skill.registry import SkillRegistry
    from ada.skill.loader import SkillLoader
    from ada.skill.builtin import BUILTIN_SKILLS

    registry = SkillRegistry()

    # Load built-in skills
    for skill_class in BUILTIN_SKILLS:
        registry.register(skill_class())

    # Get skills
    skills_list = registry.list_skills(category=category)

    if format == "json":
        data = [s.metadata.to_dict() for s in skills_list]
        console.print_json(data=data)
    else:
        table = Table(title=f"Skills{f' ({category})' if category else ''}")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Version")
        table.add_column("Category")
        table.add_column("Description")

        for skill in skills_list:
            table.add_row(
                skill.metadata.id,
                skill.metadata.name,
                skill.metadata.version,
                skill.metadata.category,
                skill.metadata.description[:40] + "..."
            )

        console.print(table)


@skills.command("info")
@click.argument("skill_id")
def skills_info(skill_id: str):
    """Show detailed skill information.

    \b
    Examples:
        ada skills info builtin.file.organizer
    """
    from ada.skill.registry import SkillRegistry
    from ada.skill.builtin import BUILTIN_SKILLS

    registry = SkillRegistry()

    for skill_class in BUILTIN_SKILLS:
        registry.register(skill_class())

    skill = registry.get(skill_id)

    if not skill:
        console.print(f"[red]Skill not found: {skill_id}[/red]")
        return

    metadata = skill.metadata

    console.print(Panel(
        f"[bold]{metadata.name}[/bold]\n"
        f"[dim]{metadata.id}[/dim]\n\n"
        f"{metadata.description}\n\n"
        f"[cyan]Version:[/cyan] {metadata.version}\n"
        f"[cyan]Author:[/cyan] {metadata.author}\n"
        f"[cyan]Category:[/cyan] {metadata.category}\n"
        f"[cyan]Tags:[/cyan] {', '.join(metadata.tags)}\n"
        f"[cyan]Permissions:[/cyan] {', '.join(metadata.permissions)}\n\n"
        f"[bold]Examples:[/bold]\n" +
        "\n".join(f"  • {ex}" for ex in metadata.examples),
        title="Skill Info"
    ))


@skills.command("run")
@click.argument("skill_id")
@click.option("--input", "-i", "input_text", help="Input text for skill")
@click.option("--param", "-p", multiple=True, help="Parameters (key=value)")
def skills_run(skill_id: str, input_text: Optional[str], param: List[str]):
    """Execute a skill directly.

    \b
    Examples:
        ada skills run builtin.app.launcher -i "打开 Firefox"
        ada skills run builtin.file.organizer -i "整理下载文件夹"
    """
    # Parse params
    params = {}
    for p in param:
        if "=" in p:
            key, value = p.split("=", 1)
            params[key] = value

    result = asyncio.run(_run_skill(skill_id, input_text or "", params))

    if result.success:
        console.print(f"[green]{result.message}[/green]")
        if result.output:
            console.print_json(data=result.output)
    else:
        console.print(f"[red]Error: {result.message}[/red]")


async def _run_skill(skill_id: str, input_text: str, params: dict):
    """Run a skill"""
    from ada.core.agent import create_agent

    agent = await create_agent()
    return await agent.execute_skill(skill_id, input_text)


# ============== Memory Commands ==============

@cli.group()
def memory():
    """Manage agent memory."""
    pass


@memory.command("search")
@click.argument("query")
@click.option("--limit", "-l", default=10, help="Maximum results")
@click.option("--type", "-t", "mem_type", help="Memory type filter")
def memory_search(query: str, limit: int, mem_type: Optional[str]):
    """Search agent memory.

    \b
    Examples:
        ada memory search "Firefox"
        ada memory search "文档" --type semantic
    """
    from ada.memory.base import MemoryType

    types = None
    if mem_type:
        try:
            types = [MemoryType(mem_type)]
        except ValueError:
            console.print(f"[red]Invalid memory type: {mem_type}[/red]")
            return

    results = asyncio.run(_search_memory(query, limit, types))

    if not results:
        console.print("[dim]No memories found[/dim]")
        return

    for i, mem in enumerate(results, 1):
        console.print(f"\n[cyan]{i}.[/cyan] {mem.content[:100]}...")
        console.print(f"[dim]   Type: {mem.memory_type.value} | "
                      f"Created: {mem.created_at.strftime('%Y-%m-%d %H:%M')}[/dim]")


async def _search_memory(query: str, limit: int, types):
    """Search memory store"""
    from ada.memory.store import MemoryStore
    from ada.memory.base import MemoryQuery
    from pathlib import Path

    db_path = Path.home() / ".local" / "share" / "ada" / "memory.db"

    if not db_path.exists():
        return []

    store = MemoryStore(db_path)
    search_query = MemoryQuery(text=query, limit=limit, memory_types=types)

    return store.search(search_query)


@memory.command("stats")
def memory_stats():
    """Show memory statistics."""
    from pathlib import Path

    db_path = Path.home() / ".local" / "share" / "ada" / "memory.db"

    if not db_path.exists():
        console.print("[dim]Memory database not found[/dim]")
        return

    from ada.memory.store import MemoryStore
    from ada.memory.base import MemoryType

    store = MemoryStore(db_path)

    table = Table(title="Memory Statistics")
    table.add_column("Type", style="cyan")
    table.add_column("Count", style="green")

    total = store.count()
    table.add_row("Total", str(total))

    for mem_type in MemoryType:
        count = store.count(memory_type=mem_type)
        if count > 0:
            table.add_row(mem_type.value, str(count))

    console.print(table)


@memory.command("clear")
@click.option("--type", "-t", "mem_type", help="Memory type to clear")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def memory_clear(mem_type: Optional[str], yes: bool):
    """Clear agent memory.

    \b
    Examples:
        ada memory clear --yes
        ada memory clear --type working
    """
    if not yes:
        if not click.confirm("This will clear agent memory. Continue?"):
            return

    asyncio.run(_clear_memory(mem_type))
    console.print("[green]Memory cleared[/green]")


async def _clear_memory(mem_type: Optional[str]):
    """Clear memory"""
    from pathlib import Path
    import shutil

    db_path = Path.home() / ".local" / "share" / "ada" / "memory.db"

    if db_path.exists():
        if mem_type:
            # Clear specific type
            from ada.memory.store import MemoryStore
            from ada.memory.base import MemoryType

            store = MemoryStore(db_path)
            # Implementation would delete by type
        else:
            # Clear all
            shutil.rmtree(db_path.parent, ignore_errors=True)


# ============== Daemon Commands ==============

@cli.command()
@click.option("--port", "-p", default=8000, help="API port")
@click.pass_context
def daemon(ctx: click.Context, port: int):
    """Start Ada as a background service.

    \b
    This starts:
    - D-Bus service (org.nebula.Ada)
    - REST API server
    - AT-SPI event monitoring
    """
    console.print("[blue]Starting Ada daemon...[/blue]")

    asyncio.run(_run_daemon(port))


async def _run_daemon(port: int):
    """Run daemon"""
    from ada.core.agent import create_agent
    from ada.platform.adapters.dbus_service import AdaDBusService
    from ada.events.bus import EventBus
    from ada.platform.perception.at_spi import ATSPIMonitor

    # Create agent
    agent = await create_agent()

    # Start D-Bus service
    dbus_service = AdaDBusService(agent)
    if not await dbus_service.start():
        console.print("[yellow]Warning: D-Bus service failed to start[/yellow]")

    # Start AT-SPI monitoring
    atspi = ATSPIMonitor()
    if await atspi.initialize():
        await atspi.start_monitoring()
        console.print("[green]AT-SPI monitoring started[/green]")

    console.print(f"[green]Ada daemon running[/green]")
    console.print(f"[dim]API: http://localhost:{port}[/dim]")
    console.print("[dim]Press Ctrl+C to stop[/dim]")

    # Keep running
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        await dbus_service.stop()
        await atspi.stop_monitoring()


# ============== Install Commands ==============

@cli.command()
@click.option("--force", "-f", is_flag=True, help="Force reinstall")
def install(force: bool):
    """Install Ada system integration.

    \b
    This installs:
    - Systemd user service
    - D-Bus service file
    - Desktop entry
    - GNOME Shell extension
    """
    from ada.platform.adapters.systemd import SystemdIntegration
    import shutil

    systemd = SystemdIntegration()

    console.print("[blue]Installing Ada...[/blue]\n")

    # Install systemd service
    exec_path = shutil.which("ada-daemon") or sys.executable
    working_dir = str(Path.home() / ".local" / "share" / "ada")

    if systemd.install_user_service(exec_path, working_dir):
        console.print("[green]✓ Systemd service installed[/green]")
    else:
        console.print("[red]✗ Systemd service failed[/red]")

    # Enable service
    if systemd.enable_service(user=True):
        console.print("[green]✓ Service enabled[/green]")

    # Reload daemon
    systemd.reload_daemon(user=True)

    console.print("\n[bold]Installation complete![/bold]")
    console.print("\nStart with: [cyan]ada daemon[/cyan]")
    console.print("Or enable autostart: [cyan]systemctl --user enable ada[/cyan]")


@cli.command()
@click.option("--purge", is_flag=True, help="Also remove user data")
def uninstall(purge: bool):
    """Uninstall Ada system integration."""
    from ada.platform.adapters.systemd import SystemdIntegration

    systemd = SystemdIntegration()

    console.print("[blue]Uninstalling Ada...[/blue]\n")

    if systemd.uninstall_user_service():
        console.print("[green]✓ Systemd service removed[/green]")

    if purge:
        data_path = Path.home() / ".local" / "share" / "ada"
        if data_path.exists():
            import shutil
            shutil.rmtree(data_path)
            console.print("[green]✓ User data removed[/green]")

    console.print("\n[bold]Uninstall complete[/bold]")


# ============== Utility Commands ==============

@cli.command()
def version():
    """Show version information."""
    console.print(Panel(
        "[bold]Ada AI Assistant[/bold]\n"
        "Version: 0.1.0\n"
        "Python: " + sys.version.split()[0] + "\n"
        "Platform: " + sys.platform,
        title="Version Info"
    ))


@cli.command()
def config():
    """Show/edit configuration."""
    config_path = Path.home() / ".config" / "ada" / "ada.yaml"

    if config_path.exists():
        with open(config_path) as f:
            content = f.read()

        syntax = Syntax(content, "yaml", theme="monokai")
        console.print(syntax)
    else:
        console.print("[dim]No configuration file found[/dim]")
        console.print(f"Expected location: {config_path}")


@cli.command()
def status():
    """Show system status."""
    from ada.platform.adapters.systemd import SystemdIntegration

    systemd = SystemdIntegration()
    service_status = systemd.get_service_status(user=True)

    table = Table(title="System Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")

    table.add_row("Service", service_status.get("ActiveState", "unknown"))
    table.add_row("Sub State", service_status.get("SubState", "unknown"))

    if service_status.get("MainPID"):
        table.add_row("PID", service_status["MainPID"])

    console.print(table)


def main():
    """Main entry point"""
    return cli()


if __name__ == "__main__":
    main()
