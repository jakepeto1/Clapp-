#!/usr/bin/env python3
import json

with open('paradigms.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print('ΦΗΜΙ Present Indicative Active:')
if 'phemi_pres_ind_act' in data:
    paradigm = data['phemi_pres_ind_act']
    print(f'  Lemma: {paradigm.get("lemma", "Not found")}')
    for person in ['1st_sg', '2nd_sg', '3rd_sg', '1st_pl', '2nd_pl', '3rd_pl']:
        form = paradigm.get(person, 'Not found')
        print(f'  {person}: {form}')
else:
    print('  Paradigm not found')

print('\nΦΗΜΙ Imperfect Indicative Active:')
if 'phemi_impf_ind_act' in data:
    paradigm = data['phemi_impf_ind_act']
    for person in ['1st_sg', '2nd_sg', '3rd_sg', '1st_pl', '2nd_pl', '3rd_pl']:
        form = paradigm.get(person, 'Not found')
        print(f'  {person}: {form}')
else:
    print('  Paradigm not found')
