# -*- coding: utf-8 -*-
"""미매칭 음식별 DB 후보 제시(rapidfuzz + 부분일치)."""
import pandas as pd, re
import foodmap
from rapidfuzz import process, fuzz
DB='data/Food_Database_Complete.xlsx'
db=pd.read_excel(DB, sheet_name='음식_전체_DB'); db['식품명']=db['식품명'].astype(str).str.strip()
DBSET=list(db['식품명'])
MAP=dict(foodmap.MAP); NOENTRY=set(foodmap.NOENTRY)

df=pd.read_csv('input_raw.tsv', sep='\t', dtype=str).fillna('')
uniq=[]
seen=set()
for _,r in df.iterrows():
    food=r['음식명'].strip()
    if food=='' or food.lower()=='x' or '섭취' in r['시간대']: continue
    if food in NOENTRY: continue
    if food in MAP or food in DBSET: continue
    if food in seen: continue
    seen.add(food); uniq.append(food)

def cands(food):
    # 부분일치 우선(음식명이 DB식품명에 포함되거나 그 역)
    subs=[d for d in DBSET if food in d or d in food]
    # 핵심어(마지막 명사 위주) 부분일치
    core=re.sub(r'\s+','',food)
    fz=[m[0] for m in process.extract(food, DBSET, scorer=fuzz.WRatio, limit=6)]
    out=[]
    for x in subs[:5]+fz:
        if x not in out: out.append(x)
    return out[:8]

for f in uniq:
    print(f'■ {f}')
    print('   →', ' | '.join(cands(f)))
