#!/usr/bin/env python3
"""
Auto-Documentation Generator for Virtuoso CCXT Trading System

This script automatically generates documentation from Python docstrings,
type hints, and code analysis. It creates markdown documentation files
that follow the standardized template format.

Features:
- Extracts docstrings and type hints from Python files
- Generates method documentation with parameters and return types
- Creates API reference documentation
- Validates documentation completeness
- Generates cross-references and links

Usage:
    python scripts/documentation/generate_docs.py [options]
    
Options:
    --source-dir: Source directory to scan (default: src/)
    --output-dir: Output directory for docs (default: docs/auto-generated/)
    --template-dir: Template directory (default: docs/templates/)
    --include-private: Include private methods (default: False)
    --update-existing: Update existing docs (default: False)
    --format: Output format (markdown, rst, html) (default: markdown)

Version: 1.0.0
"""

import os
import re
import ast
import sys
import json
import argparse
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from datetime import datetime
import inspect

@dataclass
class MethodInfo:
    """Information about a method extracted from code."""
    name: str
    docstring: Optional[str]
    parameters: Dict[str, Any]
    return_type: Optional[str]
    is_async: bool
    is_private: bool
    decorators: List[str]
    line_number: int
    class_name: Optional[str] = None

@dataclass
class ClassInfo:
    """Information about a class extracted from code."""
    name: str
    docstring: Optional[str]
    methods: List[MethodInfo]
    inheritance: List[str]
    line_number: int
    file_path: str

@dataclass
class ModuleInfo:
    """Information about a module extracted from code."""
    name: str
    file_path: str
    docstring: Optional[str]
    classes: List[ClassInfo]
    functions: List[MethodInfo]
    imports: List[str]

class DocumentationGenerator:
    """Main documentation generator class."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.source_dir = Path(config.get('source_dir', 'src/'))
        self.output_dir = Path(config.get('output_dir', 'docs/auto-generated/'))
        self.template_dir = Path(config.get('template_dir', 'docs/templates/'))
        self.include_private = config.get('include_private', False)
        self.output_format = config.get('format', 'markdown')
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load template
        self.template = self._load_template()
        
    def _load_template(self) -> str:
        """Load documentation template."""
        template_file = self.template_dir / 'DOCUMENTATION_TEMPLATE.md'
        
        if template_file.exists():
            with open(template_file, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            return self._get_default_template()
    
    def _get_default_template(self) -> str:
        """Get default template if template file doesn't exist."""
        return '''# {module_name} Documentation

## Overview

{module_docstring}

---

## Classes

{classes_section}

---

## Functions

{functions_section}

---

## API Reference

{api_reference}

---

*Auto-generated documentation - {timestamp}*
'''
    
    def generate_documentation(self) -> Dict[str, Any]:
        """Generate documentation for all Python files in source directory."""
        print("🚀 Starting documentation generation...")
        
        results = {
            'processed_files': 0,
            'generated_docs': 0,
            'errors': [],
            'modules': []
        }
        
        # Find all Python files
        python_files = list(self.source_dir.rglob('*.py'))
        
        print(f"📁 Found {len(python_files)} Python files to process")
        
        for file_path in python_files:
            try:
                # Skip __pycache__ and other unwanted directories
                if '__pycache__' in str(file_path) or '.pyc' in str(file_path):
                    continue
                
                print(f"📄 Processing {file_path}")
                
                # Extract module information
                module_info = self._extract_module_info(file_path)
                
                # Generate documentation
                doc_content = self._generate_module_documentation(module_info)
                
                # Write documentation file
                doc_file = self._get_output_path(file_path)
                self._write_documentation(doc_file, doc_content)
                
                results['processed_files'] += 1
                results['generated_docs'] += 1
                results['modules'].append({
                    'name': module_info.name,
                    'file_path': str(file_path),
                    'doc_path': str(doc_file),
                    'classes_count': len(module_info.classes),
                    'functions_count': len(module_info.functions)
                })
                
            except Exception as e:
                error_msg = f"Error processing {file_path}: {str(e)}"
                print(f"❌ {error_msg}")
                results['errors'].append(error_msg)
        
        # Generate summary report
        self._generate_summary_report(results)
        
        print(f"✅ Documentation generation complete!")
        print(f"   Processed: {results['processed_files']} files")
        print(f"   Generated: {results['generated_docs']} docs")
        print(f"   Errors: {len(results['errors'])}")
        
        return results
    
    def _extract_module_info(self, file_path: Path) -> ModuleInfo:
        """Extract information from a Python module."""
        
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse AST
        tree = ast.parse(content)
        
        # Extract module docstring
        module_docstring = ast.get_docstring(tree)
        
        # Extract imports
        imports = self._extract_imports(tree)
        
        # Extract classes and functions
        classes = []
        functions = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_info = self._extract_class_info(node, file_path)
                classes.append(class_info)
            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                # Only top-level functions (not class methods)
                if isinstance(node, ast.FunctionDef) and not any(isinstance(parent, ast.ClassDef) for parent in ast.walk(tree)):
                    function_info = self._extract_method_info(node)
                    functions.append(function_info)
        
        module_name = file_path.stem
        
        return ModuleInfo(
            name=module_name,
            file_path=str(file_path),
            docstring=module_docstring,
            classes=classes,
            functions=functions,
            imports=imports
        )
    
    def _extract_class_info(self, node: ast.ClassDef, file_path: Path) -> ClassInfo:
        """Extract information from a class definition."""
        
        # Extract class docstring
        docstring = ast.get_docstring(node)
        
        # Extract inheritance
        inheritance = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                inheritance.append(base.id)
            elif isinstance(base, ast.Attribute):
                inheritance.append(f"{base.value.id}.{base.attr}")
        
        # Extract methods
        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if self.include_private or not item.name.startswith('_'):
                    method_info = self._extract_method_info(item, node.name)
                    methods.append(method_info)
        
        return ClassInfo(
            name=node.name,
            docstring=docstring,
            methods=methods,
            inheritance=inheritance,
            line_number=node.lineno,
            file_path=str(file_path)
        )
    
    def _extract_method_info(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef], class_name: Optional[str] = None) -> MethodInfo:
        """Extract information from a method/function definition."""
        
        # Extract docstring
        docstring = ast.get_docstring(node)
        
        # Extract parameters
        parameters = {}
        for arg in node.args.args:
            arg_name = arg.arg
            
            # Skip 'self' parameter
            if arg_name == 'self':
                continue
            
            # Extract type annotation if available
            type_annotation = None
            if arg.annotation:
                type_annotation = self._extract_type_annotation(arg.annotation)
            
            parameters[arg_name] = {
                'type': type_annotation,
                'default': None
            }
        
        # Extract default values
        defaults = node.args.defaults
        if defaults:
            # Match defaults with parameters (defaults are for the last n parameters)
            param_names = [arg.arg for arg in node.args.args if arg.arg != 'self']
            num_defaults = len(defaults)
            
            for i, default in enumerate(defaults):
                param_index = len(param_names) - num_defaults + i
                if param_index >= 0:
                    param_name = param_names[param_index]
                    if param_name in parameters:
                        parameters[param_name]['default'] = self._extract_default_value(default)
        
        # Extract return type
        return_type = None
        if node.returns:
            return_type = self._extract_type_annotation(node.returns)
        
        # Extract decorators
        decorators = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                decorators.append(decorator.id)
            elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
                decorators.append(decorator.func.id)
        
        return MethodInfo(
            name=node.name,
            docstring=docstring,
            parameters=parameters,
            return_type=return_type,
            is_async=isinstance(node, ast.AsyncFunctionDef),
            is_private=node.name.startswith('_'),
            decorators=decorators,
            line_number=node.lineno,
            class_name=class_name
        )
    
    def _extract_type_annotation(self, annotation) -> str:
        """Extract type annotation as string."""
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Attribute):
            return f"{self._extract_type_annotation(annotation.value)}.{annotation.attr}"
        elif isinstance(annotation, ast.Subscript):
            # Handle generic types like Dict[str, Any]
            value = self._extract_type_annotation(annotation.value)
            slice_val = annotation.slice
            
            if isinstance(slice_val, ast.Tuple):
                slice_parts = [self._extract_type_annotation(elt) for elt in slice_val.elts]
                return f"{value}[{', '.join(slice_parts)}]"
            else:
                slice_str = self._extract_type_annotation(slice_val)
                return f"{value}[{slice_str}]"
        elif isinstance(annotation, ast.Constant):
            return str(annotation.value)
        else:
            return "Any"
    
    def _extract_default_value(self, default) -> str:
        """Extract default value as string."""
        if isinstance(default, ast.Constant):
            if isinstance(default.value, str):
                return f"'{default.value}'"
            return str(default.value)
        elif isinstance(default, ast.Name):
            return default.id
        elif isinstance(default, ast.Attribute):
            return f"{self._extract_default_value(default.value)}.{default.attr}"
        else:
            return "..."
    
    def _extract_imports(self, tree: ast.AST) -> List[str]:
        """Extract import statements from AST."""
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(f"import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"from {module} import {alias.name}")
        
        return imports
    
    def _generate_module_documentation(self, module_info: ModuleInfo) -> str:
        """Generate documentation content for a module."""
        
        # Generate classes section
        classes_section = self._generate_classes_section(module_info.classes)
        
        # Generate functions section
        functions_section = self._generate_functions_section(module_info.functions)
        
        # Generate API reference
        api_reference = self._generate_api_reference(module_info)
        
        # Replace template variables
        content = self.template.format(
            module_name=module_info.name.title().replace('_', ' '),
            module_docstring=module_info.docstring or "No module description available.",
            classes_section=classes_section,
            functions_section=functions_section,
            api_reference=api_reference,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        return content
    
    def _generate_classes_section(self, classes: List[ClassInfo]) -> str:
        """Generate classes section of documentation."""
        if not classes:
            return "No classes found in this module."
        
        sections = []
        
        for class_info in classes:
            class_section = f"### `{class_info.name}`\n\n"
            
            if class_info.docstring:
                class_section += f"{class_info.docstring}\n\n"
            
            if class_info.inheritance:
                class_section += f"**Inherits from**: {', '.join(class_info.inheritance)}\n\n"
            
            # Add methods
            if class_info.methods:
                class_section += "**Methods**:\n\n"
                for method in class_info.methods:
                    class_section += self._generate_method_documentation(method, is_class_method=True)
            
            sections.append(class_section)
        
        return "\n".join(sections)
    
    def _generate_functions_section(self, functions: List[MethodInfo]) -> str:
        """Generate functions section of documentation."""
        if not functions:
            return "No standalone functions found in this module."
        
        sections = []
        
        for function in functions:
            sections.append(self._generate_method_documentation(function, is_class_method=False))
        
        return "\n".join(sections)
    
    def _generate_method_documentation(self, method: MethodInfo, is_class_method: bool = True) -> str:
        """Generate documentation for a single method."""
        
        # Method signature
        params_str = self._generate_parameters_string(method.parameters)
        async_prefix = "async " if method.is_async else ""
        return_annotation = f" -> {method.return_type}" if method.return_type else ""
        
        if is_class_method:
            signature = f"#### `{async_prefix}def {method.name}({params_str}){return_annotation}`\n\n"
        else:
            signature = f"### `{async_prefix}def {method.name}({params_str}){return_annotation}`\n\n"
        
        doc_section = signature
        
        # Docstring
        if method.docstring:
            doc_section += f"{method.docstring}\n\n"
        else:
            doc_section += "*No description available.*\n\n"
        
        # Parameters table if there are parameters
        if method.parameters:
            doc_section += "**Parameters**:\n\n"
            doc_section += "| Parameter | Type | Default | Description |\n"
            doc_section += "|-----------|------|---------|-------------|\n"
            
            for param_name, param_info in method.parameters.items():
                param_type = param_info.get('type', 'Any')
                default = param_info.get('default', 'Required')
                description = self._extract_param_description(method.docstring, param_name)
                
                doc_section += f"| `{param_name}` | `{param_type}` | `{default}` | {description} |\n"
            
            doc_section += "\n"
        
        # Return information
        if method.return_type:
            return_desc = self._extract_return_description(method.docstring)
            doc_section += f"**Returns**: `{method.return_type}` - {return_desc}\n\n"
        
        # Decorators
        if method.decorators:
            doc_section += f"**Decorators**: {', '.join(f'`@{d}`' for d in method.decorators)}\n\n"
        
        return doc_section
    
    def _generate_parameters_string(self, parameters: Dict[str, Any]) -> str:
        """Generate parameters string for method signature."""
        param_parts = []
        
        for param_name, param_info in parameters.items():
            param_str = param_name
            
            if param_info.get('type'):
                param_str += f": {param_info['type']}"
            
            if param_info.get('default') is not None:
                param_str += f" = {param_info['default']}"
            
            param_parts.append(param_str)
        
        return ", ".join(param_parts)
    
    def _extract_param_description(self, docstring: Optional[str], param_name: str) -> str:
        """Extract parameter description from docstring."""
        if not docstring:
            return "No description"
        
        # Look for various docstring formats
        patterns = [
            rf"{param_name}[:\s]+(.+?)(?:\n|$)",  # param: description
            rf"Args:.*?{param_name}[:\s]+(.+?)(?:\n|$)",  # Args section
            rf"Parameters:.*?{param_name}[:\s]+(.+?)(?:\n|$)",  # Parameters section
        ]
        
        for pattern in patterns:
            match = re.search(pattern, docstring, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return "No description"
    
    def _extract_return_description(self, docstring: Optional[str]) -> str:
        """Extract return description from docstring."""
        if not docstring:
            return "No description"
        
        # Look for return description
        patterns = [
            r"Returns?[:\s]+(.+?)(?:\n\n|$)",
            r"Return[:\s]+(.+?)(?:\n\n|$)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, docstring, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip().replace('\n', ' ')
        
        return "No description"
    
    def _generate_api_reference(self, module_info: ModuleInfo) -> str:
        """Generate API reference section."""
        
        api_ref = "### Quick Reference\n\n"
        
        # Classes quick reference
        if module_info.classes:
            api_ref += "**Classes**:\n\n"
            for class_info in module_info.classes:
                method_count = len([m for m in class_info.methods if not m.is_private])
                api_ref += f"- [`{class_info.name}`](#{class_info.name.lower()}) - {method_count} public methods\n"
            api_ref += "\n"
        
        # Functions quick reference
        if module_info.functions:
            api_ref += "**Functions**:\n\n"
            for function in module_info.functions:
                if not function.is_private:
                    api_ref += f"- [`{function.name}()`](#{function.name.lower()}) - {function.docstring.split('.')[0] if function.docstring else 'No description'}\n"
            api_ref += "\n"
        
        return api_ref
    
    def _get_output_path(self, source_path: Path) -> Path:
        """Get output path for documentation file."""
        
        # Get relative path from source directory
        relative_path = source_path.relative_to(self.source_dir)
        
        # Change extension to .md
        doc_path = self.output_dir / relative_path.with_suffix('.md')
        
        # Ensure output directory exists
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        
        return doc_path
    
    def _write_documentation(self, output_path: Path, content: str):
        """Write documentation content to file."""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _generate_summary_report(self, results: Dict[str, Any]):
        """Generate summary report of documentation generation."""
        
        report_content = f"""# Documentation Generation Report

**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Summary

- **Files Processed**: {results['processed_files']}
- **Documentation Files Generated**: {results['generated_docs']}
- **Errors**: {len(results['errors'])}

## Generated Documentation

"""
        
        for module in results['modules']:
            report_content += f"### {module['name']}\n"
            report_content += f"- **Source**: `{module['file_path']}`\n"
            report_content += f"- **Documentation**: `{module['doc_path']}`\n"
            report_content += f"- **Classes**: {module['classes_count']}\n"
            report_content += f"- **Functions**: {module['functions_count']}\n\n"
        
        if results['errors']:
            report_content += "## Errors\n\n"
            for error in results['errors']:
                report_content += f"- {error}\n"
            report_content += "\n"
        
        report_content += "---\n*Auto-generated by Virtuoso CCXT Documentation Generator*"
        
        # Write report
        report_path = self.output_dir / 'GENERATION_REPORT.md'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"📊 Summary report saved to: {report_path}")

def main():
    """Main function to run documentation generation."""
    
    parser = argparse.ArgumentParser(
        description="Auto-generate documentation for Virtuoso CCXT Trading System"
    )
    
    parser.add_argument(
        '--source-dir',
        default='src/',
        help='Source directory to scan for Python files'
    )
    
    parser.add_argument(
        '--output-dir', 
        default='docs/auto-generated/',
        help='Output directory for generated documentation'
    )
    
    parser.add_argument(
        '--template-dir',
        default='docs/templates/',
        help='Directory containing documentation templates'
    )
    
    parser.add_argument(
        '--include-private',
        action='store_true',
        help='Include private methods in documentation'
    )
    
    parser.add_argument(
        '--update-existing',
        action='store_true',
        help='Update existing documentation files'
    )
    
    parser.add_argument(
        '--format',
        choices=['markdown', 'rst', 'html'],
        default='markdown',
        help='Output format for documentation'
    )
    
    args = parser.parse_args()
    
    # Create configuration
    config = {
        'source_dir': args.source_dir,
        'output_dir': args.output_dir,
        'template_dir': args.template_dir,
        'include_private': args.include_private,
        'update_existing': args.update_existing,
        'format': args.format
    }
    
    # Initialize generator
    generator = DocumentationGenerator(config)
    
    # Generate documentation
    try:
        results = generator.generate_documentation()
        
        if results['errors']:
            print(f"\n⚠️  {len(results['errors'])} errors occurred during generation.")
            print("Check the generation report for details.")
            sys.exit(1)
        else:
            print(f"\n🎉 Documentation generation completed successfully!")
            sys.exit(0)
            
    except Exception as e:
        print(f"\n💥 Fatal error during documentation generation: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()