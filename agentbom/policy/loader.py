"""Ruleset loader for policy validation."""

import json
import yaml
from pathlib import Path
from typing import Union, Dict, Any

from .ruleset import Rule, Ruleset, Severity, DetectPattern


class RulesetLoader:
    """Loads and validates policy rulesets from YAML/JSON files."""
    
    @staticmethod
    def load(ruleset_path: Union[str, Path]) -> Ruleset:
        """Load a ruleset from a YAML or JSON file.
        
        Args:
            ruleset_path: Path to the ruleset file
            
        Returns:
            Loaded and validated Ruleset
            
        Raises:
            ValueError: If the ruleset file is invalid or cannot be parsed
            FileNotFoundError: If the ruleset file doesn't exist
        """
        path = Path(ruleset_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Ruleset file not found: {path}")
        
        # Read file content
        try:
            content = path.read_text(encoding='utf-8')
        except Exception as e:
            raise ValueError(f"Failed to read ruleset file: {e}")
        
        # Parse based on file extension
        try:
            if path.suffix.lower() in ['.yaml', '.yml']:
                data = yaml.safe_load(content)
            elif path.suffix.lower() == '.json':
                data = json.loads(content)
            else:
                # Try YAML first, then JSON
                try:
                    data = yaml.safe_load(content)
                except yaml.YAMLError:
                    data = json.loads(content)
        except Exception as e:
            raise ValueError(f"Failed to parse ruleset file: {e}")
        
        # Validate and convert to Ruleset
        return RulesetLoader._parse_ruleset(data)
    
    @staticmethod
    def _parse_ruleset(data: Dict[str, Any]) -> Ruleset:
        """Parse ruleset data into a Ruleset object.
        
        Args:
            data: Parsed ruleset data
            
        Returns:
            Validated Ruleset object
            
        Raises:
            ValueError: If the ruleset data is invalid
        """
        if not isinstance(data, dict):
            raise ValueError("Ruleset must be a dictionary")
        
        # Validate version
        version = data.get('version')
        if not version:
            raise ValueError("Ruleset must have a 'version' field")
        
        # Parse rules
        rules_data = data.get('rules', [])
        if not isinstance(rules_data, list):
            raise ValueError("Ruleset 'rules' must be a list")
        
        rules = []
        for i, rule_data in enumerate(rules_data):
            try:
                rule = RulesetLoader._parse_rule(rule_data)
                rules.append(rule)
            except Exception as e:
                raise ValueError(f"Invalid rule at index {i}: {e}")
        
        return Ruleset(version=version, rules=rules)
    
    @staticmethod
    def _parse_rule(rule_data: Dict[str, Any]) -> Rule:
        """Parse a single rule from data.
        
        Args:
            rule_data: Rule data dictionary
            
        Returns:
            Rule object
            
        Raises:
            ValueError: If the rule data is invalid
        """
        # Required fields
        required_fields = ['id', 'title', 'category', 'severity', 'scope', 'detect']
        for field in required_fields:
            if field not in rule_data:
                raise ValueError(f"Rule missing required field: {field}")
        
        # Parse severity
        try:
            severity = Severity(rule_data['severity'].lower())
        except ValueError:
            raise ValueError(f"Invalid severity: {rule_data['severity']}")
        
        # Parse detect patterns
        detect_data = rule_data['detect']
        if not isinstance(detect_data, dict):
            raise ValueError("Rule 'detect' must be a dictionary")
        
        detect = DetectPattern(
            python_regex_any=detect_data.get('python_regex_any'),
            ts_regex_any=detect_data.get('ts_regex_any'),
            fail_if_regex=detect_data.get('fail_if_regex'),
            manifest_keys_must_exist=detect_data.get('manifest_keys_must_exist')
        )
        
        return Rule(
            id=rule_data['id'],
            title=rule_data['title'],
            category=rule_data['category'],
            severity=severity,
            scope=rule_data['scope'],
            detect=detect,
            autofix_hint=rule_data.get('autofix_hint')
        )
