# app/keyword/scraper.py - 참고 프로그램 방식 기반 단순한 접근

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

# 참고 프로그램과 동일한 상수
CAFE_HOSTS = {"cafe.naver.com", "m.cafe.naver.com"}
MAIN_RESULT_SCAN_LIMIT = 15  # 통합검색에서 상위 15개만 확인
CAFE_RESULT_SCAN_LIMIT = 20  # 카페 탭에서 상위 20개만 확인

def extract_cafe_ids(url: str):
    """참고 프로그램과 동일한 카페 ID 추출"""
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
    """참고 프로그램과 동일한 URL 매칭 로직"""
    try:
        t, c = urllib.parse.urlparse(target_url), urllib.parse.urlparse(candidate_url)
    except Exception:
        return False
        
    t_host = t.netloc.split(":")[0].lower()
    c_host = c.netloc.split(":")[0].lower()

    # 네이버 카페인 경우 ID 기반 정확한 매칭
    if (t_host in CAFE_HOSTS) or (c_host in CAFE_HOSTS):
        t_ids = extract_cafe_ids(target_url)
        c_ids = extract_cafe_ids(candidate_url)
        if t_ids and c_ids and (t_ids & c_ids):
            return True
        if t_ids and any(_id in candidate_url for _id in t_ids):
            return True

    return candidate_url.startswith(target_url[: min(len(target_url), 60)])

def human_sleep(a=0.8, b=1.8):
    time.sleep(random.uniform(a, b))

def find_links_in_main_simple(driver, keyword):
    """참고 프로그램 방식: 통합검색에서 단순하게 링크 수집"""
    links = []
    try:
        print(f"[{keyword}] 통합검색 메인 페이지에서 링크 수집 중...")
        
        # 모든 HTTP 링크 수집 (참고 프로그램과 동일)
        anchors = driver.find_elements(By.CSS_SELECTOR, 'a[href^="http"]')
        print(f"[{keyword}] 전체 {len(anchors)}개 HTTP 링크 발견")
        
        for a in anchors[:200]:  # 상위 200개만 확인
            try:
                href = a.get_attribute("href") or ""
                
                # 네이버 내부 링크 제외 (참고 프로그램과 동일)
                if any(x in href for x in ["help.naver", "nid.naver", "map.naver", "dict.naver"]):
                    continue
                if "search.naver.com" in urllib.parse.urlparse(href).netloc:
                    continue
                    
                links.append(href)
            except:
                continue
        
        # 중복 제거
        seen, unique_links = set(), []
        for link in links:
            if link not in seen:
                unique_links.append(link)
                seen.add(link)
        
        result = unique_links[:MAIN_RESULT_SCAN_LIMIT]
        print(f"[{keyword}] 통합검색에서 최종 {len(result)}개 링크 검사")
        
        return result
        
    except Exception as e:
        print(f"[{keyword}] 통합검색 링크 수집 중 오류: {e}")
        return []

def click_cafe_tab_simple(driver, keyword):
    """참고 프로그램 방식: 카페 탭 클릭"""
    try:
        # 방법 1: 텍스트로 카페 탭 찾기
        tab = WebDriverWait(driver, 8).until(
            EC.element_to_be_clickable((By.XPATH, '//a[contains(@role,"tab")][contains(normalize-space(.),"카페")]'))
        )
        driver.execute_script("arguments[0].click();", tab)
        print(f"[{keyword}] 카페 탭 클릭 성공")
        human_sleep()
        return True
    except Exception:
        pass
    
    try:
        # 방법 2: where=article URL로 찾기
        tab = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, '//a[contains(@href,"where=article") or contains(@href,"where=art")]'))
        )
        driver.execute_script("arguments[0].click();", tab)
        print(f"[{keyword}] 카페 탭 클릭 성공 (방법2)")
        human_sleep()
        return True
    except Exception:
        print(f"[{keyword}] 카페 탭 클릭 실패")
        return False

def find_links_in_cafe_simple(driver, keyword):
    """참고 프로그램 방식: 카페 탭에서 단순하게 링크 수집"""
    try:
        # 카페 링크가 로드될 때까지 대기
        try:
            WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[href^='https://cafe.naver.com/'], a[href^='https://m.cafe.naver.com/']"))
            )
        except Exception:
            pass
        
        # 카페 링크들 수집 (참고 프로그램과 동일)
        anchors = driver.find_elements(By.CSS_SELECTOR, "a[href^='https://cafe.naver.com/'], a[href^='https://m.cafe.naver.com/']")
        print(f"[{keyword}] 카페 탭에서 {len(anchors)}개 카페 링크 발견")
        
        links = []
        for a in anchors[:120]:  # 상위 120개만
            try:
                href = a.get_attribute("href") or ""
                if href:
                    links.append(href)
            except:
                continue
        
        # 중복 제거
        seen, unique_links = set(), []
        for link in links:
            if link not in seen:
                unique_links.append(link)
                seen.add(link)
        
        result = unique_links[:CAFE_RESULT_SCAN_LIMIT]
        print(f"[{keyword}] 카페 탭에서 최종 {len(result)}개 링크 검사")
        
        return result
        
    except Exception as e:
        print(f"[{keyword}] 카페 탭 링크 수집 중 오류: {e}")
        return []

def run_check(keyword: str, post_url: str) -> tuple:
    """참고 프로그램 방식: 단순하고 확실한 방법"""
    print(f"--- '{keyword}' 순위 확인 시작 (참고 프로그램 방식) ---")
    
    # 참고 프로그램과 동일한 옵션
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
        driver.implicitly_wait(2)  # 참고 프로그램과 동일
        
        # 네이버 검색 (참고 프로그램과 동일)
        q = urllib.parse.quote(keyword)
        url = f"https://search.naver.com/search.naver?query={q}"
        print(f"[{keyword}] 네이버 검색: {url}")
        
        driver.get(url)
        human_sleep()
        
        # 1단계: 통합검색 메인에서 확인
        main_links = find_links_in_main_simple(driver, keyword)
        for rank, href in enumerate(main_links, 1):
            if url_matches(post_url, href):
                print(f"[{keyword}] 통합검색 {rank}위에서 발견!")
                return ("통합검색", rank, "통합검색")
        
        print(f"[{keyword}] 통합검색에서 못 찾음. 카페 탭으로 이동...")
        
        # 2단계: 카페 탭에서 확인
        if click_cafe_tab_simple(driver, keyword):
            cafe_links = find_links_in_cafe_simple(driver, keyword)
            for rank, href in enumerate(cafe_links, 1):
                if url_matches(post_url, href):
                    print(f"[{keyword}] 카페 탭 {rank}위에서 발견!")
                    return ("노출X", None, None)  # 참고 프로그램: 카페탭에만 있으면 통합검색 노출X
            
            print(f"[{keyword}] 카페 탭에서도 못 찾음")
            return ("저품질", None, None)  # 참고 프로그램: 카페탭에도 없으면 저품질
        else:
            print(f"[{keyword}] 카페 탭 접근 실패")
            return ("노출X", None, None)

    except Exception as e:
        print(f"[{keyword}] 순위 확인 중 오류: {str(e)}")
        traceback.print_exc()
        return ("확인 실패", None, None)
    finally:
        if driver:
            driver.quit()
        print(f"--- '{keyword}' 순위 확인 완료 ---")

# 하위 호환성
def check_smart_blocks(driver, keyword, post_url):
    return None

def check_view_section(driver, keyword, post_url):
    return None

def extract_block_title(block_element, keyword):
    return "통합검색"