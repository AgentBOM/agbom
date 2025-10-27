# Example Usage Guide

This guide demonstrates how to use the example agents with AgentBOM scanner.

## Quick Start

### 1. Scan a Single Example

```bash
# Scan a LangChain Python example
python -m agentbom.cli scan --path examples/langchain_python/basic_agent.py --stdout

# Scan an AutoGen example
python -m agentbom.cli scan --path examples/autogen/simple_group_chat.py --stdout

# Scan a CrewAI example
python -m agentbom.cli scan --path examples/crewai/basic_crew.py --stdout

# Scan a LangChain TypeScript example
python -m agentbom.cli scan --path examples/langchain_typescript/basic_agent.ts --stdout
```

### 2. Scan an Entire Framework Directory

```bash
# Scan all LangChain Python examples
python -m agentbom.cli scan --path examples/langchain_python/ --out langchain_results.json

# Scan all AutoGen examples
python -m agentbom.cli scan --path examples/autogen/ --out autogen_results.json

# Scan all CrewAI examples
python -m agentbom.cli scan --path examples/crewai/ --out crewai_results.json

# Scan all TypeScript examples
python -m agentbom.cli scan --path examples/langchain_typescript/ --out typescript_results.json
```

### 3. Scan All Examples

```bash
# Scan everything in examples directory
python -m agentbom.cli scan --path examples/ --out all_examples.json
```

### 4. Run the Test Suite

```bash
# Run comprehensive test of all examples
python examples/test_all_examples.py
```

## Example Output

### Basic Agent Detection

When scanning `basic_agent.py`, you should see:

```
Found 1 Agent(s)
┏━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━┓
┃ Name        ┃ Type      ┃ Framework             ┃ Language ┃ Tools ┃ Owner   ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━┩
│ basic_agent │ LLM Agent │ LangChain,            │ Python   │ 3     │ unknown │
│             │           │ langchain_openai      │          │       │         │
└─────────────┴───────────┴───────────────────────┴──────────┴───────┴─────────┘
```

### SQL Agent Detection

When scanning `sql_agent.py`, you should see:

```
Found 1 Agent(s)
┏━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━┓
┃ Name      ┃ Type      ┃ Framework             ┃ Language ┃ Tools ┃ Owner   ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━┩
│ sql_agent │ SQL Agent │ LangChain,            │ Python   │ 4     │ unknown │
│           │           │ langchain_openai,     │          │       │         │
│           │           │ langchain_community   │          │       │         │
└───────────┴───────────┴───────────────────────┴──────────┴───────┴─────────┘
```

### AutoGen Multi-Agent System

When scanning `research_team.py`, you should see:

```
Found 1 Agent(s)
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━┓
┃ Name            ┃ Type      ┃ Framework ┃ Language ┃ Tools ┃ Owner   ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━┩
│ research_manager│ LLM Agent │ AutoGen   │ Python   │ 0     │ unknown │
└─────────────────┴───────────┴───────────┴──────────┴───────┴─────────┘

Architecture: MAS
Agents in system: 5 (researcher, writer, critic, editor, user_proxy)
```

## Advanced Usage

### Filter by Framework

```bash
# Only detect LangChain agents
python -m agentbom.cli scan --path examples/ --frameworks langchain --stdout

# Only detect AutoGen agents
python -m agentbom.cli scan --path examples/ --frameworks autogen --stdout

# Only detect CrewAI agents
python -m agentbom.cli scan --path examples/ --frameworks crewai --stdout
```

### Verbose Output

```bash
# See detailed scanning information
python -m agentbom.cli scan --path examples/langchain_python/ --verbose --stdout
```

### Export Results

```bash
# Export to JSON file
python -m agentbom.cli scan --path examples/ --out results.json

# View the results
cat results.json | jq '.agents[] | {name: .name, type: .type, tools: .tools.count}'
```

## Expected Results Summary

### LangChain Python Examples

| Example | Agent Name | Type | Tools | Architecture |
|---------|------------|------|-------|-------------|
| basic_agent.py | basic_agent | LLM Agent | 3 | ReAct |
| sql_agent.py | sql_agent | SQL Agent | 4 | ReAct |
| retrieval_agent.py | retrieval_agent | Retrieval Agent | 4 | ReAct |
| complex_agent.py | complex_agent | LLM Agent | 7 | ReAct |
| sales_support_agent.py | sales_support_agent | LLM Agent | 3 | ReAct |
| edge_cases_agent.py | edge_case_agent | LLM Agent | 4 | ReAct |

### AutoGen Examples

| Example | Agent Name | Type | Architecture | Agents in System |
|---------|------------|------|-------------|-----------------|
| simple_group_chat.py | manager | LLM Agent | MAS | 3 |
| research_team.py | research_manager | LLM Agent | MAS | 5 |
| coding_team.py | coding_manager | LLM Agent | MAS | 4 |
| edge_cases_autogen.py | edge_case_manager | LLM Agent | MAS | 6 |

### CrewAI Examples

| Example | Agent Name | Type | Agents | Tasks | Tools |
|---------|------------|------|--------|-------|-------|
| basic_crew.py | basic_crew | LLM Agent | 2 | 2 | 2 |
| marketing_crew.py | marketing_crew | LLM Agent | 3 | 3 | 4 |
| development_crew.py | development_crew | LLM Agent | 4 | 4 | 5 |
| edge_cases_crew.py | edge_case_crew | LLM Agent | 3 | 4 | 3 |

### LangChain TypeScript Examples

| Example | Agent Name | Type | Tools | Language |
|---------|------------|------|-------|----------|
| basic_agent.ts | basicAgent | LLM Agent | 3 | TypeScript |
| sql_agent.ts | sqlAgent | SQL Agent | 4 | TypeScript |
| retrieval_agent.ts | retrievalAgent | Retrieval Agent | 4 | TypeScript |
| complex_agent.ts | complexAgent | LLM Agent | 7 | TypeScript |

## Troubleshooting

### Example Not Detected

If an example is not detected:

1. **Check the file path**
   ```bash
   ls -la examples/langchain_python/basic_agent.py
   ```

2. **Run with verbose mode**
   ```bash
   python -m agentbom.cli scan --path examples/langchain_python/basic_agent.py --verbose --stdout
   ```

3. **Verify imports are present**
   ```bash
   grep -n "from langchain" examples/langchain_python/basic_agent.py
   ```

### Tools Not Extracted

If tools are not extracted:

1. **Check tool definitions**
   ```bash
   grep -n "@tool" examples/langchain_python/basic_agent.py
   ```

2. **Verify tool list**
   ```bash
   grep -n "tools = \[" examples/langchain_python/basic_agent.py
   ```

3. **Run with strict mode off**
   ```bash
   python -m agentbom.cli scan --path examples/langchain_python/basic_agent.py --no-strict --stdout
   ```

### TypeScript Examples

For TypeScript examples, ensure the scanner can read `.ts` files:

```bash
# Check file extension handling
python -m agentbom.cli scan --path examples/langchain_typescript/ --verbose --stdout
```

## Integration Testing

### Add Examples to Your Tests

```python
from pathlib import Path
from agentbom.scanner import AgentScanner

def test_my_detection():
    # Use examples as test fixtures
    example_file = Path("examples/langchain_python/basic_agent.py")
    scanner = AgentScanner()
    result = scanner.scan_file(example_file)
    
    assert result is not None
    assert result.agent_name == "basic_agent"
    assert len(result.tools) == 3
```

### Batch Testing

```bash
# Test all examples in one go
for example in examples/langchain_python/*.py; do
    echo "Testing: $example"
    python -m agentbom.cli scan --path "$example" --quiet --stdout > /dev/null
    if [ $? -eq 0 ]; then
        echo "  ✓ Success"
    else
        echo "  ✗ Failed"
    fi
done
```

## Performance Benchmarks

Expected scanning times (approximate):

- Single file: < 1 second
- Single framework directory: 2-5 seconds
- All examples: 5-10 seconds
- With LLM enrichment: 30-60 seconds

## Contributing New Examples

When adding new examples:

1. Follow the existing structure
2. Use mock implementations
3. Add to test_all_examples.py
4. Update documentation
5. Verify detection:
   ```bash
   python -m agentbom.cli scan --path examples/your_framework/your_example.py --stdout
   ```

## Support

If you encounter issues:

1. Check this usage guide
2. Review the README.md
3. Check SUMMARY.md for expected results
4. Run the test suite: `python examples/test_all_examples.py`
5. Open an issue with verbose output

