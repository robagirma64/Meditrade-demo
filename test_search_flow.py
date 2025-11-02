#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to debug the exact search flow and identify where the issue occurs
"""

import sqlite3
import sys
from difflib import SequenceMatcher

class DatabaseManager:
    """Simple version of DatabaseManager for testing"""
    
    def __init__(self, db_name):
        self.db_name = db_name

    def get_connection(self):
        """Creates and returns a database connection."""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn

    def get_medicine_by_name(self, name):
        conn = self.get_connection()
        cursor = conn.cursor()
        print(f"DEBUG: Searching for: '{name}'")
        print(f"DEBUG: SQL query: SELECT * FROM medicines WHERE name LIKE '%{name}%' COLLATE NOCASE AND is_active = 1")
        cursor.execute("SELECT * FROM medicines WHERE name LIKE ? COLLATE NOCASE AND is_active = 1", (f'%{name}%',))
        medicines = cursor.fetchall()
        conn.close()
        result = [dict(med) for med in medicines]
        print(f"DEBUG: get_medicine_by_name returned {len(result)} results")
        return result

    def get_all_medicines(self, limit=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        query = "SELECT * FROM medicines WHERE is_active = 1 ORDER BY name"
        if limit:
            query += f" LIMIT {limit}"
        cursor.execute(query)
        medicines = cursor.fetchall()
        conn.close()
        return [dict(med) for med in medicines]

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

def find_similar_medicines(db, search_term, threshold=0.35, max_results=5):
    """Find medicines with similar names using enhanced fuzzy matching."""
    print(f"DEBUG: find_similar_medicines called with search_term='{search_term}', threshold={threshold}")
    
    all_medicines = db.get_all_medicines()
    print(f"DEBUG: Retrieved {len(all_medicines)} medicines from database")
    similar_medicines = []
    
    # Normalize search term
    search_norm = ' '.join(search_term.lower().replace('_', ' ').split())
    print(f"DEBUG: Normalized search term: '{search_norm}'")
    
    for medicine in all_medicines:
        similarity = calculate_similarity(search_term, medicine['name'])
        
        # Additional boost for very close matches
        med_name_norm = ' '.join(medicine['name'].lower().replace('_', ' ').split())
        
        # Extra boost for cases where search term is a subset of medicine name
        if search_norm in med_name_norm:
            similarity = max(similarity, 0.8)
        
        # Extra boost for exact word matches
        search_words = set(search_norm.split())
        med_words = set(med_name_norm.split())
        if search_words and med_words and search_words.issubset(med_words):
            similarity = max(similarity, 0.9)
        
        if similarity >= threshold:
            medicine['similarity_score'] = similarity
            similar_medicines.append(medicine)
            print(f"DEBUG: '{medicine['name']}' matches with {similarity*100:.1f}% similarity")
    
    # Sort by similarity score (highest first) and return top results
    similar_medicines.sort(key=lambda x: x['similarity_score'], reverse=True)
    result = similar_medicines[:max_results]
    print(f"DEBUG: Returning {len(result)} similar medicines above threshold")
    return result

def test_search_flow():
    """Test the exact search flow that happens in the bot"""
    print("=== TESTING SEARCH FLOW FOR 'med 99' ===")
    
    db = DatabaseManager('blue_pharma_v2.db')
    search_term = "med 99"
    
    # Step 1: Try exact search (this is what db.get_medicine_by_name does)
    print(f"\n--- STEP 1: Exact Search ---")
    medicines = db.get_medicine_by_name(search_term)
    print(f"Exact search results: {len(medicines)} medicines found")
    
    for med in medicines:
        print(f"  - {med['name']} (ID: {med['id']})")
    
    # Step 2: If no exact matches, try fuzzy search
    if not medicines:
        print(f"\n--- STEP 2: Fuzzy Search ---")
        similar_medicines = find_similar_medicines(db, search_term, threshold=0.35, max_results=5)
        
        if similar_medicines:
            print(f"Fuzzy search found {len(similar_medicines)} matches above 35% threshold:")
            for i, medicine in enumerate(similar_medicines, 1):
                similarity_percentage = int(medicine['similarity_score'] * 100)
                print(f"{i}. {medicine['name']} ({similarity_percentage}% match)")
        else:
            print("No fuzzy matches found above 35% threshold")
    else:
        print("Exact matches found, skipping fuzzy search")

def test_get_medicine_by_name_variations():
    """Test different variations of the get_medicine_by_name function"""
    print("\n=== TESTING GET_MEDICINE_BY_NAME VARIATIONS ===")
    
    conn = sqlite3.connect('blue_pharma_v2.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    search_variations = [
        "med 99",
        "Med 99", 
        "med_99",
        "Med_99",
        "99",
        "med"
    ]
    
    for search_term in search_variations:
        print(f"\n--- Testing search term: '{search_term}' ---")
        
        # Test current LIKE query
        cursor.execute("SELECT * FROM medicines WHERE name LIKE ? COLLATE NOCASE AND is_active = 1", (f'%{search_term}%',))
        results = cursor.fetchall()
        print(f"LIKE '%{search_term}%': {len(results)} results")
        for result in results[:3]:  # Show first 3
            print(f"  - {result['name']}")
        
        # Test exact match
        cursor.execute("SELECT * FROM medicines WHERE name = ? COLLATE NOCASE AND is_active = 1", (search_term,))
        exact_results = cursor.fetchall()
        print(f"Exact match '{search_term}': {len(exact_results)} results")
        
        # Test with underscore replacement
        search_normalized = search_term.replace(' ', '_')
        cursor.execute("SELECT * FROM medicines WHERE name LIKE ? COLLATE NOCASE AND is_active = 1", (f'%{search_normalized}%',))
        normalized_results = cursor.fetchall()
        print(f"Normalized LIKE '%{search_normalized}%': {len(normalized_results)} results")
        for result in normalized_results[:3]:  # Show first 3
            print(f"  - {result['name']}")
    
    conn.close()

if __name__ == "__main__":
    test_search_flow()
    test_get_medicine_by_name_variations()
