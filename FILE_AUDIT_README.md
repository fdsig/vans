# File Audit System

A comprehensive file change tracking system using MD5 hashing to create an audit log of all file modifications in the repository. **Now includes automatic documentation generation for changed files!**

## Overview

This system creates an audit trail for all file changes in the directory structure, allowing future agents and developers to understand what files have been modified, added, or deleted over time. When files change, the system automatically generates or updates corresponding README files in the `readme/` directory.

## Output Format

The audit log follows this format:
```
TIMESTAMP | FILE_PATH | MD5_HASH | STATUS
```

Where:
- **TIMESTAMP**: ISO format datetime when the scan was performed
- **FILE_PATH**: Relative path to the file from the project root
- **MD5_HASH**: 32-character hexadecimal MD5 hash of the file contents
- **STATUS**: One of INITIAL, NEW, MODIFIED, UNCHANGED, DELETED

## Files Created

The system creates two main files:

1. **`file_audit.log`** - The main audit log with timestamped entries
2. **`file_audit_state.json`** - Current state file (JSON) used for change detection

## 🆕 Automatic Documentation Generation

When files are added or modified, the system automatically:

- **Analyzes the file** to extract key information (functions, classes, imports for Python files)
- **Creates README files** in the `readme/` directory named `README_filename_ext.md`
- **Updates documentation** when files are modified
- **Provides structured information** including purpose, usage, and file analysis

### Supported File Types for Documentation:

- **Python files** (`.py`) - Extracts functions, classes, imports, and docstrings
- **Shell scripts** (`.sh`, `.bash`) - Extracts comments and usage information
- **Configuration files** (`.json`, `.yaml`, `.yml`) - Basic file analysis
- **Markdown files** (`.md`) - Extracts titles and structure
- **Generic files** - Basic file information and size

## Usage

### Quick Usage
```bash
python3 audit_files.py
```

### Advanced Usage
```bash
# Full feature set
python3 file_audit_logger.py [options]

# Options:
--dir, -d          # Directory to scan (default: current)
--log-file, -l     # Audit log file path (default: file_audit.log)
--state-file, -s   # State file path (default: file_audit_state.json)
--quiet, -q        # Suppress verbose output
--check-file, -c   # Check status of specific file
--no-docs          # Disable automatic documentation generation
```

### Examples

1. **Run audit with documentation generation:**
   ```bash
   python3 audit_files.py
   ```

2. **Run audit without documentation generation:**
   ```bash
   python3 file_audit_logger.py --no-docs
   ```

3. **Check specific file status:**
   ```bash
   python3 file_audit_logger.py --check-file scrapers/__init__.py
   ```

4. **Quiet mode (minimal output):**
   ```bash
   python3 file_audit_logger.py --quiet
   ```

## What Gets Tracked

### Included Files
- Python files (`.py`)
- JavaScript/TypeScript (`.js`, `.ts`)
- Web files (`.html`, `.css`)
- Configuration files (`.json`, `.yaml`, `.yml`, `.ini`, `.cfg`, `.conf`)
- Documentation (`.md`, `.txt`)
- Shell scripts (`.sh`)
- Database files (`.sql`)
- Jupyter notebooks (`.ipynb`)
- Data files (`.csv`, `.xml`)

### Excluded Directories
- `__pycache__`
- `.git`
- `.ipynb_checkpoints`
- `node_modules`
- `.vscode`, `.idea`
- `venv`, `env`, `.env`
- `logs`

### Excluded Files
- `.DS_Store`, `Thumbs.db`
- Compiled Python (`.pyc`, `.pyo`)
- Log files (`.log`)
- Temporary files (`.tmp`, `.swp`, `.bak`)

## Change Detection

The system automatically detects:

- **NEW**: Files that didn't exist in the previous scan
- **MODIFIED**: Files that exist but have different MD5 hashes
- **DELETED**: Files that existed previously but are now missing
- **UNCHANGED**: Files with identical MD5 hashes

## Example Output

### Initial Scan
```
2025-05-26T12:56:46.562369 | scrapers/__init__.py | 5e9e470cf3564f58101ded9a60e37477 | INITIAL
2025-05-26T12:56:46.562369 | get_vans.py | 097caacd3ff5a8f72e11f592c14bdd05 | INITIAL
```

### Subsequent Scans with Documentation
```
2025-05-26T13:04:40.053484 | test_file.py | 578763b36e92baefd382bf303c606c18 | NEW

📚 Generating documentation for changed files...
  📝 Generated documentation: readme/README_test_file_py.md
```

## Generated Documentation Structure

Each generated README file includes:

### For Python Files:
- **File overview** and purpose
- **Functions list** (up to 10 main functions)
- **Classes list** (detected classes)
- **Key imports** (first 5 import statements)
- **Module docstring** (if available)
- **File analysis** (size, type, last modified)
- **Audit information** (when and why generated)

### For Shell Scripts:
- **Usage instructions** with chmod and execution examples
- **Script description** from comments
- **File analysis**

### For Configuration Files:
- **Configuration overview**
- **File structure information**
- **Usage guidelines**

## Integration

### For Future Agents
Future AI agents working on this repository can:

1. Run `python3 audit_files.py` to see what changed
2. Check `file_audit.log` to understand the modification history
3. Use `--check-file` to verify specific file integrity
4. **Browse `readme/` directory for automatically generated documentation**
5. **Get instant understanding of new/modified files from generated docs**

### For Development Teams
- Run before/after major changes to track modifications
- Include in CI/CD pipelines for change tracking
- Use for security auditing and compliance
- **Automatically maintain up-to-date documentation**
- **Onboard new team members with generated file documentation**

## Programmatic Usage

```python
from file_audit_logger import FileAuditLogger

# Create logger instance with documentation generation
logger = FileAuditLogger(auto_document=True)

# Run audit and get results
file_hashes = logger.run_audit()

# Create logger without documentation generation
logger_no_docs = FileAuditLogger(auto_document=False)
file_hashes = logger_no_docs.run_audit()

# Check specific file
status = logger.get_file_status('scrapers/__init__.py')
if status:
    print(f"File: {status['path']}")
    print(f"MD5: {status['md5_hash']}")
```

## Security Considerations

- MD5 is used for change detection, not cryptographic security
- The audit log shows file modifications but not content changes
- Sensitive files should be excluded via the configuration
- Log files should be protected with appropriate file permissions
- **Generated documentation may expose file structure - review before sharing**

## Troubleshooting

### Common Issues

1. **Permission Errors**: Ensure read access to all files being scanned
2. **Large Files**: The system handles large files but may be slow
3. **Binary Files**: Only text-based file extensions are included by default
4. **Documentation Generation Fails**: Check file encoding and permissions

### Performance Tips

- Exclude large directories with `--dir` parameter
- Use `--quiet` mode for automated runs
- The state file enables fast change detection
- Use `--no-docs` flag if documentation generation is not needed

## Future Enhancements

Potential improvements:
- SHA-256 hashing option for better security
- Exclude patterns configuration file
- Integration with Git for commit tracking
- Database storage option for large repositories
- Web interface for audit log viewing
- **Custom documentation templates for different file types**
- **Integration with documentation systems like Sphinx or MkDocs**
- **AI-powered documentation enhancement based on code analysis**
