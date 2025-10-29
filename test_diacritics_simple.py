#!/usr/bin/env python3
"""Simple test script for diacritic combinations."""

import unicodedata

# Unicode combining characters for Greek diacritics
SMOOTH_BREATHING = '\u0313'  # ᾿
ROUGH_BREATHING = '\u0314'   # ῾
IOTA_SUBSCRIPT = '\u0345'    # ͅ (combines with α, η, ω)

def add_iota_subscript(char):
    """Add iota subscript to a vowel, handling existing diacritics."""
    # Decompose the character to separate base letter from combining marks
    decomposed = unicodedata.normalize('NFD', char)
    
    if not decomposed:
        return char
        
    base_char = decomposed[0]
    existing_marks = decomposed[1:]
    
    # Check if base character can have iota subscript
    base_vowels = {
        'α': 'α', 'η': 'η', 'ω': 'ω',
        'Α': 'Α', 'Η': 'Η', 'Ω': 'Ω',
        # Also handle precomposed characters with accents or breathing
        'ά': 'α', 'ή': 'η', 'ώ': 'ω',
        'ὰ': 'α', 'ὴ': 'η', 'ὼ': 'ω',
        'ᾶ': 'α', 'ῆ': 'η', 'ῶ': 'ω',
        'ἀ': 'α', 'ἠ': 'η', 'ὠ': 'ω',
        'ἁ': 'α', 'ἡ': 'η', 'ὡ': 'ω',
        'ἄ': 'α', 'ἤ': 'η', 'ὤ': 'ω',
        'ἅ': 'α', 'ἥ': 'η', 'ὥ': 'ω',
        'ἂ': 'α', 'ἢ': 'η', 'ὢ': 'ω',
        'ἃ': 'α', 'ἣ': 'η', 'ὣ': 'ω',
        'ἆ': 'α', 'ἦ': 'η', 'ὦ': 'ω',
        'ἇ': 'α', 'ἧ': 'η', 'ὧ': 'ω'
    }
    
    # Get the base vowel (remove any existing accents/breathing)
    base_vowel = base_vowels.get(base_char, base_char)
    if base_vowel not in 'αηωΑΗΩ':
        print(f"Cannot add iota subscript to {char} (only α, η, ω can have iota subscript)")
        return char
    
    # Check if iota subscript already exists
    if IOTA_SUBSCRIPT in existing_marks:
        print(f"Iota subscript already present in {char}")
        return char
    
    # Add iota subscript at the end (it comes last in canonical order)
    final_char = base_vowel + ''.join(existing_marks) + IOTA_SUBSCRIPT
    
    # Normalize to precomposed form if possible
    result = unicodedata.normalize('NFC', final_char)
    print(f"Iota subscript: {char} -> {result}")
    return result

def add_smooth_breathing(char):
    """Add smooth breathing to a vowel, handling existing diacritics."""
    # Decompose the character to separate base letter from combining marks
    decomposed = unicodedata.normalize('NFD', char)
    
    if not decomposed:
        return char
        
    base_char = decomposed[0]
    existing_marks = decomposed[1:]
    
    # Check if base character can have breathing
    base_vowels = {
        'α': 'α', 'ε': 'ε', 'η': 'η', 'ι': 'ι', 
        'ο': 'ο', 'υ': 'υ', 'ω': 'ω',
        'Α': 'Α', 'Ε': 'Ε', 'Η': 'Η', 'Ι': 'Ι',
        'Ο': 'Ο', 'Υ': 'Υ', 'Ω': 'Ω',
        # Also handle precomposed characters with accents or other marks
        'ά': 'α', 'έ': 'ε', 'ή': 'η', 'ί': 'ι', 'ό': 'ο', 'ύ': 'υ', 'ώ': 'ω',
        'ὰ': 'α', 'ὲ': 'ε', 'ὴ': 'η', 'ὶ': 'ι', 'ὸ': 'ο', 'ὺ': 'υ', 'ὼ': 'ω',
        'ᾶ': 'α', 'ῆ': 'η', 'ῖ': 'ι', 'ῦ': 'υ', 'ῶ': 'ω',
        'ᾳ': 'α', 'ῃ': 'η', 'ῳ': 'ω'
    }
    
    # Get the base vowel (remove any existing accents/breathing)
    base_vowel = base_vowels.get(base_char, base_char)
    if base_vowel not in 'αεηιουωΑΕΗΙΟΥΩ':
        print(f"Cannot add breathing to non-vowel: {char}")
        return char
    
    # Remove any existing breathing marks from existing marks
    new_marks = [mark for mark in existing_marks if mark not in [SMOOTH_BREATHING, ROUGH_BREATHING]]
    
    # Add smooth breathing at the beginning (breathing comes first in canonical order)
    final_char = base_vowel + SMOOTH_BREATHING + ''.join(new_marks)
    
    # Normalize to precomposed form if possible
    result = unicodedata.normalize('NFC', final_char)
    print(f"Smooth breathing: {char} -> {result}")
    return result

def test_diacritic_combinations():
    """Test various diacritic combinations."""
    test_cases = [
        # Test adding iota subscript to characters with breathing
        ('ἀ', add_iota_subscript, 'ᾀ'),  # smooth breathing + iota subscript
        ('ἁ', add_iota_subscript, 'ᾁ'),  # rough breathing + iota subscript
        ('ἠ', add_iota_subscript, 'ᾐ'),  # eta with smooth breathing + iota subscript
        ('ὠ', add_iota_subscript, 'ᾠ'),  # omega with smooth breathing + iota subscript
        
        # Test adding breathing to characters with iota subscript
        ('ᾳ', add_smooth_breathing, 'ᾀ'),  # iota subscript + smooth breathing
        ('ῃ', add_smooth_breathing, 'ᾐ'),  # eta iota subscript + smooth breathing
        ('ῳ', add_smooth_breathing, 'ᾠ'),  # omega iota subscript + smooth breathing
    ]
    
    print("Testing diacritic combinations:")
    print("=" * 50)
    
    for input_char, function, expected in test_cases:
        result = function(input_char)
        
        # Normalize both for comparison
        result_norm = unicodedata.normalize('NFC', result)
        expected_norm = unicodedata.normalize('NFC', expected)
        
        status = "✓" if result_norm == expected_norm else "✗"
        print(f"{status} {input_char} ({[hex(ord(c)) for c in input_char]}) -> {result} ({[hex(ord(c)) for c in result]}) (expected: {expected})")
        
        if result_norm != expected_norm:
            print(f"  MISMATCH! Expected: {[hex(ord(c)) for c in expected]}")

if __name__ == "__main__":
    test_diacritic_combinations()
