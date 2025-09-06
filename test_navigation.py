#!/usr/bin/env python3
"""
Test script for the Next Answer navigation logic
"""

import sys
import json

# Simple test to verify navigation logic without GUI
class MockApp:
    def __init__(self):
        with open('paradigms.json', 'r', encoding='utf-8') as f:
            self.paradigms = json.load(f)
        
        # Test word lists
        self.word_lists = {
            "First Declension (μουσα)": ["μούσα", "δόξα", "οἰκία", "σοφία"],
            "Present Indicative Active - Release (λύω)": ["λύω", "παύω", "φέρω", "ἄγω"]
        }
        
        self.current_word_index = 0
        self.verb_voice_order = ["Active", "Middle", "Passive"]
        self.verb_tense_order = ["Present", "Imperfect", "Future", "Aorist", "Perfect", "Pluperfect"] 
        self.verb_mood_order = ["Indicative", "Subjunctive", "Optative", "Imperative"]
        
    def get_available_combinations_for_verb(self, lemma):
        combinations = set()
        for paradigm_key, paradigm_data in self.paradigms.items():
            if (paradigm_data.get('type') == 'verb' and 
                paradigm_data.get('lemma') == lemma):
                
                tense = paradigm_data.get('tense', '')
                mood = paradigm_data.get('mood', '')
                voice = paradigm_data.get('voice', '')
                
                # Convert to display format
                tense_display = tense.title() if tense else ''
                mood_display = mood.title() if mood else ''
                voice_display = voice.title() if voice else ''
                
                if tense == 'pluperfect':
                    tense_display = 'Pluperfect'
                
                if all([tense_display, mood_display, voice_display]):
                    combinations.add((tense_display, mood_display, voice_display))
        
        return list(combinations)

# Test noun navigation
print("=== TESTING NOUN NAVIGATION ===")
app = MockApp()
mode = "First Declension (μουσα)"
print(f"Starting with mode: {mode}")
print(f"Word list: {app.word_lists[mode]}")
print(f"Starting index: {app.current_word_index}")
print(f"Current word: {app.word_lists[mode][app.current_word_index]}")

for i in range(6):  # Test going through the list twice
    app.current_word_index = (app.current_word_index + 1) % len(app.word_lists[mode])
    print(f"After click {i+1}: index={app.current_word_index}, word={app.word_lists[mode][app.current_word_index]}")

print()

# Test verb combinations
print("=== TESTING VERB COMBINATIONS ===")
lemma = "λύω"
combinations = app.get_available_combinations_for_verb(lemma)
print(f"Available combinations for {lemma}:")

# Sort combinations for consistent display
combinations.sort(key=lambda x: (
    app.verb_mood_order.index(x[1]) if x[1] in app.verb_mood_order else 999,
    app.verb_tense_order.index(x[0]) if x[0] in app.verb_tense_order else 999,
    app.verb_voice_order.index(x[2]) if x[2] in app.verb_voice_order else 999
))

for i, combo in enumerate(combinations[:10]):  # Show first 10
    print(f"  {i+1}: {combo[0]} {combo[1]} {combo[2]}")

print(f"\nTotal combinations: {len(combinations)}")
