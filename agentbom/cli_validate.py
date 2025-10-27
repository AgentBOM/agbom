"""CLI command for policy validation."""

import sys
from pathlib import Path

import click
from rich.console import Console

from .policy import RulesetLoader, PolicyEngine, PolicyReport


console = Console()


@click.command()
@click.option(
    "--path", 
    type=click.Path(exists=True, file_okay=False, dir_okay=True), 
    default=".",
    help="Path to scan for policy violations"
)
@click.option(
    "--rules",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
    help="Path to ruleset file (YAML or JSON)"
)
@click.option(
    "--changed-only",
    is_flag=True,
    help="Only check files changed since origin/main"
)
@click.option(
    "--strict",
    is_flag=True,
    help="Fail on Medium+ findings (default: High+ only)"
)
@click.option(
    "--json",
    is_flag=True,
    help="Output results in JSON format"
)
@click.option(
    "--base-ref",
    default="origin/main",
    help="Git reference to compare against for --changed-only (default: origin/main)"
)
def validate(path, rules, changed_only, strict, json, base_ref):
    """Validate code against policy ruleset.
    
    Scans Python and TypeScript files for policy violations defined in the ruleset.
    Can optionally check only changed files since a git reference.
    
    Exit codes:
      0 - All checks passed
      1 - Policy violations found (High/Critical, or Medium+ with --strict)
      2 - Ruleset parse error
      4 - Internal error
    """
    try:
        # Load ruleset
        try:
            ruleset = RulesetLoader.load(rules)
        except FileNotFoundError:
            console.print(f"[red]Error: Ruleset file not found: {rules}[/red]")
            sys.exit(2)
        except ValueError as e:
            console.print(f"[red]Error: Invalid ruleset: {e}[/red]")
            sys.exit(2)
        
        # Initialize policy engine
        engine = PolicyEngine(ruleset)
        
        # Scan files
        scan_path = Path(path).resolve()
        findings = engine.scan_files(
            scan_path=scan_path,
            changed_only=changed_only,
            base_ref=base_ref
        )
        
        # Count files scanned
        if changed_only:
            files_scanned = len(engine._get_changed_files(scan_path, base_ref))
        else:
            files_scanned = len(list(engine.file_walker.walk(scan_path)))
        
        # Generate report
        report = PolicyReport(
            findings=findings,
            total_files=files_scanned,
            rules_checked=len(ruleset.rules)
        )
        
        # Output results
        if json:
            print(report.generate_json())
        else:
            # Print summary
            report.print_summary(console)
            
            # Print detailed findings if any
            if findings:
                console.print("\n" + report.generate_table())
        
        # Determine exit code
        exit_code = report.determine_exit_code(strict=strict)
        sys.exit(exit_code)
    
    except Exception as e:
        console.print(f"[red]Internal error: {e}[/red]")
        if not json:
            console.print("Use --json for machine-readable output")
        sys.exit(4)
