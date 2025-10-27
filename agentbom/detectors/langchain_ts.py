"""LangChain TypeScript agent detector."""

import re
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging

from .base import BaseDetector, DetectorResult, ToolInfo
from .schema_extractors import SchemaExtractorFactory

logger = logging.getLogger(__name__)


class LangChainTypeScriptDetector(BaseDetector):
    """Detector for LangChain TypeScript agents (supports both AgentExecutor and LangGraph)."""
    
    def __init__(self, strict_mode: bool = True):
        """Initialize detector with schema extractor factory.
        
        Args:
            strict_mode: Whether to use strict detection mode
        """
        super().__init__(strict_mode=strict_mode)
        self.schema_factory = SchemaExtractorFactory()

    def get_presence_signatures(self) -> List[str]:
        """Get LangChain TypeScript import signatures."""
        return [
            # Old pattern: AgentExecutor
            r'import\s*\{[^}]*AgentExecutor[^}]*\}\s*from\s*["\']langchain/agents["\']',
            r'import\s*\{[^}]*AgentExecutor[^}]*\}\s*from\s*["\']@langchain/[^"\']+["\']',
            # New pattern: LangGraph createReactAgent
            r'import\s*\{[^}]*createReactAgent[^}]*\}\s*from\s*["\']@langchain/langgraph/prebuilt["\']',
            r'from\s+["\']@langchain/langgraph/prebuilt["\']',
        ]

    def get_construction_signatures(self) -> List[str]:
        """Get LangChain TypeScript construction patterns."""
        return [
            # Old pattern: AgentExecutor
            r'new\s+AgentExecutor\s*\(\s*\{[^}]*tools\s*:\s*\[',
            r'new\s+AgentExecutor\s*\(\s*\{[^}]*tools\s*:\s*\w+',
            r'AgentExecutor\.fromAgentAndTools\s*\(',
            # New pattern: createReactAgent from LangGraph
            r'createReactAgent\s*\(\s*\{[^}]*tools\s*:\s*\[',
            r'createReactAgent\s*\(\s*\{[^}]*tools\s*:\s*\w+',
            # Factory pattern for agents
            r'(?:export\s+)?(?:async\s+)?function\s+create\w*Agent\s*\(',
        ]

    def detect(self, file_path: Path, content: str) -> Optional[DetectorResult]:
        """Detect LangChain TypeScript agent in file."""
        # Check presence signature
        if not self.check_presence_signature(content):
            return None

        # Also check for tool imports
        if not self._has_tool_imports(content):
            return None

        # Check construction signature
        construction_match = self.check_construction_signature(content)
        if not construction_match:
            return None

        result = DetectorResult(
            found=True,
            constructor_file=str(file_path),
            language="TypeScript",
            frameworks=["LangChain"],
        )

        # Extract agent details with file path context for import resolution
        agent_info = self._extract_agent_info(content, file_path)
        if agent_info:
            result.agent_name = agent_info.get('name', file_path.stem)
            result.tools = agent_info.get('tools', [])
            result.metadata.update(agent_info.get('metadata', {}))

            # Check for SQL or Retrieval agent types
            if self._has_sql_tools(result.tools, content):
                result.agent_type = "SQL Agent"
            elif self._has_retrieval_tools(result.tools, content):
                result.agent_type = "Retrieval Agent"

            # Add provider frameworks
            result.frameworks.extend(self._detect_provider_frameworks(content))

        return result if result.found else None

    def _has_tool_imports(self, content: str) -> bool:
        """Check for tool-related imports."""
        tool_patterns = [
            r'import\s*\{[^}]*tool[^}]*\}\s*from\s*["\']@langchain/core/tools["\']',
            r'import\s*\{[^}]*DynamicStructuredTool[^}]*\}\s*from',
            r'import\s*\{[^}]*Tool[^}]*\}\s*from\s*["\']langchain/tools["\']',
            r'import\s*\{[^}]*StructuredToolInterface[^}]*\}\s*from\s*["\']@langchain/core/tools["\']',
            # Factory pattern imports
            r'import\s*\{[^}]*create\w+Tool[^}]*\}\s*from',
            # Check for tool usage even without explicit imports
            r'tools\s*:\s*\[',
        ]

        for pattern in tool_patterns:
            if re.search(pattern, content):
                return True
        return False

    def _extract_agent_info(self, content: str, file_path: Path) -> Optional[dict]:
        """Extract agent information from TypeScript code."""
        info = {
            'name': None,
            'tools': [],
            'metadata': {}
        }

        # Try both old and new patterns
        agent_found = False
        
        # Pattern 1: Old AgentExecutor pattern
        executor_pattern = r'(?:const|let|var)\s+(\w+)\s*=\s*new\s+AgentExecutor\s*\(\s*\{([^}]+)\}'
        match = re.search(executor_pattern, content, re.DOTALL)
        
        if match:
            agent_found = True
            info['name'] = match.group(1)
            constructor_body = match.group(2)
            info['tools'] = self._extract_tools_from_constructor(constructor_body, content, file_path)
        
        # Pattern 2: New createReactAgent pattern
        if not agent_found:
            react_agent_pattern = r'(?:const|let|var)\s+(\w+)\s*=\s*createReactAgent\s*\(\s*\{([^}]+)\}'
            match = re.search(react_agent_pattern, content, re.DOTALL)
            
            if match:
                agent_found = True
                info['name'] = match.group(1)
                constructor_body = match.group(2)
                info['tools'] = self._extract_tools_from_constructor(constructor_body, content, file_path)
        
        # Pattern 3: Factory function pattern (createXxxAgent)
        if not agent_found:
            factory_pattern = r'(?:export\s+)?(?:async\s+)?function\s+(create\w*Agent)\s*\('
            match = re.search(factory_pattern, content)
            
            if match:
                agent_found = True
                info['name'] = match.group(1)
                # Extract tools from factory function body
                info['tools'] = self._extract_tools_from_factory(content, file_path)

        return info if (agent_found and info['tools']) else None
    
    def _extract_tools_from_constructor(self, constructor_body: str, content: str, file_path: Path) -> List[ToolInfo]:
        """Extract tools from constructor body."""
        # Pattern 1: tools: [tool1, tool2, ...]
        tools_inline_pattern = r'tools\s*:\s*\[([^\]]*)\]'
        tools_match = re.search(tools_inline_pattern, constructor_body, re.DOTALL)
        
        if tools_match:
            tools_content = tools_match.group(1)
            return self._extract_tools(tools_content, content, file_path)
        
        # Pattern 2: tools: toolsVariable
        tools_ref_pattern = r'tools\s*:\s*(\w+)'
        tools_ref_match = re.search(tools_ref_pattern, constructor_body)
        
        if tools_ref_match:
            tools_var_name = tools_ref_match.group(1)
            # Find the variable definition
            var_pattern = rf'(?:const|let|var)\s+{re.escape(tools_var_name)}\s*=\s*\[([^\]]*)\]'
            var_match = re.search(var_pattern, content, re.DOTALL)
            
            if var_match:
                tools_content = var_match.group(1)
                return self._extract_tools(tools_content, content, file_path)
        
        return []
    
    def _extract_tools_from_factory(self, content: str, file_path: Path) -> List[ToolInfo]:
        """Extract tools from factory function pattern."""
        tools = []
        
        # Look for createReactAgent calls within the factory
        react_pattern = r'createReactAgent\s*\(\s*\{[^}]*tools\s*:\s*\[([^\]]+)\]'
        match = re.search(react_pattern, content, re.DOTALL)
        
        if match:
            tools_content = match.group(1)
            tools = self._extract_tools(tools_content, content, file_path)
        
        # Also look for tool factory calls (createXxxTool)
        tool_factory_pattern = r'(?:const|let|var)\s+(\w+)\s*=\s*(create\w+Tool)\s*\('
        for match in re.finditer(tool_factory_pattern, content):
            tool_var_name = match.group(1)
            factory_name = match.group(2)
            
            # Try to find the tool definition
            tool_info = self._find_tool_factory_definition(factory_name, content, file_path)
            if tool_info:
                tool_info.name = tool_var_name if tool_var_name else factory_name
                tools.append(tool_info)
            else:
                # At least record the tool name
                tools.append(ToolInfo(name=tool_var_name or factory_name, file_path=""))
        
        return tools

    def _extract_tools(self, tools_array: str, content: str, file_path: Path) -> List[ToolInfo]:
        """Extract tool information from tools array."""
        tools = []

        # Split by commas (simple approach - might need refinement for complex cases)
        tool_names = [t.strip() for t in tools_array.split(',') if t.strip()]

        for tool_name in tool_names:
            # Clean up the name
            tool_name = tool_name.strip()

            # First try to find tool definition in the same file
            tool_info = self._find_tool_definition(tool_name, content)
            if tool_info:
                tools.append(tool_info)
            else:
                # Try to find and follow import to get tool details from external file
                tool_info = self._find_tool_from_import(tool_name, content, file_path)
                if tool_info:
                    tools.append(tool_info)
                else:
                    # At least record the tool name
                    tools.append(ToolInfo(name=tool_name, file_path=""))

        return tools

    def _find_tool_factory_definition(self, factory_name: str, content: str, file_path: Path) -> Optional[ToolInfo]:
        """Find tool factory definition by looking for imports or definitions."""
        # Look for the factory function import
        import_pattern = rf'import\s*\{{[^}}]*{re.escape(factory_name)}[^}}]*\}}\s*from\s*["\']([^"\']+)["\']'
        import_match = re.search(import_pattern, content)
        
        if import_match:
            import_path = import_match.group(1)
            # Try to resolve and read the tool file
            tool_info = self._load_tool_from_import(factory_name, import_path, file_path)
            if tool_info:
                return tool_info
        
        # Try to extract more details if the factory is defined in the same file
        factory_def_pattern = rf'export\s+function\s+{re.escape(factory_name)}\s*\([^)]*\)\s*:\s*\w+\s*\{{'
        if re.search(factory_def_pattern, content):
            # Extract details from the factory definition
            return self._extract_tool_from_factory_impl(factory_name, content)
        
        return ToolInfo(name=factory_name, file_path="")
    
    def _extract_tool_from_factory_impl(self, factory_name: str, content: str) -> Optional[ToolInfo]:
        """Extract tool info from factory implementation."""
        tool_info = ToolInfo(name=factory_name, file_path="")
        
        # Find the factory function body
        factory_pattern = rf'export\s+function\s+{re.escape(factory_name)}\s*\([^)]*\)[^{{]*\{{(.{{0,5000}})\}}'
        match = re.search(factory_pattern, content, re.DOTALL)
        
        if not match:
            return tool_info
        
        factory_body = match.group(1)
        
        # Look for tool() or DynamicStructuredTool construction
        if 'tool(' in factory_body:
            # Extract name from the tool config
            name_pattern = r'name\s*:\s*["\']([^"\']+)["\']'
            name_match = re.search(name_pattern, factory_body)
            if name_match:
                tool_info.name = name_match.group(1)
            
            # Extract description
            desc_pattern = r'description\s*:\s*["\']([^"\']+)["\']'
            desc_match = re.search(desc_pattern, factory_body)
            if desc_match:
                tool_info.description = desc_match.group(1)
            
            # Extract schema parameters
            schema_pattern = r'schema\s*:\s*z\.object\s*\(\s*\{([^}]+)\}'
            schema_match = re.search(schema_pattern, factory_body, re.DOTALL)
            if schema_match:
                schema_body = schema_match.group(1)
                tool_info.parameters = self._extract_zod_schema_params(schema_body)
        
        elif 'DynamicStructuredTool' in factory_body:
            # Extract from DynamicStructuredTool
            name_pattern = r'name\s*:\s*["\']([^"\']+)["\']'
            name_match = re.search(name_pattern, factory_body)
            if name_match:
                tool_info.name = name_match.group(1)
            
            desc_pattern = r'description\s*:\s*["\']([^"\']+)["\']'
            desc_match = re.search(desc_pattern, factory_body)
            if desc_match:
                tool_info.description = desc_match.group(1)
        
        return tool_info
    
    def _find_tool_definition(self, name: str, content: str) -> Optional[ToolInfo]:
        """Find tool definition by variable name."""
        # Look for tool() function call - find the whole definition
        tool_pattern = rf'(?:const|let|var)\s+{re.escape(name)}\s*=\s*tool\s*\('
        match = re.search(tool_pattern, content)

        if match:
            # Find the matching closing brace/paren
            start_pos = match.end()
            # Extract a reasonably large chunk that should contain the whole tool definition
            chunk = content[match.start():min(match.start() + 2000, len(content))]

            tool_info = ToolInfo(name=name, file_path="")

            # Extract name
            name_pattern = r'name\s*:\s*["\']([^"\']+)["\']'
            name_match = re.search(name_pattern, chunk)
            if name_match:
                tool_info.name = name_match.group(1)

            # Extract description
            desc_pattern = r'description\s*:\s*["\']([^"\']+)["\']'
            desc_match = re.search(desc_pattern, chunk)
            if desc_match:
                tool_info.description = desc_match.group(1)

            # Extract schema parameters - look for the complete schema definition
            schema_pattern = r'schema\s*:\s*z\.object\s*\(\s*\{([^}]+)\}\s*\)'
            schema_match = re.search(schema_pattern, chunk, re.DOTALL)
            if schema_match:
                schema_body = schema_match.group(1)
                tool_info.parameters = self._extract_schema_params(content, schema_body)

            return tool_info

        # Look for DynamicStructuredTool
        dyn_tool_pattern = rf'(?:const|let|var)\s+{re.escape(name)}\s*=\s*new\s+DynamicStructuredTool\s*\(\s*\{{([^}}]+)\}}'
        match = re.search(dyn_tool_pattern, content, re.DOTALL)

        if match:
            tool_body = match.group(1)
            tool_info = ToolInfo(name=name, file_path="")

            # Extract name
            name_pattern = r'name\s*:\s*["\']([^"\']+)["\']'
            name_match = re.search(name_pattern, tool_body)
            if name_match:
                tool_info.name = name_match.group(1)

            # Extract description
            desc_pattern = r'description\s*:\s*["\']([^"\']+)["\']'
            desc_match = re.search(desc_pattern, tool_body)
            if desc_match:
                tool_info.description = desc_match.group(1)

            # Extract schema parameters
            schema_pattern = r'schema\s*:\s*z\.object\s*\(\s*\{([^}]+)\}'
            schema_match = re.search(schema_pattern, tool_body, re.DOTALL)
            if schema_match:
                schema_body = schema_match.group(1)
                tool_info.parameters = self._extract_schema_params(content, schema_body)

            return tool_info

        return None

    def _extract_schema_params(self, content: str, schema_body: str) -> Dict[str, Any]:
        """Extract schema parameters using the appropriate extractor.
        
        Args:
            content: Full file content for context
            schema_body: The schema body to parse
            
        Returns:
            Dictionary of parameter information
        """
        extractor = self.schema_factory.get_extractor(content)
        
        if extractor:
            try:
                return extractor.extract_params(content, schema_body)
            except Exception as e:
                logger.debug(f"Error extracting schema with {extractor.get_library_name()}: {e}")
                return {}
        
        # Fallback: return empty if no extractor found
        logger.debug("No schema extractor available, returning empty parameters")
        return {}
    
    def _extract_zod_schema_params(self, schema_body: str) -> Dict[str, Any]:
        """Extract parameters from Zod schema definition.
        
        DEPRECATED: This method is maintained for backward compatibility.
        Use _extract_schema_params() instead for extensible schema extraction.
        
        Args:
            schema_body: The schema body to parse
            
        Returns:
            Dictionary of parameter information
        """
        # Create a minimal Zod content for detection
        zod_content = f"import {{ z }} from 'zod'\nz.object({{{schema_body}}})"
        return self._extract_schema_params(zod_content, schema_body)

    def _has_sql_tools(self, tools: List[ToolInfo], content: str) -> bool:
        """Check if agent has SQL tools."""
        sql_indicators = [
            'SqlToolkit',
            'SqlDatabase',
            'QuerySqlTool',
            'InfoSqlDatabaseTool',
            'ListSqlDatabaseTool',
            'sql-toolkit',
        ]

        for indicator in sql_indicators:
            if indicator in content or indicator.lower() in content.lower():
                return True

        for tool in tools:
            if 'sql' in tool.name.lower() or (tool.description and 'sql' in tool.description.lower()):
                return True

        return False

    def _has_retrieval_tools(self, tools: List[ToolInfo], content: str) -> bool:
        """Check if agent has retrieval/vectorstore tools."""
        retrieval_indicators = [
            'VectorStoreRetriever',
            'vectorStore',
            'retriever',
            'RetrievalQA',
            'ConversationalRetrievalChain',
            'FAISS',
            'Chroma',
            'Pinecone',
            'Weaviate',
            'MemoryVectorStore',
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

    def _find_tool_from_import(self, tool_var_name: str, content: str, file_path: Path) -> Optional[ToolInfo]:
        """Find tool details by following its factory import."""
        # Look for the factory function that creates this tool
        # Pattern: const toolVar = createToolFactory(...)
        tool_creation_pattern = rf'(?:const|let|var)\s+{re.escape(tool_var_name)}\s*=\s*(create\w+Tool)\s*\('
        match = re.search(tool_creation_pattern, content)
        
        if not match:
            return None
        
        factory_name = match.group(1)
        
        # Find the import for this factory
        import_pattern = rf'import\s*\{{[^}}]*{re.escape(factory_name)}[^}}]*\}}\s*from\s*["\']([^"\']+)["\']'
        import_match = re.search(import_pattern, content)
        
        if not import_match:
            return None
        
        import_path = import_match.group(1)
        return self._load_tool_from_import(factory_name, import_path, file_path)
    
    def _load_tool_from_import(self, factory_name: str, import_path: str, current_file: Path) -> Optional[ToolInfo]:
        """Load and parse a tool definition from an import path."""
        try:
            # Resolve the relative import path
            resolved_path = self._resolve_import_path(import_path, current_file)
            
            if not resolved_path or not resolved_path.exists():
                logger.debug(f"Could not resolve import path: {import_path} from {current_file}")
                return None
            
            # Read the tool file
            try:
                with open(resolved_path, 'r', encoding='utf-8') as f:
                    tool_content = f.read()
            except Exception as e:
                logger.debug(f"Error reading tool file {resolved_path}: {e}")
                return None
            
            # Parse the tool from the file content
            return self._parse_tool_from_file(factory_name, tool_content, resolved_path)
            
        except Exception as e:
            logger.debug(f"Error loading tool from import {import_path}: {e}")
            return None
    
    def _resolve_import_path(self, import_path: str, current_file: Path) -> Optional[Path]:
        """Resolve a TypeScript import path to an actual file path."""
        # Get the directory of the current file
        current_dir = current_file.parent
        
        # Handle relative imports
        if import_path.startswith('.'):
            # Resolve the path (handles both ./ and ../)
            # Join the paths and resolve any parent references
            resolved = (current_dir / import_path).resolve()
            
            # Try common TypeScript file extensions
            for ext in ['.ts', '.tsx', '.js', '.jsx', '']:
                if ext == '':
                    # Check if it's already a file with extension
                    if resolved.exists() and resolved.is_file():
                        return resolved
                    # Also check for index files
                    index_file = resolved / 'index.ts'
                    if index_file.exists():
                        return index_file
                else:
                    file_with_ext = Path(str(resolved) + ext)
                    if file_with_ext.exists():
                        return file_with_ext
        
        return None
    
    def _parse_tool_from_file(self, factory_name: str, content: str, file_path: Path) -> Optional[ToolInfo]:
        """Parse tool metadata from a tool definition file."""
        tool_info = ToolInfo(name="", file_path=str(file_path))
        
        # Extract name directly from the tool config (works for both patterns)
        name_pattern = r'name\s*:\s*["\']([^"\']+)["\']'
        name_match = re.search(name_pattern, content)
        if name_match:
            tool_info.name = name_match.group(1)
        
        # Extract description - handle multi-line template strings
        desc_pattern = r'description\s*:\s*`([^`]+)`'
        desc_match = re.search(desc_pattern, content, re.DOTALL)
        if desc_match:
            tool_info.description = desc_match.group(1).strip()
        else:
            # Try single/double quotes for single-line descriptions
            desc_pattern = r'description\s*:\s*["\']([^"\']+)["\']'
            desc_match = re.search(desc_pattern, content)
            if desc_match:
                tool_info.description = desc_match.group(1).strip()
        
        # Extract schema parameters - try two patterns:
        # Pattern 1: Inline schema - schema: z.object({...})
        schema_pattern = r'schema\s*:\s*z\.object\s*\(\s*\{([^}]+)\}\s*\)'
        schema_match = re.search(schema_pattern, content, re.DOTALL)
        if schema_match:
            schema_body = schema_match.group(1)
            tool_info.parameters = self._extract_schema_params(content, schema_body)
        else:
            # Pattern 2: Schema variable reference - schema: schemaVariableName
            schema_ref_pattern = r'schema\s*:\s*(\w+)'
            schema_ref_match = re.search(schema_ref_pattern, content)
            if schema_ref_match:
                schema_var_name = schema_ref_match.group(1)
                # Find the variable definition
                var_def_pattern = rf'(?:const|let|var)\s+{re.escape(schema_var_name)}\s*=\s*z\.object\s*\(\s*\{{([^}}]+)\}}\s*\)'
                var_def_match = re.search(var_def_pattern, content, re.DOTALL)
                if var_def_match:
                    schema_body = var_def_match.group(1)
                    tool_info.parameters = self._extract_schema_params(content, schema_body)
                else:
                    logger.debug(f"Could not find schema variable {schema_var_name} in {file_path}")
        
        if not tool_info.name:
            logger.debug(f"Could not extract tool name from {file_path}")
            return None
        
        return tool_info

    def _detect_provider_frameworks(self, content: str) -> List[str]:
        """Detect additional provider frameworks."""
        providers = []

        provider_patterns = {
            '@langchain/openai': r'from\s*["\']@langchain/openai["\']',
            '@langchain/anthropic': r'from\s*["\']@langchain/anthropic["\']',
            '@langchain/google-genai': r'from\s*["\']@langchain/google-genai["\']',
            '@langchain/community': r'from\s*["\']@langchain/community["\']',
            '@langchain/experimental': r'from\s*["\']@langchain/experimental["\']',
            '@langchain/langgraph': r'from\s*["\']@langchain/langgraph[^"\']*["\']',
            '@langchain/core': r'from\s*["\']@langchain/core[^"\']*["\']',
        }

        for provider, pattern in provider_patterns.items():
            if re.search(pattern, content):
                providers.append(provider)

        return providers