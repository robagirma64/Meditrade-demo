#!/usr/bin/env python3

import sqlite3
from difflib import SequenceMatcher

def calculate_similarity(a, b):
    """Calculate similarity ratio between two strings with enhanced matching."""
    # Normalize strings: lowercase, replace underscores with spaces, remove extra spaces
    a_norm = ' '.join(a.lower().replace('_', ' ').split())
    b_norm = ' '.join(b.lower().replace('_', ' ').split())
    
    print(f"  Normalized: '{a}' -> '{a_norm}', '{b}' -> '{b_norm}'")
    
    # Primary similarity using SequenceMatcher
    primary_similarity = SequenceMatcher(None, a_norm, b_norm).ratio()
    print(f"  Primary similarity: {primary_similarity:.3f}")
    
    # Secondary check: exact word matching (for cases like "med 99" vs "med_99")
    a_words = set(a_norm.split())
    b_words = set(b_norm.split())
    
    if a_words and b_words:
        # Calculate word overlap ratio
        common_words = a_words.intersection(b_words)
        word_similarity = len(common_words) / max(len(a_words), len(b_words))
        print(f"  Word similarity: {word_similarity:.3f} (common: {common_words})")
        
        # If words match well but character similarity is low, boost the score
        if word_similarity >= 0.6 and primary_similarity < 0.5:
            primary_similarity = max(primary_similarity, word_similarity * 0.8)
            print(f"  Boosted by word matching to: {primary_similarity:.3f}")
    
    # Tertiary check: substring matching (one contains the other)
    if a_norm in b_norm or b_norm in a_norm:
        substring_similarity = min(len(a_norm), len(b_norm)) / max(len(a_norm), len(b_norm))
        primary_similarity = max(primary_similarity, substring_similarity * 0.7)
        print(f"  Boosted by substring matching to: {primary_similarity:.3f}")
    
    return primary_similarity

def find_similar_medicines_test(search_term, threshold=0.3, max_results=5):
    """Find medicines with similar names using enhanced fuzzy matching."""
    
    # Get medicines from database
    conn = sqlite3.connect('blue_pharma_v2.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, price, stock_quantity, therapeutic_category FROM medicines WHERE is_active = 1')
    all_medicines = cursor.fetchall()
    conn.close()
    
    # Convert to dict format like the bot uses
    medicines = []
    for med in all_medicines:
        medicines.append({
            'id': med[0],
            'name': med[1], 
            'price': med[2],
            'stock_quantity': med[3],
            'therapeutic_category': med[4]
        })
    
    similar_medicines = []
    
    # Normalize search term
    search_norm = ' '.join(search_term.lower().replace('_', ' ').split())
    print(f"Search term normalized: '{search_term}' -> '{search_norm}'")
    print("=" * 60)
    
    for medicine in medicines:
        print(f"\nTesting: '{search_term}' vs '{medicine['name']}'")
        similarity = calculate_similarity(search_term, medicine['name'])
        
        # Additional boost for very close matches
        med_name_norm = ' '.join(medicine['name'].lower().replace('_', ' ').split())
        
        # Extra boost for cases where search term is a subset of medicine name
        if search_norm in med_name_norm:
            similarity = max(similarity, 0.8)
            print(f"  Boosted by subset match to: {similarity:.3f}")
        
        # Extra boost for exact word matches
        search_words = set(search_norm.split())
        med_words = set(med_name_norm.split())
        if search_words and med_words and search_words.issubset(med_words):
            similarity = max(similarity, 0.9)
            print(f"  Boosted by word subset to: {similarity:.3f}")
        
        print(f"  Final similarity: {similarity:.3f} ({int(similarity*100)}%)")
        
        if similarity >= threshold:
            medicine['similarity_score'] = similarity
            similar_medicines.append(medicine)
            print(f"  -> ADDED TO SUGGESTIONS!")
        else:
            print(f"  -> Below threshold ({threshold})")
    
    # Sort by similarity score (highest first) and return top results
    similar_medicines.sort(key=lambda x: x['similarity_score'], reverse=True)
    return similar_medicines[:max_results]

if __name__ == "__main__":
    test_searches = ['med 99', 'mad_99', 'Med 9', 'med']
    
    for search_term in test_searches:
        print(f"\n{'='*80}")
        print(f"TESTING SEARCH: '{search_term}'")
        print('='*80)
        
        results = find_similar_medicines_test(search_term, threshold=0.3)
        
        print(f"\nRESULTS FOR '{search_term}':")
        print("-" * 40)
        if results:
            for i, med in enumerate(results, 1):
                print(f"{i}. {med['name']} - {med['similarity_score']:.3f} ({int(med['similarity_score']*100)}%)")
        else:
            print("No results found above threshold")
