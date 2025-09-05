#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import unicodedata

def remove_accents_for_stem_analysis(text):
    """Remove Greek accents for stem analysis"""
    if not text:
        return text
    
    # Normalize to decomposed form
    text = unicodedata.normalize('NFD', text)
    
    # Remove accent marks (combining diacriticals)
    filtered_chars = []
    for char in text:
        if unicodedata.category(char) != 'Mn':  # Mn = Mark, nonspacing (accents)
            filtered_chars.append(char)
    
    # Rejoin and normalize back
    result = ''.join(filtered_chars)
    result = unicodedata.normalize('NFC', result)
    
    return result

def find_stem_from_paradigm_forms(forms):
    """Find the stem by analyzing all forms in a paradigm with accent-aware analysis"""
    if not forms or len(forms) < 2:
        return ""
    
    # Remove accents for stem analysis
    accent_free_forms = [remove_accents_for_stem_analysis(form) for form in forms if form.strip()]
    
    if not accent_free_forms:
        return ""
    
    # Find longest common prefix among accent-free forms
    if len(accent_free_forms) == 1:
        base_stem = accent_free_forms[0]
    else:
        # Find longest common prefix
        min_length = min(len(form) for form in accent_free_forms)
        common_prefix = ""
        
        for i in range(min_length):
            char = accent_free_forms[0][i]
            if all(form[i] == char for form in accent_free_forms):
                common_prefix += char
            else:
                break
        
        base_stem = common_prefix
    
    # Refine stem based on declension patterns
    refined_stem = refine_stem_by_declension(base_stem, forms)
    
    # Ensure minimum stem length
    if len(refined_stem) < 2:
        refined_stem = base_stem
    
    # For longer words, ensure stem is at least 3 characters
    max_form_length = max(len(form) for form in forms)
    if max_form_length > 6 and len(refined_stem) < 3:
        refined_stem = base_stem[:3] if len(base_stem) >= 3 else base_stem
    
    return refined_stem

def refine_stem_by_declension(base_stem, original_forms):
    """Refine stem based on Greek declension patterns"""
    if not base_stem:
        return base_stem
    
    # Analyze forms to determine declension type
    has_alpha_eta = any('α' in form or 'η' in form for form in original_forms)
    has_omicron = any('ο' in form for form in original_forms)
    has_consonant_stem = any(form.endswith(('ς', 'ξ', 'ψ', 'ν', 'ρ')) for form in original_forms)
    
    # First declension (α/η stems)
    if has_alpha_eta and not has_consonant_stem:
        if base_stem.endswith(('α', 'η')):
            return base_stem[:-1]
    
    # Second declension (ο stems)
    elif has_omicron and not has_consonant_stem:
        if base_stem.endswith('ο'):
            return base_stem[:-1]
    
    # Third declension (consonant stems) - more conservative
    elif has_consonant_stem:
        # Keep more of the stem for consonant declensions
        return base_stem
    
    return base_stem

# Test the stem extraction
def test_paradigm_stems():
    with open('paradigms.json', 'r', encoding='utf-8') as f:
        paradigms = json.load(f)
    
    print("Testing stem extraction for various paradigms:\n")
    
    # Test μούσα paradigm specifically
    if 'μούσα' in paradigms:
        forms = list(paradigms['μούσα'].values())
        stem = find_stem_from_paradigm_forms(forms)
        print(f"μούσα paradigm:")
        print(f"  Forms: {forms}")
        print(f"  Extracted stem: '{stem}'")
        print(f"  Expected: 'μουσ'")
        print(f"  ✓ Correct!" if stem == 'μουσ' else f"  ✗ Incorrect (expected 'μουσ')")
        print()
    
    # Test a few more paradigms
    test_words = ['λόγος', 'θεός', 'νοῦς'] if any(word in paradigms for word in ['λόγος', 'θεός', 'νοῦς']) else []
    
    for word in test_words:
        if word in paradigms:
            forms = list(paradigms[word].values())
            stem = find_stem_from_paradigm_forms(forms)
            print(f"{word} paradigm:")
            print(f"  Forms: {forms[:3]}...")  # Show first 3 forms
            print(f"  Extracted stem: '{stem}'")
            print()

if __name__ == "__main__":
    test_paradigm_stems()
