#!/usr/bin/env python3
import sqlite3
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

# Connect to database
conn = sqlite3.connect('blue_pharma_v2.db')
cursor = conn.cursor()

# Get all medicine names
cursor.execute('SELECT name FROM medicines ORDER BY name')
results = cursor.fetchall()
medicine_names = [row[0] for row in results]

print("=== All Medicine Names ===")
for name in medicine_names:
    print(f"  - {name}")

print("\n=== Testing 'med 99' similarity ===")
search_term = "med 99"
print(f"Search term: '{search_term}'")

for name in medicine_names:
    similarity = calculate_similarity(search_term, name)
    if similarity > 0.1:  # Show any medicine with >10% similarity
        print(f"  {name}: {similarity:.3f} ({int(similarity*100)}%)")

print("\n=== Testing 'mad_99' similarity ===")
search_term = "mad_99"
print(f"Search term: '{search_term}'")

for name in medicine_names:
    similarity = calculate_similarity(search_term, name)
    if similarity > 0.1:  # Show any medicine with >10% similarity
        print(f"  {name}: {similarity:.3f} ({int(similarity*100)}%)")

conn.close()
