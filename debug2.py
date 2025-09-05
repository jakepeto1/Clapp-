#!/usr/bin/env python3
# Debug specific case

infinitive_form = "λυεσθαι"
print(f"Form: '{infinitive_form}' (length: {len(infinitive_form)})")

if infinitive_form.endswith('εσθαι'):
    print("✓ Ends with 'εσθαι'")
    result = infinitive_form[:-5]
    print(f"Result after removing 5 chars: '{result}'")
    print(f"Should be 'λυ'")
else:
    print("✗ Doesn't end with 'εσθαι'")

# Let's also check the future case
fut_form = "λυσειν"
print(f"\nFuture form: '{fut_form}' (length: {len(fut_form)})")

if fut_form.endswith('σειν'):
    print("✓ Ends with 'σειν'")
    result = fut_form[:-3]  # Remove ειν
    print(f"Result after removing 3 chars (ειν): '{result}'")
    print(f"Should be 'λυσ'")
else:
    print("✗ Doesn't end with 'σειν'")
    
# Wait, let me check if it's a different ending
print(f"Last 4 chars of fut_form: '{fut_form[-4:]}'")
if fut_form.endswith('ειν'):
    print("✓ Ends with 'ειν'")
    result = fut_form[:-3]
    print(f"Result after removing 3 chars (ειν): '{result}'")
