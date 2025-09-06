#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json

# Debug script to check βαίνω paradigm lookup
def debug_baino_lookup():
    # Load paradigms
    with open('paradigms.json', 'r', encoding='utf-8') as f:
        paradigms = json.load(f)
    
    print("Debugging βαίνω paradigm lookup:\n")
    
    # Check if baino paradigms exist
    baino_keys = [key for key in paradigms.keys() if 'baino' in key]
    print(f"Found βαίνω paradigm keys: {baino_keys}")
    
    # Check specific paradigm
    if 'baino_pres_ind_act' in paradigms:
        paradigm = paradigms['baino_pres_ind_act']
        print(f"\nbaino_pres_ind_act paradigm:")
        for key, value in paradigm.items():
            print(f"  {key}: {value}")
    else:
        print("ERROR: baino_pres_ind_act not found in paradigms!")
    
    # Test the paradigm mapping logic
    mode = "Present Indicative Active - Step (βαίνω)"
    paradigm_map = {
        "Present Indicative Active - Release (λύω)": "luo_pres_ind_act",
        "Present Indicative Active - To Be (εἰμί)": "eimi_pres_ind_act",
        "Present Indicative Active - Step (βαίνω)": "baino_pres_ind_act"
    }
    
    paradigm_key = paradigm_map.get(mode)
    print(f"\nMode: {mode}")
    print(f"Mapped to paradigm key: {paradigm_key}")
    
    if paradigm_key and paradigm_key in paradigms:
        print("✓ Paradigm lookup should work!")
    else:
        print("✗ Paradigm lookup will fail!")
        print(f"Available keys starting with 'baino': {[k for k in paradigms.keys() if k.startswith('baino')]}")

if __name__ == "__main__":
    debug_baino_lookup()
