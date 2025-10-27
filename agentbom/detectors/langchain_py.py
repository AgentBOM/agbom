"""LangChain Python agent detector."""

import ast
import re
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging

from .base import BaseDetector, DetectorResult, ToolInfo

logger = logging.getLogger(__name__)


class LangChainPythonDetector(BaseDetector):
    """Detector for LangChain Python agents."""

    def get_presence_signatures(self) -> List[str]:
        """Get LangChain Python import signatures."""
        return [
            r"from\s+langchain\.agents\s+import\s+.*initialize_agent",
            r"from\s+langchain\.agents\s+import\s+.*AgentExecutor",
            r"from\s+langchain\.agents\s+import\s+[^#\n]*\bAgentType\b",
        ]

    def get_construction_signatures(self) -> List[str]:
        """Get LangChain Python construction patterns."""
        return [
            r"initialize_agent\s*\([^)]*tools\s*=",
            r"AgentExecutor\s*\([^)]*tools\s*=",
            r"AgentExecutor\.from_agent_and_tools\s*\(",
        ]

    def detect(self, file_path: Path, content: str) -> Optional[DetectorResult]:
        """Detect LangChain Python agent in file."""
        # Check presence signature
        if not self.check_presence_signature(content):
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
            frameworks=["LangChain"],
        )

        # Find agent construction
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                agent_info = self._extract_agent_info(node, content, file_path)
                if agent_info:
                    result.agent_name = agent_info.get('name', file_path.stem)
                    result.tools = agent_info.get('tools', [])
                    result.architecture = agent_info.get('architecture', 'Other')
                    result.metadata.update(agent_info.get('metadata', {}))

                    # Check for SQL or Retrieval agent types
                    if self._has_sql_tools(result.tools, content):
                        result.agent_type = "SQL Agent"
                    elif self._has_retrieval_tools(result.tools, content):
                        result.agent_type = "Retrieval Agent"

                    # Add provider frameworks
                    result.frameworks.extend(self._detect_provider_frameworks(content))

                    break

        return result if result.found else None

    def _extract_agent_info(self, node: ast.Call, content: str, file_path: Path) -> Optional[Dict[str, Any]]:
        """Extract agent information from AST Call node."""
        func_name = None

        # Get function name
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        # Check if this is an agent constructor
        if func_name not in ['initialize_agent', 'AgentExecutor', 'from_agent_and_tools']:
            return None

        info = {
            'name': None,
            'tools': [],
            'architecture': 'Other',
            'metadata': {}
        }

        # Extract arguments
        for keyword in node.keywords:
            if keyword.arg == 'tools':
                # Extract tool list
                tools = self._extract_tools_from_node(keyword.value, content, file_path)
                info['tools'] = tools
            elif keyword.arg == 'agent' and func_name == 'initialize_agent':
                # Check for ReAct architecture
                if isinstance(keyword.value, ast.Attribute):
                    if keyword.value.attr == 'ZERO_SHOT_REACT_DESCRIPTION':
                        info['architecture'] = 'ReAct'
            elif keyword.arg == 'agent_name':
                # Extract agent name if provided
                name = self.extract_string_value(keyword.value)
                if name:
                    info['name'] = name

        # If assigned to a variable, use that as the name
        # Parse to find assignment
        try:
            tree = ast.parse(content)
            for n in ast.walk(tree):
                if isinstance(n, ast.Assign):
                    if n.value == node or (isinstance(n.value, ast.Call) and
                                           isinstance(n.value.func, ast.Name) and
                                           n.value.func.id == func_name):
                        # Check if this assignment has the same line number as our call
                        for target in n.targets:
                            if isinstance(target, ast.Name):
                                info['name'] = target.id
                                break
                        break
        except:
            pass

        return info if info['tools'] else None

    def _extract_tools_from_node(self, node: ast.AST, content: str, file_path: Path) -> List[ToolInfo]:
        """Extract tool information from AST node."""
        tools = []

        # Handle variable reference (e.g., tools=my_tools)
        if isinstance(node, ast.Name):
            # Find the variable definition
            tools_var_name = node.id

            # Parse the content to find the variable definition
            try:
                tree = ast.parse(content)
                for n in ast.walk(tree):
                    if isinstance(n, ast.Assign):
                        for target in n.targets:
                            if isinstance(target, ast.Name) and target.id == tools_var_name:
                                # Found the tools variable definition
                                if isinstance(n.value, (ast.List, ast.Tuple)):
                                    for item in n.value.elts:
                                        tool_info = None
                                        if isinstance(item, ast.Name):
                                            # Reference to a tool variable
                                            tool_info = self._find_tool_definition(item.id, content, file_path)
                                        elif isinstance(item, ast.Call):
                                            # Tool construction (could be Tool(), StructuredTool(), or custom class)
                                            tool_info = self._extract_tool_from_call(item, content, file_path)
                                        if tool_info:
                                            tools.append(tool_info)
            except:
                pass

        # Handle literal list/tuple
        elif isinstance(node, (ast.List, ast.Tuple)):
            for item in node.elts:
                tool_info = None

                if isinstance(item, ast.Name):
                    # Reference to a tool variable
                    tool_info = self._find_tool_definition(item.id, content, file_path)
                elif isinstance(item, ast.Call):
                    # Tool construction (could be Tool(), StructuredTool(), or custom class)
                    tool_info = self._extract_tool_from_call(item, content, file_path)

                if tool_info:
                    tools.append(tool_info)

        return tools

    def _find_tool_definition(self, name: str, content: str, file_path: Path) -> Optional[ToolInfo]:
        """Find tool definition by variable name."""
        # First check if it's a variable assignment to Tool/StructuredTool
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == name:
                            # Check if it's a Tool/StructuredTool construction
                            if isinstance(node.value, ast.Call):
                                tool_info = self._extract_tool_from_call(node.value, content, file_path)
                                if tool_info:
                                    return tool_info
        except:
            pass

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
                # Fallback to regex-based extraction
                doc_pattern = rf'def\s+{re.escape(name)}\s*\([^)]*\)\s*:\s*"""([^"]*?)"""'
                doc_match = re.search(doc_pattern, content, re.DOTALL)
                description = doc_match.group(1).strip() if doc_match else None

                return ToolInfo(
                    name=name,
                    file_path="",
                    description=description,
                )

        # Look for Tool() or StructuredTool() construction
        tool_construct_pattern = rf"{re.escape(name)}\s*=\s*(?:Tool|StructuredTool)\s*\("
        match = re.search(tool_construct_pattern, content)

        if match:
            # Try to extract name from constructor
            name_pattern = rf'{re.escape(name)}\s*=\s*(?:Tool|StructuredTool)\s*\([^)]*name\s*=\s*["\']([^"\']+)["\']'
            name_match = re.search(name_pattern, content)
            tool_name = name_match.group(1) if name_match else name

            # Try to extract description
            desc_pattern = rf'{re.escape(name)}\s*=\s*(?:Tool|StructuredTool)\s*\([^)]*description\s*=\s*["\']([^"\']+)["\']'
            desc_match = re.search(desc_pattern, content)
            description = desc_match.group(1) if desc_match else None

            return ToolInfo(
                name=tool_name,
                file_path="",
                description=description,
            )

        return None

    def _extract_tool_from_call(self, node: ast.Call, content: str, file_path: Path) -> Optional[ToolInfo]:
        """Extract tool info from Tool() or StructuredTool() call, or custom tool class instantiation."""
        if not isinstance(node.func, ast.Name):
            return None

        class_name = node.func.id
        
        # Case 1: Standard LangChain Tool or StructuredTool
        if class_name in ['Tool', 'StructuredTool']:
            tool_info = ToolInfo(name="unknown", file_path="")
            parameters = {}
            returns = None

            for keyword in node.keywords:
                if keyword.arg == 'name':
                    name = self.extract_string_value(keyword.value)
                    if name:
                        tool_info.name = name
                elif keyword.arg == 'description':
                    desc = self.extract_string_value(keyword.value)
                    if desc:
                        tool_info.description = desc
                elif keyword.arg == 'args_schema' and class_name == 'StructuredTool':
                    # Extract parameters from Pydantic model if possible
                    if isinstance(keyword.value, ast.Name):
                        # Try to find the Pydantic model definition
                        model_name = keyword.value.id
                        parameters = self._extract_pydantic_model_fields(model_name, content, file_path)
                elif keyword.arg == 'func':
                    # If func is a lambda or function reference, try to extract signature
                    if isinstance(keyword.value, ast.Lambda):
                        # Extract lambda parameters
                        lambda_args = keyword.value.args
                        for arg in lambda_args.args:
                            parameters[arg.arg] = {
                                'type': 'Any',
                                'required': True,
                                'description': None
                            }
                    elif isinstance(keyword.value, ast.Name):
                        # Reference to a function
                        func_name = keyword.value.id
                        # Try to find function definition
                        func_info = self._extract_function_info(func_name, content)
                        if func_info:
                            parameters = func_info.get('parameters', {})
                            returns = func_info.get('returns')

            tool_info.parameters = parameters
            tool_info.returns = returns
            return tool_info
        
        # Case 2: Custom tool class instantiation (e.g., FetchLDFTool())
        else:
            # Try to find the class definition in the current file first
            tool_info = self._extract_tool_from_class(class_name, content, file_path)
            if tool_info:
                return tool_info
            
            # If not found, follow imports
            tool_info = self._find_tool_class_from_import(class_name, content, file_path)
            if tool_info:
                return tool_info
            
            # Fallback: return basic info with class name
            logger.debug(f"Could not find tool class definition for {class_name}")
            return ToolInfo(name=class_name, file_path=str(file_path))

    def _extract_pydantic_model_fields(self, model_name: str, content: str, file_path: Path) -> Dict[str, Any]:
        """Extract fields from a Pydantic model definition."""
        parameters = {}
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == model_name:
                    # Check if inherits from BaseModel
                    is_pydantic = any(
                        (isinstance(base, ast.Name) and 'Model' in base.id) or
                        (isinstance(base, ast.Attribute) and 'Model' in base.attr)
                        for base in node.bases
                    )

                    if is_pydantic:
                        # Extract class fields
                        for item in node.body:
                            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                                field_name = item.target.id
                                field_type = self._ast_to_type_string(item.annotation) if item.annotation else 'Any'

                                # Check if has default value
                                required = True
                                default = None
                                if item.value:
                                    # Has default value
                                    if isinstance(item.value, ast.Call) and isinstance(item.value.func, ast.Name):
                                        if item.value.func.id == 'Field':
                                            # Pydantic Field() with potential default
                                            for kw in item.value.keywords:
                                                if kw.arg == 'default':
                                                    default = self._ast_to_value_string(kw.value)
                                                    required = False
                                                elif kw.arg == 'default_factory':
                                                    required = False
                                                    default = 'factory'
                                        else:
                                            default = self._ast_to_value_string(item.value)
                                            required = False
                                    else:
                                        default = self._ast_to_value_string(item.value)
                                        required = False

                                # Check if Optional type
                                if 'Optional' in field_type or '| None' in field_type:
                                    required = False

                                parameters[field_name] = {
                                    'type': field_type,
                                    'required': required,
                                    'description': None
                                }
                                if default is not None:
                                    parameters[field_name]['default'] = default
        except:
            pass

        return parameters

    def _extract_function_info(self, func_name: str, content: str) -> Optional[Dict[str, Any]]:
        """Extract function signature and docstring info."""
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == func_name:
                    # Extract function signature
                    signature = self.extract_function_signature(node)

                    # Get docstring
                    docstring = ast.get_docstring(node)

                    # Merge signature with docstring info
                    return self.merge_docstring_info(signature, docstring)
        except:
            pass
        return None

    def _find_parent_assign(self, node: ast.AST, content: str) -> Optional[ast.AST]:
        """Find parent assignment node."""
        # This is a simplified version - in production, we'd use a proper parent tracker
        try:
            tree = ast.parse(content)
            for parent in ast.walk(tree):
                if isinstance(parent, ast.Assign):
                    if any(child == node for child in ast.walk(parent.value)):
                        return parent
        except:
            pass
        return None

    def _has_sql_tools(self, tools: List[ToolInfo], content: str) -> bool:
        """Check if agent has SQL tools."""
        sql_indicators = [
            'SQLDatabaseToolkit',
            'sql_toolkit',
            'QuerySQLDataBaseTool',
            'InfoSQLDatabaseTool',
            'ListSQLDatabaseTool',
        ]

        for indicator in sql_indicators:
            if indicator in content:
                return True

        for tool in tools:
            if 'sql' in tool.name.lower() or (tool.description and 'sql' in tool.description.lower()):
                return True

        return False

    def _has_retrieval_tools(self, tools: List[ToolInfo], content: str) -> bool:
        """Check if agent has retrieval/vectorstore tools."""
        retrieval_indicators = [
            'VectorStoreRetriever',
            'vectorstore',
            'retriever',
            'RetrievalQA',
            'ConversationalRetrievalChain',
            'FAISS',
            'Chroma',
            'Pinecone',
            'Weaviate',
        ]

        for indicator in retrieval_indicators:
            if indicator in content:
                return True

        for tool in tools:
            name_lower = tool.name.lower()
            if any(term in name_lower for term in ['retriev', 'search', 'vector', 'embed']):
                return True
            if tool.description:
                desc_lower = tool.description.lower()
                if any(term in desc_lower for term in ['retriev', 'search', 'vector', 'embed']):
                    return True

        return False

    def _detect_provider_frameworks(self, content: str) -> List[str]:
        """Detect additional provider frameworks."""
        providers = []

        provider_patterns = {
            'langchain_openai': r'from\s+langchain_openai\s+import',
            'langchain_anthropic': r'from\s+langchain_anthropic\s+import',
            'langchain_google_genai': r'from\s+langchain_google_genai\s+import',
            'langchain_community': r'from\s+langchain_community\s+import',
            'langchain_experimental': r'from\s+langchain_experimental\s+import',
        }

        for provider, pattern in provider_patterns.items():
            if re.search(pattern, content):
                providers.append(provider)

        return providers
    
    def _extract_tool_from_class(self, class_name: str, content: str, file_path: Path) -> Optional[ToolInfo]:
        """Extract tool information from a class definition.
        
        Handles BaseTool subclasses with class attributes like:
            name = "tool_name"
            description = "Tool description"
            args_schema: Type[BaseModel] = SchemaClass
        """
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    # Check if inherits from BaseTool
                    is_tool = any(
                        (isinstance(base, ast.Name) and 'Tool' in base.id) or
                        (isinstance(base, ast.Attribute) and 'Tool' in base.attr)
                        for base in node.bases
                    )
                    
                    if is_tool:
                        tool_info = ToolInfo(name="", file_path=str(file_path))
                        args_schema_name = None
                        
                        # Extract class attributes
                        for item in node.body:
                            # Handle: name = "tool_name"
                            if isinstance(item, ast.Assign):
                                for target in item.targets:
                                    if isinstance(target, ast.Name):
                                        if target.id == 'name':
                                            name_val = self.extract_string_value(item.value)
                                            if name_val:
                                                tool_info.name = name_val
                                        elif target.id == 'description':
                                            desc_val = self.extract_string_value(item.value)
                                            if desc_val:
                                                tool_info.description = desc_val
                            
                            # Handle: args_schema: Type[BaseModel] = SchemaClass
                            elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                                if item.target.id == 'args_schema' and item.value:
                                    if isinstance(item.value, ast.Name):
                                        args_schema_name = item.value.id
                        
                        # Extract parameters from args_schema if found
                        if args_schema_name:
                            tool_info.parameters = self._extract_pydantic_model_fields(args_schema_name, content, file_path)
                        
                        if tool_info.name:
                            return tool_info
        except:
            pass
        
        return None
    
    def _find_tool_class_from_import(self, class_name: str, content: str, file_path: Path) -> Optional[ToolInfo]:
        """Follow imports to find tool class definition in external files.
        
        Handles patterns like:
            from orchestrator.api.tools import FetchLDFTool
            from .tools import FetchLDFTool
        """
        try:
            tree = ast.parse(content)
            
            # Find import statement for the class
            for node in ast.walk(tree):
                # Handle: from module import ClassName
                if isinstance(node, ast.ImportFrom):
                    if node.module:
                        for alias in node.names:
                            if alias.name == class_name:
                                # Found the import!
                                module_path = node.module
                                
                                # Resolve the module path to a file path
                                resolved_path = self._resolve_python_import(module_path, file_path)
                                if resolved_path and resolved_path.exists():
                                    try:
                                        tool_file_content = resolved_path.read_text(encoding='utf-8')
                                        # Extract tool info from the external file
                                        tool_info = self._extract_tool_from_class(class_name, tool_file_content, resolved_path)
                                        if tool_info:
                                            logger.debug(f"Found tool {class_name} in {resolved_path}")
                                            return tool_info
                                    except Exception as e:
                                        logger.debug(f"Error reading tool file {resolved_path}: {e}")
        except:
            pass
        
        return None
    
    def _resolve_python_import(self, module_path: str, current_file: Path) -> Optional[Path]:
        """Resolve a Python import path to an actual file path.
        
        Handles:
        - Relative imports: .tools, ..api.tools
        - Absolute imports: orchestrator.api.tools
        """
        current_dir = current_file.parent
        
        # Handle relative imports
        if module_path.startswith('.'):
            # Count leading dots
            level = 0
            for char in module_path:
                if char == '.':
                    level += 1
                else:
                    break
            
            # Remove leading dots
            module_path = module_path[level:]
            
            # Go up directories based on level
            target_dir = current_dir
            for _ in range(level - 1):
                target_dir = target_dir.parent
            
            # Convert module path to file path
            if module_path:
                parts = module_path.split('.')
                for part in parts:
                    target_dir = target_dir / part
            
            # Try .py file or __init__.py
            for candidate in [target_dir.with_suffix('.py'), target_dir / '__init__.py']:
                if candidate.exists():
                    return candidate
        
        # Handle absolute imports (try to find relative to current file's parent directories)
        else:
            parts = module_path.split('.')
            
            # Try to find the module starting from current directory and going up
            search_dir = current_dir
            for _ in range(5):  # Search up to 5 levels up
                candidate_path = search_dir
                for part in parts:
                    candidate_path = candidate_path / part
                
                # Try .py file or __init__.py
                for candidate in [candidate_path.with_suffix('.py'), candidate_path / '__init__.py']:
                    if candidate.exists():
                        return candidate
                
                search_dir = search_dir.parent
                if search_dir == search_dir.parent:  # Reached root
                    break
        
        return None