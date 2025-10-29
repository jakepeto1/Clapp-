#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
import os

# Add the current directory to Python path to import from stoa_grammar.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# We need to create a minimal test environment
class TestVerbStemExtraction:
    def __init__(self):
        with open('paradigms.json', 'r', encoding='utf-8') as f:
            self.paradigms = json.load(f)
    
    def remove_augment(self, word):
        """Remove temporal augment from Greek verbs"""
        if word.startswith('ἐ') and len(word) > 2:
            return word[1:]
        elif word.startswith('ἠ') and len(word) > 2:
            return 'ε' + word[1:]
        elif word.startswith('ἤ') and len(word) > 2:
            return 'ε' + word[1:]
        elif word.startswith('εἰ') and len(word) > 3:
            return 'ἰ' + word[2:]
        elif word.startswith('ηὐ') and len(word) > 3:
            return 'αὐ' + word[2:]
        return word
    
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
    
    def extract_aorist_stem_from_paradigm(self, accent_free_forms, lemma):
        """Extract aorist stem from all forms in aorist paradigm"""
        # Find the common prefix across all aorist forms
        common_stem = self.find_common_verb_stem(accent_free_forms)
        
        # For sigmatic aorist, the stem includes the σ
        if 'σ' in common_stem:
            sigma_pos = common_stem.find('σ')
            if sigma_pos >= 0:
                return common_stem[:sigma_pos + 1]  # Include the σ
        
        return common_stem
    
    def remove_accents_for_stem_analysis(self, word):
        """Remove Greek accents for stem analysis"""
        import unicodedata
        nfd = unicodedata.normalize('NFD', word)
        accent_marks = {'\u0301', '\u0300', '\u0342', '\u0308'}
        filtered = ''.join(char for char in nfd if char not in accent_marks)
        return unicodedata.normalize('NFC', filtered)
    
    def test_consistent_stems(self):
        print("Testing consistent verb stem extraction:\n")
        
        # Test aorist λύω paradigm
        if 'luo_aor_ind_act' in self.paradigms:
            paradigm = self.paradigms['luo_aor_ind_act']
            forms = [value for key, value in paradigm.items() 
                    if key not in ["type", "tense", "mood", "voice", "lemma"]]
            
            print(f"Aorist Active Indicative of λύω:")
            print(f"  Forms: {forms}")
            
            # Remove accents
            accent_free_forms = [self.remove_accents_for_stem_analysis(form) for form in forms]
            print(f"  Accent-free: {accent_free_forms}")
            
            # Extract consistent stem
            consistent_stem = self.extract_aorist_stem_from_paradigm(accent_free_forms, "λύω")
            print(f"  Consistent stem: '{consistent_stem}'")
            print(f"  Expected: 'ἐλυσ' (augment + λυ + σ)")
            
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
        
        # Test present λύω paradigm for comparison
        if 'luo_pres_ind_act' in self.paradigms:
            paradigm = self.paradigms['luo_pres_ind_act']
            forms = [value for key, value in paradigm.items() 
                    if key not in ["type", "tense", "mood", "voice", "lemma"]]
            
            print(f"Present Active Indicative of λύω:")
            print(f"  Forms: {forms}")
            
            # For present, just find common stem
            accent_free_forms = [self.remove_accents_for_stem_analysis(form) for form in forms]
            consistent_stem = self.find_common_verb_stem(accent_free_forms)
            
            # Remove theme vowel for thematic verbs
            if consistent_stem.endswith(('ο', 'ε')):
                consistent_stem = consistent_stem[:-1]
                
            print(f"  Consistent stem: '{consistent_stem}'")
            print(f"  Expected: 'λυ'")
            print()

if __name__ == "__main__":
    tester = TestVerbStemExtraction()
    tester.test_consistent_stems()
