#!/usr/bin/env python3
"""
Database Migration Script
========================

This script migrates the postcode_intelligence.db database to the new schema
expected by the CarGurus scraper.

Old schema:
- postcode, total_listings, total_scrapes, success_rate, last_updated

New schema:
- postcode, total_attempts, total_listings, avg_listings_per_page, last_updated
"""

import sqlite3
import sys
from pathlib import Path

def migrate_database(db_path: str = "data/postcode_intelligence.db"):
    """Migrate database to new schema"""
    
    if not Path(db_path).exists():
        print(f"❌ Database file {db_path} not found!")
        return False
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print('🔄 Migrating database schema...')

        # Check current schema
        cursor.execute('PRAGMA table_info(postcode_success)')
        columns = [col[1] for col in cursor.fetchall()]
        print(f'Current columns: {columns}')

        # Add missing columns if they don't exist
        if 'avg_listings_per_page' not in columns:
            print('➕ Adding avg_listings_per_page column...')
            cursor.execute('ALTER TABLE postcode_success ADD COLUMN avg_listings_per_page REAL DEFAULT 0')
            
        if 'total_attempts' not in columns:
            print('➕ Adding total_attempts column...')
            cursor.execute('ALTER TABLE postcode_success ADD COLUMN total_attempts INTEGER DEFAULT 0')
            
            # Migrate data: copy total_scrapes to total_attempts if it exists
            if 'total_scrapes' in columns:
                print('📊 Migrating total_scrapes to total_attempts...')
                cursor.execute('UPDATE postcode_success SET total_attempts = total_scrapes')

        # Calculate avg_listings_per_page from existing data
        print('🧮 Calculating avg_listings_per_page from existing data...')
        cursor.execute('''
            UPDATE postcode_success 
            SET avg_listings_per_page = CASE 
                WHEN total_attempts > 0 THEN CAST(total_listings AS REAL) / total_attempts 
                ELSE total_listings 
            END
            WHERE avg_listings_per_page = 0 OR avg_listings_per_page IS NULL
        ''')

        # Commit changes
        conn.commit()

        # Verify the migration
        cursor.execute('PRAGMA table_info(postcode_success)')
        columns = cursor.fetchall()
        print('✅ Updated columns:')
        for col in columns:
            print(f'  {col[1]} ({col[2]})')

        # Show sample data
        cursor.execute('SELECT * FROM postcode_success LIMIT 3')
        rows = cursor.fetchall()
        if rows:
            print('📊 Sample data:')
            for row in rows:
                print(f'  {row}')
        else:
            print('📊 No existing data found')

        conn.close()
        print('✅ Database migration completed successfully!')
        return True
        
    except Exception as e:
        print(f'❌ Migration failed: {e}')
        return False

if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "data/postcode_intelligence.db"
    success = migrate_database(db_path)
    sys.exit(0 if success else 1) 
