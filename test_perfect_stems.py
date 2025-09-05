#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
import os

# Add the current directory to Python path to import from greek_grammar.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class TestPerfectStems:
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
    
    def extract_perfect_stem_from_paradigm(self, accent_free_forms, lemma):
        """Extract perfect stem from all forms in perfect paradigm"""
        common_stem = self.find_common_verb_stem(accent_free_forms)
        
        # Perfect has reduplication + κ marker (active)
        # For now, return the common stem as-is
        return common_stem
    
    def test_perfect_stems(self):
        print("Testing Perfect and Pluperfect stem extraction:\n")
        
        # Test Perfect Active Indicative
        if 'luo_perf_ind_act' in self.paradigms:
            paradigm = self.paradigms['luo_perf_ind_act']
            forms = [value for key, value in paradigm.items() 
                    if key not in ["type", "tense", "mood", "voice", "lemma"]]
            
            print(f"Perfect Active Indicative of λύω:")
            print(f"  Forms: {forms}")
            
            # Remove accents
            accent_free_forms = [self.remove_accents_for_stem_analysis(form) for form in forms]
            print(f"  Accent-free: {accent_free_forms}")
            
            # Extract consistent stem
            consistent_stem = self.extract_perfect_stem_from_paradigm(accent_free_forms, "λύω")
            print(f"  Consistent stem: '{consistent_stem}'")
            print(f"  Expected: 'λελυκ' (reduplication + λυ + κ)")
            
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
        
        # Test Pluperfect Active Indicative
        if 'luo_plpf_ind_act' in self.paradigms:
            paradigm = self.paradigms['luo_plpf_ind_act']
            forms = [value for key, value in paradigm.items() 
                    if key not in ["type", "tense", "mood", "voice", "lemma"]]
            
            print(f"Pluperfect Active Indicative of λύω:")
            print(f"  Forms: {forms}")
            
            # For pluperfect, should include augment + perfect stem
            accent_free_forms = [self.remove_accents_for_stem_analysis(form) for form in forms]
            consistent_stem = self.find_common_verb_stem(accent_free_forms)
            
            print(f"  Consistent stem: '{consistent_stem}'")
            print(f"  Expected: 'ἐλελυκ' (augment + λελυκ)")
            print()
        
        # Test Perfect Infinitive
        if 'luo_perf_inf_act' in self.paradigms:
            paradigm = self.paradigms['luo_perf_inf_act']
            infinitive_form = paradigm.get('inf_active', '')
            
            print(f"Perfect Active Infinitive of λύω:")
            print(f"  Form: {infinitive_form}")
            
            # For perfect infinitive λελυκέναι, stem should be λελυκ
            accent_free_form = self.remove_accents_for_stem_analysis(infinitive_form)
            if accent_free_form.endswith('εναι'):
                stem = accent_free_form[:-4]  # Remove εναι
            elif accent_free_form.endswith('ναι'):
                stem = accent_free_form[:-3]  # Remove ναι
            else:
                stem = accent_free_form[:-2]  # Fallback
            
            print(f"  Extracted stem: '{stem}'")
            print(f"  Expected: 'λελυκ'")
            print()

if __name__ == "__main__":
    tester = TestPerfectStems()
    tester.test_perfect_stems()
