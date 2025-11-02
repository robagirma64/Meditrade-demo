#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('blue_pharma_v2.db')
cursor = conn.cursor()

print('=== CURRENT MEDICINES IN DATABASE ===')
cursor.execute('SELECT name, therapeutic_category, price, stock_quantity FROM medicines WHERE is_active = 1 ORDER BY therapeutic_category, name')
medicines = cursor.fetchall()

current_category = None
for medicine in medicines:
    name, category, price, stock = medicine
    if category != current_category:
        print(f'\n📂 {category if category else "Uncategorized"}:')
        current_category = category
    print(f'  • {name} - {price} ETB (Stock: {stock})')

print(f'\n📊 Total medicines: {len(medicines)}')

print('\n=== CATEGORIES ===')
cursor.execute('SELECT DISTINCT therapeutic_category FROM medicines WHERE is_active = 1 AND therapeutic_category IS NOT NULL ORDER BY therapeutic_category')
categories = cursor.fetchall()
for cat in categories:
    print(f'  • {cat[0]}')

print(f'\n📊 Total categories: {len(categories)}')

conn.close()
