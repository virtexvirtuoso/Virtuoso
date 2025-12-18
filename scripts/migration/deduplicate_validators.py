#!/usr/bin/env python3
"""
Phase 2: Remove duplicate validation files intelligently
"""
import os
import ast
import hashlib
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
import difflib

class ValidatorDeduplicator:
    def __init__(self, src_path: str, dry_run: bool = True):
        self.src_path = Path(src_path)
        self.dry_run = dry_run
        self.duplicates = []
        self.merge_log = []
        
    def find_duplicate_validators(self) -> List[Tuple[str, str, float]]:
        """Find duplicate validators and calculate similarity"""
        validators = {}
        duplicates = []
        
        # Find all validator files
        validation_dir = self.src_path / 'validation'
        for root, dirs, files in os.walk(validation_dir):
            for file in files:
                if file.endswith('_validator.py') or file == 'validators.py':
                    file_path = Path(root) / file
                    rel_path = file_path.relative_to(self.src_path)
                    
                    # Group by base name
                    base_name = file.replace('_validator.py', '').replace('.py', '')
                    if base_name not in validators:
                        validators[base_name] = []
                    validators[base_name].append(str(rel_path))
        
        # Find duplicates
        for base_name, paths in validators.items():
            if len(paths) > 1:
                # Calculate similarity between files
                for i in range(len(paths)):
                    for j in range(i + 1, len(paths)):
                        similarity = self.calculate_similarity(
                            self.src_path / paths[i],
                            self.src_path / paths[j]
                        )
                        duplicates.append((paths[i], paths[j], similarity))
        
        return sorted(duplicates, key=lambda x: x[2], reverse=True)
    
    def calculate_similarity(self, file1: Path, file2: Path) -> float:
        """Calculate similarity between two files"""
        try:
            content1 = file1.read_text(encoding='utf-8').splitlines()
            content2 = file2.read_text(encoding='utf-8').splitlines()
            
            # Use difflib to calculate similarity
            matcher = difflib.SequenceMatcher(None, content1, content2)
            return matcher.ratio()
            
        except Exception:
            return 0.0
    
    def analyze_validator_content(self, file_path: Path) -> Dict:
        """Analyze validator file content"""
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content)
            
            analysis = {
                'imports': [],
                'classes': {},
                'functions': {},
                'has_todos': False,
                'line_count': len(content.splitlines())
            }
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        analysis['imports'].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    for alias in node.names:
                        analysis['imports'].append(f"{module}.{alias.name}")
                elif isinstance(node, ast.ClassDef):
                    analysis['classes'][node.name] = {
                        'methods': [n.name for n in node.body if isinstance(n, ast.FunctionDef)],
                        'bases': [ast.unparse(base) for base in node.bases]
                    }
                elif isinstance(node, ast.FunctionDef) and node.col_offset == 0:
                    analysis['functions'][node.name] = len(node.body)
            
            # Check for TODOs
            if 'TODO' in content or 'FIXME' in content:
                analysis['has_todos'] = True
                
            return analysis
            
        except Exception as e:
            return {'error': str(e)}
    
    def merge_validators(self, primary: str, secondary: str) -> Optional[str]:
        """Merge two validator files intelligently"""
        primary_path = self.src_path / primary
        secondary_path = self.src_path / secondary
        
        primary_analysis = self.analyze_validator_content(primary_path)
        secondary_analysis = self.analyze_validator_content(secondary_path)
        
        # If either has errors, skip
        if 'error' in primary_analysis or 'error' in secondary_analysis:
            self.merge_log.append(f"SKIP: Error analyzing {primary} or {secondary}")
            return None
        
        # Determine which file to keep as base
        primary_score = len(primary_analysis['classes']) + len(primary_analysis['functions'])
        secondary_score = len(secondary_analysis['classes']) + len(secondary_analysis['functions'])
        
        if secondary_score > primary_score:
            # Swap if secondary has more content
            primary, secondary = secondary, primary
            primary_path, secondary_path = secondary_path, primary_path
            primary_analysis, secondary_analysis = secondary_analysis, primary_analysis
        
        # Find unique elements in secondary
        unique_classes = set(secondary_analysis['classes'].keys()) - set(primary_analysis['classes'].keys())
        unique_functions = set(secondary_analysis['functions'].keys()) - set(primary_analysis['functions'].keys())
        
        if not unique_classes and not unique_functions:
            # No unique content in secondary, safe to remove
            self.merge_log.append(f"REMOVE: {secondary} (no unique content)")
            if not self.dry_run:
                secondary_path.unlink()
            return primary
        
        # Create merged content
        self.merge_log.append(f"MERGE: {secondary} -> {primary}")
        self.merge_log.append(f"  Unique classes: {unique_classes}")
        self.merge_log.append(f"  Unique functions: {unique_functions}")
        
        if not self.dry_run:
            # Read both files
            primary_content = primary_path.read_text(encoding='utf-8')
            secondary_content = secondary_path.read_text(encoding='utf-8')
            
            # Extract unique content from secondary
            secondary_tree = ast.parse(secondary_content)
            unique_nodes = []
            
            for node in secondary_tree.body:
                if isinstance(node, ast.ClassDef) and node.name in unique_classes:
                    unique_nodes.append(node)
                elif isinstance(node, ast.FunctionDef) and node.name in unique_functions:
                    unique_nodes.append(node)
            
            if unique_nodes:
                # Append unique content to primary
                merged_content = primary_content.rstrip() + '\n\n'
                merged_content += f"# Merged from {secondary}\n"
                
                for node in unique_nodes:
                    merged_content += ast.unparse(node) + '\n\n'
                
                primary_path.write_text(merged_content, encoding='utf-8')
            
            # Remove secondary file
            secondary_path.unlink()
        
        return primary
    
    def run_deduplication(self):
        """Run the deduplication process"""
        print(f"Starting validator deduplication (dry_run={self.dry_run})")
        print("=" * 60)
        
        # Find duplicates
        duplicates = self.find_duplicate_validators()
        
        if not duplicates:
            print("No duplicate validators found!")
            return
        
        print(f"\nFound {len(duplicates)} potential duplicate pairs:")
        for file1, file2, similarity in duplicates[:5]:
            print(f"  {file1}")
            print(f"  {file2}")
            print(f"  Similarity: {similarity:.1%}\n")
        
        if len(duplicates) > 5:
            print(f"  ... and {len(duplicates) - 5} more pairs")
        
        # Analyze each duplicate pair
        print("\nAnalyzing duplicates...")
        processed = set()
        
        for file1, file2, similarity in duplicates:
            # Skip if already processed
            if file1 in processed or file2 in processed:
                continue
                
            if similarity > 0.9:
                # Very similar, merge
                result = self.merge_validators(file1, file2)
                if result:
                    processed.add(file2)
            elif similarity > 0.5:
                # Moderately similar, analyze content
                print(f"\nAnalyzing: {file1} vs {file2}")
                
                analysis1 = self.analyze_validator_content(self.src_path / file1)
                analysis2 = self.analyze_validator_content(self.src_path / file2)
                
                print(f"  {file1}: {len(analysis1.get('classes', {}))} classes, {len(analysis1.get('functions', {}))} functions")
                print(f"  {file2}: {len(analysis2.get('classes', {}))} classes, {len(analysis2.get('functions', {}))} functions")
                
                # Merge if they complement each other
                if set(analysis1.get('classes', {}).keys()).isdisjoint(set(analysis2.get('classes', {}).keys())):
                    result = self.merge_validators(file1, file2)
                    if result:
                        processed.add(file2)
        
        # Save merge log
        log_file = Path('validator_deduplication_log.txt')
        with open(log_file, 'w') as f:
            f.write("Validator Deduplication Log\n")
            f.write("=" * 60 + "\n\n")
            f.write('\n'.join(self.merge_log))
        
        print(f"\nDeduplication complete!")
        print(f"Log saved to: {log_file}")
        print(f"Operations performed: {len(self.merge_log)}")

def main():
    import argparse

    # Default to project src directory relative to script location
    default_src = str(Path(__file__).parent.parent.parent / 'src')

    parser = argparse.ArgumentParser(description='Deduplicate validator files')
    parser.add_argument('--execute', action='store_true', help='Execute deduplication (default is dry-run)')
    parser.add_argument('--analyze', action='store_true', help='Only analyze, don\'t deduplicate')
    parser.add_argument('--src', default=default_src, help='Source directory')
    
    args = parser.parse_args()
    
    deduplicator = ValidatorDeduplicator(args.src, dry_run=not args.execute)
    
    if args.analyze:
        # Just analyze and report
        duplicates = deduplicator.find_duplicate_validators()
        print(f"Found {len(duplicates)} duplicate pairs")
        for file1, file2, similarity in duplicates:
            print(f"\n{file1}")
            print(f"{file2}")
            print(f"Similarity: {similarity:.1%}")
    else:
        deduplicator.run_deduplication()

if __name__ == "__main__":
    main()