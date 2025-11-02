#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug script to examine database content and test fuzzy matching for 'med 99' issue
"""

import sqlite3
import sys
from difflib import SequenceMatcher

def calculate_similarity(a, b):
    """Calculate similarity ratio between two strings with enhanced matching."""
    # Normalize strings: lowercase, replace underscores with spaces, remove extra spaces
    a_norm = ' '.join(a.lower().replace('_', ' ').split())
    b_norm = ' '.join(b.lower().replace('_', ' ').split())
    
    # Primary similarity using SequenceMatcher
    primary_similarity = SequenceMatcher(None, a_norm, b_norm).ratio()
    
    # Secondary check: exact word matching (for cases like "med 99" vs "med_99")
    a_words = set(a_norm.split())
    b_words = set(b_norm.split())
    
    if a_words and b_words:
        # Calculate word overlap ratio
        common_words = a_words.intersection(b_words)
        word_similarity = len(common_words) / max(len(a_words), len(b_words))
        
        # Enhanced matching for partial matches like "med" in "med 99"
        if word_similarity >= 0.5 and primary_similarity < 0.6:
            primary_similarity = max(primary_similarity, word_similarity * 0.85)
        
        # Special boost for numeric patterns (like "99" in "med 99" vs "med_99")
        for word in a_words:
            if word.isdigit():
                for b_word in b_words:
                    if word == b_word:
                        primary_similarity = max(primary_similarity, 0.8)
    
    # Tertiary check: substring matching (one contains the other)
    if a_norm in b_norm or b_norm in a_norm:
        substring_similarity = min(len(a_norm), len(b_norm)) / max(len(a_norm), len(b_norm))
        primary_similarity = max(primary_similarity, substring_similarity * 0.75)
    
    # Special handling for common patterns like "med" + numbers
    if 'med' in a_norm and 'med' in b_norm:
        # Extract numbers from both strings
        import re
        a_nums = re.findall(r'\d+', a_norm)
        b_nums = re.findall(r'\d+', b_norm)
        if a_nums and b_nums and any(num in b_nums for num in a_nums):
            primary_similarity = max(primary_similarity, 0.7)
    
    return primary_similarity

def main():
    print("=== DATABASE CONTENT ANALYSIS ===")
    
    # Connect to database
    try:
        conn = sqlite3.connect('blue_pharma_v2.db')
        cursor = conn.cursor()
        
        # Check if database exists and has data
        cursor.execute("SELECT COUNT(*) FROM medicines WHERE is_active = 1")
        total_count = cursor.fetchone()[0]
        print(f"Total active medicines: {total_count}")
        
        # Get medicines with 'med' in the name
        cursor.execute("SELECT id, name, stock_quantity, price FROM medicines WHERE name LIKE '%med%' COLLATE NOCASE AND is_active = 1")
        med_medicines = cursor.fetchall()
        
        print("\n=== MEDICINES WITH 'MED' IN NAME ===")
        for med in med_medicines:
            print(f"ID: {med[0]}, Name: \"{med[1]}\", Stock: {med[2]}, Price: {med[3]}")
        
        print(f"\nFound {len(med_medicines)} medicines with 'med' in name")
        
        # Get all medicines for broader testing
        cursor.execute("SELECT id, name, stock_quantity, price FROM medicines WHERE is_active = 1 LIMIT 30")
        all_meds = cursor.fetchall()
        
        print("\n=== ALL MEDICINES (first 30) ===")
        for med in all_meds:
            print(f"ID: {med[0]}, Name: \"{med[1]}\", Stock: {med[2]}, Price: {med[3]}")
        
        # Test fuzzy matching specifically for "med 99"
        print("\n=== FUZZY MATCHING TEST FOR 'med 99' ===")
        search_term = "med 99"
        
        cursor.execute("SELECT id, name FROM medicines WHERE is_active = 1")
        all_medicine_names = cursor.fetchall()
        
        matches = []
        for med_id, med_name in all_medicine_names:
            similarity = calculate_similarity(search_term, med_name)
            if similarity >= 0.1:  # Lower threshold for debugging
                matches.append((med_id, med_name, similarity))
        
        # Sort by similarity
        matches.sort(key=lambda x: x[2], reverse=True)
        
        print(f"Search term: '{search_term}'")
        print(f"Threshold: 0.35 (35%)")
        print(f"Total medicines checked: {len(all_medicine_names)}")
        print(f"Matches above 10% similarity: {len(matches)}")
        
        print("\n--- TOP 10 SIMILARITY MATCHES ---")
        for i, (med_id, med_name, similarity) in enumerate(matches[:10]):
            percentage = int(similarity * 100)
            status = "✅" if similarity >= 0.35 else "❌"
            print(f"{status} {i+1}. \"{med_name}\" - {percentage}% similarity")
        
        # Test exact name search
        print(f"\n=== EXACT NAME SEARCH TEST ===")
        cursor.execute("SELECT * FROM medicines WHERE name LIKE ? COLLATE NOCASE AND is_active = 1", (f'%{search_term}%',))
        exact_matches = cursor.fetchall()
        print(f"Exact search results for '{search_term}': {len(exact_matches)} matches")
        for match in exact_matches:
            print(f"  - ID: {match[0]}, Name: \"{match[1]}\"")
        
        conn.close()
        
    except Exception as e:
        print(f"Database error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
