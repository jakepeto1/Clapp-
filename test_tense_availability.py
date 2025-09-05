#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json

# Test which tenses are available for different verbs
def test_verb_tenses():
    
    # Simulate the logic from get_base_available_tenses
    def get_tenses_for_mode(mode):
        if "εἰμί" in mode:
            return ["Present", "Imperfect"]
        elif "οἶδα" in mode:
            return ["Present", "Imperfect"]
        elif "εἶμι" in mode:
            return ["Present", "Imperfect", "Future"]
        elif "λύω" in mode or "Release" in mode:
            # Only λύω has Perfect and Pluperfect paradigms for now
            return ["Present", "Imperfect", "Aorist", "Future", "Perfect", "Pluperfect"]
        else:
            return ["Present", "Imperfect", "Aorist", "Future"]
    
    # Test different verb types
    test_modes = [
        "Present Indicative Active - Release (λύω)",
        "Present Indicative Active - To Be (εἰμί)",
        "Present Indicative Active - Love (φιλέω)",
        "Present Indicative Active - Honor (τιμάω)",
        "Present Indicative Active - Know (οἶδα)",
        "Present Indicative Active - Go (εἶμι)",
        "Present Indicative Active - Throw (βάλλω)"
    ]
    
    print("Testing tense availability for different verbs:\n")
    
    for mode in test_modes:
        tenses = get_tenses_for_mode(mode)
        verb_name = mode.split(" - ")[1] if " - " in mode else mode
        
        print(f"{verb_name}:")
        print(f"  Available tenses: {tenses}")
        has_perfect = "Perfect" in tenses
        has_pluperfect = "Pluperfect" in tenses
        print(f"  Has Perfect: {'✓' if has_perfect else '✗'}")
        print(f"  Has Pluperfect: {'✓' if has_pluperfect else '✗'}")
        print()
    
    print("Summary:")
    print("- Only λύω should have Perfect and Pluperfect tenses")
    print("- All other verbs should NOT have Perfect and Pluperfect tenses")
    print("- Special verbs (εἰμί, οἶδα, εἶμι) have limited tense options")

if __name__ == "__main__":
    test_verb_tenses()
