#!/usr/bin/env python3
import sqlite3
from difflib import SequenceMatcher

class DatabaseManager:
    def __init__(self, db_name):
        self.db_name = db_name

    def get_connection(self):
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn

    def get_medicine_by_name(self, name):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM medicines WHERE name LIKE ? COLLATE NOCASE AND is_active = 1", (f'%{name}%',))
        medicines = cursor.fetchall()
        conn.close()
        return [dict(med) for med in medicines]
        
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
    
    print(f"  Comparing: '{a_norm}' vs '{b_norm}'")
    
    # Primary similarity using SequenceMatcher
    primary_similarity = SequenceMatcher(None, a_norm, b_norm).ratio()
    print(f"    Primary similarity: {primary_similarity:.3f}")
    
    # Secondary check: exact word matching (for cases like "med 99" vs "med_99")
    a_words = set(a_norm.split())
    b_words = set(b_norm.split())
    
    if a_words and b_words:
        # Calculate word overlap ratio
        common_words = a_words.intersection(b_words)
        word_similarity = len(common_words) / max(len(a_words), len(b_words))
        print(f"    Word similarity: {word_similarity:.3f} (common words: {common_words})")
        
        # Enhanced matching for partial matches like "med" in "med 99"
        if word_similarity >= 0.5 and primary_similarity < 0.6:
            old_primary = primary_similarity
            primary_similarity = max(primary_similarity, word_similarity * 0.85)
            print(f"    Word boost applied: {old_primary:.3f} -> {primary_similarity:.3f}")
        
        # Special boost for numeric patterns (like "99" in "med 99" vs "med_99")
        for word in a_words:
            if word.isdigit():
                for b_word in b_words:
                    if word == b_word:
                        old_primary = primary_similarity
                        primary_similarity = max(primary_similarity, 0.8)
                        print(f"    Numeric boost applied: {old_primary:.3f} -> {primary_similarity:.3f}")
    
    # Tertiary check: substring matching (one contains the other)
    if a_norm in b_norm or b_norm in a_norm:
        substring_similarity = min(len(a_norm), len(b_norm)) / max(len(a_norm), len(b_norm))
        old_primary = primary_similarity
        primary_similarity = max(primary_similarity, substring_similarity * 0.75)
        print(f"    Substring boost applied: {old_primary:.3f} -> {primary_similarity:.3f}")
    
    # Special handling for common patterns like "med" + numbers
    if 'med' in a_norm and 'med' in b_norm:
        # Extract numbers from both strings
        import re
        a_nums = re.findall(r'\d+', a_norm)
        b_nums = re.findall(r'\d+', b_norm)
        if a_nums and b_nums and any(num in b_nums for num in a_nums):
            old_primary = primary_similarity
            primary_similarity = max(primary_similarity, 0.7)
            print(f"    Med+number boost applied: {old_primary:.3f} -> {primary_similarity:.3f}")
    
    print(f"    Final similarity: {primary_similarity:.3f}")
    return primary_similarity

def find_similar_medicines(db, search_term, threshold=0.35, max_results=5):
    """Find medicines with similar names using enhanced fuzzy matching."""
    all_medicines = db.get_all_medicines()
    similar_medicines = []
    
    print(f"\nSearching for medicines similar to: '{search_term}'")
    print(f"Threshold: {threshold} ({int(threshold*100)}%)")
    print(f"Total medicines in database: {len(all_medicines)}")
    
    # Normalize search term
    search_norm = ' '.join(search_term.lower().replace('_', ' ').split())
    print(f"Normalized search term: '{search_norm}'")
    
    for medicine in all_medicines:
        similarity = calculate_similarity(search_term, medicine['name'])
        
        # Additional boost for very close matches
        med_name_norm = ' '.join(medicine['name'].lower().replace('_', ' ').split())
        
        # Extra boost for cases where search term is a subset of medicine name
        if search_norm in med_name_norm:
            old_similarity = similarity
            similarity = max(similarity, 0.8)
            print(f"    Subset boost for {medicine['name']}: {old_similarity:.3f} -> {similarity:.3f}")
        
        # Extra boost for exact word matches
        search_words = set(search_norm.split())
        med_words = set(med_name_norm.split())
        if search_words and med_words and search_words.issubset(med_words):
            old_similarity = similarity
            similarity = max(similarity, 0.9)
            print(f"    Word subset boost for {medicine['name']}: {old_similarity:.3f} -> {similarity:.3f}")
        
        if similarity >= threshold:
            medicine['similarity_score'] = similarity
            similar_medicines.append(medicine)
            print(f"✓ Added {medicine['name']} with similarity {similarity:.3f}")
    
    # Sort by similarity score (highest first) and return top results
    similar_medicines.sort(key=lambda x: x['similarity_score'], reverse=True)
    return similar_medicines[:max_results]

# Test the bot's search flow
db = DatabaseManager('blue_pharma_v2.db')

print("=== Testing Bot Search Flow ===")

# Test 1: Direct database search for "med 99"
print("\n1. Testing direct database search for 'med 99':")
direct_results = db.get_medicine_by_name("med 99")
print(f"Direct search results: {len(direct_results)}")
for med in direct_results:
    print(f"  - {med['name']}")

# Test 2: Fuzzy search for "med 99" 
print("\n2. Testing fuzzy search for 'med 99':")
fuzzy_results = find_similar_medicines(db, "med 99", threshold=0.35, max_results=5)
print(f"Fuzzy search results: {len(fuzzy_results)}")
for med in fuzzy_results:
    print(f"  - {med['name']} ({med['similarity_score']:.3f})")

# Test 3: Direct database search for "mad_99"
print("\n3. Testing direct database search for 'mad_99':")
direct_results = db.get_medicine_by_name("mad_99")
print(f"Direct search results: {len(direct_results)}")
for med in direct_results:
    print(f"  - {med['name']}")

# Test 4: Fuzzy search for "mad_99"
print("\n4. Testing fuzzy search for 'mad_99':")
fuzzy_results = find_similar_medicines(db, "mad_99", threshold=0.35, max_results=5)
print(f"Fuzzy search results: {len(fuzzy_results)}")
for med in fuzzy_results:
    print(f"  - {med['name']} ({med['similarity_score']:.3f})")
