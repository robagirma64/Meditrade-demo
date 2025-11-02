#!/usr/bin/env python3
"""
Medicine Excel Template Generator
Creates a template Excel file for bulk medicine uploads
"""

import pandas as pd
from datetime import datetime, timedelta
import os

def create_medicine_template():
    """Create an Excel template with sample medicine data"""
    
    # Sample data with correct column names
    sample_data = [
        {
            'name': 'Paracetamol 500mg',
            'therapeutic_category': 'Analgesic',
            'manufacturing_date': '2024-01-15',
            'expiring_date': '2026-01-15', 
            'dosage_form': 'Tablet',
            'price': 5.50,
            'stock_quantity': 100
        },
        {
            'name': 'Amoxicillin 250mg',
            'therapeutic_category': 'Antibiotic',
            'manufacturing_date': '2024-02-10',
            'expiring_date': '2027-02-10',
            'dosage_form': 'Capsule',
            'price': 8.75,
            'stock_quantity': 75
        },
        {
            'name': 'Ibuprofen 400mg',
            'therapeutic_category': 'Anti-inflammatory',
            'manufacturing_date': '2024-03-05',
            'expiring_date': '2026-03-05',
            'dosage_form': 'Tablet',
            'price': 6.25,
            'stock_quantity': 150
        },
        {
            'name': 'Cough Syrup 100ml',
            'therapeutic_category': 'Respiratory',
            'manufacturing_date': '2024-01-20',
            'expiring_date': '2025-01-20',
            'dosage_form': 'Syrup',
            'price': 12.00,
            'stock_quantity': 50
        },
        {
            'name': 'Vitamin C 1000mg',
            'therapeutic_category': 'Supplement',
            'manufacturing_date': '2024-04-01',
            'expiring_date': '2026-04-01',
            'dosage_form': 'Tablet',
            'price': 15.30,
            'stock_quantity': 200
        }
    ]
    
    # Create DataFrame
    df = pd.DataFrame(sample_data)
    
    # Save to Excel
    filename = 'Medicine_Upload_Template.xlsx'
    df.to_excel(filename, index=False)
    
    print(f"✅ Excel template created: {filename}")
    print("\n📋 Column Requirements:")
    print("1. name - Medicine name (required)")
    print("2. therapeutic_category - Category like 'Analgesic', 'Antibiotic', etc.")
    print("3. manufacturing_date - Format: YYYY-MM-DD")
    print("4. expiring_date - Format: YYYY-MM-DD") 
    print("5. dosage_form - Form like 'Tablet', 'Capsule', 'Syrup', etc.")
    print("6. price - Price in Ethiopian Birr (ETB)")
    print("7. stock_quantity - Number of units in stock")
    print("\n🎯 Tips for successful upload:")
    print("- Make sure all required columns are present")
    print("- Use proper date format (YYYY-MM-DD)")
    print("- Price should be a number (no currency symbols)")
    print("- Stock quantity should be a whole number")
    print("- Save as .xlsx format")
    
    return filename

if __name__ == "__main__":
    create_medicine_template()