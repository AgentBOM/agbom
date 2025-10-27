# AgentBOM

**Discover, inventory, and understand AI agents across your codebase.**

AgentBOM is a CLI scanner that finds AI agents in your GitHub repositories (org/repo/local path), extracts their metadata—tools, integrations, owners, change history—and produces a single, validated JSON file conforming to the Agent BOM (Bill of Materials) schema.

Think `trivy` or `grype`, but for AI agents instead of packages.

---

## Quick Start

```bash
# Install
pip install agentbom

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
   - Tools (with parameters, integrations, permissions)
   - Owner (via CODEOWNERS or git history)
   - Created/updated timestamps
   - Files that define the agent

3. **Outputs validated JSON** matching the Agent BOM Schema (MIT-licensed)

---

## Why Two Licenses?

- **Discovery Engine** (CLI, detectors): [PolyForm Internal Use 1.0.0](LICENSE_ENGINE)  
  Use internally; don't resell as a service.

- **Agent BOM Schema** (/schema): [MIT](LICENSE_SCHEMA)  
  Fully open for maximum adoption and interoperability.

See [NOTICE](NOTICE) for details.

---

## GitHub Organization Scanning

When scanning organizations with many repositories, AgentBOM uses **smart search** to dramatically reduce scan time:

```bash
# Automatically searches for repos with agent/LLM code
# Searches for: LangChain, AutoGen, CrewAI, LlamaIndex, OpenAI, Anthropic,
#              HuggingFace, Ollama, and many more frameworks/providers
agentbom scan --org acme

# Filter by language
agentbom scan --org acme --search-languages Python,TypeScript

# Use custom keywords
agentbom scan --org acme --search-keywords "langchain,openai,agent"
```

**Benefits:**
- ⚡ **90-97% faster** for large orgs (4 hours → 8 minutes for 500 repos)
- 🔒 **Privacy-focused** - only clones repos with relevant code
- 💾 **Resource-efficient** - minimal disk/bandwidth usage
- 🛡️ **Automatic rate limit handling** - waits and retries automatically

**Note:** 
- Requires GitHub authentication. Set `GITHUB_ACCESS_TOKEN` environment variable.
- Search API limits vary (10-30 requests). Check with `agentbom rate-limit` before scanning.
- Smart mode (default) reduces API calls by 90% - **essential for low rate limits**.

See **[GITHUB_ORG_SEARCH.md](GITHUB_ORG_SEARCH.md)** for complete documentation and **[RATE_LIMIT_GUIDE.md](RATE_LIMIT_GUIDE.md)** for rate limit handling.

---

## Documentation

- **[REQUIREMENTS.md](REQUIREMENTS.md)** — Full engineering specs, detection rules, CLI reference
- **[GITHUB_ORG_SEARCH.md](GITHUB_ORG_SEARCH.md)** — Organization scanning & smart search guide
- **[SEARCH_KEYWORDS_UPDATE.md](SEARCH_KEYWORDS_UPDATE.md)** — Comprehensive search keywords for finding all AI/LLM repos
- **[RATE_LIMIT_GUIDE.md](RATE_LIMIT_GUIDE.md)** — GitHub API rate limit handling & troubleshooting
- **[RATE_LIMIT_10_REQUEST.md](RATE_LIMIT_10_REQUEST.md)** — Quick guide for 10-request limits (common with fine-grained PATs)
- **[Schema](schema/)** — Agent BOM JSON Schema (coming soon)
- **[Examples](examples/)** — Sample code and usage examples

---

## Status

🚧 **v0.1 MVP** — In active development

Currently supported:
- ✅ LangChain Python
- ✅ LangChain TypeScript
- ⏳ AutoGen (planned)
- ⏳ CrewAI (planned)

---

## Contributing

See [REQUIREMENTS.md](REQUIREMENTS.md) for the complete spec.

We welcome contributions, especially:
- Additional framework detectors (LlamaIndex, LangGraph, etc.)
- Improved tool parameter extraction
- Schema enhancements

---

## License

Dual-licensed — see [NOTICE](NOTICE):
- Engine/CLI: PolyForm Internal Use 1.0.0
- Schema: MIT

---

**Questions?** Open an issue or reach out to the maintainers.

