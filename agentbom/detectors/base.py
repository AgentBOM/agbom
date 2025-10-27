"""Base detector interface and utilities."""

import ast
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Any
from agentbom.utils.docstring_parser import DocstringParser


@dataclass
class ToolInfo:
    """Information about a detected tool."""

    name: str
    file_path: str
    line_number: int = 0
    description: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    returns: Optional[Dict[str, Any]] = None
    raw_definition: Optional[str] = None


@dataclass
class DetectorResult:
    """Result from agent detection."""

    found: bool = False
    agent_name: Optional[str] = None
    constructor_file: Optional[str] = None
    tool_files: List[str] = field(default_factory=list)
    tools: List[ToolInfo] = field(default_factory=list)
    architecture: str = "Other"
    frameworks: List[str] = field(default_factory=list)
    language: str = ""
    agent_type: str = "LLM Agent"
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseDetector(ABC):
    """Base class for framework-specific agent detectors."""

    def __init__(self, strict_mode: bool = True):
        """Initialize detector.

        Args:
            strict_mode: If True, require literal tool arrays and direct constructors
        """
        self.strict_mode = strict_mode

    @abstractmethod
    def get_presence_signatures(self) -> List[str]:
        """Get import patterns that must be present for this framework.

        Returns:
            List of import patterns (regex or literal strings)
        """
        pass

    @abstractmethod
    def get_construction_signatures(self) -> List[str]:
        """Get construction patterns that identify an agent.

        Returns:
            List of construction patterns (regex)
        """
        pass

    @abstractmethod
    def detect(self, file_path: Path, content: str) -> Optional[DetectorResult]:
        """Detect agent in a file.

        Args:
            file_path: Path to the file
            content: File content

        Returns:
            DetectorResult if agent found, None otherwise
        """
        pass

    def check_presence_signature(self, content: str) -> bool:
        """Check if file contains required imports/presence signatures.

        Args:
            content: File content

        Returns:
            True if presence signature found
        """
        signatures = self.get_presence_signatures()
        for signature in signatures:
            if re.search(signature, content, re.MULTILINE):
                return True
        return False

    def check_construction_signature(self, content: str) -> Optional[re.Match]:
        """Check if file contains agent construction pattern.

        Args:
            content: File content

        Returns:
            Match object if construction found, None otherwise
        """
        signatures = self.get_construction_signatures()
        for signature in signatures:
            match = re.search(signature, content, re.MULTILINE | re.DOTALL)
            if match:
                return match
        return None

    @staticmethod
    def extract_string_value(node: ast.AST) -> Optional[str]:
        """Extract string value from AST node."""
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        elif isinstance(node, ast.Str):  # Python < 3.8
            return node.s
        return None

    @staticmethod
    def extract_list_items(node: ast.AST) -> List[str]:
        """Extract item names from a list/tuple AST node."""
        items = []
        if isinstance(node, (ast.List, ast.Tuple)):
            for item in node.elts:
                if isinstance(item, ast.Name):
                    items.append(item.id)
                elif isinstance(item, ast.Call) and isinstance(item.func, ast.Name):
                    items.append(item.func.id)
        return items

    @staticmethod
    def extract_function_signature(func_node: ast.FunctionDef) -> Dict[str, Any]:
        """Extract parameter and return information from a function definition.

        Args:
            func_node: AST FunctionDef node

        Returns:
            Dict containing parameters and returns information
        """
        params = {}

        # Extract parameters
        args = func_node.args

        # Get positional arguments
        defaults_offset = len(args.args) - len(args.defaults)

        for i, arg in enumerate(args.args):
            param_info = {
                "type": "Any",
                "required": i < defaults_offset,
                "description": None,
            }

            # Extract type annotation if present
            if arg.annotation:
                param_info["type"] = BaseDetector._ast_to_type_string(arg.annotation)

            # Extract default value if present
            if i >= defaults_offset:
                default_idx = i - defaults_offset
                if default_idx < len(args.defaults):
                    param_info["default"] = BaseDetector._ast_to_value_string(
                        args.defaults[default_idx]
                    )
                    param_info["required"] = False

            params[arg.arg] = param_info

        # Handle *args
        if args.vararg:
            params[f"*{args.vararg.arg}"] = {
                "type": BaseDetector._ast_to_type_string(args.vararg.annotation)
                if args.vararg.annotation
                else "Any",
                "required": False,
                "description": "Variable positional arguments",
            }

        # Handle keyword-only arguments
        kwonly_defaults_offset = len(args.kwonlyargs) - len(args.kw_defaults)
        for i, arg in enumerate(args.kwonlyargs):
            param_info = {"type": "Any", "required": True, "description": None}

            # Check if has default
            if i >= kwonly_defaults_offset:
                default_idx = i - kwonly_defaults_offset
                if (
                    default_idx < len(args.kw_defaults)
                    and args.kw_defaults[default_idx] is not None
                ):
                    param_info["default"] = BaseDetector._ast_to_value_string(
                        args.kw_defaults[default_idx]
                    )
                    param_info["required"] = False

            # Extract type annotation
            if arg.annotation:
                param_info["type"] = BaseDetector._ast_to_type_string(arg.annotation)

            params[arg.arg] = param_info

        # Handle **kwargs
        if args.kwarg:
            params[f"**{args.kwarg.arg}"] = {
                "type": BaseDetector._ast_to_type_string(args.kwarg.annotation)
                if args.kwarg.annotation
                else "Any",
                "required": False,
                "description": "Variable keyword arguments",
            }

        # Extract return type
        return_type = None
        if func_node.returns:
            return_type = BaseDetector._ast_to_type_string(func_node.returns)

        return {
            "parameters": params,
            "returns": {"type": return_type or "Any", "description": None},
        }

    @staticmethod
    def _ast_to_type_string(node: ast.AST) -> str:
        """Convert an AST type annotation to a string representation.

        Args:
            node: AST node representing a type annotation

        Returns:
            String representation of the type
        """
        if node is None:
            return "Any"

        # Handle Name nodes (simple types like str, int, bool)
        if isinstance(node, ast.Name):
            return node.id

        # Handle Constant nodes (literal types)
        elif isinstance(node, ast.Constant):
            return repr(node.value)

        # Handle Subscript nodes (Generic types like List[str], Dict[str, int])
        elif isinstance(node, ast.Subscript):
            base_type = BaseDetector._ast_to_type_string(node.value)

            # Handle single subscript (e.g., List[str], Optional[int])
            if hasattr(node.slice, "value"):  # Python 3.8
                slice_type = BaseDetector._ast_to_type_string(node.slice.value)
                return f"{base_type}[{slice_type}]"
            elif isinstance(node.slice, ast.Index):  # Python 3.8 compatibility
                slice_type = BaseDetector._ast_to_type_string(node.slice.value)
                return f"{base_type}[{slice_type}]"
            elif isinstance(node.slice, ast.Tuple):
                # Handle multiple subscripts (e.g., Dict[str, int])
                slice_types = [
                    BaseDetector._ast_to_type_string(elt) for elt in node.slice.elts
                ]
                return f"{base_type}[{', '.join(slice_types)}]"
            else:
                # Direct slice node (Python 3.9+)
                slice_type = BaseDetector._ast_to_type_string(node.slice)
                return f"{base_type}[{slice_type}]"

        # Handle Union types (Python 3.10+ with |)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            left_type = BaseDetector._ast_to_type_string(node.left)
            right_type = BaseDetector._ast_to_type_string(node.right)
            return f"{left_type} | {right_type}"

        # Handle Tuple types
        elif isinstance(node, ast.Tuple):
            types = [BaseDetector._ast_to_type_string(elt) for elt in node.elts]
            return f"Tuple[{', '.join(types)}]"

        # Handle Attribute (e.g., typing.Optional, pd.DataFrame)
        elif isinstance(node, ast.Attribute):
            base = BaseDetector._ast_to_type_string(node.value)
            return f"{base}.{node.attr}"

        # Handle string annotations (forward references)
        elif isinstance(node, ast.Str):  # Python < 3.8
            return node.s

        # Default fallback
        else:
            return "Any"

    @staticmethod
    def _ast_to_value_string(node: ast.AST) -> str:
        """Convert an AST node to its value representation.

        Args:
            node: AST node representing a value

        Returns:
            String representation of the value
        """
        if node is None:
            return "None"

        # Handle constants
        if isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.Str):  # Python < 3.8
            return repr(node.s)
        elif isinstance(node, ast.Num):  # Python < 3.8
            return str(node.n)
        elif isinstance(node, ast.NameConstant):  # Python < 3.8
            return str(node.value)

        # Handle Name nodes (variable references)
        elif isinstance(node, ast.Name):
            return node.id

        # Handle negative numbers
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return f"-{BaseDetector._ast_to_value_string(node.operand)}"

        # Handle lists/tuples
        elif isinstance(node, (ast.List, ast.Tuple)):
            values = [BaseDetector._ast_to_value_string(elt) for elt in node.elts]
            if isinstance(node, ast.List):
                return f"[{', '.join(values)}]"
            else:
                return f"({', '.join(values)})"

        # Handle dicts
        elif isinstance(node, ast.Dict):
            items = []
            for k, v in zip(node.keys, node.values):
                key = BaseDetector._ast_to_value_string(k)
                value = BaseDetector._ast_to_value_string(v)
                items.append(f"{key}: {value}")
            return f"{{{', '.join(items)}}}"

        # Default
        else:
            return "..."

    @staticmethod
    def merge_docstring_info(
        signature: Dict[str, Any], docstring: Optional[str]
    ) -> Dict[str, Any]:
        """Merge function signature with docstring information.

        Args:
            signature: Function signature extracted from AST
            docstring: Function docstring

        Returns:
            Merged parameter and return information
        """
        if not docstring:
            return signature

        # Parse docstring
        doc_info = DocstringParser.parse(docstring)

        # Merge parameter descriptions
        for param_doc in doc_info.parameters:
            if param_doc.name in signature["parameters"]:
                # Update with docstring info
                param_info = signature["parameters"][param_doc.name]

                if param_doc.description:
                    param_info["description"] = param_doc.description

                # If docstring has type info and signature doesn't, use docstring type
                if param_doc.type and param_info["type"] == "Any":
                    param_info["type"] = param_doc.type

                # Update default and required from docstring if available
                if param_doc.default is not None:
                    param_info["default"] = param_doc.default
                    param_info["required"] = False

        # Merge return information
        if doc_info.returns:
            if doc_info.returns.get("description"):
                signature["returns"]["description"] = doc_info.returns["description"]

            # Use docstring return type if signature doesn't have one
            if doc_info.returns.get("type") and signature["returns"]["type"] == "Any":
                signature["returns"]["type"] = doc_info.returns["type"]

        # Add overall description if available
        if doc_info.description:
            signature["description"] = doc_info.description

        return signature
