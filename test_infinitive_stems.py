#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
import os

# Add the current directory to Python path to import from greek_grammar.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class TestInfinitiveStems:
    def __init__(self):
        with open('paradigms.json', 'r', encoding='utf-8') as f:
            self.paradigms = json.load(f)
    
    def remove_accents_for_stem_analysis(self, word):
        """Remove Greek accents for stem analysis"""
        import unicodedata
        nfd = unicodedata.normalize('NFD', word)
        accent_marks = {'\u0301', '\u0300', '\u0342', '\u0308'}
        filtered = ''.join(char for char in nfd if char not in accent_marks)
        return unicodedata.normalize('NFC', filtered)
    
    def extract_infinitive_stem_from_paradigm(self, accent_free_forms, tense, voice, lemma):
        """Extract infinitive stem based on known infinitive endings"""
        if not accent_free_forms:
            return ""
        
        infinitive_form = accent_free_forms[0]  # Only one form for infinitives
        
        if tense == "present":
            if voice == "active":
                # Present active infinitive: λύειν → λυ
                if infinitive_form.endswith('ειν'):
                    return infinitive_form[:-3]
                elif infinitive_form.endswith('ναι'):  # εἶναι type
                    return infinitive_form[:-3]
            elif voice in ["middle", "passive"]:
                # Present middle/passive infinitive: λύεσθαι → λυ
                if infinitive_form.endswith('εσθαι'):
                    return infinitive_form[:-6]
                elif infinitive_form.endswith('σθαι'):  # shorter ending
                    return infinitive_form[:-4]
                    
        elif tense == "aorist":
            if voice == "active":
                # Aorist active infinitive: λύσαι → λυσ (but for consistency, should be λυ)
                if infinitive_form.endswith('σαι'):
                    base = infinitive_form[:-3]  # Remove σαι
                    # For consistency with other aorist forms, remove the σ too
                    return base  # This gives λυ instead of λυσ
                elif infinitive_form.endswith('αι'):  # strong aorist
                    return infinitive_form[:-2]
            elif voice == "middle":
                # Aorist middle infinitive: λύσασθαι → λυ (consistent with aorist active)
                if infinitive_form.endswith('σασθαι'):
                    base = infinitive_form[:-6]  # Remove σασθαι 
                    return base  # This gives λυ
                elif infinitive_form.endswith('ασθαι'):  # strong aorist
                    return infinitive_form[:-5]
            elif voice == "passive":
                # Aorist passive infinitive: λυθῆναι → λυθ
                if infinitive_form.endswith('θηναι'):
                    return infinitive_form[:-5]
                elif infinitive_form.endswith('ηναι'):
                    return infinitive_form[:-4]
        
        # Fallback: return most of the form
        return infinitive_form[:-2] if len(infinitive_form) > 2 else infinitive_form
    
    def test_infinitive_stems(self):
        print("Testing infinitive stem extraction:\n")
        
        # Find infinitive paradigms for λύω
        infinitive_paradigms = {}
        for key, paradigm in self.paradigms.items():
            if (paradigm.get("type") == "verb" and 
                paradigm.get("mood") == "infinitive" and
                paradigm.get("lemma") == "λύω"):
                infinitive_paradigms[key] = paradigm
        
        expected_stems = {
            "present": "λυ",  # All present infinitives should have λυ stem
            "aorist": "λυ",   # For consistency, aorist infinitives should also show λυ
            "future": "λυσ",  # Future has the σ marker
            "perfect": "λελυκ" # Perfect has reduplication + κ
        }
        
        for paradigm_key, paradigm in infinitive_paradigms.items():
            tense = paradigm.get("tense", "unknown")
            voice = paradigm.get("voice", "unknown")
            
            # Get the infinitive form
            infinitive_form = None
            for key, value in paradigm.items():
                if key.startswith("inf_") and isinstance(value, str):
                    infinitive_form = value
                    break
            
            if infinitive_form:
                print(f"Paradigm: {paradigm_key}")
                print(f"  Tense: {tense}, Voice: {voice}")
                print(f"  Infinitive: {infinitive_form}")
                
                # Remove accents
                accent_free_form = self.remove_accents_for_stem_analysis(infinitive_form)
                print(f"  Accent-free: '{accent_free_form}'")
                
                # Extract stem
                extracted_stem = self.extract_infinitive_stem_from_paradigm([accent_free_form], tense, voice, "λύω")
                expected_stem = expected_stems.get(tense, "unknown")
                
                print(f"  Extracted stem: '{extracted_stem}'")
                print(f"  Expected stem: '{expected_stem}'")
                
                if extracted_stem == expected_stem:
                    print(f"  ✓ Correct!")
                else:
                    print(f"  ✗ Incorrect")
                print()

if __name__ == "__main__":
    tester = TestInfinitiveStems()
    tester.test_infinitive_stems()
