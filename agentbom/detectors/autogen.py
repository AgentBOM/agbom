"""AutoGen Python agent detector."""

import ast
from pathlib import Path
from typing import List, Optional, Dict, Any

from .base import BaseDetector, DetectorResult


class AutoGenDetector(BaseDetector):
    """Detector for AutoGen Python agents."""

    def get_presence_signatures(self) -> List[str]:
        """Get AutoGen import signatures."""
        return [
            r"from\s+autogen\s+import\s+.*AssistantAgent",
            r"from\s+autogen\s+import\s+.*UserProxyAgent",
            r"from\s+autogen\s+import\s+.*GroupChat",
            r"from\s+autogen\s+import\s+.*GroupChatManager",
        ]

    def get_construction_signatures(self) -> List[str]:
        """Get AutoGen construction patterns."""
        return [
            r"GroupChatManager\s*\([^)]*groupchat\s*=",
        ]

    def detect(self, file_path: Path, content: str) -> Optional[DetectorResult]:
        """Detect AutoGen agent in file."""
        # Check if all required imports are present
        required_imports = [
            "AssistantAgent",
            "UserProxyAgent",
            "GroupChat",
            "GroupChatManager",
        ]

        for required in required_imports:
            if required not in content:
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
            frameworks=["AutoGen"],
            architecture="MAS",  # Multi-Agent System
        )

        # Extract agent information
        agents_info = self._extract_agents_info(tree, content)
        if agents_info:
            result.agent_name = agents_info.get("name", file_path.stem)
            result.metadata["agents"] = agents_info.get("agents", [])
            result.metadata["group_chat"] = agents_info.get("group_chat", {})

        return result if result.found else None

    def _extract_agents_info(
        self, tree: ast.AST, content: str
    ) -> Optional[Dict[str, Any]]:
        """Extract information about AutoGen agents."""
        info = {"name": None, "agents": [], "group_chat": {}}

        agents = {}
        group_chat_agents = []
        group_chat_var = None

        # First pass: find all agent definitions
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                if isinstance(node.value, ast.Call):
                    if isinstance(node.value.func, ast.Name):
                        func_name = node.value.func.id

                        # Extract agent definitions
                        if func_name in ["AssistantAgent", "UserProxyAgent"]:
                            for target in node.targets:
                                if isinstance(target, ast.Name):
                                    agent_name = target.id
                                    agent_info = self._extract_agent_details(node.value)
                                    agents[agent_name] = {
                                        "variable": agent_name,
                                        "type": func_name,
                                        **agent_info,
                                    }

                        # Extract GroupChat definition
                        elif func_name == "GroupChat":
                            for target in node.targets:
                                if isinstance(target, ast.Name):
                                    group_chat_var = target.id

                            # Extract agents list from GroupChat
                            for keyword in node.value.keywords:
                                if keyword.arg == "agents":
                                    if isinstance(keyword.value, ast.List):
                                        for item in keyword.value.elts:
                                            if isinstance(item, ast.Name):
                                                group_chat_agents.append(item.id)

                        # Extract GroupChatManager
                        elif func_name == "GroupChatManager":
                            for target in node.targets:
                                if isinstance(target, ast.Name):
                                    info["name"] = target.id

                            # Verify groupchat parameter
                            for keyword in node.value.keywords:
                                if keyword.arg == "groupchat":
                                    if isinstance(keyword.value, ast.Name):
                                        if keyword.value.id == group_chat_var:
                                            info["group_chat"]["linked"] = True

        # Match agents with group chat
        for agent_var in group_chat_agents:
            if agent_var in agents:
                info["agents"].append(agents[agent_var])

        return info if info["agents"] else None

    def _extract_agent_details(self, call_node: ast.Call) -> Dict[str, Any]:
        """Extract details from agent constructor call."""
        details = {}

        for keyword in call_node.keywords:
            if keyword.arg == "name":
                name = self.extract_string_value(keyword.value)
                if name:
                    details["name"] = name
            elif keyword.arg == "system_message":
                message = self.extract_string_value(keyword.value)
                if message:
                    details["system_message"] = message[:200]  # Truncate long messages
            elif keyword.arg == "max_consecutive_auto_reply":
                if isinstance(keyword.value, ast.Constant):
                    details["max_consecutive_auto_reply"] = keyword.value.value
            elif keyword.arg == "code_execution_config":
                details["has_code_execution"] = True
            elif keyword.arg == "function_map":
                details["has_functions"] = True
            elif keyword.arg == "llm_config":
                details["has_llm_config"] = True

        return details
