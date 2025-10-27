# Agent BOM Example Agents

This directory contains example agents for all supported frameworks. These examples are designed to test the AgentBOM scanner's ability to detect and analyze different types of agents across various frameworks.

## Directory Structure

```
examples/
├── langchain_python/     # LangChain Python examples
├── langchain_typescript/ # LangChain TypeScript examples
├── autogen/             # AutoGen examples
└── crewai/              # CrewAI examples
```

## LangChain Python Examples

### basic_agent.py
A simple LangChain agent with basic tools for weather, distance calculation, and time queries.
- **Tools**: 3 simple tools
- **Architecture**: ReAct
- **Use Case**: Travel assistance

### sql_agent.py
A LangChain agent specialized for database operations.
- **Tools**: SQL query tools
- **Agent Type**: SQL Agent
- **Use Case**: Database querying and analysis

### retrieval_agent.py
A LangChain agent with vector search and retrieval capabilities.
- **Tools**: Documentation search, knowledge base retrieval
- **Agent Type**: Retrieval Agent
- **Use Case**: Knowledge management and support

### complex_agent.py
An advanced LangChain agent with multiple tools and conversation memory.
- **Tools**: 7 diverse tools (web search, email, calendar, NLP)
- **Features**: Conversation memory, advanced configuration
- **Use Case**: Executive assistant

## AutoGen Examples

### simple_group_chat.py
A basic AutoGen multi-agent system with 3 agents.
- **Agents**: CodeExecutor, DataAnalyst, Planner
- **Architecture**: Multi-Agent System (MAS)
- **Use Case**: Data analysis workflow

### research_team.py
An AutoGen research team with specialized agents.
- **Agents**: 5 agents (Researcher, Writer, Critic, Editor, UserProxy)
- **Architecture**: Multi-Agent System (MAS)
- **Use Case**: Content creation and research

### coding_team.py
An AutoGen coding team with developer agents.
- **Agents**: 4 agents (Executor, SeniorDev, Reviewer, QA)
- **Features**: Code execution, function mapping
- **Use Case**: Software development

## CrewAI Examples

### basic_crew.py
A simple CrewAI crew with 2 agents and 2 tasks.
- **Agents**: Researcher, Analyst
- **Tasks**: Sequential workflow
- **Use Case**: Research and analysis

### marketing_crew.py
A CrewAI marketing team with specialized roles.
- **Agents**: 3 agents (Strategist, ContentCreator, CampaignManager)
- **Features**: Delegation, multiple tools
- **Use Case**: Marketing campaign development

### development_crew.py
A CrewAI software development crew.
- **Agents**: 4 agents (Architect, Developer, Reviewer, TechWriter)
- **Process**: Sequential development workflow
- **Use Case**: Software project lifecycle

## LangChain TypeScript Examples

### basic_agent.ts
A simple TypeScript agent with basic tools.
- **Tools**: 3 tools using Zod schemas
- **Language**: TypeScript
- **Use Case**: Travel assistance

### sql_agent.ts
A TypeScript SQL agent for database operations.
- **Tools**: SQL-related tools
- **Agent Type**: SQL Agent
- **Use Case**: Database management

### retrieval_agent.ts
A TypeScript retrieval agent with vector search.
- **Tools**: Vector search and retrieval tools
- **Features**: Embeddings, memory vector store
- **Use Case**: Knowledge retrieval

### complex_agent.ts
An advanced TypeScript agent with comprehensive tools.
- **Tools**: 7 diverse tools
- **Features**: Buffer memory, advanced configuration
- **Use Case**: Executive assistant

## Running the Examples

### Python Examples

```bash
# Run a LangChain Python example
python examples/langchain_python/basic_agent.py

# Run an AutoGen example
python examples/autogen/simple_group_chat.py

# Run a CrewAI example
python examples/crewai/basic_crew.py
```

### TypeScript Examples

```bash
# Install dependencies first
npm install

# Run a TypeScript example
ts-node examples/langchain_typescript/basic_agent.ts
```

## Scanning Examples

To scan these examples with AgentBOM:

```bash
# Scan all Python examples
agentbom scan examples/langchain_python
agentbom scan examples/autogen
agentbom scan examples/crewai

# Scan TypeScript examples
agentbom scan examples/langchain_typescript
```

## Testing Coverage

These examples are designed to test:

1. **Framework Detection**: Verify correct framework identification
2. **Tool Extraction**: Ensure all tools are properly detected
3. **Agent Types**: Test detection of SQL agents, retrieval agents, etc.
4. **Multi-Agent Systems**: Validate MAS detection (AutoGen, CrewAI)
5. **Metadata Extraction**: Verify extraction of agent configurations
6. **Cross-Language Support**: Test both Python and TypeScript
7. **Architecture Detection**: Test ReAct, MAS, and other patterns

## Example Characteristics

| Example | Framework | Language | Agents | Tools | Architecture |
|---------|-----------|----------|--------|-------|-------------|
| basic_agent.py | LangChain | Python | 1 | 3 | ReAct |
| sql_agent.py | LangChain | Python | 1 | 4 | ReAct |
| retrieval_agent.py | LangChain | Python | 1 | 4 | ReAct |
| complex_agent.py | LangChain | Python | 1 | 7 | ReAct |
| simple_group_chat.py | AutoGen | Python | 3 | 0 | MAS |
| research_team.py | AutoGen | Python | 5 | 0 | MAS |
| coding_team.py | AutoGen | Python | 4 | 2 | MAS |
| basic_crew.py | CrewAI | Python | 2 | 2 | MAS |
| marketing_crew.py | CrewAI | Python | 3 | 4 | MAS |
| development_crew.py | CrewAI | Python | 4 | 5 | MAS |
| basic_agent.ts | LangChain | TypeScript | 1 | 3 | Other |
| sql_agent.ts | LangChain | TypeScript | 1 | 4 | Other |
| retrieval_agent.ts | LangChain | TypeScript | 1 | 4 | Other |
| complex_agent.ts | LangChain | TypeScript | 1 | 7 | Other |

## Contributing

When adding new examples:

1. Follow the existing structure and naming conventions
2. Include clear docstrings and comments
3. Add mock implementations for tools (no real API calls)
4. Update this README with the new example details
5. Test that the scanner correctly detects your example

