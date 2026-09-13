"""캔프로 자동화 공용 헬퍼. CDP로 떠있는 크롬에 연결한다."""
from playwright.sync_api import sync_playwright

CDP = "http://localhost:9222"
SHOT_DIR = "shots"

def get_page(p):
    """현재 떠있는 첫 컨텍스트의 첫 페이지를 돌려준다."""
    browser = p.chromium.connect_over_cdp(CDP)
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    return browser, ctx, page
