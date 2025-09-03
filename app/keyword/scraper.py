# app/keyword/scraper.py

import time
import random
import urllib.parse
import re
import traceback # 에러 출력을 위해 추가
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- 보조 함수들 (변경 없음) ---
CAFE_HOSTS = {"cafe.naver.com", "m.cafe.naver.com"}
def extract_cafe_ids(url: str):
    try: p = urllib.parse.urlparse(url)
    except Exception: return set()
    ids = set(); qs = urllib.parse.parse_qs(p.query)
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

# --- 메인 실행 함수 (로직 대폭 개선) ---
def run_check(keyword: str, post_url: str) -> tuple:
    print(f"--- '{keyword}' 순위 확인 시작 ---")
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
        q = urllib.parse.quote(keyword)
        
        # 1. 통합검색 VIEW 영역 먼저 확인
        driver.get(f"https://search.naver.com/search.naver?where=view&query={q}")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "main_pack")))
        human_sleep()

        # 좀 더 포괄적인 선택자로 변경
        view_items = driver.find_elements(By.CSS_SELECTOR, "#main_pack .view_wrap")
        print(f"[VIEW] 검색 결과 {len(view_items)}개 항목을 찾았습니다.")

        for index, item in enumerate(view_items):
            rank = index + 1
            # 제목 링크를 직접 찾는 방식으로 변경
            links = item.find_elements(By.CSS_SELECTOR, 'a.title_link, a.dsc_link, a.api_txt_lines')
            for link in links:
                href = link.get_attribute("href") or ""
                if url_matches(post_url, href):
                    print(f"성공! VIEW {rank}위에서 URL을 찾았습니다.")
                    return ("VIEW 노출", rank)

        print("[VIEW] 에서는 URL을 찾지 못했습니다. '카페' 탭을 확인합니다.")
        
        # 2. 통합검색에서 못 찾으면 '카페' 탭 확인
        driver.get(f"https://search.naver.com/search.naver?where=article&query={q}")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "main_pack")))
        human_sleep()
        
        cafe_items = driver.find_elements(By.CSS_SELECTOR, "#main_pack ul.lst_total > li")
        print(f"[카페] 검색 결과 {len(cafe_items)}개 항목을 찾았습니다.")

        for index, item in enumerate(cafe_items):
            rank = index + 1
            link = item.find_element(By.CSS_SELECTOR, 'a.total_dsc')
            href = link.get_attribute("href") or ""
            if url_matches(post_url, href):
                print(f"성공! 카페 {rank}위에서 URL을 찾았습니다.")
                return ("카페 노출", rank)
        
        # 3. 어디에서도 찾지 못하면 '노출X'
        print("어디에서도 URL을 찾지 못했습니다.")
        return ("노출X", None)
    except Exception as e:
        print("!!! 순위 확인 중 심각한 오류 발생 !!!")
        traceback.print_exc() # 터미널에 전체 에러 로그 출력
        return ("확인 실패", None)
    finally:
        if driver:
            driver.quit()
        print(f"--- '{keyword}' 순위 확인 종료 ---")