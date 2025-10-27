"""Policy validation reporting."""

import json
from dataclasses import dataclass
from typing import List, Dict, Any

from rich.console import Console
from rich.table import Table

from .ruleset import Severity
from .engine import Finding


@dataclass
class PolicySummary:
    """Summary of policy validation results."""
    
    total_files: int
    total_findings: int
    findings_by_severity: Dict[Severity, int]
    rules_checked: int


class PolicyReport:
    """Generates policy validation reports."""
    
    def __init__(self, findings: List[Finding], total_files: int, rules_checked: int):
        """Initialize the report.
        
        Args:
            findings: List of policy violations found
            total_files: Total number of files scanned
            rules_checked: Number of rules checked
        """
        self.findings = findings
        self.total_files = total_files
        self.rules_checked = rules_checked
        self.summary = self._generate_summary()
    
    def _generate_summary(self) -> PolicySummary:
        """Generate summary statistics."""
        findings_by_severity = {severity: 0 for severity in Severity}
        
        for finding in self.findings:
            findings_by_severity[finding.severity] += 1
        
        return PolicySummary(
            total_files=self.total_files,
            total_findings=len(self.findings),
            findings_by_severity=findings_by_severity,
            rules_checked=self.rules_checked
        )
    
    def generate_table(self) -> str:
        """Generate a compact table report.
        
        Returns:
            Formatted table as string
        """
        console = Console()
        table = Table(title="Policy Validation Results")
        
        table.add_column("Rule", style="cyan")
        table.add_column("File", style="yellow")
        table.add_column("Line", style="blue")
        table.add_column("Severity", style="red")
        table.add_column("Hint", style="white")
        
        # Add findings
        for finding in self.findings:
            severity_color = self._get_severity_color(finding.severity)
            table.add_row(
                finding.rule_id,
                finding.file_path,
                str(finding.line_number),
                f"[{severity_color}]{finding.severity.value}[/{severity_color}]",
                finding.hint
            )
        
        # Capture table output
        with console.capture() as capture:
            console.print(table)
        
        return capture.get()
    
    def generate_json(self) -> str:
        """Generate JSON report.
        
        Returns:
            JSON formatted report
        """
        report_data = {
            "summary": {
                "total_files": self.summary.total_files,
                "total_findings": self.summary.total_findings,
                "findings_by_severity": {
                    severity.value: count 
                    for severity, count in self.summary.findings_by_severity.items()
                },
                "rules_checked": self.summary.rules_checked
            },
            "findings": [
                {
                    "rule_id": finding.rule_id,
                    "file_path": finding.file_path,
                    "line_number": finding.line_number,
                    "severity": finding.severity.value,
                    "hint": finding.hint,
                    "matched_text": finding.matched_text
                }
                for finding in self.findings
            ]
        }
        
        return json.dumps(report_data, indent=2)
    
    def determine_exit_code(self, strict: bool = False) -> int:
        """Determine the appropriate exit code.
        
        Args:
            strict: If True, fail on Medium+ findings. If False, fail on High+ findings.
            
        Returns:
            Exit code: 0=pass, 1=violations found, 2=ruleset error, 4=internal error
        """
        if not self.findings:
            return 0
        
        # Check if we have any high/critical findings
        high_critical_findings = [
            f for f in self.findings 
            if f.severity in [Severity.HIGH, Severity.CRITICAL]
        ]
        
        if high_critical_findings:
            return 1
        
        # In strict mode, also fail on medium findings
        if strict:
            medium_findings = [
                f for f in self.findings 
                if f.severity == Severity.MEDIUM
            ]
            if medium_findings:
                return 1
        
        # If we have findings but they're all low severity and not in strict mode
        return 0
    
    def _get_severity_color(self, severity: Severity) -> str:
        """Get color for severity level.
        
        Args:
            severity: Severity level
            
        Returns:
            Rich color string
        """
        color_map = {
            Severity.LOW: "yellow",
            Severity.MEDIUM: "orange3",
            Severity.HIGH: "red",
            Severity.CRITICAL: "bright_red"
        }
        return color_map.get(severity, "white")
    
    def print_summary(self, console: Console) -> None:
        """Print a summary of the validation results.
        
        Args:
            console: Rich console for output
        """
        summary = self.summary
        
        # Overall status
        if summary.total_findings == 0:
            console.print("✅ [green]All policy checks passed![/green]")
        else:
            console.print(f"❌ [red]Found {summary.total_findings} policy violation(s)[/red]")
        
        # Statistics
        console.print(f"   Files scanned: {summary.total_files}")
        console.print(f"   Rules checked: {summary.rules_checked}")
        
        # Findings by severity
        if summary.total_findings > 0:
            console.print("   Findings by severity:")
            for severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW]:
                count = summary.findings_by_severity[severity]
                if count > 0:
                    color = self._get_severity_color(severity)
                    console.print(f"     {severity.value}: [{color}]{count}[/{color}]")
