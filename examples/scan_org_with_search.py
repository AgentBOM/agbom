#!/usr/bin/env python3
"""
Example: Scanning a GitHub organization using smart search.

This example demonstrates how to use the smart search feature to efficiently
scan large GitHub organizations for AI agents.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agentbom import Scanner


def example_basic_org_scan():
    """Basic organization scan with smart search (recommended)."""
    print("=" * 60)
    print("Example 1: Basic Organization Scan with Smart Search")
    print("=" * 60)
    
    scanner = Scanner(
        frameworks=['langchain-py', 'langchain-ts', 'autogen', 'crewai']
    )
    
    # Smart search is enabled by default
    bom = scanner.scan_org(
        org="your-org-name",  # Replace with your org
        use_search=True  # Default, can be omitted
    )
    
    print(f"\nFound {len(bom.agents)} agent(s)")
    for agent in bom.agents:
        print(f"  - {agent.name} ({agent.type}) in {agent.repository}")
    
    return bom


def example_filtered_by_language():
    """Organization scan filtered by programming language."""
    print("\n" + "=" * 60)
    print("Example 2: Scan with Language Filter")
    print("=" * 60)
    
    scanner = Scanner()
    
    # Only scan Python repositories
    bom = scanner.scan_org(
        org="your-org-name",
        use_search=True,
        search_languages=["Python"]
    )
    
    print(f"\nFound {len(bom.agents)} agent(s) in Python repos")
    return bom


def example_custom_keywords():
    """Organization scan with custom search keywords."""
    print("\n" + "=" * 60)
    print("Example 3: Scan with Custom Keywords")
    print("=" * 60)
    
    scanner = Scanner()
    
    # Use custom keywords to find your specific agent patterns
    custom_keywords = [
        "from langchain",
        "import openai",
        "MyCustomAgent",  # Your custom agent class
        "CompanyAIService",  # Your custom service
    ]
    
    bom = scanner.scan_org(
        org="your-org-name",
        use_search=True,
        search_keywords=custom_keywords
    )
    
    print(f"\nFound {len(bom.agents)} agent(s) using custom keywords")
    return bom


def example_combined_filters():
    """Organization scan with multiple filters."""
    print("\n" + "=" * 60)
    print("Example 4: Scan with Combined Filters")
    print("=" * 60)
    
    scanner = Scanner(
        frameworks=['langchain-py', 'langchain-ts'],
        parallel=4  # Scan 4 files in parallel
    )
    
    # Combine language filter with custom keywords
    bom = scanner.scan_org(
        org="your-org-name",
        use_search=True,
        search_keywords=["from langchain", "ChatOpenAI", "AgentExecutor"],
        search_languages=["Python", "TypeScript"]
    )
    
    print(f"\nFound {len(bom.agents)} agent(s)")
    
    # Group by repository
    repos_with_agents = {}
    for agent in bom.agents:
        if agent.repository not in repos_with_agents:
            repos_with_agents[agent.repository] = []
        repos_with_agents[agent.repository].append(agent)
    
    print(f"\nAgents found in {len(repos_with_agents)} repository(ies):")
    for repo, agents in repos_with_agents.items():
        print(f"\n  {repo}:")
        for agent in agents:
            print(f"    - {agent.name} ({agent.type})")
            print(f"      Tools: {agent.tools.count}")
            print(f"      Files: {', '.join(agent.files)}")
    
    return bom


def example_no_search_mode():
    """Organization scan WITHOUT smart search (not recommended)."""
    print("\n" + "=" * 60)
    print("Example 5: Scan ALL Repos (No Search - Use with Caution)")
    print("=" * 60)
    print("\n⚠️  WARNING: This will clone and scan ALL repositories!")
    print("    Only use this for small organizations or comprehensive audits.")
    
    scanner = Scanner()
    
    # Disable smart search - will scan ALL repos
    bom = scanner.scan_org(
        org="your-small-org",  # Only use for small orgs!
        use_search=False
    )
    
    print(f"\nScanned all repos, found {len(bom.agents)} agent(s)")
    return bom


def example_save_results():
    """Scan and save results to a file."""
    print("\n" + "=" * 60)
    print("Example 6: Scan and Save Results")
    print("=" * 60)
    
    scanner = Scanner()
    
    bom = scanner.scan_org(
        org="your-org-name",
        use_search=True,
        search_languages=["Python", "TypeScript"]
    )
    
    # Save to file
    output_path = Path("org_agents.json")
    output_path.write_text(bom.to_json())
    print(f"\n✅ Results saved to {output_path}")
    print(f"   Found {len(bom.agents)} agent(s)")
    
    # Pretty print summary
    if bom.agents:
        print("\nAgent Summary:")
        for agent in bom.agents:
            print(f"\n  {agent.name}")
            print(f"    Repository: {agent.repository}")
            print(f"    Type: {agent.type}")
            print(f"    Language: {agent.language}")
            print(f"    Frameworks: {', '.join(agent.frameworks)}")
            print(f"    Tools: {agent.tools.count}")
            print(f"    Owner: {agent.owner}")
    
    return bom


def main():
    """Run examples."""
    # Check for GitHub token
    if not os.environ.get('GITHUB_ACCESS_TOKEN'):
        print("⚠️  WARNING: GITHUB_ACCESS_TOKEN not set")
        print("   Set it for better rate limits and private repo access:")
        print("   export GITHUB_ACCESS_TOKEN=ghp_your_token_here")
        print()
    
    print("AgentBOM Organization Scanning Examples")
    print("=" * 60)
    print("\nThese examples demonstrate different ways to scan GitHub")
    print("organizations using the smart search feature.\n")
    
    # Note: Replace 'your-org-name' with an actual organization name to run
    print("📝 Note: Update the examples with your organization name to run them.")
    print("\nUncomment the example you want to run:\n")
    
    # Uncomment the example you want to run:
    
    # Example 1: Basic scan with smart search
    # bom = example_basic_org_scan()
    
    # Example 2: Filter by language
    # bom = example_filtered_by_language()
    
    # Example 3: Custom keywords
    # bom = example_custom_keywords()
    
    # Example 4: Combined filters (recommended for production)
    # bom = example_combined_filters()
    
    # Example 5: No search mode (not recommended)
    # bom = example_no_search_mode()
    
    # Example 6: Save results
    # bom = example_save_results()
    
    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60)


if __name__ == '__main__':
    main()

