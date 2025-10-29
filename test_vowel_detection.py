#!/usr/bin/env python3
"""Test script for Greek vowel detection."""

import unicodedata

def is_greek_vowel(char):
    """Check if a character is a Greek vowel (with or without diacritics)."""
    if not char:
        return False
    
    # Decompose the character to get the base letter
    decomposed = unicodedata.normalize('NFD', char)
    base_char = decomposed[0] if decomposed else char
    
    # Check basic Greek vowels
    if base_char.lower() in 'αεηιουω':
        return True
    
    # Also check common precomposed Greek vowels with diacritics
    greek_vowels = {
        # Basic vowels
        'α', 'ε', 'η', 'ι', 'ο', 'υ', 'ω',
        'Α', 'Ε', 'Η', 'Ι', 'Ο', 'Υ', 'Ω',
        # With accents
        'ά', 'έ', 'ή', 'ί', 'ό', 'ύ', 'ώ',
        'Ά', 'Έ', 'Ή', 'Ί', 'Ό', 'Ύ', 'Ώ',
        'ὰ', 'ὲ', 'ὴ', 'ὶ', 'ὸ', 'ὺ', 'ὼ',
        'Ὰ', 'Ὲ', 'Ὴ', 'Ὶ', 'Ὸ', 'Ὺ', 'Ὼ',
        'ᾶ', 'ῆ', 'ῖ', 'ῦ', 'ῶ',
        # With breathing marks
        'ἀ', 'ἐ', 'ἠ', 'ἰ', 'ὀ', 'ὐ', 'ὠ',
        'ἁ', 'ἑ', 'ἡ', 'ἱ', 'ὁ', 'ὑ', 'ὡ',
        'Ἀ', 'Ἐ', 'Ἠ', 'Ἰ', 'Ὀ', 'Ὑ', 'Ὠ',
        'Ἁ', 'Ἑ', 'Ἡ', 'Ἱ', 'Ὁ', 'Ὑ', 'Ὡ',
        # With breathing and accents
        'ἄ', 'ἔ', 'ἤ', 'ἴ', 'ὄ', 'ὔ', 'ὤ',
        'ἅ', 'ἕ', 'ἥ', 'ἵ', 'ὅ', 'ὕ', 'ὥ',
        'ἂ', 'ἒ', 'ἢ', 'ἲ', 'ὂ', 'ὒ', 'ὢ',
        'ἃ', 'ἓ', 'ἣ', 'ἳ', 'ὃ', 'ὓ', 'ὣ',
        'ἆ', 'ἦ', 'ἶ', 'ὖ', 'ὦ',
        'ἇ', 'ἧ', 'ἷ', 'ὗ', 'ὧ',
        # With iota subscript
        'ᾳ', 'ῃ', 'ῳ',
        'ᾼ', 'ῌ', 'ῼ',
        # With breathing and iota subscript
        'ᾀ', 'ᾐ', 'ᾠ', 'ᾁ', 'ᾑ', 'ᾡ',
        'ᾄ', 'ᾔ', 'ᾤ', 'ᾅ', 'ᾕ', 'ᾥ',
        'ᾂ', 'ᾒ', 'ᾢ', 'ᾃ', 'ᾓ', 'ᾣ',
        'ᾆ', 'ᾖ', 'ᾦ', 'ᾇ', 'ᾗ', 'ᾧ',
        # With accents and iota subscript
        'ᾴ', 'ῄ', 'ῴ', 'ᾲ', 'ῂ', 'ῲ', 'ᾷ', 'ῇ', 'ῷ'
    }
    
    return char in greek_vowels

def test_vowel_detection():
    """Test Greek vowel detection."""
    test_cases = [
        # Should return True
        ('α', True),
        ('ἀ', True), # alpha with smooth breathing
        ('ἁ', True), # alpha with rough breathing
        ('ᾳ', True), # alpha with iota subscript
        ('ᾀ', True), # alpha with smooth breathing and iota subscript
        ('ἄ', True), # alpha with smooth breathing and acute
        ('ή', True), # eta with acute
        ('ὠ', True), # omega with smooth breathing
        
        # Should return False
        ('β', False), # beta (consonant)
        ('γ', False), # gamma (consonant)
        ('1', False), # number
        ('', False),  # empty string
    ]
    
    print("Testing Greek vowel detection:")
    print("=" * 40)
    
    for char, expected in test_cases:
        result = is_greek_vowel(char)
        status = "✓" if result == expected else "✗"
        print(f"{status} '{char}' -> {result} (expected: {expected})")

if __name__ == "__main__":
    test_vowel_detection()
