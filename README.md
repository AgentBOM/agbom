# AgentBOM

**Discover, inventory, and understand AI agents across your codebase.**

AgentBOM is a CLI scanner that finds AI agents in your GitHub repositories (org/repo/local path), extracts their metadata—tools, integrations, owners, change history—and produces a single, validated JSON file conforming to the Agent BOM (Bill of Materials) schema.

Think `trivy` or `grype`, but for AI agents instead of packages.

---

## Quick Start

```bash
# Install dependencies (from source)
pip install -e .

# Scan current directory
agentbom scan --path .

# Scan a GitHub repo
agentbom scan --repo acme/ai-sales

# Scan entire GitHub org (uses smart search to filter repos)
agentbom scan --org acme --out ./agents.json

# Check GitHub API rate limits
agentbom rate-limit
```

---

## What It Does

1. **Discovers agents** using deterministic signatures for:
   - LangChain (Python & TypeScript)
   - AutoGen (Python)
   - CrewAI (Python)

2. **Extracts metadata**:
   - Agent name, purpose, architecture
   - Tools (with parameters, descriptions, return types)
   - Owner (via CODEOWNERS or git history)
   - Created/updated timestamps
   - Files that define the agent

3. **Outputs validated JSON** matching the Agent BOM Schema (MIT-licensed)

---

## Why Two Licenses?

- **Discovery Engine** (CLI, detectors): [PolyForm Internal Use 1.0.0](LICENSE_ENGINE)  
  Use internally; don't resell as a service.

- **Agent BOM Schema**: [MIT](LICENSE_SCHEMA)  
  Fully open for maximum adoption and interoperability.

See [NOTICE](NOTICE) for details.

---

## GitHub Organization Scanning

When scanning organizations with many repositories, AgentBOM uses **smart search** to dramatically reduce scan time:

```bash
# Automatically searches for repos with agent/LLM code
# Smart mode (default) uses 4 combined queries covering:
#   - LangChain, AutoGen, CrewAI, LlamaIndex frameworks
#   - OpenAI, Anthropic, Cohere, HuggingFace providers
#   - Generic agent patterns
agentbom scan --org acme

# Filter by language (reduces API calls)
agentbom scan --org acme --search-languages Python,TypeScript

# Use custom keywords for targeted search
agentbom scan --org acme --search-keywords "langchain,openai,agent"

# Disable search to scan all repos (not recommended for large orgs)
agentbom scan --org acme --no-search
```

### Benefits

- ⚡ **90-97% faster** for large orgs (4 hours → 8 minutes for 500 repos)
- 🔒 **Privacy-focused** - only clones repos with relevant code
- 💾 **Resource-efficient** - minimal disk/bandwidth usage
- 🛡️ **Automatic rate limit handling** - waits and retries automatically

### Rate Limits

GitHub Search API limits vary by token type:
- **Unauthenticated**: 10 requests/min
- **Fine-grained PAT**: 10 requests/10min (common)
- **Classic PAT**: 10-30 requests/min
- **GitHub App**: 30 requests/min

**Best Practices:**
1. Set `GITHUB_ACCESS_TOKEN` environment variable
2. Check limits first: `agentbom rate-limit`
3. Use smart mode (default) - reduces 25+ queries to 4
4. Filter by language to minimize API calls
5. Wait 10+ minutes between scans if you have strict limits

---

## Policy Validation (Build Step)

AgentBOM includes a static policy validation engine for CI/CD pipelines that checks code against organizational rulesets.

### Quick Start

```bash
# Validate current directory against ruleset
agentbom validate --path . --rules .github/agentbom/rules.yml

# Check only changed files since origin/main
agentbom validate --path . --rules .github/agentbom/rules.yml --changed-only

# Strict mode (fail on Medium+ findings)
agentbom validate --path . --rules .github/agentbom/rules.yml --strict

# JSON output for CI/CD
agentbom validate --path . --rules .github/agentbom/rules.yml --json
```

### Exit Codes

- **0**: All checks passed
- **1**: Policy violations found (High/Critical, or Medium+ with `--strict`)
- **2**: Ruleset parse error
- **4**: Internal error

### Ruleset Format

Rulesets are YAML or JSON files defining policy rules:

```yaml
version: "1"
rules:
  - id: LCP-001
    title: Execution step cap present
    category: reliability
    severity: high
    scope: build
    detect:
      python_regex_any: ["max_steps\\s*=\\s*\\d+"]
      ts_regex_any: ["maxSteps\\s*:\\s*\\d+"]
    autofix_hint: "Add max_steps=50 to your agent configuration"
```

### Built-in Rules

The default ruleset (`.github/agentbom/rules.yml`) includes:

- **LCP-001**: Execution step cap present (prevents infinite loops)
- **LCP-002**: Model version pinned (bans `"latest"` model references)
- **LCP-004**: Typed tool inputs (requires Pydantic/TypeScript interfaces)
- **LCP-008**: Prompt templates (bans f-string concatenation with user input)

### CI/CD Integration

```yaml
# GitHub Actions example
- name: Validate Policy
  run: |
    agentbom validate --path . --rules .github/agentbom/rules.yml --strict --json
```

---

## Supported Frameworks

| Framework | Language | Status | Examples |
|-----------|----------|--------|----------|
| **LangChain** | Python | ✅ Fully supported | [examples/langchain_python/](examples/langchain_python/) |
| **LangChain** | TypeScript | ✅ Fully supported | [examples/langchain_typescript/](examples/langchain_typescript/) |
| **AutoGen** | Python | ✅ Fully supported | [examples/autogen/](examples/autogen/) |
| **CrewAI** | Python | ✅ Fully supported | [examples/crewai/](examples/crewai/) |

---

## Documentation

- **[examples/README.md](examples/README.md)** — Comprehensive examples for all supported frameworks
- **[examples/USAGE.md](examples/USAGE.md)** — Usage patterns and scanning examples

---

## CLI Reference

### Scan Command

```bash
agentbom scan [OPTIONS]
```

**Source Options** (choose one):
- `--path PATH` - Scan local directory (default: current directory)
- `--repo ORG/REPO` - Scan GitHub repository
- `--org ORG` - Scan GitHub organization

**Output Options**:
- `--out FILE` - Output file path (default: agent_bom.json)
- `--stdout` - Output to stdout instead of file

**Framework Options**:
- `--frameworks LIST` - Frameworks to detect (default: langchain-py,langchain-ts)
  - Options: `langchain-py`, `langchain-ts`, `autogen`, `crewai`

**Search Options** (for `--org` only):
- `--search/--no-search` - Use smart search to filter repos (default: on)
- `--search-keywords KEYWORDS` - Custom search keywords (comma-separated)
- `--search-languages LANGS` - Filter by languages (e.g., Python,TypeScript)

**Advanced Options**:
- `--max-file-mb SIZE` - Maximum file size in MB (default: 1.5)
- `--parallel N` - Parallel workers (default: 8)
- `--strict/--no-strict` - Strict detection mode (default: on)
- `-v, --verbose` - Verbose output
- `--quiet` - Quiet mode (errors only)

### Rate Limit Command

```bash
agentbom rate-limit
```

Shows current GitHub API rate limit status for both Core API and Search API.

### Version Command

```bash
agentbom --version
```

---

## Examples

See [examples/](examples/) directory for comprehensive examples including:

- **LangChain Python**: Basic agents, SQL agents, retrieval agents, complex agents
- **LangChain TypeScript**: TypeScript equivalents with Zod schemas
- **AutoGen**: Multi-agent systems, research teams, coding teams
- **CrewAI**: Crews with tasks, marketing teams, development workflows

Run any example to see it in action, then scan it with AgentBOM:

```bash
# Run an example
python examples/langchain_python/basic_agent.py

# Scan it
agentbom scan --path examples/langchain_python --out basic_agent_bom.json

# View results
cat basic_agent_bom.json | jq
```

---

## Development

```bash
# Clone repository
git clone https://github.com/AgentBOM/agbom.git
cd agbom

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check .

# Format code
black .
```

---

## Contributing

We welcome contributions! Areas of interest:

- Additional framework detectors (LlamaIndex, LangGraph, Semantic Kernel, etc.)
- Improved tool parameter extraction
- Schema enhancements
- Documentation improvements

Please ensure:
1. Tests pass: `pytest`
2. Code is formatted: `black .`
3. Linting passes: `ruff check .`
4. Examples are updated if adding new detectors

---

## License

Dual-licensed — see [NOTICE](NOTICE):
- **Engine/CLI**: PolyForm Internal Use 1.0.0
- **Schema**: MIT

---

## Status

🚧 **v0.1.0** — Active development

This project is functional but still evolving. APIs and output formats may change.

---

**Questions?** Open an issue at [github.com/AgentBOM/agbom](https://github.com/AgentBOM/agbom)

