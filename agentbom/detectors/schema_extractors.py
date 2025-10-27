"""Schema extractors for different validation libraries."""

import re
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class SchemaExtractor(ABC):
    """Base class for schema parameter extraction."""
    
    @abstractmethod
    def can_extract(self, content: str) -> bool:
        """Check if this extractor can handle the given content.
        
        Args:
            content: File content to check
            
        Returns:
            True if this extractor can handle the content
        """
        pass
    
    @abstractmethod
    def extract_params(self, content: str, schema_body: str) -> Dict[str, Any]:
        """Extract parameters from schema definition.
        
        Args:
            content: Full file content (for context)
            schema_body: The schema body to parse
            
        Returns:
            Dictionary of parameter name -> parameter info
        """
        pass
    
    @abstractmethod
    def get_library_name(self) -> str:
        """Get the name of the schema library this extractor handles."""
        pass


class ZodSchemaExtractor(SchemaExtractor):
    """Extract parameters from Zod schemas (LangChain/LangGraph standard)."""
    
    def can_extract(self, content: str) -> bool:
        """Check if content uses Zod schemas."""
        zod_indicators = [
            r'import\s*\{[^}]*z[^}]*\}\s*from\s*["\']zod["\']',
            r'from\s+["\']zod["\']',
            r'z\.object\s*\(',
            r'z\.string\s*\(',
            r'z\.number\s*\(',
        ]
        
        return any(re.search(pattern, content) for pattern in zod_indicators)
    
    def get_library_name(self) -> str:
        return "Zod"
    
    def extract_params(self, content: str, schema_body: str) -> Dict[str, Any]:
        """Extract parameters from Zod schema definition."""
        parameters = {}

        # Pattern to match individual schema fields with various Zod types
        # Matches complex patterns like: fieldName: z.type(...).optional().describe("...")
        field_pattern = r'(\w+)\s*:\s*z\.(\w+)\s*\(([^)]*)\)([^,\n]*?)(?=,|\n|$|\})'

        for match in re.finditer(field_pattern, schema_body, re.DOTALL):
            field_name = match.group(1)
            field_type = match.group(2)
            field_args = match.group(3).strip()  # Arguments inside z.type(...)
            field_modifiers = match.group(4).strip()  # Everything after: .optional().describe(...)

            # Map Zod types to standard types
            type_map = {
                'string': 'str',
                'number': 'number',
                'boolean': 'bool',
                'object': 'object',
                'array': 'array',
                'date': 'date',
                'any': 'any',
                'literal': 'literal',
                'enum': 'enum',
            }

            param_type = type_map.get(field_type, field_type)
            
            # For literals and enums, add the value/options to the type
            if field_type == 'literal' and field_args:
                # Extract literal value: z.literal('value') -> literal<'value'>
                param_type = f"literal<{field_args}>"
            elif field_type == 'enum' and field_args:
                # Extract enum options: z.enum(['a', 'b']) -> enum<['a', 'b']>
                param_type = f"enum<{field_args}>"
            elif field_type == 'array' and field_args:
                # For arrays, show the element type if possible
                if 'z.object' in field_args:
                    param_type = 'array<object>'
                elif 'z.string' in field_args:
                    param_type = 'array<str>'
                else:
                    param_type = 'array'

            param_info = {
                'type': param_type,
                'required': True,
                'description': None
            }

            # Check if optional
            if '.optional()' in field_modifiers:
                param_info['required'] = False

            # Extract description - handle both single and double quotes
            desc_pattern = r'\.describe\s*\(\s*["\']([^"\']+)["\']'
            desc_match = re.search(desc_pattern, field_modifiers)
            if desc_match:
                param_info['description'] = desc_match.group(1)
            else:
                # Try template string
                desc_pattern = r'\.describe\s*\(\s*`([^`]+)`'
                desc_match = re.search(desc_pattern, field_modifiers)
                if desc_match:
                    param_info['description'] = desc_match.group(1).strip()

            parameters[field_name] = param_info

        return parameters


class TypeScriptInterfaceExtractor(SchemaExtractor):
    """Extract parameters from plain TypeScript interfaces."""
    
    def can_extract(self, content: str) -> bool:
        """Check if content uses TypeScript interfaces."""
        return 'interface' in content and '{' in content
    
    def get_library_name(self) -> str:
        return "TypeScript"
    
    def extract_params(self, content: str, schema_body: str) -> Dict[str, Any]:
        """Extract parameters from TypeScript interface definition."""
        parameters = {}
        
        # Pattern to match TypeScript interface fields
        # Matches: fieldName: string | fieldName?: number | fieldName: 'literal'
        field_pattern = r'(\w+)\??:\s*([^;,\n]+)'
        
        for match in re.finditer(field_pattern, schema_body):
            field_name = match.group(1)
            field_type_raw = match.group(2).strip()
            
            # Check if optional (has ? before :)
            is_optional = '?' in match.group(0).split(':')[0]
            
            # Map TypeScript types to standard types
            type_map = {
                'string': 'str',
                'number': 'number',
                'boolean': 'bool',
                'object': 'object',
                'any': 'any',
                'Array': 'array',
            }
            
            # Handle literal types
            if field_type_raw.startswith("'") or field_type_raw.startswith('"'):
                param_type = f"literal<{field_type_raw}>"
            # Handle union types (enums)
            elif '|' in field_type_raw:
                param_type = f"enum<{field_type_raw}>"
            # Handle array types
            elif field_type_raw.endswith('[]'):
                base_type = field_type_raw[:-2]
                param_type = f"array<{type_map.get(base_type, base_type)}>"
            else:
                param_type = type_map.get(field_type_raw, field_type_raw)
            
            parameters[field_name] = {
                'type': param_type,
                'required': not is_optional,
                'description': None
            }
        
        return parameters


class YupSchemaExtractor(SchemaExtractor):
    """Extract parameters from Yup schemas."""
    
    def can_extract(self, content: str) -> bool:
        """Check if content uses Yup schemas."""
        yup_indicators = [
            r'import\s*\{[^}]*yup[^}]*\}',
            r'from\s+["\']yup["\']',
            r'yup\.object\s*\(',
            r'yup\.string\s*\(',
        ]
        
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in yup_indicators)
    
    def get_library_name(self) -> str:
        return "Yup"
    
    def extract_params(self, content: str, schema_body: str) -> Dict[str, Any]:
        """Extract parameters from Yup schema definition."""
        parameters = {}
        
        # Pattern to match Yup fields: fieldName: yup.type()
        field_pattern = r'(\w+)\s*:\s*yup\.(\w+)\s*\(\)([^,\n]*?)(?=,|\n|$|\})'
        
        for match in re.finditer(field_pattern, schema_body, re.DOTALL):
            field_name = match.group(1)
            field_type = match.group(2)
            field_modifiers = match.group(3).strip()
            
            # Map Yup types to standard types
            type_map = {
                'string': 'str',
                'number': 'number',
                'boolean': 'bool',
                'object': 'object',
                'array': 'array',
                'date': 'date',
            }
            
            param_info = {
                'type': type_map.get(field_type, field_type),
                'required': True,
                'description': None
            }
            
            # Check if optional
            if '.optional()' in field_modifiers or '.notRequired()' in field_modifiers:
                param_info['required'] = False
            
            # Extract description
            desc_pattern = r'\.label\s*\(\s*["\']([^"\']+)["\']'
            desc_match = re.search(desc_pattern, field_modifiers)
            if desc_match:
                param_info['description'] = desc_match.group(1)
            
            parameters[field_name] = param_info
        
        return parameters


class SchemaExtractorFactory:
    """Factory for creating appropriate schema extractors."""
    
    def __init__(self):
        """Initialize factory with available extractors."""
        self.extractors = [
            ZodSchemaExtractor(),
            YupSchemaExtractor(),
            TypeScriptInterfaceExtractor(),
        ]
    
    def get_extractor(self, content: str) -> Optional[SchemaExtractor]:
        """Get the appropriate schema extractor for the content.
        
        Args:
            content: File content to analyze
            
        Returns:
            The first extractor that can handle the content, or None
        """
        for extractor in self.extractors:
            if extractor.can_extract(content):
                logger.debug(f"Using {extractor.get_library_name()} schema extractor")
                return extractor
        
        logger.debug("No schema extractor found for content")
        return None
    
    def register_extractor(self, extractor: SchemaExtractor):
        """Register a new schema extractor.
        
        Args:
            extractor: The extractor to register
        """
        self.extractors.insert(0, extractor)  # Insert at beginning for priority
        logger.info(f"Registered {extractor.get_library_name()} schema extractor")

