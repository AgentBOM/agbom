"""CrewAI Python agent detector."""

import ast
import re
from pathlib import Path
from typing import List, Optional, Dict, Any

from .base import BaseDetector, DetectorResult, ToolInfo


class CrewAIDetector(BaseDetector):
    """Detector for CrewAI Python agents."""

    def get_presence_signatures(self) -> List[str]:
        """Get CrewAI import signatures."""
        return [
            r"from\s+crewai\s+import\s+.*Agent",
            r"from\s+crewai\s+import\s+.*Task",
            r"from\s+crewai\s+import\s+.*Crew",
        ]

    def get_construction_signatures(self) -> List[str]:
        """Get CrewAI construction patterns."""
        return [
            r"Crew\s*\([^)]*agents\s*=\s*\[",
        ]

    def detect(self, file_path: Path, content: str) -> Optional[DetectorResult]:
        """Detect CrewAI agent in file."""
        # Check if all required imports are present
        required_patterns = [
            r"from\s+crewai\s+import.*\bAgent\b",
            r"from\s+crewai\s+import.*\bTask\b",
            r"from\s+crewai\s+import.*\bCrew\b",
        ]

        for pattern in required_patterns:
            if not re.search(pattern, content):
                return None

        # Check construction signature
        construction_match = self.check_construction_signature(content)
        if not construction_match:
            return None

        # Parse AST to extract details
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return None

        result = DetectorResult(
            found=True,
            constructor_file=str(file_path),
            language="Python",
            frameworks=["CrewAI"],
            architecture="MAS",  # Multi-Agent System
        )

        # Extract crew information
        crew_info = self._extract_crew_info(tree, content)
        if crew_info:
            result.agent_name = crew_info.get('name', file_path.stem)
            result.metadata['agents'] = crew_info.get('agents', [])
            result.metadata['tasks'] = crew_info.get('tasks', [])
            result.tools = crew_info.get('tools', [])

        return result if result.found else None

    def _extract_crew_info(self, tree: ast.AST, content: str) -> Optional[Dict[str, Any]]:
        """Extract information about CrewAI crew and agents."""
        info = {
            'name': None,
            'agents': [],
            'tasks': [],
            'tools': []
        }

        agents = {}
        tasks = {}
        crew_agents = []
        crew_tasks = []

        # First pass: find all agent and task definitions
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                if isinstance(node.value, ast.Call):
                    if isinstance(node.value.func, ast.Name):
                        func_name = node.value.func.id

                        # Extract Agent definitions
                        if func_name == 'Agent':
                            for target in node.targets:
                                if isinstance(target, ast.Name):
                                    agent_var = target.id
                                    agent_info = self._extract_agent_details(node.value, content)
                                    agents[agent_var] = {
                                        'variable': agent_var,
                                        **agent_info
                                    }

                        # Extract Task definitions
                        elif func_name == 'Task':
                            for target in node.targets:
                                if isinstance(target, ast.Name):
                                    task_var = target.id
                                    task_info = self._extract_task_details(node.value, content)
                                    tasks[task_var] = {
                                        'variable': task_var,
                                        **task_info
                                    }

                        # Extract Crew definition
                        elif func_name == 'Crew':
                            for target in node.targets:
                                if isinstance(target, ast.Name):
                                    info['name'] = target.id

                            # Extract agents and tasks from Crew
                            for keyword in node.value.keywords:
                                if keyword.arg == 'agents':
                                    if isinstance(keyword.value, ast.List):
                                        for item in keyword.value.elts:
                                            if isinstance(item, ast.Name):
                                                crew_agents.append(item.id)
                                elif keyword.arg == 'tasks':
                                    if isinstance(keyword.value, ast.List):
                                        for item in keyword.value.elts:
                                            if isinstance(item, ast.Name):
                                                crew_tasks.append(item.id)

        # Match agents and tasks with crew
        for agent_var in crew_agents:
            if agent_var in agents:
                agent_info = agents[agent_var]
                info['agents'].append(agent_info)

                # Extract tools from agent
                if 'tools' in agent_info:
                    for tool in agent_info['tools']:
                        info['tools'].append(tool)

        for task_var in crew_tasks:
            if task_var in tasks:
                info['tasks'].append(tasks[task_var])

        return info if info['agents'] else None

    def _extract_agent_details(self, call_node: ast.Call, content: str) -> Dict[str, Any]:
        """Extract details from Agent constructor call."""
        details = {}

        for keyword in call_node.keywords:
            if keyword.arg == 'role':
                role = self.extract_string_value(keyword.value)
                if role:
                    details['role'] = role
            elif keyword.arg == 'goal':
                goal = self.extract_string_value(keyword.value)
                if goal:
                    details['goal'] = goal[:200]  # Truncate long goals
            elif keyword.arg == 'backstory':
                backstory = self.extract_string_value(keyword.value)
                if backstory:
                    details['backstory'] = backstory[:200]
            elif keyword.arg == 'tools':
                # Extract tools if provided
                tools = self._extract_tools_from_node(keyword.value, content)
                if tools:
                    details['tools'] = tools
            elif keyword.arg == 'allow_delegation':
                if isinstance(keyword.value, ast.Constant):
                    details['allow_delegation'] = keyword.value.value
            elif keyword.arg == 'verbose':
                if isinstance(keyword.value, ast.Constant):
                    details['verbose'] = keyword.value.value
            elif keyword.arg == 'max_iter':
                if isinstance(keyword.value, ast.Constant):
                    details['max_iter'] = keyword.value.value

        return details

    def _extract_task_details(self, call_node: ast.Call, content: str) -> Dict[str, Any]:
        """Extract details from Task constructor call."""
        details = {}

        for keyword in call_node.keywords:
            if keyword.arg == 'description':
                desc = self.extract_string_value(keyword.value)
                if desc:
                    details['description'] = desc[:200]
            elif keyword.arg == 'agent':
                if isinstance(keyword.value, ast.Name):
                    details['assigned_agent'] = keyword.value.id
            elif keyword.arg == 'expected_output':
                output = self.extract_string_value(keyword.value)
                if output:
                    details['expected_output'] = output[:200]
            elif keyword.arg == 'tools':
                tools = self._extract_tools_from_node(keyword.value, content)
                if tools:
                    details['tools'] = tools

        return details

    def _extract_tools_from_node(self, node: ast.AST, content: str = "") -> List[ToolInfo]:
        """Extract tool information from AST node."""
        tools = []

        if isinstance(node, (ast.List, ast.Tuple)):
            for item in node.elts:
                if isinstance(item, ast.Name):
                    # Reference to a tool variable - try to find its definition
                    tool_info = self._find_tool_definition(item.id, content) if content else None
                    if tool_info:
                        tools.append(tool_info)
                    else:
                        # Fallback to basic info
                        tools.append(ToolInfo(
                            name=item.id,
                            file_path="",
                            description=None
                        ))
                elif isinstance(item, ast.Call):
                    # Direct tool construction
                    if isinstance(item.func, ast.Name):
                        tool_name = item.func.id
                        tools.append(ToolInfo(
                            name=tool_name,
                            file_path="",
                            description=None
                        ))

        return tools

    def _find_tool_definition(self, name: str, content: str) -> Optional[ToolInfo]:
        """Find tool definition by variable name."""
        # Look for @tool decorator
        tool_pattern = rf"@tool.*?\ndef\s+{re.escape(name)}\s*\([^)]*\)"
        match = re.search(tool_pattern, content, re.DOTALL | re.MULTILINE)

        if match:
            # Parse AST to get function details
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name == name:
                        # Check if has @tool decorator
                        has_tool_decorator = any(
                            (isinstance(dec, ast.Name) and dec.id == 'tool') or
                            (isinstance(dec, ast.Attribute) and dec.attr == 'tool')
                            for dec in node.decorator_list
                        )

                        if has_tool_decorator:
                            # Extract function signature
                            signature = self.extract_function_signature(node)

                            # Get docstring
                            docstring = ast.get_docstring(node)

                            # Merge signature with docstring info
                            full_info = self.merge_docstring_info(signature, docstring)

                            # Convert to ToolInfo
                            return ToolInfo(
                                name=name,
                                file_path="",
                                description=full_info.get('description', docstring.split('\n')[0] if docstring else None),
                                parameters=full_info.get('parameters', {}),
                                returns=full_info.get('returns')
                            )
            except:
                # Fallback to basic extraction
                doc_pattern = rf'def\s+{re.escape(name)}\s*\([^)]*\)\s*:\s*"""([^"]*?)"""'
                doc_match = re.search(doc_pattern, content, re.DOTALL)
                description = doc_match.group(1).strip() if doc_match else None

                return ToolInfo(
                    name=name,
                    file_path="",
                    description=description,
                )

        return None