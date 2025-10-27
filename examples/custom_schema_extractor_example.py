"""
Example: Adding a Custom Schema Extractor

This example demonstrates how to create and register a custom schema extractor
for a validation library that isn't supported out-of-the-box.
"""

import re
from typing import Dict, Any
from agentbom.detectors.schema_extractors import SchemaExtractor, SchemaExtractorFactory


class TypeBoxSchemaExtractor(SchemaExtractor):
    """
    Custom extractor for TypeBox schemas.
    TypeBox: https://github.com/sinclairzx81/typebox
    
    Example schema:
        const schema = Type.Object({
          name: Type.String(),
          age: Type.Number(),
          email: Type.Optional(Type.String())
        })
    """
    
    def can_extract(self, content: str) -> bool:
        """Check if content uses TypeBox schemas."""
        # Look for TypeBox imports and usage patterns
        typebox_indicators = [
            r'import\s*\{[^}]*Type[^}]*\}\s*from\s*["\']@sinclair/typebox["\']',
            r"from\s+['\"]@sinclair/typebox['\"]",
            r'Type\.Object\s*\(',
            r'Type\.String\s*\(',
        ]
        
        return any(re.search(pattern, content) for pattern in typebox_indicators)
    
    def get_library_name(self) -> str:
        return "TypeBox"
    
    def extract_params(self, content: str, schema_body: str) -> Dict[str, Any]:
        """Extract parameters from TypeBox schema definition."""
        parameters = {}
        
        # Pattern to match TypeBox fields
        # Matches: fieldName: Type.TypeName(...) or fieldName: Type.Optional(Type.TypeName())
        field_pattern = r'(\w+)\s*:\s*Type\.(Optional\s*\(\s*)?Type\.(\w+)\s*\('
        
        for match in re.finditer(field_pattern, schema_body):
            field_name = match.group(1)
            is_optional = match.group(2) is not None
            field_type = match.group(3)
            
            # Map TypeBox types to standard types
            type_map = {
                'String': 'str',
                'Number': 'number',
                'Boolean': 'bool',
                'Object': 'object',
                'Array': 'array',
                'Date': 'date',
                'Literal': 'literal',
                'Union': 'enum',
            }
            
            param_info = {
                'type': type_map.get(field_type, field_type.lower()),
                'required': not is_optional,
                'description': None
            }
            
            # Try to extract description if present
            # TypeBox uses: Type.String({ description: '...' })
            desc_pattern = rf'{re.escape(field_name)}\s*:.*?description\s*:\s*["\']([^"\']+)["\']'
            desc_match = re.search(desc_pattern, schema_body)
            if desc_match:
                param_info['description'] = desc_match.group(1)
            
            parameters[field_name] = param_info
        
        return parameters


class JoiSchemaExtractor(SchemaExtractor):
    """
    Custom extractor for Joi schemas.
    Joi: https://joi.dev/
    
    Example schema:
        const schema = Joi.object({
          name: Joi.string().required(),
          age: Joi.number().optional(),
          email: Joi.string().email()
        })
    """
    
    def can_extract(self, content: str) -> bool:
        """Check if content uses Joi schemas."""
        joi_indicators = [
            r'import\s+Joi\s+from\s+["\']joi["\']',
            r'require\s*\(\s*["\']joi["\']\s*\)',
            r'Joi\.object\s*\(',
            r'Joi\.string\s*\(',
        ]
        
        return any(re.search(pattern, content) for pattern in joi_indicators)
    
    def get_library_name(self) -> str:
        return "Joi"
    
    def extract_params(self, content: str, schema_body: str) -> Dict[str, Any]:
        """Extract parameters from Joi schema definition."""
        parameters = {}
        
        # Pattern to match Joi fields
        # Matches: fieldName: Joi.type()...
        field_pattern = r'(\w+)\s*:\s*Joi\.(\w+)\s*\(\)([^,\n}]*?)(?=,|\n|$|\})'
        
        for match in re.finditer(field_pattern, schema_body, re.DOTALL):
            field_name = match.group(1)
            field_type = match.group(2)
            field_modifiers = match.group(3).strip()
            
            # Map Joi types to standard types
            type_map = {
                'string': 'str',
                'number': 'number',
                'boolean': 'bool',
                'object': 'object',
                'array': 'array',
                'date': 'date',
                'any': 'any',
            }
            
            param_info = {
                'type': type_map.get(field_type, field_type),
                'required': '.required()' in field_modifiers,
                'description': None
            }
            
            # Extract description
            desc_pattern = r'\.description\s*\(\s*["\']([^"\']+)["\']'
            desc_match = re.search(desc_pattern, field_modifiers)
            if desc_match:
                param_info['description'] = desc_match.group(1)
            
            parameters[field_name] = param_info
        
        return parameters


# Example usage
def demo_custom_extractors():
    """Demonstrate how to use custom extractors."""
    
    # Create factory
    factory = SchemaExtractorFactory()
    
    # Register custom extractors
    print("Registering custom extractors...")
    factory.register_extractor(TypeBoxSchemaExtractor())
    factory.register_extractor(JoiSchemaExtractor())
    print("✅ Custom extractors registered!\n")
    
    # Example 1: TypeBox schema
    typebox_content = """
    import { Type } from '@sinclair/typebox'
    
    const schema = Type.Object({
      name: Type.String({ description: 'User name' }),
      age: Type.Number(),
      email: Type.Optional(Type.String())
    })
    """
    
    schema_body = """
    name: Type.String({ description: 'User name' }),
    age: Type.Number(),
    email: Type.Optional(Type.String())
    """
    
    print("Example 1: TypeBox Schema")
    print("-" * 50)
    extractor = factory.get_extractor(typebox_content)
    if extractor:
        print(f"Detected library: {extractor.get_library_name()}")
        params = extractor.extract_params(typebox_content, schema_body)
        print(f"Extracted parameters: {params}")
    print()
    
    # Example 2: Joi schema
    joi_content = """
    import Joi from 'joi'
    
    const schema = Joi.object({
      username: Joi.string().required().description('Username'),
      password: Joi.string().required(),
      age: Joi.number().optional()
    })
    """
    
    schema_body = """
    username: Joi.string().required().description('Username'),
    password: Joi.string().required(),
    age: Joi.number().optional()
    """
    
    print("Example 2: Joi Schema")
    print("-" * 50)
    extractor = factory.get_extractor(joi_content)
    if extractor:
        print(f"Detected library: {extractor.get_library_name()}")
        params = extractor.extract_params(joi_content, schema_body)
        print(f"Extracted parameters: {params}")
    print()
    
    # Example 3: Still works with Zod (built-in)
    zod_content = """
    import { z } from 'zod'
    
    const schema = z.object({
      role: z.literal('agent'),
      content: z.string().describe('Message content')
    })
    """
    
    schema_body = """
    role: z.literal('agent'),
    content: z.string().describe('Message content')
    """
    
    print("Example 3: Zod Schema (Built-in)")
    print("-" * 50)
    extractor = factory.get_extractor(zod_content)
    if extractor:
        print(f"Detected library: {extractor.get_library_name()}")
        params = extractor.extract_params(zod_content, schema_body)
        print(f"Extracted parameters: {params}")
    print()


def integrate_with_detector():
    """Show how to integrate custom extractors with the detector."""
    from agentbom.detectors.langchain_ts import LangChainTypeScriptDetector
    
    print("Integration Example")
    print("=" * 50)
    
    # Create detector
    detector = LangChainTypeScriptDetector()
    
    # Register custom extractors
    detector.schema_factory.register_extractor(TypeBoxSchemaExtractor())
    detector.schema_factory.register_extractor(JoiSchemaExtractor())
    
    print("✅ Custom extractors integrated with detector")
    print("   Now the detector can handle TypeBox and Joi schemas!")
    print()
    
    # The detector will now automatically use these extractors
    # when scanning TypeScript files that use TypeBox or Joi


if __name__ == "__main__":
    print("=" * 50)
    print("Custom Schema Extractor Examples")
    print("=" * 50)
    print()
    
    demo_custom_extractors()
    integrate_with_detector()
    
    print("=" * 50)
    print("Summary:")
    print("  ✅ Created TypeBox extractor")
    print("  ✅ Created Joi extractor")
    print("  ✅ Registered with factory")
    print("  ✅ Integrated with detector")
    print()
    print("Now you can scan projects using TypeBox or Joi!")
    print("=" * 50)

