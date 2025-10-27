"""Tests for policy validation functionality."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml

from agentbom.policy import RulesetLoader, PolicyEngine, PolicyReport, Severity
from agentbom.cli_validate import validate


class TestRulesetLoader:
    """Test ruleset loading functionality."""
    
    def test_load_valid_yaml_ruleset(self):
        """Test loading a valid YAML ruleset."""
        ruleset_data = {
            "version": "1",
            "rules": [
                {
                    "id": "TEST-001",
                    "title": "Test Rule",
                    "category": "test",
                    "severity": "high",
                    "scope": "build",
                    "detect": {
                        "python_regex_any": ["test_pattern"]
                    },
                    "autofix_hint": "Fix this"
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(ruleset_data, f)
            f.flush()
            
            try:
                ruleset = RulesetLoader.load(f.name)
                assert ruleset.version == "1"
                assert len(ruleset.rules) == 1
                assert ruleset.rules[0].id == "TEST-001"
                assert ruleset.rules[0].severity == Severity.HIGH
            finally:
                Path(f.name).unlink()
    
    def test_load_invalid_ruleset_missing_version(self):
        """Test loading ruleset without version fails."""
        ruleset_data = {"rules": []}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(ruleset_data, f)
            f.flush()
            
            try:
                with pytest.raises(ValueError, match="Ruleset must have a 'version' field"):
                    RulesetLoader.load(f.name)
            finally:
                Path(f.name).unlink()
    
    def test_load_invalid_rule_severity(self):
        """Test loading ruleset with invalid severity fails."""
        ruleset_data = {
            "version": "1",
            "rules": [
                {
                    "id": "TEST-001",
                    "title": "Test Rule",
                    "category": "test",
                    "severity": "invalid",
                    "scope": "build",
                    "detect": {}
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(ruleset_data, f)
            f.flush()
            
            try:
                with pytest.raises(ValueError, match="Invalid severity"):
                    RulesetLoader.load(f.name)
            finally:
                Path(f.name).unlink()


class TestPolicyEngine:
    """Test policy validation engine."""
    
    def test_check_file_python_regex_any(self):
        """Test checking Python file with regex patterns."""
        ruleset_data = {
            "version": "1",
            "rules": [
                {
                    "id": "TEST-001",
                    "title": "Test Rule",
                    "category": "test",
                    "severity": "high",
                    "scope": "build",
                    "detect": {
                        "python_regex_any": ["max_steps\\s*=\\s*\\d+"]
                    }
                }
            ]
        }
        
        ruleset = RulesetLoader._parse_ruleset(ruleset_data)
        engine = PolicyEngine(ruleset)
        
        # Create test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("max_steps = 50\n")
            f.flush()
            
            try:
                findings = engine.check_file(Path(f.name), Path(f.name).parent)
                assert len(findings) == 0  # Should pass because pattern matches
            finally:
                Path(f.name).unlink()
    
    def test_check_file_fail_if_regex(self):
        """Test checking file with fail_if_regex patterns."""
        ruleset_data = {
            "version": "1",
            "rules": [
                {
                    "id": "TEST-002",
                    "title": "Test Rule",
                    "category": "test",
                    "severity": "high",
                    "scope": "build",
                    "detect": {
                        "fail_if_regex": ["model\\s*=\\s*['\"]latest['\"]"]
                    }
                }
            ]
        }
        
        ruleset = RulesetLoader._parse_ruleset(ruleset_data)
        engine = PolicyEngine(ruleset)
        
        # Create test file with violation
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('model = "latest"\n')
            f.flush()
            
            try:
                findings = engine.check_file(Path(f.name), Path(f.name).parent)
                assert len(findings) == 1
                assert findings[0].rule_id == "TEST-002"
                assert findings[0].severity == Severity.HIGH
            finally:
                Path(f.name).unlink()


class TestPolicyReport:
    """Test policy reporting functionality."""
    
    def test_generate_json(self):
        """Test JSON report generation."""
        from agentbom.policy.engine import Finding
        
        findings = [
            Finding(
                rule_id="TEST-001",
                file_path="test.py",
                line_number=1,
                severity=Severity.HIGH,
                hint="Test hint",
                matched_text="test"
            )
        ]
        
        report = PolicyReport(findings=findings, total_files=1, rules_checked=1)
        json_output = report.generate_json()
        
        data = json.loads(json_output)
        assert data["summary"]["total_findings"] == 1
        assert data["summary"]["findings_by_severity"]["high"] == 1
        assert len(data["findings"]) == 1
        assert data["findings"][0]["rule_id"] == "TEST-001"
    
    def test_determine_exit_code_no_findings(self):
        """Test exit code with no findings."""
        report = PolicyReport(findings=[], total_files=1, rules_checked=1)
        assert report.determine_exit_code() == 0
        assert report.determine_exit_code(strict=True) == 0
    
    def test_determine_exit_code_high_findings(self):
        """Test exit code with high severity findings."""
        from agentbom.policy.engine import Finding
        
        findings = [
            Finding(
                rule_id="TEST-001",
                file_path="test.py",
                line_number=1,
                severity=Severity.HIGH,
                hint="Test hint",
                matched_text="test"
            )
        ]
        
        report = PolicyReport(findings=findings, total_files=1, rules_checked=1)
        assert report.determine_exit_code() == 1
        assert report.determine_exit_code(strict=True) == 1
    
    def test_determine_exit_code_medium_findings_strict(self):
        """Test exit code with medium findings in strict mode."""
        from agentbom.policy.engine import Finding
        
        findings = [
            Finding(
                rule_id="TEST-001",
                file_path="test.py",
                line_number=1,
                severity=Severity.MEDIUM,
                hint="Test hint",
                matched_text="test"
            )
        ]
        
        report = PolicyReport(findings=findings, total_files=1, rules_checked=1)
        assert report.determine_exit_code() == 0  # Not strict
        assert report.determine_exit_code(strict=True) == 1  # Strict mode


class TestCLIValidate:
    """Test CLI validate command."""
    
    def test_validate_command_help(self):
        """Test that validate command shows help."""
        from click.testing import CliRunner
        
        runner = CliRunner()
        result = runner.invoke(validate, ['--help'])
        assert result.exit_code == 0
        assert "Validate code against policy ruleset" in result.output
    
    @patch('agentbom.cli_validate.RulesetLoader.load')
    @patch('agentbom.cli_validate.PolicyEngine')
    def test_validate_command_success(self, mock_engine_class, mock_loader):
        """Test successful validation."""
        from click.testing import CliRunner
        
        # Mock ruleset
        mock_ruleset = MagicMock()
        mock_ruleset.rules = []
        mock_loader.return_value = mock_ruleset
        
        # Mock engine
        mock_engine = MagicMock()
        mock_engine.scan_files.return_value = []
        mock_engine.file_walker.walk.return_value = [Path("test.py")]
        mock_engine._get_changed_files.return_value = [Path("test.py")]
        mock_engine_class.return_value = mock_engine
        
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_file = Path(tmpdir) / "rules.yml"
            rules_file.write_text("version: '1'\nrules: []")
            
            result = runner.invoke(validate, [
                '--path', tmpdir,
                '--rules', str(rules_file)
            ])
            
            assert result.exit_code == 0
            assert "All policy checks passed!" in result.output


# Test fixtures
@pytest.fixture
def py_bad_model_latest():
    """Python file with model='latest' violation."""
    return '''
model = "latest"
llm = OpenAI(model=model)
'''

@pytest.fixture
def ts_bad_concat():
    """TypeScript file with string concatenation violation."""
    return '''
const prompt = "Hello " + user.name + "!";
const message = `Welcome ${user.name}!`;
'''

@pytest.fixture
def py_good():
    """Python file that passes all rules."""
    return '''
from pydantic import BaseModel
from langchain.prompts import PromptTemplate

class UserInput(BaseModel):
    name: str
    email: str

template = PromptTemplate(
    input_variables=["name"],
    template="Hello {name}!"
)

max_steps = 50
model = "gpt-4@2024-01-01"
'''

@pytest.fixture
def ts_good():
    """TypeScript file that passes all rules."""
    return '''
interface UserInput {
    name: string;
    email: string;
}

const template = new PromptTemplate({
    inputVariables: ["name"],
    template: "Hello {name}!"
});

const maxSteps = 50;
const model = "gpt-4@2024-01-01";
'''

@pytest.fixture
def rules_test():
    """Minimal test ruleset."""
    return {
        "version": "1",
        "rules": [
            {
                "id": "TEST-001",
                "title": "No latest model",
                "category": "security",
                "severity": "high",
                "scope": "build",
                "detect": {
                    "fail_if_regex": ["model\\s*=\\s*['\"]latest['\"]"]
                },
                "autofix_hint": "Pin model version"
            }
        ]
    }
