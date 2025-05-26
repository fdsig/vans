#!/bin/bash
# File Audit Cron Script
# Usage: ./cron_audit.sh
# 
# This script can be added to crontab for automated file auditing
# Example crontab entry (run every hour):
# 0 * * * * /path/to/vans/cron_audit.sh

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the script directory
cd "$SCRIPT_DIR"

# Run the audit in quiet mode
python3 file_audit_logger.py --quiet

# Optional: Add timestamp to a separate cron log
echo "$(date): File audit completed" >> cron_audit.log 
