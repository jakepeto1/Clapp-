#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
import os

# Add the current directory to Python path to import from greek_grammar.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class TestRootAorist:
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
    
    def find_common_verb_stem(self, forms):
        """Find common prefix among verb forms"""
        if not forms:
            return ""
        if len(forms) == 1:
            return forms[0][:-1] if len(forms[0]) > 1 else forms[0]
        
        min_length = min(len(form) for form in forms)
        common_prefix = ""
        
        for i in range(min_length):
            char = forms[0][i]
            if all(form[i] == char for form in forms):
                common_prefix += char
            else:
                break
        
        return common_prefix
    
    def extract_aorist_stem_from_paradigm(self, accent_free_forms, lemma, paradigm=None):
        """Extract aorist stem from all forms in aorist paradigm"""
        # Check for root aorist first
        if paradigm and paradigm.get("aorist_type") == "root":
            aorist_root = paradigm.get("aorist_root", "")
            if aorist_root:
                # For root aorists like βαίνω → ἔβην, stem is augment + root
                return f"ἐ{aorist_root}" if aorist_root else aorist_root
        
        # Regular aorist handling
        common_stem = self.find_common_verb_stem(accent_free_forms)
        
        if 'σ' in common_stem:
            sigma_pos = common_stem.find('σ')
            if sigma_pos >= 0:
                return common_stem[:sigma_pos + 1]  # Include the σ
        
        return common_stem
    
    def extract_infinitive_stem_from_paradigm(self, accent_free_forms, tense, voice, lemma, paradigm=None):
        """Extract infinitive stem based on known infinitive endings"""
        if not accent_free_forms:
            return ""
        
        infinitive_form = accent_free_forms[0]  # Only one form for infinitives
        
        if tense == "aorist":
            # Check for root aorist first
            if paradigm and paradigm.get("aorist_type") == "root":
                aorist_root = paradigm.get("aorist_root", "")
                if aorist_root and voice == "active":
                    # Root aorist infinitive: βῆναι → βη
                    if infinitive_form.endswith('ναι'):
                        return aorist_root  # Direct root without augment for infinitive
                    elif infinitive_form.endswith('αι'):
                        return aorist_root
            
            # Regular aorist patterns
            if voice == "active":
                if infinitive_form.endswith('σαι'):
                    return infinitive_form[:-3]  # Remove σαι
                elif infinitive_form.endswith('αι'):  # strong aorist
                    return infinitive_form[:-2]
        
        # Fallback
        return infinitive_form[:-2] if len(infinitive_form) > 2 else infinitive_form
    
    def test_root_aorist_stems(self):
        print("Testing Root Aorist stem extraction for βαίνω:\n")
        
        # Test Root Aorist Active Indicative
        if 'baino_aor_ind_act' in self.paradigms:
            paradigm = self.paradigms['baino_aor_ind_act']
            forms = [value for key, value in paradigm.items() 
                    if key not in ["type", "tense", "mood", "voice", "lemma", "aorist_type", "aorist_root"]]
            
            print(f"Root Aorist Active Indicative of βαίνω:")
            print(f"  Forms: {forms}")
            print(f"  Paradigm info: aorist_type={paradigm.get('aorist_type')}, aorist_root={paradigm.get('aorist_root')}")
            
            # Remove accents
            accent_free_forms = [self.remove_accents_for_stem_analysis(form) for form in forms]
            print(f"  Accent-free: {accent_free_forms}")
            
            # Extract consistent stem
            consistent_stem = self.extract_aorist_stem_from_paradigm(accent_free_forms, "βαίνω", paradigm)
            print(f"  Consistent stem: '{consistent_stem}'")
            print(f"  Expected: 'ἐβη' (augment + βη root)")
            
            # Test each form
            for form in forms:
                accent_free_form = self.remove_accents_for_stem_analysis(form)
                if accent_free_form.startswith(consistent_stem):
                    stem_length = len(consistent_stem)
                    extracted_stem = form[:stem_length]
                    ending = form[stem_length:]
                    print(f"  {form} → stem: '{extracted_stem}', ending: '{ending}'")
                else:
                    print(f"  {form} → stem doesn't match!")
            print()
        
        # Test Root Aorist Active Infinitive
        if 'baino_aor_inf_act' in self.paradigms:
            paradigm = self.paradigms['baino_aor_inf_act']
            infinitive_form = paradigm.get('inf_active', '')
            
            print(f"Root Aorist Active Infinitive of βαίνω:")
            print(f"  Form: {infinitive_form}")
            print(f"  Paradigm info: aorist_type={paradigm.get('aorist_type')}, aorist_root={paradigm.get('aorist_root')}")
            
            # Extract stem
            accent_free_form = self.remove_accents_for_stem_analysis(infinitive_form)
            stem = self.extract_infinitive_stem_from_paradigm([accent_free_form], "aorist", "active", "βαίνω", paradigm)
            
            print(f"  Extracted stem: '{stem}'")
            print(f"  Expected: 'βη' (just the root, no augment for infinitive)")
            print()
        
        # Compare with regular aorist for reference
        if 'luo_aor_ind_act' in self.paradigms:
            paradigm = self.paradigms['luo_aor_ind_act']
            forms = [value for key, value in paradigm.items() 
                    if key not in ["type", "tense", "mood", "voice", "lemma"]]
            
            print(f"Regular Sigmatic Aorist of λύω (for comparison):")
            print(f"  Forms: {forms}")
            
            accent_free_forms = [self.remove_accents_for_stem_analysis(form) for form in forms]
            consistent_stem = self.extract_aorist_stem_from_paradigm(accent_free_forms, "λύω", paradigm)
            print(f"  Consistent stem: '{consistent_stem}'")
            print(f"  Expected: 'ἐλυσ' (augment + λυ + σ)")
            print()

if __name__ == "__main__":
    tester = TestRootAorist()
    tester.test_root_aorist_stems()
