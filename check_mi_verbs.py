#!/usr/bin/env python3
import json

with open('paradigms.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

mi_verbs = ['didomi', 'tithemi', 'histemi', 'hiemi']
for verb in mi_verbs:
    paradigm_key = f'{verb}_aor_ind_act'
    if paradigm_key in data:
        paradigm = data[paradigm_key]
        print(f'{verb.upper()} Aorist Indicative Active:')
        print(f'  Lemma: {paradigm.get("lemma", "Not found")}')
        for person in ['1st_sg', '2nd_sg', '3rd_sg', '1st_pl', '2nd_pl', '3rd_pl']:
            print(f'  {person}: {paradigm.get(person, "Not found")}')
        print()
    else:
        print(f'{verb.upper()}: Paradigm not found')
