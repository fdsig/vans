#!/usr/bin/env python3
"""
Simple File Audit Runner
========================

Quick script to run file audit logging with automatic documentation generation.
Usage: python audit_files.py
"""

from file_audit_logger import FileAuditLogger

def quick_audit(auto_document=True):
    """Run a quick audit of the current directory with documentation generation."""
    logger = FileAuditLogger(auto_document=auto_document)
    return logger.run_audit()

if __name__ == "__main__":
    print("Running file audit with documentation generation...")
    quick_audit()
    print("Audit complete! Check file_audit.log for results and readme/ for generated docs.") 
