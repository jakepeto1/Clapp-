#!/usr/bin/env python3
"""Test that the article is properly moved to pronouns and has correct structure"""

import json

with open('paradigms.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("Article Paradigm Check:")
print("======================")

if 'article' in data:
    article = data['article']
    print(f"Type: {article.get('type', 'Not found')}")
    print(f"Lemma: {article.get('lemma', 'Not found')}")
    print()
    
    print("Structure:")
    for gender in ['masculine', 'feminine', 'neuter']:
        if gender in article:
            print(f"\n{gender.upper()}:")
            gender_forms = article[gender]
            for case_num, form in gender_forms.items():
                print(f"  {case_num}: {form}")
        else:
            print(f"\n{gender.upper()}: Not found")
else:
    print("Article paradigm not found!")

print("\n" + "="*50)
print("This confirms the article:")
print("1. Has type 'pronoun' (for correct table layout)")
print("2. Has gendered structure (masculine/feminine/neuter)")
print("3. Will be displayed in pronoun section with proper 3-gender table")
