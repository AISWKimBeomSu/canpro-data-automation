# -*- coding: utf-8 -*-
"""<연구 그룹명> 그룹에 사용자 기본정보 등록. 이미 있는 ID는 skip."""
import sys, re, pandas as pd
from playwright.sync_api import sync_playwright

def user_count(pg):
    m=re.search(r'개수 : (\d+)', pg.evaluate('()=>document.body.innerText'))
    return int(m.group(1)) if m else -1

GROUP='<연구 그룹명>'
INFO='data/user_info.tsv'
LOG='data/register_log.tsv'

only=None; sl=None
if len(sys.argv)>1:
    if sys.argv[1]=='--slice':
        sl=(int(sys.argv[2]), int(sys.argv[3]))
    else:
        only=set(sys.argv[1:])
logf=open(LOG,'a')
def log(*a):
    s='\t'.join(str(x) for x in a); print(s, flush=True); logf.write(s+'\n'); logf.flush()

def existing_ids(pg):
    return set(pg.evaluate('''()=>[...document.getElementById("grid3").querySelectorAll("tr.jqgrow")].map(r=>{var td=r.querySelector("td");return td?td.innerText.trim():"";}).filter(x=>x)'''))

def add_one(pg, u):
    before=user_count(pg)
    pg.get_by_role('button', name='신규 사용자 추가').first.click()
    pg.wait_for_timeout(900)
    pg.fill('#lbl5', str(u['ID'])); pg.fill('#lbl6', str(u['성명']))
    pg.fill('#lbl8', str(u['나이'])); pg.fill('#lbl9', str(u['신장'])); pg.fill('#lbl10', str(u['체중']))
    sexval='M' if str(u['성별']).strip()=='남' else 'F'
    pg.check(f'input[ng-model="userInfo.sexdstnCode"][value="{sexval}"]')
    pg.select_option('#lbl11', label=str(u['활동정도']).strip())
    pg.wait_for_timeout(250)
    # 모델 검증(ID/이름 실제 반영됐는지)
    mid=pg.evaluate('()=>{var u=angular.element(document.getElementById("lbl5")).scope().userInfo||{};return u.userId||"";}')
    if str(mid)!=str(u['ID']):
        return False, f'모델ID불일치({mid})'
    pg.wait_for_function('()=>{var b=[...document.querySelectorAll("button")].find(x=>x.innerText.trim()==="현재 사용자 정보 저장");return b && !b.disabled;}', timeout=4000)
    pg.get_by_role('button', name='현재 사용자 정보 저장').first.click()
    pg.wait_for_timeout(1200)
    for lbl in ['확인','예']:
        bt=pg.get_by_role('button', name=lbl)
        if bt.count() and bt.first.is_visible(): bt.first.click(); pg.wait_for_timeout(600); break
    after=user_count(pg)
    ingrid=pg.evaluate('(idv)=>[...document.getElementById("grid3").querySelectorAll("tr.jqgrow")].some(r=>r.innerText.includes(idv))', str(u['ID']))
    ok = (after==before+1) or ingrid
    return ok, ('등록됨' if ok else f'실패(개수 {before}->{after})')

df=pd.read_csv(INFO, sep='\t', dtype=str).fillna('')
if only: df=df[df['ID'].isin(only)]
if sl: df=df.iloc[sl[0]:sl[1]]

added=skip=fail=0; failed=[]
with sync_playwright() as p:
    b=p.chromium.connect_over_cdp('http://localhost:9222')
    pg=[x for x in b.contexts[0].pages if 'canpro' in x.url.lower()][0]
    pg.on('dialog', lambda d: d.accept())
    pg.wait_for_timeout(500)
    for lbl in ['닫기','오늘하루 열지않음']:
        for bt in pg.get_by_role('button', name=lbl).all():
            try:
                if bt.is_visible(): bt.click(timeout=800)
            except Exception: pass
    grp=pg.eval_on_selector('#lbl2','e=>e.value')
    log('### GROUP', grp)
    if GROUP not in grp:
        log('!!! 그룹 불일치 - 중단'); raise SystemExit
    have=existing_ids(pg)
    for _,u in df.iterrows():
        uid=str(u['ID'])
        if uid in have:
            skip+=1; log('SKIP', uid, u['성명'], '이미존재'); continue
        try:
            ok,msg=add_one(pg, u)
        except Exception as e:
            ok=False; msg='예외:'+str(e)[:40]
        if ok: added+=1; have.add(uid); log('OK', uid, u['성명'], u['성별'], u['나이'], u['신장'], u['체중'], u['활동정도'])
        else: fail+=1; failed.append((uid,u['성명'],msg)); log('FAIL', uid, u['성명'], msg)
    log('##### 요약 추가',added,'건너뜀',skip,'실패',fail)
    for f in failed: log('  실패:', f)
logf.close()
