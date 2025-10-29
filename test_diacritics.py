#!/usr/bin/env python3
"""Test script for diacritic combinations."""

import greek_grammar
import unicodedata

# Create a simple test app instance to test diacritic functions
class TestApp:
    def __init__(self):
        self.app = greek_grammar.GreekGrammarApp(None)
    
    def test_diacritic_combinations(self):
        """Test various diacritic combinations."""
        test_cases = [
            # Test adding iota subscript to characters with breathing
            ('ἀ', 'add_iota_subscript', 'ᾀ'),  # smooth breathing + iota subscript
            ('ἁ', 'add_iota_subscript', 'ᾁ'),  # rough breathing + iota subscript
            ('ἠ', 'add_iota_subscript', 'ᾐ'),  # eta with smooth breathing + iota subscript
            ('ὠ', 'add_iota_subscript', 'ᾠ'),  # omega with smooth breathing + iota subscript
            
            # Test adding breathing to characters with iota subscript
            ('ᾳ', 'add_smooth_breathing', 'ᾀ'),  # iota subscript + smooth breathing
            ('ᾳ', 'add_rough_breathing', 'ᾁ'),   # iota subscript + rough breathing
            ('ῃ', 'add_smooth_breathing', 'ᾐ'),  # eta iota subscript + smooth breathing
            ('ῳ', 'add_rough_breathing', 'ᾡ'),   # omega iota subscript + rough breathing
            
            # Test adding accents to characters with breathing
            ('ἀ', 'add_acute_accent', 'ἄ'),     # smooth breathing + acute
            ('ἁ', 'add_grave_accent', 'ἃ'),     # rough breathing + grave
            ('ὠ', 'add_circumflex_accent', 'ὦ'), # smooth breathing + circumflex
            
            # Test complex combinations
            ('ἀ', 'add_acute_accent', 'ἄ'),     # First add accent to breathing
            ('ἄ', 'add_iota_subscript', 'ᾄ'),   # Then add iota subscript
        ]
        
        print("Testing diacritic combinations:")
        print("=" * 50)
        
        for input_char, method_name, expected in test_cases:
            method = getattr(self.app, method_name)
            result = method(input_char)
            
            # Normalize both for comparison
            result_norm = unicodedata.normalize('NFC', result)
            expected_norm = unicodedata.normalize('NFC', expected)
            
            status = "✓" if result_norm == expected_norm else "✗"
            print(f"{status} {input_char} -> {method_name} -> {result} (expected: {expected})")
            
            if result_norm != expected_norm:
                print(f"  Result: {[hex(ord(c)) for c in result]}")
                print(f"  Expected: {[hex(ord(c)) for c in expected]}")

if __name__ == "__main__":
    # We can't create a full Tkinter app in a test, so we'll mock the parts we need
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()  # Hide the window
        
        test_app = TestApp()
        test_app.test_diacritic_combinations()
        
        root.destroy()
        
    except Exception as e:
        print(f"Error during testing: {e}")
        print("This might be expected in a headless environment.")
