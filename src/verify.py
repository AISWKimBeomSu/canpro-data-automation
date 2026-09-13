# -*- coding: utf-8 -*-
"""배치10 검토: CANPRO 실입력 데이터를 (참가자,날짜,끼니)별로 읽어 mapped_rows 기대값과 대조."""
import pandas as pd
from playwright.sync_api import sync_playwright
from engine import connect, select_group, select_user, set_date, set_meal, meal_codes

GROUP='<연구 그룹명>'
MEALS_ORDER=['아침','오전간식','점심','오후간식','저녁','야식']
m=pd.read_csv('mapped_rows.tsv', sep='\t', dtype=str)
m['code6']=m['식품번호'].apply(lambda x: str(x).zfill(6))

part_order=list(dict.fromkeys(m['ID'].tolist()))
report=[]; tot_exp=0; tot_found=0; tot_datefail=0

with sync_playwright() as p:
    b,page=connect(p)
    select_group(page, GROUP)
    for pid in part_order:
        pm=m[m['ID']==pid]; name=pm['성명'].iloc[0]
        select_user(page, pid)
        missing=[]; datefail=[]; exp_n=0; found_n=0; ndates=0
        for date in sorted(pm['조회일'].unique()):
            dm=pm[pm['조회일']==date]
            try:
                set_date(page, date)
            except Exception as e:
                datefail.append(date); tot_datefail+=1; continue
            # 날짜 실제 반영 재확인
            cur=page.eval_on_selector('#lbl3','e=>e.value')
            if cur!=date:
                datefail.append(f'{date}(현재{cur})'); tot_datefail+=1; continue
            ndates+=1
            for meal in [me for me in MEALS_ORDER if me in dm['식사종류'].values]:
                set_meal(page, meal)
                actual=set(str(x) for x in meal_codes(page))
                exp=set(dm[dm['식사종류']==meal]['code6'])
                exp_n+=len(exp)
                for c in exp:
                    if c in actual: found_n+=1
                    else:
                        row=dm[(dm['식사종류']==meal)&(dm['code6']==c)].iloc[0]
                        missing.append(f"{date}|{meal}|{row['원본음식']}→{row['매칭음식']}({c})")
        tot_exp+=exp_n; tot_found+=found_n
        status='OK' if (not missing and not datefail) else '⚠️'
        report.append((pid,name,exp_n,found_n,ndates,missing,datefail,status))
        print(f"{status} {pid} {name}: 기대{exp_n} 확인{found_n} 날짜{ndates}개"
              + (f" | 누락{len(missing)}" if missing else "")
              + (f" | 날짜실패{len(datefail)}" if datefail else ""), flush=True)

print('\n===== 검토 요약 =====')
print(f"총 기대 {tot_exp} / 확인 {tot_found} / 미확인 {tot_exp-tot_found} / 날짜실패 {tot_datefail}")
prob=[r for r in report if r[5] or r[6]]
if not prob:
    print('✅ 전 참가자 날짜·음식 100% 일치(모든 매핑음식이 올바른 조회일/끼니에 존재)')
else:
    print(f'⚠️ 문제 참가자 {len(prob)}명:')
    for pid,name,en,fn,nd,miss,df,st in prob:
        if df: print(f'  {pid} {name} 날짜실패: {df}')
        for x in miss: print(f'  {pid} {name} 누락: {x}')
