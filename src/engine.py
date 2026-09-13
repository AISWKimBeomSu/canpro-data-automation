# -*- coding: utf-8 -*-
"""캔프로 24시간 회상법 자동입력 엔진."""
import time
from playwright.sync_api import sync_playwright
from lib import CDP

def connect(p):
    b=p.chromium.connect_over_cdp(CDP)
    ctx=b.contexts[0]
    cand=[pg for pg in ctx.pages if 'ntkFoodLst' in pg.url]
    if not cand: cand=[pg for pg in ctx.pages if 'canpro' in pg.url.lower()]
    page=cand[0] if cand else ctx.pages[0]
    return b, page

def select_group(page, group_label):
    val=page.evaluate('(g)=>{const s=document.getElementById("lbl1");const o=[...s.options].find(o=>o.text.includes(g));return o?o.value:null;}', group_label)
    if val is None: raise RuntimeError(f'그룹 옵션 없음: {group_label}')
    page.select_option('#lbl1', value=val)
    page.wait_for_timeout(1200)

def select_user(page, idtext):
    val=page.evaluate('(idt)=>{const s=document.getElementById("lbl2");const o=[...s.options].find(o=>o.text.includes(idt));return o?o.value:null;}', idtext)
    if val is None: raise RuntimeError(f'사용자 옵션 없음: {idtext}')
    page.select_option('#lbl2', value=val)
    page.wait_for_timeout(1200)

class DateSetError(Exception):
    pass

def _cur_date(page):
    try: return page.eval_on_selector('#lbl3','e=>e.value')
    except Exception: return None

def set_date(page, date):
    """조회일을 date로 설정하고 실제 반영 검증(최대 3회). 실패시 DateSetError."""
    for _ in range(3):
        page.evaluate('(d)=>{var el=document.getElementById("lbl3");if(!el)return;var ng=angular.element(el);ng.val(d);ng.triggerHandler("input");try{ng.scope().$apply()}catch(e){}}', date)
        page.wait_for_timeout(1500)
        if _cur_date(page)==date:
            return
    raise DateSetError(f'조회일 설정실패: 목표 {date} / 현재 {_cur_date(page)}')

def set_meal(page, meal):
    page.select_option('#lbl10', label=meal)
    page.wait_for_timeout(1000)

def meal_codes(page):
    return page.evaluate('''()=>[...document.getElementById("ntkMealGrid").querySelectorAll("tr.jqgrow")].map(r=>r.querySelector("td")?.innerText.trim())''')

class SessionExpired(Exception):
    pass

def ensure_search_tab(page):
    """검색패널의 '음식검색어' 탭이 숨겨져 있으면 활성화(탭 클릭만; 모델은 안건드림)."""
    page.evaluate('''()=>{
      var inp=document.querySelector('[ng-model="foodInfo.foodCode"]');
      if(!inp) return;
      var pane=inp; while(pane && !(pane.classList&&pane.classList.contains('tab-pane'))) pane=pane.parentElement;
      if(pane && getComputedStyle(pane).display==='none'){
        var tc=pane.parentElement; var idx=[...tc.children].indexOf(pane);
        var nav=tc.previousElementSibling, hop=0;
        while(nav && !(nav.querySelector&&nav.querySelector('a[ng-click]')) && hop<5){nav=nav.previousElementSibling;hop++;}
        if(nav){ var links=nav.querySelectorAll('li a[ng-click]'); if(links[idx]) links[idx].click(); }
      }
    }''')
    page.wait_for_timeout(200)

def add_food(page, code):
    """식품번호 code를 음식코드로 검색→행선택→추가. (원본방식: 라디오 실제클릭+fill+모델검증)"""
    c6=str(code).zfill(6)
    if 'egovLoginUsr' in page.url or not page.query_selector('#lbl1'):
        raise SessionExpired('세션만료(로그인페이지)')
    ensure_search_tab(page)
    page.check('#lbl6')                                   # 음식코드 라디오 실제 클릭
    box=page.locator('[ng-model="foodInfo.foodCode"]')
    box.wait_for(state='visible', timeout=4000)
    box.click(); box.fill(c6)
    page.wait_for_timeout(150)
    # Angular 모델 동기화 확인 (안되면 폴백)
    mc=page.evaluate('()=>{var s=angular.element(document.getElementById("lbl6")).scope();return (s.foodInfo&&s.foodInfo.foodCode)||"";}')
    if str(mc)!=c6:
        page.evaluate('(c)=>{var s=angular.element(document.getElementById("lbl6")).scope();s.foodRadioBtn="foodCode";s.foodInfo.foodCode=c;s.$apply();}', c6)
        page.wait_for_timeout(100)
    page.get_by_role('button', name='검색').first.click()
    # 검색결과에서 첫 셀이 정확히 c6인 행을 대기 후 클릭
    try:
        page.wait_for_function('(c)=>{var t=document.getElementById("gridFoodSearch");if(!t)return false;return [...t.querySelectorAll("tr.jqgrow")].some(r=>r.querySelector("td")&&r.querySelector("td").innerText.trim()===c);}', arg=c6, timeout=4000)
    except Exception:
        return False, '검색결과없음'
    # 정확한 행 클릭
    clicked=page.evaluate('''(c)=>{var t=document.getElementById("gridFoodSearch");var rows=[...t.querySelectorAll("tr.jqgrow")];var r=rows.find(x=>x.querySelector("td")&&x.querySelector("td").innerText.trim()===c);if(r){r.querySelector("td").click();return true;}return false;}''', c6)
    page.wait_for_timeout(300)
    before=meal_codes(page)
    page.get_by_role('button', name='섭취음식 목록에 추가').first.click()
    page.wait_for_timeout(900)
    after=[str(x) for x in meal_codes(page)]
    ok = c6 in after and len(after)>len(before)
    return ok, ('추가됨' if ok else f'추가안됨 b={before} a={after}')
