#!/usr/bin/env python3
"""
File Audit Logger
==================

Creates an audit log of file changes using MD5 hashing.
Tracks all file modifications in the repository for future agents.
Automatically generates documentation for changed files.

Output format: datetime / file path / md5 hash
"""

import hashlib
import os
import datetime
import json
from pathlib import Path
from typing import Dict, Set, Tuple, Optional, List
import argparse


class DocumentationGenerator:
    """
    Generates documentation for changed files automatically.
    """
    
    def __init__(self, readme_dir: str = "readme"):
        """
        Initialize the documentation generator.
        
        Args:
            readme_dir: Directory where README files will be stored
        """
        self.readme_dir = Path(readme_dir)
        self.readme_dir.mkdir(exist_ok=True)
    
    def get_file_analysis(self, file_path: Path) -> Dict[str, str]:
        """
        Analyze a file and extract key information for documentation.
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            Dictionary with file analysis information
        """
        analysis = {
            'file_type': file_path.suffix.lower(),
            'file_name': file_path.name,
            'relative_path': str(file_path),
            'purpose': 'Unknown',
            'functions': [],
            'classes': [],
            'imports': [],
            'description': ''
        }
        
        try:
            if file_path.suffix.lower() == '.py':
                analysis.update(self._analyze_python_file(file_path))
            elif file_path.suffix.lower() in ['.sh', '.bash']:
                analysis.update(self._analyze_shell_script(file_path))
            elif file_path.suffix.lower() in ['.json', '.yaml', '.yml']:
                analysis.update(self._analyze_config_file(file_path))
            elif file_path.suffix.lower() == '.md':
                analysis.update(self._analyze_markdown_file(file_path))
            else:
                analysis.update(self._analyze_generic_file(file_path))
        except Exception as e:
            analysis['error'] = f"Could not analyze file: {e}"
        
        return analysis
    
    def _analyze_python_file(self, file_path: Path) -> Dict[str, any]:
        """Analyze Python file for functions, classes, imports."""
        analysis = {'purpose': 'Python module/script'}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            functions = []
            classes = []
            imports = []
            docstring = ""
            
            # Extract module docstring
            in_docstring = False
            docstring_lines = []
            for line in lines[:20]:  # Check first 20 lines for module docstring
                line = line.strip()
                if line.startswith('"""') or line.startswith("'''"):
                    if in_docstring:
                        break
                    in_docstring = True
                    if len(line) > 3:
                        docstring_lines.append(line[3:])
                elif in_docstring:
                    if line.endswith('"""') or line.endswith("'''"):
                        docstring_lines.append(line[:-3])
                        break
                    docstring_lines.append(line)
            
            docstring = '\n'.join(docstring_lines).strip()
            
            for line in lines:
                line = line.strip()
                if line.startswith('def ') and '(' in line:
                    func_name = line.split('(')[0].replace('def ', '').strip()
                    functions.append(func_name)
                elif line.startswith('class ') and ':' in line:
                    class_name = line.split(':')[0].replace('class ', '').strip()
                    classes.append(class_name)
                elif line.startswith('import ') or line.startswith('from '):
                    imports.append(line)
            
            analysis.update({
                'functions': functions,
                'classes': classes,
                'imports': imports[:10],  # Limit to first 10 imports
                'description': docstring
            })
            
        except Exception as e:
            analysis['error'] = f"Error analyzing Python file: {e}"
        
        return analysis
    
    def _analyze_shell_script(self, file_path: Path) -> Dict[str, any]:
        """Analyze shell script."""
        analysis = {'purpose': 'Shell script'}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            # Look for comments at the top
            description_lines = []
            for line in lines[:10]:
                if line.strip().startswith('#') and not line.strip().startswith('#!/'):
                    description_lines.append(line.strip()[1:].strip())
            
            analysis['description'] = '\n'.join(description_lines)
            
        except Exception as e:
            analysis['error'] = f"Error analyzing shell script: {e}"
        
        return analysis
    
    def _analyze_config_file(self, file_path: Path) -> Dict[str, any]:
        """Analyze configuration file."""
        analysis = {'purpose': 'Configuration file'}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Count lines and estimate complexity
            lines = len(content.split('\n'))
            analysis['description'] = f"Configuration file with {lines} lines"
            
        except Exception as e:
            analysis['error'] = f"Error analyzing config file: {e}"
        
        return analysis
    
    def _analyze_markdown_file(self, file_path: Path) -> Dict[str, any]:
        """Analyze markdown file."""
        analysis = {'purpose': 'Documentation file'}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            title = ""
            
            # Find the first heading
            for line in lines[:5]:
                if line.startswith('# '):
                    title = line[2:].strip()
                    break
            
            analysis['description'] = f"Documentation: {title}" if title else "Markdown documentation file"
            
        except Exception as e:
            analysis['error'] = f"Error analyzing markdown file: {e}"
        
        return analysis
    
    def _analyze_generic_file(self, file_path: Path) -> Dict[str, any]:
        """Analyze generic file."""
        analysis = {'purpose': f'{file_path.suffix.upper()} file'}
        
        try:
            file_size = file_path.stat().st_size
            analysis['description'] = f"File of type {file_path.suffix} ({file_size} bytes)"
        except Exception as e:
            analysis['error'] = f"Error analyzing file: {e}"
        
        return analysis
    
    def generate_readme_content(self, file_path: Path, analysis: Dict[str, any], change_type: str) -> str:
        """
        Generate README content for a changed file.
        
        Args:
            file_path: Path to the changed file
            analysis: File analysis data
            change_type: Type of change (NEW, MODIFIED, etc.)
            
        Returns:
            Generated README content as markdown
        """
        timestamp = datetime.datetime.now().isoformat()
        
        content = f"""# {analysis['file_name']}

**File Type:** {analysis['file_type'].upper()}  
**Path:** `{analysis['relative_path']}`  
**Last Updated:** {timestamp}  
**Change Type:** {change_type}

## Overview

{analysis.get('description', 'No description available.')}

## Purpose

{analysis.get('purpose', 'Unknown purpose')}

"""
        
        # Add Python-specific sections
        if analysis['file_type'] == '.py':
            if analysis.get('functions'):
                content += f"""## Functions

{', '.join(f'`{func}`' for func in analysis['functions'][:10])}

"""
            
            if analysis.get('classes'):
                content += f"""## Classes

{', '.join(f'`{cls}`' for cls in analysis['classes'][:10])}

"""
            
            if analysis.get('imports'):
                content += f"""## Key Imports

```python
{chr(10).join(analysis['imports'][:5])}
```

"""
        
        # Add shell script specific sections
        elif analysis['file_type'] in ['.sh', '.bash']:
            content += """## Usage

```bash
# Make executable
chmod +x """ + analysis['file_name'] + """

# Run script
./""" + analysis['file_name'] + """
```

"""
        
        # Add configuration file sections
        elif analysis['file_type'] in ['.json', '.yaml', '.yml']:
            content += """## Configuration

This file contains configuration settings for the application.

"""
        
        content += f"""## File Analysis

- **File Size:** {file_path.stat().st_size if file_path.exists() else 'Unknown'} bytes
- **File Type:** {analysis['file_type']}
- **Last Modified:** {datetime.datetime.fromtimestamp(file_path.stat().st_mtime).isoformat() if file_path.exists() else 'Unknown'}

## Audit Information

This documentation was automatically generated by the File Audit System when the file was {change_type.lower()}.

---
*Generated on {timestamp} by File Audit Logger*
"""
        
        return content
    
    def create_or_update_readme(self, file_path: Path, change_type: str) -> Optional[Path]:
        """
        Create or update README file for a changed file.
        
        Args:
            file_path: Path to the changed file
            change_type: Type of change (NEW, MODIFIED, etc.)
            
        Returns:
            Path to the created/updated README file
        """
        try:
            # Generate README filename based on original file
            readme_name = f"README_{file_path.name.replace('.', '_')}.md"
            readme_path = self.readme_dir / readme_name
            
            # Analyze the file
            analysis = self.get_file_analysis(file_path)
            
            # Generate content
            content = self.generate_readme_content(file_path, analysis, change_type)
            
            # Write README file
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return readme_path
            
        except Exception as e:
            print(f"Error creating README for {file_path}: {e}")
            return None


class FileAuditLogger:
    """
    A comprehensive file audit logging system that tracks file changes using MD5 hashes.
    """
    
    def __init__(self, 
                 root_dir: str = ".", 
                 audit_log_file: str = "file_audit.log",
                 state_file: str = "file_audit_state.json",
                 auto_document: bool = True):
        """
        Initialize the FileAuditLogger.
        
        Args:
            root_dir: Root directory to scan (default: current directory)
            audit_log_file: Path to the audit log file
            state_file: Path to store current state for change detection
            auto_document: Whether to automatically generate documentation for changes
        """
        self.root_dir = Path(root_dir).resolve()
        self.audit_log_file = Path(audit_log_file)
        self.state_file = Path(state_file)
        self.auto_document = auto_document
        
        # Initialize documentation generator
        if auto_document:
            self.doc_generator = DocumentationGenerator()
        
        # Directories and files to exclude from scanning
        self.excluded_dirs = {
            '__pycache__', '.git', '.ipynb_checkpoints', 
            'node_modules', '.vscode', '.idea', 'venv', 
            'env', '.env', 'logs'
        }
        
        self.excluded_files = {
            '.DS_Store', 'Thumbs.db', '*.pyc', '*.pyo',
            '*.log', '*.tmp', '*.swp', '*.bak'
        }
        
        # File extensions to include (if None, include all)
        self.included_extensions = {
            '.py', '.js', '.ts', '.html', '.css', '.json', 
            '.yaml', '.yml', '.md', '.txt', '.sh', '.sql',
            '.ipynb', '.csv', '.xml', '.ini', '.cfg', '.conf'
        }
    
    def calculate_md5(self, file_path: Path) -> str:
        """
        Calculate MD5 hash of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            MD5 hash as hexadecimal string
        """
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except (IOError, OSError) as e:
            print(f"Warning: Could not read {file_path}: {e}")
            return "ERROR_READING_FILE"
    
    def should_include_file(self, file_path: Path) -> bool:
        """
        Determine if a file should be included in the audit.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file should be included
        """
        # Check if file is in excluded files
        if file_path.name in self.excluded_files:
            return False
        
        # Check file extension
        if self.included_extensions:
            return file_path.suffix.lower() in self.included_extensions
        
        # Include all files if no extension filter is set
        return True
    
    def scan_directory(self) -> Dict[str, str]:
        """
        Scan directory and calculate MD5 hashes for all relevant files.
        
        Returns:
            Dictionary mapping relative file paths to MD5 hashes
        """
        file_hashes = {}
        
        for root, dirs, files in os.walk(self.root_dir):
            # Remove excluded directories from the search
            dirs[:] = [d for d in dirs if d not in self.excluded_dirs]
            
            for file in files:
                file_path = Path(root) / file
                
                # Skip if file should not be included
                if not self.should_include_file(file_path):
                    continue
                
                # Calculate relative path from root directory
                try:
                    rel_path = file_path.relative_to(self.root_dir)
                    md5_hash = self.calculate_md5(file_path)
                    file_hashes[str(rel_path)] = md5_hash
                except ValueError:
                    # Skip if file is outside root directory
                    continue
        
        return file_hashes
    
    def load_previous_state(self) -> Dict[str, str]:
        """
        Load previous file state from JSON file.
        
        Returns:
            Dictionary of previous file hashes, empty if file doesn't exist
        """
        if not self.state_file.exists():
            return {}
        
        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load previous state: {e}")
            return {}
    
    def save_current_state(self, file_hashes: Dict[str, str]) -> None:
        """
        Save current file state to JSON file.
        
        Args:
            file_hashes: Dictionary mapping file paths to MD5 hashes
        """
        try:
            with open(self.state_file, 'w') as f:
                json.dump(file_hashes, f, indent=2, sort_keys=True)
        except IOError as e:
            print(f"Warning: Could not save current state: {e}")
    
    def detect_changes(self, current_hashes: Dict[str, str], 
                      previous_hashes: Dict[str, str]) -> Tuple[Set[str], Set[str], Set[str]]:
        """
        Detect file changes between current and previous state.
        
        Args:
            current_hashes: Current file hashes
            previous_hashes: Previous file hashes
            
        Returns:
            Tuple of (new_files, modified_files, deleted_files)
        """
        current_files = set(current_hashes.keys())
        previous_files = set(previous_hashes.keys())
        
        new_files = current_files - previous_files
        deleted_files = previous_files - current_files
        
        # Find modified files (files that exist in both but have different hashes)
        common_files = current_files & previous_files
        modified_files = {
            file for file in common_files 
            if current_hashes[file] != previous_hashes[file]
        }
        
        return new_files, modified_files, deleted_files
    
    def generate_documentation(self, changed_files: Set[str], change_type: str) -> List[Path]:
        """
        Generate documentation for changed files.
        
        Args:
            changed_files: Set of file paths that changed
            change_type: Type of change (NEW, MODIFIED)
            
        Returns:
            List of created README file paths
        """
        created_readmes = []
        
        if not self.auto_document:
            return created_readmes
        
        for file_path_str in changed_files:
            file_path = self.root_dir / file_path_str
            
            # Skip readme files themselves to avoid recursion
            if file_path_str.startswith('readme/'):
                continue
            
            # Skip certain file types that don't need documentation
            if file_path.suffix.lower() in ['.log', '.json', '.csv']:
                continue
            
            try:
                readme_path = self.doc_generator.create_or_update_readme(file_path, change_type)
                if readme_path:
                    created_readmes.append(readme_path)
                    print(f"  📝 Generated documentation: {readme_path}")
            except Exception as e:
                print(f"  ❌ Failed to generate docs for {file_path}: {e}")
        
        return created_readmes
    
    def write_audit_log(self, file_hashes: Dict[str, str], 
                       changes: Optional[Tuple[Set[str], Set[str], Set[str]]] = None) -> None:
        """
        Write audit log entries for files.
        
        Args:
            file_hashes: Dictionary mapping file paths to MD5 hashes
            changes: Optional tuple of (new_files, modified_files, deleted_files)
        """
        timestamp = datetime.datetime.now().isoformat()
        
        # Create audit log file if it doesn't exist
        if not self.audit_log_file.exists():
            with open(self.audit_log_file, 'w') as f:
                f.write("# File Audit Log\n")
                f.write("# Format: TIMESTAMP | FILE_PATH | MD5_HASH | STATUS\n")
                f.write("# Status: NEW, MODIFIED, UNCHANGED, DELETED\n\n")
        
        with open(self.audit_log_file, 'a') as f:
            if changes:
                new_files, modified_files, deleted_files = changes
                
                # Log deleted files
                for file_path in deleted_files:
                    f.write(f"{timestamp} | {file_path} | DELETED | DELETED\n")
                
                # Log all current files with their status
                for file_path, md5_hash in sorted(file_hashes.items()):
                    if file_path in new_files:
                        status = "NEW"
                    elif file_path in modified_files:
                        status = "MODIFIED"
                    else:
                        status = "UNCHANGED"
                    
                    f.write(f"{timestamp} | {file_path} | {md5_hash} | {status}\n")
            else:
                # Initial scan - log all files as NEW
                for file_path, md5_hash in sorted(file_hashes.items()):
                    f.write(f"{timestamp} | {file_path} | {md5_hash} | INITIAL\n")
    
    def run_audit(self, verbose: bool = True) -> Dict[str, str]:
        """
        Run a complete audit scan and update logs.
        
        Args:
            verbose: Whether to print detailed output
            
        Returns:
            Dictionary of current file hashes
        """
        if verbose:
            print(f"Starting file audit scan in: {self.root_dir}")
        
        # Scan current directory
        current_hashes = self.scan_directory()
        
        if verbose:
            print(f"Scanned {len(current_hashes)} files")
        
        # Load previous state
        previous_hashes = self.load_previous_state()
        
        # Detect changes if we have previous state
        if previous_hashes:
            changes = self.detect_changes(current_hashes, previous_hashes)
            new_files, modified_files, deleted_files = changes
            
            if verbose:
                print(f"Changes detected:")
                print(f"  New files: {len(new_files)}")
                print(f"  Modified files: {len(modified_files)}")
                print(f"  Deleted files: {len(deleted_files)}")
                
                if new_files:
                    print("  New files:", ", ".join(sorted(new_files)))
                if modified_files:
                    print("  Modified files:", ", ".join(sorted(modified_files)))
                if deleted_files:
                    print("  Deleted files:", ", ".join(sorted(deleted_files)))
            
            # Generate documentation for changed files
            if self.auto_document and (new_files or modified_files):
                if verbose:
                    print("\n📚 Generating documentation for changed files...")
                
                # Generate docs for new files
                if new_files:
                    self.generate_documentation(new_files, "NEW")
                
                # Generate docs for modified files
                if modified_files:
                    self.generate_documentation(modified_files, "MODIFIED")
            
            # Write audit log with changes
            self.write_audit_log(current_hashes, changes)
        else:
            if verbose:
                print("No previous state found. Creating initial audit log.")
            # Initial scan
            self.write_audit_log(current_hashes)
        
        # Save current state
        self.save_current_state(current_hashes)
        
        if verbose:
            print(f"Audit complete. Log written to: {self.audit_log_file}")
        
        return current_hashes
    
    def get_file_status(self, file_path: str) -> Optional[Dict]:
        """
        Get the current status of a specific file.
        
        Args:
            file_path: Relative path to the file
            
        Returns:
            Dictionary with file information or None if not found
        """
        current_hashes = self.scan_directory()
        
        if file_path in current_hashes:
            return {
                'path': file_path,
                'md5_hash': current_hashes[file_path],
                'exists': True,
                'last_scanned': datetime.datetime.now().isoformat()
            }
        
        return None


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description='File Audit Logger - Track file changes with MD5 hashes')
    parser.add_argument('--dir', '-d', default='.', help='Directory to scan (default: current directory)')
    parser.add_argument('--log-file', '-l', default='file_audit.log', help='Audit log file path')
    parser.add_argument('--state-file', '-s', default='file_audit_state.json', help='State file path')
    parser.add_argument('--quiet', '-q', action='store_true', help='Suppress verbose output')
    parser.add_argument('--check-file', '-c', help='Check status of specific file')
    parser.add_argument('--no-docs', action='store_true', help='Disable automatic documentation generation')
    
    args = parser.parse_args()
    
    # Create audit logger
    logger = FileAuditLogger(
        root_dir=args.dir,
        audit_log_file=args.log_file,
        state_file=args.state_file,
        auto_document=not args.no_docs
    )
    
    if args.check_file:
        # Check specific file
        status = logger.get_file_status(args.check_file)
        if status:
            print(f"File: {status['path']}")
            print(f"MD5 Hash: {status['md5_hash']}")
            print(f"Last Scanned: {status['last_scanned']}")
        else:
            print(f"File not found: {args.check_file}")
    else:
        # Run full audit
        logger.run_audit(verbose=not args.quiet)


if __name__ == "__main__":
    main() 
