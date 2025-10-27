#!/usr/bin/env python3
"""Generate AgentBOM JSON file from all example agents.

This script scans all example agents and generates a complete AgentBOM JSON file.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agentbom.scanner import Scanner


def main():
    """Generate AgentBOM from all examples."""
    print("Generating AgentBOM from example agents...")
    print("=" * 80)

    # Initialize scanner with all frameworks and exclude test/utility files
    scanner = Scanner(
        frameworks=["langchain-py", "langchain-ts", "autogen", "crewai"],
        exclude_patterns=[
            "**/test_*.py",  # Test files
            "**/*_test.py",  # Test files
            "**/generate_bom.py",  # This script itself
            "**/test_all_examples.py",  # Old test script
            "**/__pycache__/**",  # Python cache
            "**/node_modules/**",  # Node modules
            "**/.gitignore",  # Git files
            "**/README*.md",  # Documentation
            "**/INDEX.md",  # Documentation
            "**/USAGE.md",  # Documentation
            "**/*.json",  # JSON files
        ],
    )

    # Scan the examples directory
    examples_dir = Path(__file__).parent
    print(f"\nScanning directory: {examples_dir}")
    print("Excluding: test files, utilities, documentation\n")

    # Run the scan
    bom = scanner.scan_path(examples_dir)

    # Filter out problematic detections
    # - "examples" is a failed name extraction from edge_cases_autogen.py
    original_count = len(bom.agents)
    bom.agents = [
        agent for agent in bom.agents if agent.name not in ["examples", None, ""]
    ]

    if len(bom.agents) < original_count:
        print(
            f"\n⚠ Filtered out {original_count - len(bom.agents)} problematic detection(s)"
        )

    # Print summary
    print(f"\n✓ Found {len(bom.agents)} valid agents")
    print("\nAgents detected:")
    for i, agent in enumerate(bom.agents, 1):
        print(f"  {i}. {agent.name}")
        print(f"     Framework: {', '.join(agent.frameworks)}")
        print(f"     Language: {agent.language}")
        print(f"     Tools: {agent.tools.count}")
        print(f"     Architecture: {agent.architecture}")
        print()

    # Save to JSON file
    output_file = examples_dir.parent / "agentbom.json"
    json_output = bom.to_json(indent=2)

    with open(output_file, "w") as f:
        f.write(json_output)

    print("=" * 80)
    print(f"✓ AgentBOM saved to: {output_file}")
    print(f"  Total agents: {len(bom.agents)}")
    print(f"  Total tools: {sum(agent.tools.count for agent in bom.agents)}")

    # Also save to examples directory
    examples_output = examples_dir / "agentbom.json"
    with open(examples_output, "w") as f:
        f.write(json_output)

    print(f"  Also saved to: {examples_output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
