# File Audit System

A comprehensive file change tracking system using MD5 hashing to create an audit log of all file modifications in the repository.

## Overview

This system creates an audit trail for all file changes in the directory structure, allowing future agents and developers to understand what files have been modified, added, or deleted over time.

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
```

### Examples

1. **Run audit on current directory:**
   ```bash
   python3 audit_files.py
   ```

2. **Run audit with custom log file:**
   ```bash
   python3 file_audit_logger.py --log-file my_audit.log
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

### Subsequent Scans
```
2025-05-26T12:57:31.392366 | test_file_change.py | 578763b36e92baefd382bf303c606c18 | NEW
2025-05-26T12:57:47.024390 | test_file_change.py | 9bf6a93daa6d235b0c6b5042c026e42d | MODIFIED
```

## Integration

### For Future Agents
Future AI agents working on this repository can:

1. Run `python3 audit_files.py` to see what changed
2. Check `file_audit.log` to understand the modification history
3. Use `--check-file` to verify specific file integrity

### For Development Teams
- Run before/after major changes to track modifications
- Include in CI/CD pipelines for change tracking
- Use for security auditing and compliance

## Programmatic Usage

```python
from file_audit_logger import FileAuditLogger

# Create logger instance
logger = FileAuditLogger()

# Run audit and get results
file_hashes = logger.run_audit()

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

## Troubleshooting

### Common Issues

1. **Permission Errors**: Ensure read access to all files being scanned
2. **Large Files**: The system handles large files but may be slow
3. **Binary Files**: Only text-based file extensions are included by default

### Performance Tips

- Exclude large directories with `--dir` parameter
- Use `--quiet` mode for automated runs
- The state file enables fast change detection

## Future Enhancements

Potential improvements:
- SHA-256 hashing option for better security
- Exclude patterns configuration file
- Integration with Git for commit tracking
- Database storage option for large repositories
- Web interface for audit log viewing 
