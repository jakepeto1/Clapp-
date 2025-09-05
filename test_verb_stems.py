#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import unicodedata

def remove_accents_for_stem_analysis(word):
    import unicodedata
    nfd = unicodedata.normalize('NFD', word)
    accent_marks = {'\u0301', '\u0300', '\u0342', '\u0308'}
    filtered = ''.join(char for char in nfd if char not in accent_marks)
    return unicodedata.normalize('NFC', filtered)

def remove_augment(verb_form):
    """Remove temporal augments from Greek verb forms"""
    if not verb_form:
        return verb_form
    
    # Syllabic augment (ἐ-) - most common
    if verb_form.startswith('ἐ') and len(verb_form) > 1:
        return verb_form[1:]
    
    # Temporal augment for vowel-initial verbs (lengthening)
    augment_mappings = {
        'η': ['α', 'ε'],  # η could be augmented α or ε
        'ω': ['ο'],       # ω could be augmented ο
        'ῃ': ['ᾳ'],       # ῃ could be augmented ᾳ
    }
    
    if len(verb_form) > 2:
        first_char = verb_form[0]
        if first_char in augment_mappings:
            for original in augment_mappings[first_char]:
                return original + verb_form[1:]
    
    return verb_form

def find_common_verb_stem(accent_free_forms):
    """Find the longest common prefix among verb forms"""
    if not accent_free_forms:
        return ""
    
    if len(accent_free_forms) == 1:
        form = accent_free_forms[0]
        if len(form) > 3:
            return form[:-2]  # Leave 2 chars for ending
        else:
            return form[:-1] if len(form) > 1 else form
    
    # Multiple forms - find longest common prefix
    min_length = min(len(form) for form in accent_free_forms)
    common_prefix = ""
    
    for i in range(min_length):
        char = accent_free_forms[0][i]
        if all(form[i] == char for form in accent_free_forms):
            common_prefix += char
        else:
            break
    
    # Ensure reasonable minimum stem length
    if len(common_prefix) < 2:
        if accent_free_forms:
            shortest = min(accent_free_forms, key=len)
            return shortest[:max(2, len(shortest) - 2)]
    
    return common_prefix

def extract_present_stem(accent_free_forms, target_form):
    """Extract present stem from present tense forms"""
    common_stem = find_common_verb_stem(accent_free_forms)
    
    # For thematic verbs, remove theme vowel
    if len(common_stem) > 1 and common_stem[-1] in ['ο', 'ε']:
        # Check if this looks like theme vowel by examining endings
        endings = [form[len(common_stem):] for form in accent_free_forms if form.startswith(common_stem)]
        # If we see typical thematic endings, remove the theme vowel
        thematic_endings = {'ω', 'εις', 'ει', 'ομεν', 'ετε', 'ουσι'}
        if any(ending in thematic_endings for ending in endings):
            common_stem = common_stem[:-1]
    
    return common_stem

def test_verb_stem_extraction():
    with open('paradigms.json', 'r', encoding='utf-8') as f:
        paradigms = json.load(f)
    
    print("Testing verb stem extraction:\n")
    
    # Test different verb paradigms
    test_cases = [
        ("luo_pres_ind_act", "λύω", "λυ"),      # Present: should be λυ-
        ("luo_impf_ind_act", "ἔλυον", "λυ"),    # Imperfect: should be λυ- (remove augment)
        ("phileo_pres_ind_act", "φιλέω", "φιλε"), # Contract verb present: φιλε-
        ("timao_pres_ind_act", "τιμάω", "τιμα"),  # Contract verb present: τιμα-
    ]
    
    for paradigm_key, test_word, expected_stem in test_cases:
        if paradigm_key in paradigms:
            paradigm = paradigms[paradigm_key]
            
            # Get all verb forms
            verb_forms = []
            for key, value in paradigm.items():
                if key not in ["type", "tense", "mood", "voice", "lemma"] and value and isinstance(value, str):
                    verb_forms.append(value)
            
            # Remove accents
            accent_free_forms = [remove_accents_for_stem_analysis(form) for form in verb_forms]
            accent_free_target = remove_accents_for_stem_analysis(test_word)
            
            # Get tense info
            tense = paradigm.get("tense", "present")
            
            print(f"Paradigm: {paradigm_key}")
            print(f"  Tense: {tense}")
            print(f"  Forms: {verb_forms}")
            print(f"  Test word: {test_word}")
            
            # Apply tense-specific logic
            if tense == "present":
                stem = extract_present_stem(accent_free_forms, accent_free_target)
            elif tense == "imperfect":
                # Remove augments first
                unaugmented_forms = [remove_augment(form) for form in accent_free_forms]
                stem = extract_present_stem(unaugmented_forms, remove_augment(accent_free_target))
            else:
                stem = find_common_verb_stem(accent_free_forms)
            
            print(f"  Extracted stem: '{stem}'")
            print(f"  Expected stem: '{expected_stem}'")
            print(f"  ✓ Correct!" if stem == expected_stem else f"  ✗ Incorrect")
            print()

if __name__ == "__main__":
    test_verb_stem_extraction()
