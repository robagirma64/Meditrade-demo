#!/usr/bin/env python3
"""
Add sample medicines to Blue Pharma database
This script adds comprehensive medicine data with proper categories
"""

import sqlite3
from datetime import datetime, date
import random

def add_sample_medicines():
    """Add sample medicines to the database"""
    conn = sqlite3.connect('blue_pharma_v2.db')
    cursor = conn.cursor()
    
    # Sample medicines with categories
    medicines = [
        # Analgesics (Pain Relief)
        ("Paracetamol 500mg", "BTH001", "2024-01-15", "2026-01-15", "Tablet", "Analgesics", 25.50, 150),
        ("Ibuprofen 400mg", "BTH002", "2024-02-10", "2026-02-10", "Tablet", "Analgesics", 35.00, 120),
        ("Aspirin 300mg", "BTH003", "2024-01-20", "2026-01-20", "Tablet", "Analgesics", 20.00, 200),
        ("Acetaminophen 650mg", "BTH004", "2024-03-05", "2026-03-05", "Capsule", "Analgesics", 30.00, 80),
        ("Diclofenac 50mg", "BTH005", "2024-02-15", "2026-02-15", "Tablet", "Analgesics", 45.00, 90),
        
        # Antibiotics
        ("Amoxicillin 500mg", "BTH006", "2024-02-20", "2026-02-20", "Capsule", "Antibiotics", 65.00, 75),
        ("Azithromycin 250mg", "BTH007", "2024-01-30", "2026-01-30", "Tablet", "Antibiotics", 120.00, 50),
        ("Ciprofloxacin 500mg", "BTH008", "2024-03-01", "2026-03-01", "Tablet", "Antibiotics", 85.00, 60),
        ("Penicillin V 250mg", "BTH009", "2024-02-25", "2026-02-25", "Tablet", "Antibiotics", 45.00, 40),
        ("Cephalexin 500mg", "BTH010", "2024-01-25", "2026-01-25", "Capsule", "Antibiotics", 95.00, 35),
        
        # Cardiovascular
        ("Amlodipine 5mg", "BTH011", "2024-01-10", "2026-01-10", "Tablet", "Cardiovascular", 55.00, 100),
        ("Metoprolol 50mg", "BTH012", "2024-02-05", "2026-02-05", "Tablet", "Cardiovascular", 70.00, 85),
        ("Lisinopril 10mg", "BTH013", "2024-01-18", "2026-01-18", "Tablet", "Cardiovascular", 60.00, 70),
        ("Atenolol 50mg", "BTH014", "2024-03-10", "2026-03-10", "Tablet", "Cardiovascular", 48.00, 65),
        ("Losartan 50mg", "BTH015", "2024-02-12", "2026-02-12", "Tablet", "Cardiovascular", 75.00, 55),
        
        # Respiratory
        ("Salbutamol Inhaler", "BTH016", "2024-01-28", "2026-01-28", "Inhaler", "Respiratory", 180.00, 30),
        ("Cough Syrup", "BTH017", "2024-02-18", "2025-02-18", "Syrup", "Respiratory", 65.00, 45),
        ("Loratadine 10mg", "BTH018", "2024-01-22", "2026-01-22", "Tablet", "Respiratory", 38.00, 110),
        ("Cetirizine 10mg", "BTH019", "2024-03-02", "2026-03-02", "Tablet", "Respiratory", 42.00, 95),
        ("Prednisolone 5mg", "BTH020", "2024-02-08", "2026-02-08", "Tablet", "Respiratory", 85.00, 40),
        
        # Neurological
        ("Diazepam 5mg", "BTH021", "2024-01-12", "2026-01-12", "Tablet", "Neurological", 95.00, 25),
        ("Gabapentin 300mg", "BTH022", "2024-02-22", "2026-02-22", "Capsule", "Neurological", 125.00, 35),
        ("Carbamazepine 200mg", "BTH023", "2024-01-16", "2026-01-16", "Tablet", "Neurological", 110.00, 20),
        ("Phenytoin 100mg", "BTH024", "2024-03-08", "2026-03-08", "Capsule", "Neurological", 90.00, 30),
        
        # Anti-infective
        ("Metronidazole 400mg", "BTH025", "2024-02-14", "2026-02-14", "Tablet", "Anti-infective", 55.00, 80),
        ("Fluconazole 150mg", "BTH026", "2024-01-26", "2026-01-26", "Capsule", "Anti-infective", 185.00, 25),
        ("Acyclovir 400mg", "BTH027", "2024-03-05", "2026-03-05", "Tablet", "Anti-infective", 145.00, 15),
        
        # Vitamins & Supplements
        ("Vitamin C 500mg", "BTH028", "2024-01-08", "2026-01-08", "Tablet", "Vitamins & Supplements", 25.00, 200),
        ("Vitamin D3 1000IU", "BTH029", "2024-02-28", "2026-02-28", "Capsule", "Vitamins & Supplements", 35.00, 180),
        ("Calcium Carbonate 600mg", "BTH030", "2024-01-14", "2026-01-14", "Tablet", "Vitamins & Supplements", 45.00, 150),
        ("Iron Sulfate 325mg", "BTH031", "2024-03-12", "2026-03-12", "Tablet", "Vitamins & Supplements", 30.00, 120),
        ("Folic Acid 5mg", "BTH032", "2024-02-06", "2026-02-06", "Tablet", "Vitamins & Supplements", 20.00, 160),
        ("Multivitamin Complex", "BTH033", "2024-01-04", "2026-01-04", "Tablet", "Vitamins & Supplements", 85.00, 90),
        
        # Other Medicines
        ("Omeprazole 20mg", "BTH034", "2024-02-01", "2026-02-01", "Capsule", "Other Medicines", 75.00, 85),
        ("Simethicone 40mg", "BTH035", "2024-01-19", "2026-01-19", "Tablet", "Other Medicines", 35.00, 110),
        ("Loperamide 2mg", "BTH036", "2024-03-15", "2026-03-15", "Tablet", "Other Medicines", 45.00, 70),
        ("Hydrocortisone Cream 1%", "BTH037", "2024-02-11", "2025-02-11", "Cream", "Other Medicines", 95.00, 40),
        ("Eye Drops", "BTH038", "2024-01-23", "2025-01-23", "Drops", "Other Medicines", 125.00, 35),
        ("Antacid Tablets", "BTH039", "2024-03-07", "2026-03-07", "Tablet", "Other Medicines", 28.00, 130),
    ]
    
    print("🔄 Adding sample medicines to database...")
    
    try:
        for medicine in medicines:
            cursor.execute('''
                INSERT INTO medicines (name, batch_number, manufacturing_date, expiring_date, 
                                     dosage_form, therapeutic_category, price, stock_quantity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', medicine)
        
        conn.commit()
        print(f"✅ Successfully added {len(medicines)} medicines to the database")
        
        # Print summary by category
        cursor.execute('''
            SELECT therapeutic_category, COUNT(*) as count, SUM(stock_quantity) as total_stock
            FROM medicines 
            GROUP BY therapeutic_category 
            ORDER BY count DESC
        ''')
        
        print("\n📊 Medicine Categories Summary:")
        print("=" * 50)
        for row in cursor.fetchall():
            category, count, total_stock = row
            print(f"• {category}: {count} medicines, {total_stock} units")
        
        cursor.execute('SELECT COUNT(*) FROM medicines')
        total_medicines = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(stock_quantity) FROM medicines')
        total_stock = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(price * stock_quantity) FROM medicines')
        total_value = cursor.fetchone()[0]
        
        print("=" * 50)
        print(f"📈 Total Medicines: {total_medicines}")
        print(f"📦 Total Stock Units: {total_stock}")
        print(f"💰 Total Inventory Value: {total_value:.2f} ETB")
        
    except Exception as e:
        print(f"❌ Error adding medicines: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    add_sample_medicines()
