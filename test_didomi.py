#!/usr/bin/env python3
import json

# Load paradigms
with open('paradigms.json', 'r', encoding='utf-8') as f:
    paradigms = json.load(f)

# Check didomi aorist indicative active paradigm
if 'didomi_aor_ind_act' in paradigms:
    paradigm = paradigms['didomi_aor_ind_act']
    print("Found didomi_aor_ind_act paradigm:")
    print(f"Lemma: {paradigm.get('lemma', 'Not found')}")
    print(f"1st_sg: {paradigm.get('1st_sg', 'Not found')}")
    print(f"2nd_sg: {paradigm.get('2nd_sg', 'Not found')}")
    print(f"3rd_sg: {paradigm.get('3rd_sg', 'Not found')}")
    print(f"1st_pl: {paradigm.get('1st_pl', 'Not found')}")
    print(f"2nd_pl: {paradigm.get('2nd_pl', 'Not found')}")
    print(f"3rd_pl: {paradigm.get('3rd_pl', 'Not found')}")
else:
    print("didomi_aor_ind_act paradigm not found!")

# Check all didomi paradigms
didomi_paradigms = [key for key in paradigms.keys() if key.startswith('didomi_')]
print(f"\nFound {len(didomi_paradigms)} didomi paradigms:")
for paradigm_key in didomi_paradigms:
    print(f"- {paradigm_key}")
