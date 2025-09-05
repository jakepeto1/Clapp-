#!/usr/bin/env python3
"""Test script for the new context-appropriate stem logic"""

def test_special_stems():
    # Test cases for special stems
    test_cases = [
        # οἶδα (know) - different stems for singular/plural
        ("οἶδα", "present", "1st_sg", False, "οἰ"),  # singular should get "οἰ"
        ("οἶδα", "present", "1st_pl", True, "ἰσ"),   # plural should get "ἰσ"
        
        # ἵημι (send) - shorter stem
        ("ἵημι", "present", "1st_sg", False, "ἱ"),   # should get short "ἱ"
        ("ἵημι", "present", "1st_pl", True, "ἱ"),    # should get short "ἱ"
        
        # φημί (say) - different stems for singular/plural
        ("φημί", "present", "1st_sg", False, "φη"),  # singular should get "φη"
        ("φημί", "present", "1st_pl", True, "φα"),   # plural should get "φα"
        ("φημί", "imperfect", "1st_sg", False, "φη"), # imperfect singular should get "φη"
        ("φημί", "imperfect", "1st_pl", True, "φα"),  # imperfect plural should get "φα"
        
        # δίδωμι (give) - different stems for aorist singular/plural
        ("δίδωμι", "aorist", "1st_sg", False, "δω"), # aorist singular should get "δω"
        ("δίδωμι", "aorist", "1st_pl", True, "δο"),  # aorist plural should get "δο"
        
        # τίθημι (place) - different stems for aorist singular/plural
        ("τίθημι", "aorist", "1st_sg", False, "θη"), # aorist singular should get "θη"
        ("τίθημι", "aorist", "1st_pl", True, "θε"),  # aorist plural should get "θε"
        
        # ἵστημι (stand) - different stems for aorist singular/plural
        ("ἵστημι", "aorist", "1st_sg", False, "στησ"), # aorist singular should get "στησ"
        ("ἵστημι", "aorist", "1st_pl", True, "στη"),   # aorist plural should get "στη"
    ]
    
    print("Special Stem Test Cases:")
    print("========================")
    for lemma, tense, entry_key, is_plural, expected in test_cases:
        print(f"Lemma: {lemma}")
        print(f"  Tense: {tense}, Entry: {entry_key}, Plural: {is_plural}")
        print(f"  Expected stem: {expected}")
        print()

if __name__ == "__main__":
    test_special_stems()
