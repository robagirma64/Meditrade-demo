# -*- coding: utf-8 -*-
from database.db_init import DatabaseManager
import sqlite3

def check_database_schema():
    db = DatabaseManager()
    conn = db.get_connection()
    cursor = conn.cursor()

    print('=== CURRENT DATABASE SCHEMA ===')
    cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
    tables = cursor.fetchall()

    for (table_name,) in tables:
        print(f'\n--- Table: {table_name} ---')
        cursor.execute(f'PRAGMA table_info({table_name})')
        columns = cursor.fetchall()
        for col in columns:
            print(f'{col[1]:<20} {col[2]:<15} {"NOT NULL" if col[3] else "NULL":<8} {"PK" if col[5] else "":<3}')

    print('\n=== INDEXES ===')
    cursor.execute('SELECT name, tbl_name, sql FROM sqlite_master WHERE type="index" AND sql IS NOT NULL')
    indexes = cursor.fetchall()
    for idx in indexes:
        print(f'{idx[0]} on {idx[1]}:')
        print(f'  {idx[2]}')

    print('\n=== FOREIGN KEYS ===')
    for (table_name,) in tables:
        cursor.execute(f'PRAGMA foreign_key_list({table_name})')
        fks = cursor.fetchall()
        if fks:
            print(f'{table_name}:')
            for fk in fks:
                print(f'  {fk[3]} -> {fk[2]}.{fk[4]}')

    conn.close()

if __name__ == '__main__':
    check_database_schema()
