#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Debug the specific issue with λύεσθαι

infinitive_form = "λύεσθαι"
print(f"Infinitive form: '{infinitive_form}'")

# Check if it ends with 'εσθαι'
if infinitive_form.endswith('εσθαι'):
    print("✓ Ends with 'εσθαι'")
    result = infinitive_form[:-5]  # Remove εσθαι (5 characters)
    print(f"After removing 'εσθαι': '{result}'")
    print(f"Length of 'εσθαι': {len('εσθαι')}")
else:
    print("✗ Does not end with 'εσθαι'")
    print(f"Last 5 characters: '{infinitive_form[-5:]}'")

# Let's check character by character
print("\nCharacter analysis:")
for i, char in enumerate(infinitive_form):
    print(f"Position {i}: '{char}' (Unicode: {ord(char)})")

# Check the ending more carefully
ending = infinitive_form[-5:]
print(f"\nLast 5 characters: '{ending}'")
expected_ending = 'εσθαι'
print(f"Expected ending: '{expected_ending}'")
print(f"Match: {ending == expected_ending}")

# Check if it's an accent issue
import unicodedata
nfd_form = unicodedata.normalize('NFD', infinitive_form)
print(f"\nNFD form: '{nfd_form}'")
print("NFD Character analysis:")
for i, char in enumerate(nfd_form):
    print(f"Position {i}: '{char}' (Unicode: {ord(char)}) Category: {unicodedata.category(char)}")
