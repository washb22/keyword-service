# app/keyword/scraper.py

import time
import random
import urllib.parse
import re
import traceback
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- 보조 함수들 ---
CAFE_HOSTS = {"cafe.naver.com", "m.cafe.naver.com"}

def extract_cafe_ids(url: str):
    try: 
        p = urllib.parse.urlparse(url)
    except Exception: 
        return set()
    ids = set()
    qs = urllib.parse.parse_qs(p.query)
    for key in ("articleid", "clubid", "articleId", "clubId"):
        for val in qs.get(key, []):
            if val.isdigit(): 
                ids.add(val)
    for token in re.split(r"[/?=&]", p.path):
        if token.isdigit() and len(token) >= 4: 
            ids.add(token)
    return ids

def url_matches(target_url: str, candidate_url: str) -> bool:
    try: 
        t, c = urllib.parse.urlparse(target_url), urllib.parse.urlparse(candidate_url)
    except Exception: 
        return False
    t_host, c_host = t.netloc.split(":")[0].lower(), c.netloc.split(":")[0].lower()
    if (t_host in CAFE_HOSTS) or (c_host in CAFE_HOSTS):
        t_ids, c_ids = extract_cafe_ids(target_url), extract_cafe_ids(candidate_url)
        if t_ids and c_ids and (t_ids & c_ids): 
            return True
        if t_ids and any(_id in candidate_url for _id in t_ids): 
            return True
    return candidate_url.startswith(target_url[: min(len(target_url), 60)])

def human_sleep(a=0.8, b=1.8):
    time.sleep(random.uniform(a, b))

# --- 메인 실행 함수 (이전 작동 방식 + 스마트블록 추가) ---
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
        
        # 1. 통합검색 페이지에서 스마트블록들과 VIEW 모두 확인
        print(f"[{keyword}] 통합검색 페이지 접근 중...")
        driver.get(f"https://search.naver.com/search.naver?query={q}")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "main_pack")))
        human_sleep()

        # 1-1. 먼저 스마트블록들에서 확인 (더 구체적인 정보이므로 우선)
        smart_result = check_smart_blocks(driver, keyword, post_url)
        if smart_result:
            return smart_result

        # 1-2. VIEW 영역에서 확인
        view_result = check_view_section(driver, keyword, post_url)
        if view_result:
            return view_result

        # 2. 통합검색에서 못 찾으면 직접 VIEW 탭으로 이동 (이전 방식)
        print(f"[{keyword}] 통합검색에서 못 찾음. 직접 VIEW 탭으로 이동...")
        driver.get(f"https://search.naver.com/search.naver?where=view&query={q}")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "main_pack")))
        human_sleep()

        view_items = driver.find_elements(By.CSS_SELECTOR, "#main_pack .view_wrap")
        print(f"[VIEW 탭] {len(view_items)}개 항목 발견")

        for index, item in enumerate(view_items):
            rank = index + 1
            links = item.find_elements(By.CSS_SELECTOR, 'a.title_link, a.dsc_link, a.api_txt_lines, a[href*="cafe.naver.com"]')
            for link in links:
                href = link.get_attribute("href") or ""
                if url_matches(post_url, href):
                    print(f"[VIEW 탭] {rank}위에서 발견!")
                    return ("VIEW", rank, "VIEW")

        # 3. 카페 탭에서 확인 (이전 방식)
        print(f"[{keyword}] VIEW 탭에서도 못 찾음. 카페 탭으로 이동...")
        driver.get(f"https://search.naver.com/search.naver?where=article&query={q}")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "main_pack")))
        human_sleep()
        
        cafe_items = driver.find_elements(By.CSS_SELECTOR, "#main_pack ul.lst_total > li")
        print(f"[카페 탭] {len(cafe_items)}개 항목 발견")

        for index, item in enumerate(cafe_items):
            rank = index + 1
            try:
                link = item.find_element(By.CSS_SELECTOR, 'a.total_dsc')
                href = link.get_attribute("href") or ""
                if url_matches(post_url, href):
                    print(f"[카페 탭] {rank}위에서 발견!")
                    return ("노출X", None, None)  # 카페탭에만 있으면 통합검색 노출X
            except:
                continue
        
        print(f"[{keyword}] 모든 탭에서 URL을 찾지 못함")
        return ("노출X", None, None)

    except Exception as e:
        print(f"[{keyword}] 순위 확인 중 오류 발생: {str(e)}")
        traceback.print_exc()
        return ("확인 실패", None, None)
    finally:
        if driver:
            driver.quit()
        print(f"--- '{keyword}' 순위 확인 완료 ---")


def check_smart_blocks(driver, keyword, post_url):
    """스마트블록에서 확인"""
    try:
        smart_blocks = driver.find_elements(By.CSS_SELECTOR, ".sc_new")
        print(f"[{keyword}] {len(smart_blocks)}개 스마트블록 발견")
        
        for block_idx, block in enumerate(smart_blocks, 1):
            try:
                # 블록 제목 추출
                section_name = extract_block_title(block, keyword)
                print(f"[{keyword}] 스마트블록 {block_idx}: '{section_name}' 확인 중...")
                
                # 블록 내 링크들을 순서대로 확인
                links = block.find_elements(By.CSS_SELECTOR, 'a[href*="cafe.naver.com"]')
                print(f"[{keyword}] '{section_name}' 블록에서 {len(links)}개 링크 발견")
                
                for rank, link in enumerate(links, 1):
                    href = link.get_attribute("href") or ""
                    if url_matches(post_url, href):
                        print(f"[{keyword}] '{section_name}' 블록 {rank}위에서 발견!")
                        return (section_name, rank, section_name)
                        
            except Exception as e:
                print(f"[{keyword}] 블록 {block_idx} 처리 중 오류: {e}")
                continue
        
        return None
    except Exception as e:
        print(f"[{keyword}] 스마트블록 확인 중 오류: {e}")
        return None


def check_view_section(driver, keyword, post_url):
    """통합검색 페이지의 VIEW 섹션에서 확인"""
    try:
        view_section = driver.find_elements(By.CSS_SELECTOR, ".view_wrap")
        if not view_section:
            return None
            
        print(f"[{keyword}] 통합검색 VIEW 섹션 확인 중...")
        
        # VIEW 섹션 내의 모든 링크를 순서대로 확인
        links = view_section[0].find_elements(By.CSS_SELECTOR, 'a[href*="cafe.naver.com"]')
        print(f"[{keyword}] VIEW 섹션에서 {len(links)}개 링크 발견")
        
        for rank, link in enumerate(links, 1):
            href = link.get_attribute("href") or ""
            if url_matches(post_url, href):
                print(f"[{keyword}] VIEW 섹션 {rank}위에서 발견!")
                return ("VIEW", rank, "VIEW")
        
        return None
    except Exception as e:
        print(f"[{keyword}] VIEW 섹션 확인 중 오류: {e}")
        return None


def extract_block_title(block_element, keyword):
    """스마트블록의 제목 추출 (간단한 방식)"""
    try:
        # 가장 일반적인 제목 태그들 확인
        title_selectors = ['h2', 'h3', '.title']
        
        for selector in title_selectors:
            try:
                title_elem = block_element.find_element(By.CSS_SELECTOR, selector)
                title_text = title_elem.text.strip()
                
                # 제목이 있고, 너무 길지 않으면 사용
                if title_text and len(title_text) < 100 and not title_text.endswith('?'):
                    return title_text
            except:
                continue
        
        # 제목을 찾지 못하면 키워드 기반 이름
        return f"{keyword} 관련"
        
    except:
        return f"{keyword} 관련"