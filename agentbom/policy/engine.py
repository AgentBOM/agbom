"""Policy validation engine."""

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Set, Optional

from .ruleset import Rule, Ruleset, Severity
from ..utils.file_walker import FileWalker


@dataclass
class Finding:
    """A policy violation finding."""
    
    rule_id: str
    file_path: str
    line_number: int
    severity: Severity
    hint: str
    matched_text: str


class PolicyEngine:
    """Main policy validation engine."""
    
    def __init__(self, ruleset: Ruleset):
        """Initialize the policy engine.
        
        Args:
            ruleset: The ruleset to validate against
        """
        self.ruleset = ruleset
        self.file_walker = FileWalker()
    
    def scan_files(
        self, 
        scan_path: Path, 
        changed_only: bool = False,
        base_ref: str = "origin/main"
    ) -> List[Finding]:
        """Scan files for policy violations.
        
        Args:
            scan_path: Path to scan
            changed_only: If True, only scan files changed since base_ref
            base_ref: Git reference to compare against for changed files
            
        Returns:
            List of policy violations found
        """
        findings = []
        
        # Get files to scan
        if changed_only:
            files_to_scan = self._get_changed_files(scan_path, base_ref)
        else:
            files_to_scan = list(self.file_walker.walk(scan_path))
        
        # Scan each file
        for file_path in files_to_scan:
            file_findings = self.check_file(file_path, scan_path)
            findings.extend(file_findings)
        
        return findings
    
    def check_file(self, file_path: Path, root_path: Path) -> List[Finding]:
        """Check a single file against all applicable rules.
        
        Args:
            file_path: File to check
            root_path: Root path for relative path calculation
            
        Returns:
            List of findings for this file
        """
        findings = []
        
        # Read file content
        content = self.file_walker.read_file_safely(file_path)
        if not content:
            return findings
        
        # Get relative path for reporting
        try:
            rel_path = str(file_path.relative_to(root_path))
        except ValueError:
            rel_path = str(file_path)
        
        # Check each rule
        for rule in self.ruleset.rules:
            rule_findings = self._check_rule(rule, file_path, rel_path, content)
            findings.extend(rule_findings)
        
        return findings
    
    def _check_rule(
        self, 
        rule: Rule, 
        file_path: Path, 
        rel_path: str, 
        content: str
    ) -> List[Finding]:
        """Check a single rule against file content.
        
        Args:
            rule: Rule to check
            file_path: File being checked
            rel_path: Relative path for reporting
            content: File content
            
        Returns:
            List of findings for this rule
        """
        findings = []
        
        # Determine file type
        file_ext = file_path.suffix.lower()
        is_python = file_ext in ['.py']
        is_typescript = file_ext in ['.ts', '.tsx', '.js', '.jsx']
        
        # Check fail_if_regex patterns (these cause violations)
        if rule.detect.fail_if_regex:
            for pattern in rule.detect.fail_if_regex:
                matches = self._find_regex_matches(pattern, content)
                for match in matches:
                    findings.append(Finding(
                        rule_id=rule.id,
                        file_path=rel_path,
                        line_number=match['line'],
                        severity=rule.severity,
                        hint=rule.autofix_hint or f"Violation of rule {rule.id}",
                        matched_text=match['text']
                    ))
        
        # Check positive patterns (python_regex_any, ts_regex_any)
        positive_patterns = []
        if is_python and rule.detect.python_regex_any:
            positive_patterns.extend(rule.detect.python_regex_any)
        elif is_typescript and rule.detect.ts_regex_any:
            positive_patterns.extend(rule.detect.ts_regex_any)
        
        # If we have positive patterns, check if any match
        if positive_patterns:
            any_match = False
            for pattern in positive_patterns:
                if self._find_regex_matches(pattern, content):
                    any_match = True
                    break
            
            # If no positive patterns matched, this is a violation
            if not any_match:
                findings.append(Finding(
                    rule_id=rule.id,
                    file_path=rel_path,
                    line_number=1,  # File-level violation
                    severity=rule.severity,
                    hint=rule.autofix_hint or f"Missing required pattern for rule {rule.id}",
                    matched_text=""
                ))
        
        # Check manifest requirements
        if rule.detect.manifest_keys_must_exist:
            manifest_violation = self._check_manifest_requirements(
                rule, rel_path, root_path=file_path.parent
            )
            if manifest_violation:
                findings.append(manifest_violation)
        
        return findings
    
    def _find_regex_matches(self, pattern: str, content: str) -> List[dict]:
        """Find all regex matches in content.
        
        Args:
            pattern: Regex pattern
            content: Content to search
            
        Returns:
            List of matches with line numbers and text
        """
        matches = []
        lines = content.split('\n')
        
        try:
            compiled_pattern = re.compile(pattern, re.MULTILINE)
            for line_num, line in enumerate(lines, 1):
                for match in compiled_pattern.finditer(line):
                    matches.append({
                        'line': line_num,
                        'text': match.group(0),
                        'start': match.start(),
                        'end': match.end()
                    })
        except re.error:
            # Invalid regex pattern, skip
            pass
        
        return matches
    
    def _check_manifest_requirements(
        self, 
        rule: Rule, 
        rel_path: str, 
        root_path: Path
    ) -> Optional[Finding]:
        """Check if manifest file requirements are met.
        
        Args:
            rule: Rule being checked
            rel_path: Relative path for reporting
            root_path: Root directory to search for manifests
            
        Returns:
            Finding if requirements not met, None otherwise
        """
        # Look for manifest files
        manifest_files = ['abom.json', 'agents.yaml', 'agents.yml']
        manifest_path = None
        
        for manifest_file in manifest_files:
            potential_path = root_path / manifest_file
            if potential_path.exists():
                manifest_path = potential_path
                break
        
        # If no manifest found, skip this rule (as per requirements)
        if not manifest_path:
            return None
        
        # Check if required keys exist
        try:
            import json
            import yaml
            
            content = manifest_path.read_text()
            if manifest_path.suffix.lower() == '.json':
                data = json.loads(content)
            else:
                data = yaml.safe_load(content)
            
            missing_keys = []
            for key in rule.detect.manifest_keys_must_exist:
                if not self._key_exists(data, key):
                    missing_keys.append(key)
            
            if missing_keys:
                return Finding(
                    rule_id=rule.id,
                    file_path=rel_path,
                    line_number=1,
                    severity=rule.severity,
                    hint=f"Missing manifest keys: {', '.join(missing_keys)}",
                    matched_text=""
                )
        
        except Exception:
            # If we can't parse the manifest, skip this check
            pass
        
        return None
    
    def _key_exists(self, data: dict, key_path: str) -> bool:
        """Check if a nested key exists in a dictionary.
        
        Args:
            data: Dictionary to check
            key_path: Dot-separated key path (e.g., "policy.default_steps")
            
        Returns:
            True if key exists, False otherwise
        """
        keys = key_path.split('.')
        current = data
        
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                return False
            current = current[key]
        
        return True
    
    def _get_changed_files(self, scan_path: Path, base_ref: str) -> List[Path]:
        """Get list of files changed since base_ref.
        
        Args:
            scan_path: Path to scan
            base_ref: Git reference to compare against
            
        Returns:
            List of changed file paths
        """
        try:
            # Try origin/main first, then origin/master
            refs_to_try = [base_ref, "origin/master"]
            
            for ref in refs_to_try:
                try:
                    result = subprocess.run(
                        ['git', 'diff', '--name-only', ref],
                        cwd=scan_path,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    
                    if result.returncode == 0:
                        changed_files = []
                        for line in result.stdout.strip().split('\n'):
                            if line.strip():
                                file_path = scan_path / line.strip()
                                if file_path.exists():
                                    changed_files.append(file_path)
                        return changed_files
                
                except subprocess.CalledProcessError:
                    continue
            
            # If no ref works, return all files
            return list(self.file_walker.walk(scan_path))
        
        except Exception:
            # If git command fails, return all files
            return list(self.file_walker.walk(scan_path))
