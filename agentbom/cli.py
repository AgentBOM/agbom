"""Command-line interface for AgentBOM."""

import sys
import json
import logging
from pathlib import Path
from typing import List, Optional

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from . import __version__
from .scanner import Scanner
from .models import AgentBOM

console = Console()


@click.group(invoke_without_command=True)
@click.pass_context
@click.version_option(version=__version__, prog_name="agentbom")
def cli(ctx):
    """AgentBOM - Discover, inventory, and understand AI agents across your codebase."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()
@click.option('--path', type=click.Path(exists=True), default=".", help='Local path to scan')
@click.option('--repo', help='GitHub repository (org/repo format)')
@click.option('--org', help='GitHub organization (scans all repos)')
@click.option('--out', default='agent_bom.json', help='Output file path')
@click.option('--stdout', is_flag=True, help='Output to stdout instead of file')
@click.option('--frameworks', default='langchain-py,langchain-ts',
              help='Comma-separated list of frameworks to detect')
@click.option('--llm', type=click.Choice(['auto', 'on', 'off']), default='auto',
              help='LLM enrichment mode')
@click.option('--include', help='Include file patterns (glob)')
@click.option('--exclude', help='Exclude file patterns (glob)')
@click.option('--max-file-mb', type=float, default=1.5, help='Maximum file size in MB')
@click.option('--parallel', type=int, default=8, help='Number of parallel workers')
@click.option('--strict/--no-strict', default=True, help='Strict mode (literal tool arrays)')
@click.option('--search/--no-search', default=True,
              help='Use smart search to filter org repos (recommended, only applies to --org)')
@click.option('--search-keywords', help='Custom search keywords (comma-separated, only applies to --org with --search)')
@click.option('--search-languages', help='Filter by languages (comma-separated, e.g., Python,TypeScript)')
@click.option('-v', '--verbose', is_flag=True, help='Verbose output')
@click.option('--quiet', is_flag=True, help='Quiet mode (minimal output)')
def scan(path, repo, org, out, stdout, frameworks, llm, include, exclude,
         max_file_mb, parallel, strict, search, search_keywords, search_languages,
         verbose, quiet):
    """Scan for AI agents in code."""
    # Set up logging
    if quiet:
        logging.basicConfig(level=logging.ERROR)
    elif verbose:
        logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(message)s')

    # Parse frameworks
    framework_list = [f.strip() for f in frameworks.split(',')]

    # Parse include/exclude patterns
    include_patterns = [p.strip() for p in include.split(',')] if include else []
    exclude_patterns = [p.strip() for p in exclude.split(',')] if exclude else []
    
    # Parse search options
    search_keywords_list = None
    if search_keywords:
        search_keywords_list = [k.strip() for k in search_keywords.split(',')]
    
    search_languages_list = None
    if search_languages:
        search_languages_list = [l.strip() for l in search_languages.split(',')]

    # Validate inputs
    if sum([bool(path != '.'), bool(repo), bool(org)]) > 1:
        console.print("[red]Error: Specify only one of --path, --repo, or --org[/red]")
        sys.exit(2)

    # Determine scan target
    scan_target = None
    scan_type = None

    if repo:
        scan_target = repo
        scan_type = 'repo'
    elif org:
        scan_target = org
        scan_type = 'org'
    else:
        scan_target = Path(path).resolve()
        scan_type = 'path'

    # Create scanner
    scanner = Scanner(
        frameworks=framework_list,
        strict_mode=strict,
        max_file_mb=max_file_mb,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        parallel=parallel,
        llm_mode=llm,
    )

    # Perform scan
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            disable=quiet,
        ) as progress:
            if scan_type == 'org':
                task = progress.add_task(f"Scanning organization {scan_target}...", total=None)
                bom = scanner.scan_org(
                    scan_target,
                    use_search=search,
                    search_keywords=search_keywords_list,
                    search_languages=search_languages_list
                )
            elif scan_type == 'repo':
                task = progress.add_task(f"Scanning repository {scan_target}...", total=None)
                bom = scanner.scan_repo(scan_target)
            else:
                task = progress.add_task(f"Scanning {scan_target}...", total=None)
                bom = scanner.scan_path(scan_target)

            progress.update(task, completed=True)

    except Exception as e:
        console.print(f"[red]Error during scan: {e}[/red]")
        sys.exit(3)

    # Output results
    if not quiet:
        _print_summary(bom)

    # Write output
    if stdout:
        print(bom.to_json())
    else:
        try:
            output_path = Path(out)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(bom.to_json())

            if not quiet:
                console.print(f"\n✅ Results written to {output_path}")

        except Exception as e:
            console.print(f"[red]Error writing output: {e}[/red]")
            sys.exit(1)

    # Exit with appropriate code
    if not bom.agents:
        if not quiet:
            console.print("[yellow]No agents found[/yellow]")

    sys.exit(0)


@cli.command()
@click.argument('file', type=click.Path(exists=True))
def validate(file):
    """Validate an Agent BOM file against the schema."""
    try:
        # Read file
        file_path = Path(file)
        content = file_path.read_text()
        data = json.loads(content)

        # Try to parse as AgentBOM
        bom = AgentBOM.model_validate(data)

        console.print(f"✅ [green]Valid Agent BOM file[/green]")
        console.print(f"   Agents found: {len(bom.agents)}")

        # Show summary
        if bom.agents:
            _print_summary(bom)

        sys.exit(0)

    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON: {e}[/red]")
        sys.exit(1)

    except Exception as e:
        console.print(f"[red]Schema validation failed: {e}[/red]")
        sys.exit(1)


@cli.command(name='rate-limit')
def rate_limit():
    """Check GitHub API rate limit status."""
    from .utils import GitHubClient
    from datetime import datetime
    
    client = GitHubClient()
    
    if not client.token:
        console.print("[yellow]⚠️  No GitHub token found. Set GITHUB_ACCESS_TOKEN for authenticated requests.[/yellow]")
        console.print("   Unauthenticated requests have much lower rate limits.\n")
    
    try:
        rate_info = client.check_rate_limit()
        
        if not rate_info:
            console.print("[red]Failed to check rate limit[/red]")
            sys.exit(1)
        
        # Core API limits
        core = rate_info.get('resources', {}).get('core', {})
        search = rate_info.get('resources', {}).get('search', {})
        
        table = Table(title="GitHub API Rate Limits")
        table.add_column("Resource", style="cyan")
        table.add_column("Remaining", style="yellow")
        table.add_column("Limit", style="green")
        table.add_column("Resets At", style="magenta")
        
        # Core API
        if core:
            reset_time = datetime.fromtimestamp(core.get('reset', 0))
            remaining = core.get('remaining', 0)
            limit = core.get('limit', 0)
            
            status = "✓" if remaining > limit * 0.2 else "⚠️"
            table.add_row(
                f"{status} Core API",
                str(remaining),
                str(limit),
                reset_time.strftime('%H:%M:%S')
            )
        
        # Search API
        if search:
            reset_time = datetime.fromtimestamp(search.get('reset', 0))
            remaining = search.get('remaining', 0)
            limit = search.get('limit', 0)
            
            status = "✓" if remaining > limit * 0.2 else "⚠️"
            table.add_row(
                f"{status} Search API",
                str(remaining),
                str(limit),
                reset_time.strftime('%H:%M:%S')
            )
        
        console.print(table)
        
        # Recommendations
        if search.get('remaining', 1) == 0:
            reset_time = datetime.fromtimestamp(search.get('reset', 0))
            console.print(f"\n[yellow]⚠️  Search API rate limit exhausted. Resets at {reset_time.strftime('%H:%M:%S')}[/yellow]")
            console.print("   Tip: The tool will automatically wait if you run a scan.")
        elif search.get('remaining', 100) < 10:
            console.print(f"\n[yellow]⚠️  Search API limit low: {search.get('remaining')} remaining[/yellow]")
            console.print("   Tip: Use --search with smart_mode (default) to reduce API calls.")
        else:
            console.print(f"\n[green]✓ Sufficient rate limit available[/green]")
        
        sys.exit(0)
        
    except Exception as e:
        console.print(f"[red]Error checking rate limit: {e}[/red]")
        sys.exit(1)


def _print_summary(bom: AgentBOM):
    """Print summary of detected agents."""
    if not bom.agents:
        return

    table = Table(title=f"Found {len(bom.agents)} Agent(s)")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="yellow")
    table.add_column("Framework", style="green")
    table.add_column("Language", style="blue")
    table.add_column("Tools", style="magenta")
    table.add_column("Owner", style="white")

    for agent in bom.agents:
        frameworks = ', '.join(agent.frameworks[:2])
        if len(agent.frameworks) > 2:
            frameworks += f' (+{len(agent.frameworks)-2})'

        table.add_row(
            agent.name,
            agent.type,
            frameworks,
            agent.language,
            str(agent.tools.count),
            agent.owner[:30] + '...' if len(agent.owner) > 30 else agent.owner
        )

    console.print(table)


def main():
    """Main entry point."""
    cli()


if __name__ == '__main__':
    main()