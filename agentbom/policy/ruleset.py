"""Ruleset data models for policy validation."""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Rule severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DetectPattern(BaseModel):
    """Detection pattern configuration for a rule."""
    
    # Python regex patterns (any must match)
    python_regex_any: Optional[List[str]] = None
    
    # TypeScript regex patterns (any must match)
    ts_regex_any: Optional[List[str]] = None
    
    # Fail if any of these patterns match
    fail_if_regex: Optional[List[str]] = None
    
    # Manifest keys that must exist
    manifest_keys_must_exist: Optional[List[str]] = None


@dataclass
class Rule:
    """Individual policy rule definition."""
    
    id: str
    title: str
    category: str
    severity: Severity
    scope: str
    detect: DetectPattern
    autofix_hint: Optional[str] = None


@dataclass
class Ruleset:
    """Complete policy ruleset."""
    
    version: str
    rules: List[Rule]
    
    def get_rules_by_severity(self, severity: Severity) -> List[Rule]:
        """Get all rules with a specific severity."""
        return [rule for rule in self.rules if rule.severity == severity]
    
    def get_rules_by_category(self, category: str) -> List[Rule]:
        """Get all rules in a specific category."""
        return [rule for rule in self.rules if rule.category == category]
