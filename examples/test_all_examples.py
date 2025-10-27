"""Test script to scan all example agents and verify detection."""

import sys
import os
from pathlib import Path

# Add parent directory to path to import agentbom
sys.path.insert(0, str(Path(__file__).parent.parent))

from agentbom.scanner import AgentScanner
from agentbom.models import ScanResult
import json


def test_langchain_python_examples():
    """Test LangChain Python examples."""
    print("\n" + "="*80)
    print("Testing LangChain Python Examples")
    print("="*80)
    
    examples = [
        "langchain_python/basic_agent.py",
        "langchain_python/sql_agent.py",
        "langchain_python/retrieval_agent.py",
        "langchain_python/complex_agent.py",
        "langchain_python/sales_support_agent.py",
        "langchain_python/edge_cases_agent.py",
    ]
    
    examples_dir = Path(__file__).parent
    results = []
    
    for example in examples:
        example_path = examples_dir / example
        print(f"\nScanning: {example}")
        
        scanner = AgentScanner()
        result = scanner.scan_file(example_path)
        
        if result:
            print(f"  ✓ Detected: {result.frameworks}")
            print(f"    Agent Name: {result.agent_name}")
            print(f"    Tools: {len(result.tools)}")
            print(f"    Architecture: {result.architecture}")
            if result.agent_type:
                print(f"    Agent Type: {result.agent_type}")
            results.append({
                "file": example,
                "detected": True,
                "frameworks": result.frameworks,
                "tools": len(result.tools),
                "agent_name": result.agent_name
            })
        else:
            print(f"  ✗ Not detected")
            results.append({
                "file": example,
                "detected": False
            })
    
    return results


def test_autogen_examples():
    """Test AutoGen examples."""
    print("\n" + "="*80)
    print("Testing AutoGen Examples")
    print("="*80)
    
    examples = [
        "autogen/simple_group_chat.py",
        "autogen/research_team.py",
        "autogen/coding_team.py",
        "autogen/edge_cases_autogen.py",
    ]
    
    examples_dir = Path(__file__).parent
    results = []
    
    for example in examples:
        example_path = examples_dir / example
        print(f"\nScanning: {example}")
        
        scanner = AgentScanner()
        result = scanner.scan_file(example_path)
        
        if result:
            print(f"  ✓ Detected: {result.frameworks}")
            print(f"    Agent Name: {result.agent_name}")
            print(f"    Architecture: {result.architecture}")
            if 'agents' in result.metadata:
                print(f"    Agents: {len(result.metadata['agents'])}")
            results.append({
                "file": example,
                "detected": True,
                "frameworks": result.frameworks,
                "architecture": result.architecture,
                "agent_name": result.agent_name
            })
        else:
            print(f"  ✗ Not detected")
            results.append({
                "file": example,
                "detected": False
            })
    
    return results


def test_crewai_examples():
    """Test CrewAI examples."""
    print("\n" + "="*80)
    print("Testing CrewAI Examples")
    print("="*80)
    
    examples = [
        "crewai/basic_crew.py",
        "crewai/marketing_crew.py",
        "crewai/development_crew.py",
        "crewai/edge_cases_crew.py",
    ]
    
    examples_dir = Path(__file__).parent
    results = []
    
    for example in examples:
        example_path = examples_dir / example
        print(f"\nScanning: {example}")
        
        scanner = AgentScanner()
        result = scanner.scan_file(example_path)
        
        if result:
            print(f"  ✓ Detected: {result.frameworks}")
            print(f"    Agent Name: {result.agent_name}")
            print(f"    Architecture: {result.architecture}")
            print(f"    Tools: {len(result.tools)}")
            if 'agents' in result.metadata:
                print(f"    Agents: {len(result.metadata['agents'])}")
            if 'tasks' in result.metadata:
                print(f"    Tasks: {len(result.metadata['tasks'])}")
            results.append({
                "file": example,
                "detected": True,
                "frameworks": result.frameworks,
                "tools": len(result.tools),
                "agent_name": result.agent_name
            })
        else:
            print(f"  ✗ Not detected")
            results.append({
                "file": example,
                "detected": False
            })
    
    return results


def test_langchain_typescript_examples():
    """Test LangChain TypeScript examples."""
    print("\n" + "="*80)
    print("Testing LangChain TypeScript Examples")
    print("="*80)
    
    examples = [
        "langchain_typescript/basic_agent.ts",
        "langchain_typescript/sql_agent.ts",
        "langchain_typescript/retrieval_agent.ts",
        "langchain_typescript/complex_agent.ts",
    ]
    
    examples_dir = Path(__file__).parent
    results = []
    
    for example in examples:
        example_path = examples_dir / example
        print(f"\nScanning: {example}")
        
        scanner = AgentScanner()
        result = scanner.scan_file(example_path)
        
        if result:
            print(f"  ✓ Detected: {result.frameworks}")
            print(f"    Agent Name: {result.agent_name}")
            print(f"    Language: {result.language}")
            print(f"    Tools: {len(result.tools)}")
            if result.agent_type:
                print(f"    Agent Type: {result.agent_type}")
            results.append({
                "file": example,
                "detected": True,
                "frameworks": result.frameworks,
                "tools": len(result.tools),
                "agent_name": result.agent_name
            })
        else:
            print(f"  ✗ Not detected")
            results.append({
                "file": example,
                "detected": False
            })
    
    return results


def print_summary(all_results):
    """Print summary of test results."""
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    total = sum(len(results) for results in all_results.values())
    detected = sum(
        sum(1 for r in results if r.get("detected", False))
        for results in all_results.values()
    )
    
    print(f"\nTotal examples: {total}")
    print(f"Detected: {detected}")
    print(f"Not detected: {total - detected}")
    print(f"Detection rate: {detected/total*100:.1f}%")
    
    print("\nBy framework:")
    for framework, results in all_results.items():
        detected_count = sum(1 for r in results if r.get("detected", False))
        print(f"  {framework}: {detected_count}/{len(results)}")
    
    # List any failures
    failures = []
    for framework, results in all_results.items():
        for r in results:
            if not r.get("detected", False):
                failures.append(f"{framework}/{r['file']}")
    
    if failures:
        print("\nFailed to detect:")
        for failure in failures:
            print(f"  ✗ {failure}")
    else:
        print("\n✓ All examples detected successfully!")


def main():
    """Run all tests."""
    print("AgentBOM Example Scanner Test")
    print("="*80)
    
    all_results = {
        "LangChain Python": test_langchain_python_examples(),
        "AutoGen": test_autogen_examples(),
        "CrewAI": test_crewai_examples(),
        "LangChain TypeScript": test_langchain_typescript_examples(),
    }
    
    print_summary(all_results)
    
    # Save results to JSON
    output_file = Path(__file__).parent / "test_results.json"
    with open(output_file, "w") as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\nDetailed results saved to: {output_file}")
    
    # Return exit code based on success
    total = sum(len(results) for results in all_results.values())
    detected = sum(
        sum(1 for r in results if r.get("detected", False))
        for results in all_results.values()
    )
    
    return 0 if detected == total else 1


if __name__ == "__main__":
    sys.exit(main())

