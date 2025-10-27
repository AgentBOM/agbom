"""Acceptance tests for AgentBOM based on requirements."""

import json
import tempfile
from pathlib import Path

from agentbom.scanner import Scanner


def test_langchain_python_agent():
    """Test LangChain Python agent detection (Acceptance Test #1)."""
    # Create test file with LangChain Python agent
    code = '''
from langchain.agents import initialize_agent, AgentType
from langchain.tools import tool
from langchain.llms import OpenAI

@tool
def search_docs(query: str) -> str:
    """Search product documentation."""
    return f"Results for {query}"

@tool
def answer_with_citations(query: str) -> str:
    """Answer with citations."""
    return f"Answer to {query}"

tools = [search_docs, answer_with_citations]
llm = OpenAI()

agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True
)
'''

    with tempfile.TemporaryDirectory() as tmpdir:
        # Write test file
        test_file = Path(tmpdir) / "sales_agent.py"
        test_file.write_text(code)

        # Scan
        scanner = Scanner(frameworks=["langchain-py"])
        bom = scanner.scan_path(Path(tmpdir))

        # Assertions
        assert len(bom.agents) == 1
        agent = bom.agents[0]

        assert agent.language == "Python"
        assert "LangChain" in agent.frameworks
        assert agent.architecture == "ReAct"  # Due to ZERO_SHOT_REACT_DESCRIPTION
        assert agent.tools.count == 2
        assert agent.name == "agent"

        # Check tool details
        tool_names = [t.tool_name for t in agent.tools.details]
        assert "search_docs" in tool_names
        assert "answer_with_citations" in tool_names

        # Validate schema
        json_str = bom.to_json()
        data = json.loads(json_str)
        assert "agents" in data
        assert len(data["agents"]) == 1


def test_langchain_typescript_agent():
    """Test LangChain TypeScript agent detection (Acceptance Test #2)."""
    code = """
import { AgentExecutor } from "langchain/agents";
import { tool } from "@langchain/core/tools";
import { ChatOpenAI } from "@langchain/openai";

const searchTool = tool({
  name: "search",
  description: "Search for information",
  func: async (query: string) => {
    return `Results for ${query}`;
  }
});

const llm = new ChatOpenAI();
const exec = new AgentExecutor({
  llm: llm,
  tools: [searchTool]
});
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        # Write test file
        test_file = Path(tmpdir) / "agent.ts"
        test_file.write_text(code)

        # Scan
        scanner = Scanner(frameworks=["langchain-ts"])
        bom = scanner.scan_path(Path(tmpdir))

        # Assertions
        assert len(bom.agents) == 1
        agent = bom.agents[0]

        assert agent.language == "TypeScript"
        assert "LangChain" in agent.frameworks
        assert agent.tools.count == 1
        assert agent.name == "exec"

        # Validate schema
        json_str = bom.to_json()
        data = json.loads(json_str)
        assert "agents" in data


def test_autogen_agent():
    """Test AutoGen agent detection (Acceptance Test #3)."""
    code = """
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager

assistant = AssistantAgent(
    name="Assistant",
    system_message="You are a helpful assistant.",
    llm_config={"model": "gpt-4"}
)

user = UserProxyAgent(
    name="User",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=10
)

group = GroupChat(
    agents=[assistant, user],
    messages=[],
    max_round=10
)

manager = GroupChatManager(groupchat=group, llm_config={"model": "gpt-4"})
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        # Write test file
        test_file = Path(tmpdir) / "autogen_agent.py"
        test_file.write_text(code)

        # Scan
        scanner = Scanner(frameworks=["autogen"])
        bom = scanner.scan_path(Path(tmpdir))

        # Assertions
        assert len(bom.agents) == 1
        agent = bom.agents[0]

        assert agent.language == "Python"
        assert "AutoGen" in agent.frameworks
        assert agent.architecture == "MAS"  # Multi-Agent System

        # Validate schema
        json_str = bom.to_json()
        data = json.loads(json_str)
        assert "agents" in data


def test_crewai_agent():
    """Test CrewAI agent detection (Acceptance Test #4)."""
    code = """
from crewai import Agent, Task, Crew

analyst = Agent(
    role="Data Analyst",
    goal="Analyze data and provide insights",
    backstory="You are an experienced data analyst",
    verbose=True
)

analysis_task = Task(
    description="Analyze the sales data",
    agent=analyst,
    expected_output="A detailed analysis report"
)

crew = Crew(
    agents=[analyst],
    tasks=[analysis_task],
    verbose=2
)
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        # Write test file
        test_file = Path(tmpdir) / "crew.py"
        test_file.write_text(code)

        # Scan
        scanner = Scanner(frameworks=["crewai"])
        bom = scanner.scan_path(Path(tmpdir))

        # Assertions
        assert len(bom.agents) == 1
        agent = bom.agents[0]

        assert agent.language == "Python"
        assert "CrewAI" in agent.frameworks
        assert agent.architecture == "MAS"  # Multi-Agent System

        # Validate schema
        json_str = bom.to_json()
        data = json.loads(json_str)
        assert "agents" in data


def test_zero_agents():
    """Test handling of zero agents (Acceptance Test #5)."""
    code = """
# Regular Python code without any AI agents
def hello_world():
    print("Hello, world!")

if __name__ == "__main__":
    hello_world()
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        # Write test file
        test_file = Path(tmpdir) / "hello.py"
        test_file.write_text(code)

        # Scan
        scanner = Scanner()
        bom = scanner.scan_path(Path(tmpdir))

        # Assertions
        assert len(bom.agents) == 0

        # Validate schema - should still be valid with empty agents
        json_str = bom.to_json()
        data = json.loads(json_str)
        assert "agents" in data
        assert data["agents"] == []


def test_multiple_agents_in_project():
    """Test detecting multiple agents in a project."""
    langchain_code = """
from langchain.agents import initialize_agent
from langchain.tools import Tool

def search(query: str) -> str:
    return f"Search: {query}"

tools = [Tool(name="search", func=search, description="Search")]

agent1 = initialize_agent(tools=tools, llm=None, agent="zero-shot-react-description")
"""

    crewai_code = """
from crewai import Agent, Task, Crew

researcher = Agent(role="Researcher", goal="Research topics", backstory="Expert researcher")
task = Task(description="Research AI", agent=researcher)
crew = Crew(agents=[researcher], tasks=[task])
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        # Write test files
        (Path(tmpdir) / "agent1.py").write_text(langchain_code)
        (Path(tmpdir) / "agent2.py").write_text(crewai_code)

        # Scan with both frameworks
        scanner = Scanner(frameworks=["langchain-py", "crewai"])
        bom = scanner.scan_path(Path(tmpdir))

        # Assertions
        assert len(bom.agents) == 2

        # Check we have one of each type
        frameworks = [agent.frameworks[0] for agent in bom.agents]
        assert "LangChain" in frameworks
        assert "CrewAI" in frameworks


def test_file_filtering():
    """Test that file filtering works correctly."""
    agent_code = """
from langchain.agents import initialize_agent
tools = []
agent = initialize_agent(tools=tools, llm=None, agent="zero-shot-react-description")
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create directory structure
        src_dir = Path(tmpdir) / "src"
        src_dir.mkdir()
        test_dir = Path(tmpdir) / "tests"
        test_dir.mkdir()

        # Write agent files
        (src_dir / "agent.py").write_text(agent_code)
        (test_dir / "test_agent.py").write_text(agent_code)

        # Scan with exclusion
        scanner = Scanner(frameworks=["langchain-py"], exclude_patterns=["tests/**"])
        bom = scanner.scan_path(Path(tmpdir))

        # Should only find agent in src, not in tests
        assert len(bom.agents) == 1
        assert "src" in bom.agents[0].files[0]
        assert "tests" not in bom.agents[0].files[0]


if __name__ == "__main__":
    # Run tests
    test_langchain_python_agent()
    print("✅ LangChain Python agent test passed")

    test_langchain_typescript_agent()
    print("✅ LangChain TypeScript agent test passed")

    test_autogen_agent()
    print("✅ AutoGen agent test passed")

    test_crewai_agent()
    print("✅ CrewAI agent test passed")

    test_zero_agents()
    print("✅ Zero agents test passed")

    test_multiple_agents_in_project()
    print("✅ Multiple agents test passed")

    test_file_filtering()
    print("✅ File filtering test passed")

    print("\n🎉 All acceptance tests passed!")
