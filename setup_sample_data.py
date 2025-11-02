# -*- coding: utf-8 -*-
"""
Blue Pharma Bot - Sample Data Setup
Creates sample medicines and test data for demonstration
"""

import sqlite3
import json
from datetime import datetime

def setup_sample_data():
    """Setup sample data for testing the bot"""
    
    print("🏥 Setting up Blue Pharma Bot sample data...")
    
    # Connect to database
    conn = sqlite3.connect('blue_pharma_v2.db')
    cursor = conn.cursor()
    
    # Execute schema first
    print("📋 Creating database schema...")
    with open('database_schema.sql', 'r', encoding='utf-8') as f:
        schema_sql = f.read()
        cursor.executescript(schema_sql)
    
    print("✅ Database schema created successfully!")
    
    # Sample medicines data
    sample_medicines = [
        # Pain Relief
        ("Paracetamol", "Acetaminophen", "Panadol", "Pain Relief", "Pain reliever and fever reducer", "500mg", "Tablet", "GSK", 15.50, 100, 10, False),
        ("Ibuprofen", "Ibuprofen", "Brufen", "Pain Relief", "Anti-inflammatory pain relief", "400mg", "Tablet", "Abbott", 22.00, 75, 15, False),
        ("Aspirin", "Acetylsalicylic acid", "Disprin", "Pain Relief", "Pain relief and blood thinner", "300mg", "Tablet", "Bayer", 18.75, 60, 10, False),
        
        # Antibiotics
        ("Amoxicillin", "Amoxicillin", "Amoxil", "Antibiotics", "Broad spectrum antibiotic", "250mg", "Capsule", "Pfizer", 45.00, 40, 5, True),
        ("Azithromycin", "Azithromycin", "Zithromax", "Antibiotics", "Macrolide antibiotic", "500mg", "Tablet", "Pfizer", 120.00, 25, 5, True),
        ("Ciprofloxacin", "Ciprofloxacin", "Cipro", "Antibiotics", "Fluoroquinolone antibiotic", "500mg", "Tablet", "Bayer", 85.50, 30, 5, True),
        
        # Cold & Flu
        ("Cough Syrup", "Dextromethorphan", "Robitussin", "Cold & Flu", "Cough suppressant", "15mg/5ml", "Syrup", "GSK", 35.00, 50, 8, False),
        ("Loratadine", "Loratadine", "Claritin", "Cold & Flu", "Antihistamine for allergies", "10mg", "Tablet", "Bayer", 28.50, 65, 10, False),
        ("Pseudoephedrine", "Pseudoephedrine", "Sudafed", "Cold & Flu", "Nasal decongestant", "30mg", "Tablet", "Johnson & Johnson", 32.00, 45, 8, False),
        
        # Vitamins
        ("Vitamin C", "Ascorbic Acid", "Redoxon", "Vitamins", "Immune system booster", "1000mg", "Tablet", "Bayer", 25.00, 80, 15, False),
        ("Multivitamin", "Multiple Vitamins", "Centrum", "Vitamins", "Complete daily nutrition", "Daily dose", "Tablet", "Pfizer", 55.00, 70, 12, False),
        ("Vitamin D3", "Cholecalciferol", "D-Vital", "Vitamins", "Bone health support", "2000IU", "Tablet", "GSK", 38.00, 55, 10, False),
        
        # Digestive
        ("Omeprazole", "Omeprazole", "Losec", "Digestive", "Proton pump inhibitor", "20mg", "Capsule", "AstraZeneca", 65.00, 35, 8, False),
        ("Antacid", "Aluminum/Magnesium", "Maalox", "Digestive", "Stomach acid neutralizer", "400mg", "Tablet", "Sanofi", 20.00, 90, 15, False),
        ("Loperamide", "Loperamide", "Imodium", "Digestive", "Anti-diarrheal medication", "2mg", "Capsule", "Johnson & Johnson", 42.50, 40, 8, False),
        
        # Cardiovascular (Prescription required)
        ("Amlodipine", "Amlodipine", "Norvasc", "Cardiovascular", "Calcium channel blocker", "10mg", "Tablet", "Pfizer", 95.00, 25, 5, True),
        ("Atorvastatin", "Atorvastatin", "Lipitor", "Cardiovascular", "Cholesterol medication", "20mg", "Tablet", "Pfizer", 125.00, 20, 5, True),
        
        # Women's Health
        ("Folic Acid", "Folic Acid", "Folacin", "Women's Health", "Essential for pregnancy", "5mg", "Tablet", "GSK", 30.00, 60, 12, False),
        ("Iron Supplement", "Ferrous Sulfate", "Feroglobin", "Women's Health", "Iron deficiency treatment", "200mg", "Tablet", "Vitabiotics", 48.00, 45, 10, False),
        
        # Diabetes
        ("Metformin", "Metformin HCl", "Glucophage", "Diabetes", "Type 2 diabetes medication", "500mg", "Tablet", "Merck", 85.00, 30, 5, True),
        ("Glibenclamide", "Glibenclamide", "Daonil", "Diabetes", "Blood sugar control", "5mg", "Tablet", "Sanofi", 72.00, 25, 5, True)
    ]
    
    print("💊 Adding sample medicines...")
    for medicine in sample_medicines:
        cursor.execute("""
            INSERT INTO medicines 
            (name, generic_name, brand_name, category, description, dosage, form, 
             manufacturer, retail_price, retail_stock, minimum_stock, requires_prescription)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, medicine)
    
    print(f"✅ Added {len(sample_medicines)} sample medicines")
    
    # Create a sample staff user
    cursor.execute("""
        INSERT INTO users (telegram_id, first_name, last_name, user_type)
        VALUES (?, ?, ?, ?)
    """, (999999999, "Admin", "User", "staff"))
    
    staff_user_id = cursor.lastrowid
    
    cursor.execute("""
        INSERT INTO staff_info (user_id, employee_id, department, position, is_admin)
        VALUES (?, ?, ?, ?, ?)
    """, (staff_user_id, "STAFF001", "Administration", "System Administrator", True))
    
    print("👥 Created sample staff user (Telegram ID: 999999999)")
    
    # Update contact info
    cursor.execute("""
        UPDATE contact_info SET 
        phone = '+251-11-555-0123',
        email = 'contact@bluepharma.et',
        address = '123 Pharmacy Street, Addis Ababa, Ethiopia',
        working_hours = '08:00-22:00 Daily',
        emergency_contact = '+251-91-555-0123',
        website = 'www.bluepharma.et'
        WHERE id = 1
    """)
    
    print("📞 Updated contact information")
    
    # Commit changes
    conn.commit()
    conn.close()
    
    print("\n🎉 Sample data setup completed successfully!")
    print("\n📋 **What's been created:**")
    print(f"• {len(sample_medicines)} sample medicines across multiple categories")
    print("• Pain Relief, Antibiotics, Cold & Flu, Vitamins, Digestive, etc.")
    print("• Some medicines require prescription (marked accordingly)")
    print("• Sample staff user for testing admin features")
    print("• Updated contact information")
    
    print("\n🚀 **Ready to test:**")
    print("• Customer: Browse medicines, add to cart, place orders")
    print("• Staff (Telegram ID 999999999): Access bulk operations, manage inventory")
    print("• All conversation flows and interactive features")
    
    print(f"\n▶️  Start the bot with: py bot_v2.py")

if __name__ == "__main__":
    setup_sample_data()
