"""Test parameter and return type extraction functionality."""

import json
import tempfile
from pathlib import Path

from agentbom.scanner import Scanner


def test_parameter_extraction_with_type_hints():
    """Test that parameters and return types are extracted from type hints."""
    code = '''
from langchain.agents import initialize_agent, AgentType
from langchain.tools import tool
from typing import Dict, List, Optional

@tool
def advanced_search(
    query: str,
    max_results: int = 10,
    filters: Optional[Dict[str, str]] = None,
    include_metadata: bool = True
) -> Dict[str, List[str]]:
    """Search with advanced options.

    Args:
        query: The search query string
        max_results: Maximum number of results to return
        filters: Optional filters to apply
        include_metadata: Whether to include metadata in results

    Returns:
        Dict mapping categories to lists of results
    """
    return {"results": [], "metadata": []}

@tool
def simple_tool(text: str) -> str:
    """Simple tool with minimal signature."""
    return text

tools = [advanced_search, simple_tool]
agent = initialize_agent(tools=tools, llm=llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION)
'''

    with tempfile.TemporaryDirectory() as tmpdir:
        agent_file = Path(tmpdir) / "agent.py"
        agent_file.write_text(code)

        scanner = Scanner(frameworks=['langchain-py'])
        bom = scanner.scan_path(Path(tmpdir))

        assert len(bom.agents) == 1
        agent = bom.agents[0]

        # Check advanced_search tool
        advanced_search_tool = next((t for t in agent.tools.details if t.tool_name == 'advanced_search'), None)
        assert advanced_search_tool is not None

        # Check parameters
        params = advanced_search_tool.parameters
        assert 'query' in params
        assert params['query'].type == 'str'
        assert params['query'].required is True
        assert params['query'].description == 'The search query string'

        assert 'max_results' in params
        assert params['max_results'].type == 'int'
        assert params['max_results'].required is False

        assert 'filters' in params
        assert 'Optional' in params['filters'].type or 'Dict' in params['filters'].type
        assert params['filters'].required is False

        assert 'include_metadata' in params
        assert params['include_metadata'].type == 'bool'
        assert params['include_metadata'].required is False

        # Check return type
        assert advanced_search_tool.returns is not None
        assert 'Dict' in advanced_search_tool.returns.type
        assert 'List' in advanced_search_tool.returns.type or 'list' in advanced_search_tool.returns.type

        # Check simple_tool
        simple_tool = next((t for t in agent.tools.details if t.tool_name == 'simple_tool'), None)
        assert simple_tool is not None
        assert 'text' in simple_tool.parameters
        assert simple_tool.parameters['text'].type == 'str'
        assert simple_tool.returns.type == 'str'


def test_parameter_extraction_from_docstrings():
    """Test that parameters can be extracted from docstrings when type hints are missing."""
    code = '''
from langchain.agents import initialize_agent, AgentType
from langchain.tools import tool

@tool
def process_data(data, format_type="json"):
    """Process data in various formats.

    Args:
        data (list): The data to process
        format_type (str, optional): Output format. Defaults to "json".

    Returns:
        dict: Processed data
    """
    return {"processed": True}

tools = [process_data]
agent = initialize_agent(tools=tools, llm=llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION)
'''

    with tempfile.TemporaryDirectory() as tmpdir:
        agent_file = Path(tmpdir) / "agent.py"
        agent_file.write_text(code)

        scanner = Scanner(frameworks=['langchain-py'])
        bom = scanner.scan_path(Path(tmpdir))

        assert len(bom.agents) == 1
        agent = bom.agents[0]

        tool = agent.tools.details[0]
        assert tool.tool_name == 'process_data'

        # Check parameters extracted from docstring
        params = tool.parameters
        assert 'data' in params
        # Type should be extracted from docstring
        assert params['data'].type == 'list' or params['data'].type == 'Any'
        assert params['data'].required is True

        assert 'format_type' in params
        assert params['format_type'].type == 'str' or params['format_type'].type == 'Any'
        assert params['format_type'].required is False

        # Check return type from docstring
        assert tool.returns is not None
        assert 'dict' in tool.returns.type.lower() or tool.returns.type == 'Any'


def test_structured_tool_with_pydantic():
    """Test parameter extraction from StructuredTool with Pydantic schema."""
    code = '''
from langchain.agents import initialize_agent, AgentType
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
from typing import Optional

class SearchInput(BaseModel):
    query: str = Field(description="The search query")
    limit: int = Field(default=10, description="Max results")
    category: Optional[str] = Field(default=None, description="Filter by category")

def search_func(query: str, limit: int = 10, category: Optional[str] = None) -> str:
    return f"Results for {query}"

search_tool = StructuredTool(
    name="search",
    func=search_func,
    description="Search for information",
    args_schema=SearchInput
)

tools = [search_tool]
agent = initialize_agent(tools=tools, llm=llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION)
'''

    with tempfile.TemporaryDirectory() as tmpdir:
        agent_file = Path(tmpdir) / "agent.py"
        agent_file.write_text(code)

        scanner = Scanner(frameworks=['langchain-py'])
        bom = scanner.scan_path(Path(tmpdir))

        assert len(bom.agents) == 1
        agent = bom.agents[0]

        tool = agent.tools.details[0]
        assert tool.tool_name == 'search'

        # Check parameters extracted from Pydantic model
        params = tool.parameters
        assert 'query' in params
        assert params['query'].type == 'str'
        assert params['query'].required is True

        assert 'limit' in params
        assert params['limit'].type == 'int'
        assert params['limit'].required is False

        assert 'category' in params
        assert 'Optional' in params['category'].type or params['category'].required is False


def test_lambda_tool():
    """Test parameter extraction from lambda-based tools."""
    code = '''
from langchain.agents import initialize_agent, AgentType
from langchain.tools import Tool

calculator = Tool(
    name="calculator",
    func=lambda x, y: str(float(x) + float(y)),
    description="Add two numbers"
)

tools = [calculator]
agent = initialize_agent(tools=tools, llm=llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION)
'''

    with tempfile.TemporaryDirectory() as tmpdir:
        agent_file = Path(tmpdir) / "agent.py"
        agent_file.write_text(code)

        scanner = Scanner(frameworks=['langchain-py'])
        bom = scanner.scan_path(Path(tmpdir))

        assert len(bom.agents) == 1
        agent = bom.agents[0]

        tool = agent.tools.details[0]
        assert tool.tool_name == 'calculator'

        # Lambda parameters should be extracted
        params = tool.parameters
        assert 'x' in params
        assert 'y' in params
        # Lambda params don't have type hints, so should be 'Any'
        assert params['x'].type == 'Any'
        assert params['y'].type == 'Any'


def test_numpy_style_docstring():
    """Test parameter extraction from NumPy-style docstrings."""
    code = '''
from langchain.agents import initialize_agent, AgentType
from langchain.tools import tool

@tool
def analyze_data(data, method="mean"):
    """Analyze numerical data.

    Parameters
    ----------
    data : array-like
        The numerical data to analyze
    method : str, optional
        Analysis method to use. Default: "mean"

    Returns
    -------
    float
        The analysis result
    """
    return 0.0

tools = [analyze_data]
agent = initialize_agent(tools=tools, llm=llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION)
'''

    with tempfile.TemporaryDirectory() as tmpdir:
        agent_file = Path(tmpdir) / "agent.py"
        agent_file.write_text(code)

        scanner = Scanner(frameworks=['langchain-py'])
        bom = scanner.scan_path(Path(tmpdir))

        assert len(bom.agents) == 1
        agent = bom.agents[0]

        tool = agent.tools.details[0]
        assert tool.tool_name == 'analyze_data'

        # Check parameters from NumPy docstring
        params = tool.parameters
        assert 'data' in params
        assert 'method' in params
        assert params['method'].required is False

        # Check return type
        assert tool.returns is not None
        assert tool.returns.type == 'float' or tool.returns.type == 'Any'


def test_sphinx_style_docstring():
    """Test parameter extraction from Sphinx-style docstrings."""
    code = '''
from langchain.agents import initialize_agent, AgentType
from langchain.tools import tool

@tool
def format_text(text, style="plain"):
    """Format text with specified style.

    :param text: The text to format
    :type text: str
    :param style: Formatting style to apply
    :type style: str
    :return: Formatted text
    :rtype: str
    """
    return text

tools = [format_text]
agent = initialize_agent(tools=tools, llm=llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION)
'''

    with tempfile.TemporaryDirectory() as tmpdir:
        agent_file = Path(tmpdir) / "agent.py"
        agent_file.write_text(code)

        scanner = Scanner(frameworks=['langchain-py'])
        bom = scanner.scan_path(Path(tmpdir))

        assert len(bom.agents) == 1
        agent = bom.agents[0]

        tool = agent.tools.details[0]
        assert tool.tool_name == 'format_text'

        # Check parameters from Sphinx docstring
        params = tool.parameters
        assert 'text' in params
        assert params['text'].type == 'str' or params['text'].type == 'Any'

        assert 'style' in params

        # Check return type
        assert tool.returns is not None
        assert tool.returns.type == 'str' or tool.returns.type == 'Any'


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])