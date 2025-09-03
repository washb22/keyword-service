# app/keyword/scraper.py

import time, random, urllib.parse, re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# (main.py에 있던 URL 매칭 함수들을 그대로 가져옴)
CAFE_HOSTS = {"cafe.naver.com", "m.cafe.naver.com"}
def extract_cafe_ids(url: str):
    try: p = urllib.parse.urlparse(url)
    except Exception: return set()
    ids = set()
    qs = urllib.parse.parse_qs(p.query)
    for key in ("articleid", "clubid", "articleId", "clubId"):
        for val in qs.get(key, []):
            if val.isdigit(): ids.add(val)
    for token in re.split(r"[/?=&]", p.path):
        if token.isdigit() and len(token) >= 4: ids.add(token)
    return ids

def url_matches(target_url: str, candidate_url: str) -> bool:
    try: t, c = urllib.parse.urlparse(target_url), urllib.parse.urlparse(candidate_url)
    except Exception: return False
    t_host, c_host = t.netloc.split(":")[0].lower(), c.netloc.split(":")[0].lower()
    if (t_host in CAFE_HOSTS) or (c_host in CAFE_HOSTS):
        t_ids, c_ids = extract_cafe_ids(target_url), extract_cafe_ids(candidate_url)
        if t_ids and c_ids and (t_ids & c_ids): return True
        if t_ids and any(_id in candidate_url for _id in t_ids): return True
    return candidate_url.startswith(target_url[: min(len(target_url), 60)])

def human_sleep(a=0.8, b=1.8):
    time.sleep(random.uniform(a, b))

# --- 순찰 봇 메인 함수 ---
def run_check(keyword: str, post_url: str) -> str:
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1280,2200")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    
    driver = None
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.implicitly_wait(2)
        
        q = urllib.parse.quote(keyword)
        driver.get(f"https://search.naver.com/search.naver?query={q}")
        human_sleep()

        # 통합검색 확인
        main_links = driver.find_elements(By.CSS_SELECTOR, 'a[href^="http"]')
        for a in main_links[:20]:
            href = a.get_attribute("href") or ""
            if url_matches(post_url, href):
                return "최상단 노출"
        
        # 카페 탭 클릭
        try:
            tab = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, '//a[contains(@role,"tab")][contains(normalize-space(.),"카페")]')))
            driver.execute_script("arguments[0].click();", tab)
            human_sleep()
        except Exception:
            return "노출X" # 카페 탭을 못 찾으면 더 이상 확인 불가

        # 카페 탭 검색 결과 확인
        cafe_links = driver.find_elements(By.CSS_SELECTOR, "a[href^='https://cafe.naver.com/'], a[href^='https://m.cafe.naver.com/']")
        for a in cafe_links[:100]:
            href = a.get_attribute("href") or ""
            if url_matches(post_url, href):
                return "노출X" # 통합검색이 아닌 카페 탭에서만 노출
        
        return "저품질" # 어디에도 없음
    finally:
        if driver:
            driver.quit()