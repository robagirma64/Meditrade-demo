import sqlite3
import os

# Try both database names
db_names = ['blue_pharma_v2.db', 'database/bluepharma.db']
for db_name in db_names:
    if os.path.exists(db_name):
        print(f'Checking database: {db_name}')
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        
        # Check if contact_settings table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='contact_settings'")
        if cursor.fetchone():
            print('Contact settings table found!')
            cursor.execute('SELECT setting_key, setting_value FROM contact_settings')
            settings = cursor.fetchall()
            for key, value in settings:
                print(f'{key}: {value}')
        else:
            print('Contact settings table not found')
        
        conn.close()
        break
else:
    print('No database files found')