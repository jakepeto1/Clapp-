#!/usr/bin/env python3
# Simple test for the present middle infinitive issue

def extract_infinitive_stem_debug(infinitive_form, tense, voice):
    print(f"Processing: '{infinitive_form}' (tense: {tense}, voice: {voice})")
    
    if tense == "present":
        if voice in ["middle", "passive"]:
            print(f"  Form ends with 'εσθαι': {infinitive_form.endswith('εσθαι')}")
            if infinitive_form.endswith('εσθαι'):
                result = infinitive_form[:-5]  # Remove εσθαι
                print(f"  Removing 'εσθαι' (5 chars): '{result}'")
                return result
            elif infinitive_form.endswith('σθαι'):
                result = infinitive_form[:-4]  # Remove σθαι
                print(f"  Removing 'σθαι' (4 chars): '{result}'")
                return result
    
    print(f"  No match found, returning fallback")
    return infinitive_form[:-2]

# Test the problematic case
result = extract_infinitive_stem_debug("λυεσθαι", "present", "middle")
print(f"Final result: '{result}'\n")

# Test another case
result2 = extract_infinitive_stem_debug("λυσειν", "future", "active")
print(f"Final result: '{result2}'")
