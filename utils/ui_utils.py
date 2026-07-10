from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich import box

console = Console()

def print_header(title):
    console.print(Panel(f"[bold cyan]{title}[/bold cyan]", expand=False, border_style="bright_blue"))

def print_error(msg):
    console.print(f"[bold red]❌ {msg}[/bold red]")

def print_success(msg):
    console.print(f"[bold green]✅ {msg}[/bold green]")

def create_table(title, columns):
    table = Table(title=title, box=box.ROUNDED, header_style="bold magenta")
    for col in columns:
        table.add_column(col)
    return table

def get_progress():
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console
    )
