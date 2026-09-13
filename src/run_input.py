# -*- coding: utf-8 -*-
"""배치 자동입력. 그룹=<연구 그룹명>. 기존/중복 skip. 세션만료/날짜실패시 중단."""
import sys, pandas as pd
from playwright.sync_api import sync_playwright
from engine import connect, select_group, select_user, set_date, set_meal, add_food, meal_codes, SessionExpired, DateSetError

GROUP='<연구 그룹명>'
MEALS_ORDER=['아침','오전간식','점심','오후간식','저녁','야식']
LOG='data/run_log.tsv'
MAPPED='data/mapped_rows.tsv'

only=set(sys.argv[1:]) if len(sys.argv)>1 else None
m=pd.read_csv(MAPPED, sep='\t', dtype=str)
part_order=list(dict.fromkeys(m['ID'].tolist()))
if only: part_order=[p for p in part_order if p in only]

logf=open(LOG,'a')
def log(*a):
    line='\t'.join(str(x) for x in a); print(line, flush=True); logf.write(line+'\n'); logf.flush()

stats={}
aborted=False
with sync_playwright() as p:
    b, page = connect(p)
    select_group(page, GROUP)
    log('### GROUP', GROUP)
    try:
        for pid in part_order:
            pm=m[m['ID']==pid]; name=pm['성명'].iloc[0]
            select_user(page, pid)
            st={'added':0,'skip':0,'fail':0,'failed':[]}
            log('### USER', pid, name)
            for date in sorted(pm['조회일'].unique()):
                dm=pm[pm['조회일']==date]; set_date(page, date)
                for meal in [me for me in MEALS_ORDER if me in dm['식사종류'].values]:
                    set_meal(page, meal)
                    existing=set(str(x) for x in meal_codes(page)); seen=set()
                    for _,r in dm[dm['식사종류']==meal].iterrows():
                        code6=str(r['식품번호']).zfill(6)
                        tag=f"{pid}|{date}|{meal}|{r['원본음식']}→{r['매칭음식']}({code6})"
                        if code6 in existing or code6 in seen:
                            st['skip']+=1; log('SKIP', tag); continue
                        ok,msg=add_food(page, r['식품번호'])
                        seen.add(code6)
                        if ok: existing.add(code6); st['added']+=1; log('OK', tag)
                        else: st['fail']+=1; st['failed'].append(tag); log('FAIL', tag, msg)
            stats[pid]=(name,st)
            log('=== DONE', pid, name, 'added',st['added'],'skip',st['skip'],'fail',st['fail'])
    except SessionExpired as e:
        aborted=True
        log('!!! 중단(세션만료):', str(e), '| 재로그인 후 재실행하면 이어서 진행됨')
    except DateSetError as e:
        aborted=True
        log('!!! 중단(날짜설정실패):', str(e), '| 잘못된 날짜 입력 방지 위해 정지')

log('\n##### 배치 요약'+(' (중단됨)' if aborted else '')+' #####')
ta=ts=tf=0
for pid,(name,st) in stats.items():
    ta+=st['added']; ts+=st['skip']; tf+=st['fail']
    log(f"{pid} {name}: 추가{st['added']} 건너뜀{st['skip']} 실패{st['fail']}")
    for f in st['failed']: log('   실패:', f)
log(f"합계: 추가 {ta} / 건너뜀 {ts} / 실패 {tf}")
logf.close()
