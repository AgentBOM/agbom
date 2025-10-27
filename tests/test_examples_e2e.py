"""End-to-end tests for all example agents.

This test suite validates that all examples are correctly detected and analyzed
by the AgentBOM scanner with expected results.
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agentbom.scanner import Scanner
from agentbom.models import Agent


class TestResult:
    """Container for test results."""

    def __init__(self, name: str):
        self.name = name
        self.passed = True
        self.failures: List[str] = []
        self.warnings: List[str] = []

    def fail(self, message: str):
        """Mark test as failed with message."""
        self.passed = False
        self.failures.append(message)

    def warn(self, message: str):
        """Add warning message."""
        self.warnings.append(message)

    def __str__(self) -> str:
        """String representation."""
        status = "✓ PASS" if self.passed else "✗ FAIL"
        return f"{status}: {self.name}"


class E2ETestSuite:
    """End-to-end test suite for example agents."""

    def __init__(self):
        # Initialize scanner with ALL frameworks
        self.scanner = Scanner(
            frameworks=["langchain-py", "langchain-ts", "autogen", "crewai"]
        )
        self.examples_dir = Path(__file__).parent.parent / "examples"
        self.results: List[TestResult] = []

    def assert_detected(
        self, agent: Optional[Agent], test: TestResult, example_name: str
    ) -> bool:
        """Assert that agent was detected."""
        if agent is None:
            test.fail(f"Agent not detected in {example_name}")
            return False
        return True

    def assert_equals(self, actual: Any, expected: Any, field: str, test: TestResult):
        """Assert that values are equal."""
        if actual != expected:
            test.fail(f"{field}: expected '{expected}', got '{actual}'")

    def assert_in(self, item: Any, collection: List[Any], field: str, test: TestResult):
        """Assert that item is in collection."""
        if item not in collection:
            test.fail(f"{field}: '{item}' not in {collection}")

    def assert_min_count(self, actual: int, minimum: int, field: str, test: TestResult):
        """Assert that count is at least minimum."""
        if actual < minimum:
            test.fail(f"{field}: expected at least {minimum}, got {actual}")

    def assert_tool_exists(self, tools: Any, tool_name: str, test: TestResult):
        """Assert that a specific tool exists."""
        tool_names = [t.tool_name for t in tools.details]
        if tool_name not in tool_names:
            test.fail(f"Tool '{tool_name}' not found. Available: {tool_names}")

    def test_langchain_basic_agent(self) -> TestResult:
        """Test LangChain basic agent."""
        test = TestResult("LangChain Python - basic_agent.py")
        file_path = self.examples_dir / "langchain_python" / "basic_agent.py"

        bom = self.scanner.scan_path(file_path)
        agent = bom.agents[0] if bom.agents else None
        if not self.assert_detected(agent, test, "basic_agent.py"):
            return test

        # Validate results
        self.assert_equals(agent.name, "basic_agent", "agent_name", test)
        self.assert_equals(agent.language, "Python", "language", test)
        self.assert_in("LangChain", agent.frameworks, "frameworks", test)
        self.assert_equals(agent.architecture, "ReAct", "architecture", test)
        self.assert_min_count(agent.tools.count, 3, "tools count", test)

        # Validate specific tools
        self.assert_tool_exists(agent.tools, "get_current_weather", test)
        self.assert_tool_exists(agent.tools, "calculate_distance", test)
        self.assert_tool_exists(agent.tools, "get_time", test)

        return test

    def test_langchain_sql_agent(self) -> TestResult:
        """Test LangChain SQL agent."""
        test = TestResult("LangChain Python - sql_agent.py")
        file_path = self.examples_dir / "langchain_python" / "sql_agent.py"

        bom = self.scanner.scan_path(file_path)
        agent = bom.agents[0] if bom.agents else None
        if not self.assert_detected(agent, test, "sql_agent.py"):
            return test

        self.assert_equals(agent.name, "sql_agent", "agent_name", test)
        self.assert_equals(agent.type, "SQL Agent", "agent_type", test)
        self.assert_equals(agent.language, "Python", "language", test)
        self.assert_in("LangChain", agent.frameworks, "frameworks", test)
        self.assert_min_count(agent.tools.count, 4, "tools count", test)

        # Validate SQL-related tools
        self.assert_tool_exists(agent.tools, "query_database", test)
        self.assert_tool_exists(agent.tools, "get_table_schema", test)

        return test

    def test_langchain_retrieval_agent(self) -> TestResult:
        """Test LangChain retrieval agent."""
        test = TestResult("LangChain Python - retrieval_agent.py")
        file_path = self.examples_dir / "langchain_python" / "retrieval_agent.py"

        bom = self.scanner.scan_path(file_path)
        agent = bom.agents[0] if bom.agents else None
        if not self.assert_detected(agent, test, "retrieval_agent.py"):
            return test

        self.assert_equals(agent.name, "retrieval_agent", "agent_name", test)
        self.assert_equals(agent.type, "Retrieval Agent", "agent_type", test)
        self.assert_equals(agent.language, "Python", "language", test)
        self.assert_min_count(agent.tools.count, 4, "tools count", test)

        # Validate retrieval tools
        self.assert_tool_exists(agent.tools, "search_documentation", test)
        self.assert_tool_exists(agent.tools, "search_knowledge_base", test)

        return test

    def test_langchain_complex_agent(self) -> TestResult:
        """Test LangChain complex agent."""
        test = TestResult("LangChain Python - complex_agent.py")
        file_path = self.examples_dir / "langchain_python" / "complex_agent.py"

        bom = self.scanner.scan_path(file_path)
        agent = bom.agents[0] if bom.agents else None
        if not self.assert_detected(agent, test, "complex_agent.py"):
            return test

        self.assert_equals(agent.name, "complex_agent", "agent_name", test)
        self.assert_equals(agent.language, "Python", "language", test)
        self.assert_min_count(agent.tools.count, 7, "tools count", test)

        # Validate diverse tool set
        self.assert_tool_exists(agent.tools, "web_search", test)
        self.assert_tool_exists(agent.tools, "send_email", test)
        self.assert_tool_exists(agent.tools, "create_calendar_event", test)

        return test

    def test_langchain_sales_support_agent(self) -> TestResult:
        """Test LangChain sales support agent (original example)."""
        test = TestResult("LangChain Python - sales_support_agent.py")
        file_path = self.examples_dir / "langchain_python" / "sales_support_agent.py"

        bom = self.scanner.scan_path(file_path)
        agent = bom.agents[0] if bom.agents else None
        if not self.assert_detected(agent, test, "sales_support_agent.py"):
            return test

        self.assert_equals(agent.name, "sales_support_agent", "agent_name", test)
        self.assert_equals(agent.language, "Python", "language", test)
        self.assert_min_count(agent.tools.count, 3, "tools count", test)

        return test

    def test_langchain_edge_cases_agent(self) -> TestResult:
        """Test LangChain edge cases agent."""
        test = TestResult("LangChain Python - edge_cases_agent.py")
        file_path = self.examples_dir / "langchain_python" / "edge_cases_agent.py"

        bom = self.scanner.scan_path(file_path)
        agent = bom.agents[0] if bom.agents else None
        if not self.assert_detected(agent, test, "edge_cases_agent.py"):
            return test

        self.assert_equals(agent.language, "Python", "language", test)
        self.assert_in("LangChain", agent.frameworks, "frameworks", test)
        self.assert_min_count(agent.tools.count, 3, "tools count", test)

        # Should detect at least some tools despite edge cases
        if agent.tools.count < 3:
            test.warn("Some edge case tools may not be detected")

        return test

    def test_langchain_ts_basic_agent(self) -> TestResult:
        """Test LangChain TypeScript basic agent."""
        test = TestResult("LangChain TypeScript - basic_agent.ts")
        file_path = self.examples_dir / "langchain_typescript" / "basic_agent.ts"

        bom = self.scanner.scan_path(file_path)
        agent = bom.agents[0] if bom.agents else None
        if not self.assert_detected(agent, test, "basic_agent.ts"):
            return test

        self.assert_equals(agent.name, "basicAgent", "agent_name", test)
        self.assert_equals(agent.language, "TypeScript", "language", test)
        self.assert_in("LangChain", agent.frameworks, "frameworks", test)
        self.assert_min_count(agent.tools.count, 3, "tools count", test)

        return test

    def test_langchain_ts_sql_agent(self) -> TestResult:
        """Test LangChain TypeScript SQL agent."""
        test = TestResult("LangChain TypeScript - sql_agent.ts")
        file_path = self.examples_dir / "langchain_typescript" / "sql_agent.ts"

        bom = self.scanner.scan_path(file_path)
        agent = bom.agents[0] if bom.agents else None
        if not self.assert_detected(agent, test, "sql_agent.ts"):
            return test

        self.assert_equals(agent.name, "sqlAgent", "agent_name", test)
        self.assert_equals(agent.type, "SQL Agent", "agent_type", test)
        self.assert_equals(agent.language, "TypeScript", "language", test)
        self.assert_min_count(agent.tools.count, 4, "tools count", test)

        return test

    def test_langchain_ts_retrieval_agent(self) -> TestResult:
        """Test LangChain TypeScript retrieval agent."""
        test = TestResult("LangChain TypeScript - retrieval_agent.ts")
        file_path = self.examples_dir / "langchain_typescript" / "retrieval_agent.ts"

        bom = self.scanner.scan_path(file_path)
        agent = bom.agents[0] if bom.agents else None
        if not self.assert_detected(agent, test, "retrieval_agent.ts"):
            return test

        self.assert_equals(agent.name, "retrievalAgent", "agent_name", test)
        self.assert_equals(agent.type, "Retrieval Agent", "agent_type", test)
        self.assert_equals(agent.language, "TypeScript", "language", test)
        self.assert_min_count(agent.tools.count, 4, "tools count", test)

        return test

    def test_langchain_ts_complex_agent(self) -> TestResult:
        """Test LangChain TypeScript complex agent."""
        test = TestResult("LangChain TypeScript - complex_agent.ts")
        file_path = self.examples_dir / "langchain_typescript" / "complex_agent.ts"

        bom = self.scanner.scan_path(file_path)
        agent = bom.agents[0] if bom.agents else None
        if not self.assert_detected(agent, test, "complex_agent.ts"):
            return test

        self.assert_equals(agent.name, "complexAgent", "agent_name", test)
        self.assert_equals(agent.language, "TypeScript", "language", test)
        self.assert_min_count(agent.tools.count, 7, "tools count", test)

        return test

    def test_autogen_simple_group_chat(self) -> TestResult:
        """Test AutoGen simple group chat."""
        test = TestResult("AutoGen - simple_group_chat.py")
        file_path = self.examples_dir / "autogen" / "simple_group_chat.py"

        bom = self.scanner.scan_path(file_path)
        agent = bom.agents[0] if bom.agents else None
        if not self.assert_detected(agent, test, "simple_group_chat.py"):
            return test

        self.assert_equals(agent.name, "manager", "agent_name", test)
        self.assert_equals(agent.language, "Python", "language", test)
        self.assert_in("AutoGen", agent.frameworks, "frameworks", test)
        self.assert_equals(agent.architecture, "MAS", "architecture", test)

        # Note: Multi-agent system counts are not directly testable
        # The scanner aggregates MAS into single agent entries

        return test

    def test_autogen_research_team(self) -> TestResult:
        """Test AutoGen research team."""
        test = TestResult("AutoGen - research_team.py")
        file_path = self.examples_dir / "autogen" / "research_team.py"

        bom = self.scanner.scan_path(file_path)
        agent = bom.agents[0] if bom.agents else None
        if not self.assert_detected(agent, test, "research_team.py"):
            return test

        self.assert_equals(agent.name, "research_manager", "agent_name", test)
        self.assert_equals(agent.architecture, "MAS", "architecture", test)

        # Validate 5-agent system
        # Note: Multi-agent counts are not directly accessible from Agent model
        # The scanner aggregates MAS into single agent entries

        return test

    def test_autogen_coding_team(self) -> TestResult:
        """Test AutoGen coding team."""
        test = TestResult("AutoGen - coding_team.py")
        file_path = self.examples_dir / "autogen" / "coding_team.py"

        bom = self.scanner.scan_path(file_path)
        agent = bom.agents[0] if bom.agents else None
        if not self.assert_detected(agent, test, "coding_team.py"):
            return test

        self.assert_equals(agent.name, "coding_manager", "agent_name", test)
        self.assert_equals(agent.architecture, "MAS", "architecture", test)

        # Validate 4-agent system
        # Note: Multi-agent counts are not directly accessible from Agent model
        # The scanner aggregates MAS into single agent entries

        return test

    def test_autogen_edge_cases(self) -> TestResult:
        """Test AutoGen edge cases."""
        test = TestResult("AutoGen - edge_cases_autogen.py")
        file_path = self.examples_dir / "autogen" / "edge_cases_autogen.py"

        bom = self.scanner.scan_path(file_path)
        agent = bom.agents[0] if bom.agents else None
        if not self.assert_detected(agent, test, "edge_cases_autogen.py"):
            return test

        self.assert_equals(agent.architecture, "MAS", "architecture", test)

        # Validate large multi-agent system
        # Note: Multi-agent counts are not directly accessible from Agent model
        # The scanner aggregates MAS into single agent entries

        return test

    def test_crewai_basic_crew(self) -> TestResult:
        """Test CrewAI basic crew."""
        test = TestResult("CrewAI - basic_crew.py")
        file_path = self.examples_dir / "crewai" / "basic_crew.py"

        bom = self.scanner.scan_path(file_path)
        agent = bom.agents[0] if bom.agents else None
        if not self.assert_detected(agent, test, "basic_crew.py"):
            return test

        self.assert_equals(agent.name, "basic_crew", "agent_name", test)
        self.assert_equals(agent.language, "Python", "language", test)
        self.assert_in("CrewAI", agent.frameworks, "frameworks", test)
        self.assert_equals(agent.architecture, "MAS", "architecture", test)

        # Validate agents and tasks
        # Note: Multi-agent counts are not directly accessible from Agent model
        # The scanner aggregates MAS into single agent entries

        self.assert_min_count(agent.tools.count, 2, "tools count", test)

        return test

    def test_crewai_marketing_crew(self) -> TestResult:
        """Test CrewAI marketing crew."""
        test = TestResult("CrewAI - marketing_crew.py")
        file_path = self.examples_dir / "crewai" / "marketing_crew.py"

        bom = self.scanner.scan_path(file_path)
        agent = bom.agents[0] if bom.agents else None
        if not self.assert_detected(agent, test, "marketing_crew.py"):
            return test

        self.assert_equals(agent.name, "marketing_crew", "agent_name", test)
        self.assert_equals(agent.architecture, "MAS", "architecture", test)

        # Note: Multi-agent counts are not directly testable from Agent model
        # The scanner aggregates MAS into single agent entries

        self.assert_min_count(agent.tools.count, 4, "tools count", test)

        return test

    def test_crewai_development_crew(self) -> TestResult:
        """Test CrewAI development crew."""
        test = TestResult("CrewAI - development_crew.py")
        file_path = self.examples_dir / "crewai" / "development_crew.py"

        bom = self.scanner.scan_path(file_path)
        agent = bom.agents[0] if bom.agents else None
        if not self.assert_detected(agent, test, "development_crew.py"):
            return test

        self.assert_equals(agent.name, "development_crew", "agent_name", test)
        self.assert_equals(agent.architecture, "MAS", "architecture", test)

        # Validate 4-agent system
        # Note: Multi-agent counts are not directly accessible from Agent model
        # The scanner aggregates MAS into single agent entries

        self.assert_min_count(agent.tools.count, 5, "tools count", test)

        return test

    def test_crewai_edge_cases(self) -> TestResult:
        """Test CrewAI edge cases."""
        test = TestResult("CrewAI - edge_cases_crew.py")
        file_path = self.examples_dir / "crewai" / "edge_cases_crew.py"

        bom = self.scanner.scan_path(file_path)
        agent = bom.agents[0] if bom.agents else None
        if not self.assert_detected(agent, test, "edge_cases_crew.py"):
            return test

        self.assert_equals(agent.architecture, "MAS", "architecture", test)

        # Note: Multi-agent counts are not directly testable from Agent model
        # The scanner aggregates MAS into single agent entries

        return test

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and return results."""
        print("\n" + "=" * 80)
        print("Running E2E Tests for AgentBOM Examples")
        print("=" * 80 + "\n")

        # Run all test methods
        test_methods = [
            # LangChain Python
            self.test_langchain_basic_agent,
            self.test_langchain_sql_agent,
            self.test_langchain_retrieval_agent,
            self.test_langchain_complex_agent,
            self.test_langchain_sales_support_agent,
            self.test_langchain_edge_cases_agent,
            # LangChain TypeScript
            self.test_langchain_ts_basic_agent,
            self.test_langchain_ts_sql_agent,
            self.test_langchain_ts_retrieval_agent,
            self.test_langchain_ts_complex_agent,
            # AutoGen
            self.test_autogen_simple_group_chat,
            self.test_autogen_research_team,
            self.test_autogen_coding_team,
            self.test_autogen_edge_cases,
            # CrewAI
            self.test_crewai_basic_crew,
            self.test_crewai_marketing_crew,
            self.test_crewai_development_crew,
            self.test_crewai_edge_cases,
        ]

        for test_method in test_methods:
            test_result = test_method()
            self.results.append(test_result)

            # Print result
            print(str(test_result))
            if test_result.failures:
                for failure in test_result.failures:
                    print(f"    ✗ {failure}")
            if test_result.warnings:
                for warning in test_result.warnings:
                    print(f"    ⚠ {warning}")

        return self.generate_report()

    def generate_report(self) -> Dict[str, Any]:
        """Generate test report."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed

        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"\nTotal Tests:  {total}")
        print(f"✓ Passed:     {passed}")
        print(f"✗ Failed:     {failed}")
        print(f"Success Rate: {passed / total * 100:.1f}%")

        if failed > 0:
            print("\nFailed Tests:")
            for result in self.results:
                if not result.passed:
                    print(f"  ✗ {result.name}")
                    for failure in result.failures:
                        print(f"      - {failure}")
        else:
            print("\n🎉 All tests passed!")

        # Framework breakdown
        print("\n" + "-" * 80)
        print("By Framework:")

        frameworks = {
            "LangChain Python": [
                r for r in self.results if "LangChain Python" in r.name
            ],
            "LangChain TypeScript": [
                r for r in self.results if "LangChain TypeScript" in r.name
            ],
            "AutoGen": [r for r in self.results if "AutoGen" in r.name],
            "CrewAI": [r for r in self.results if "CrewAI" in r.name],
        }

        for framework, tests in frameworks.items():
            passed_count = sum(1 for t in tests if t.passed)
            print(f"  {framework}: {passed_count}/{len(tests)}")

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "success_rate": passed / total * 100,
            "results": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "failures": r.failures,
                    "warnings": r.warnings,
                }
                for r in self.results
            ],
        }


def main():
    """Main entry point."""
    suite = E2ETestSuite()
    report = suite.run_all_tests()

    # Save report to JSON
    output_file = Path(__file__).parent.parent / "examples" / "e2e_test_results.json"
    with open(output_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nDetailed report saved to: {output_file}")

    # Exit with appropriate code
    return 0 if report["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
