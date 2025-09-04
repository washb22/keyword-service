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
    """카페 URL에서 ID 추출"""
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
    """두 URL이 같은 게시물인지 확인"""
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

def url_or_title_matches(target_url, target_title, candidate_link):
    """URL 또는 제목으로 매칭"""
    href = candidate_link.get_attribute("href") or ""
    link_text = candidate_link.text.strip()
    
    # URL 매칭
    if url_matches(target_url, href):
        return True
    
    # 제목 매칭 (공백 등 정규화 후 비교)
    if target_title and link_text:
        normalized_target = "".join(target_title.split()).lower()
        normalized_link = "".join(link_text.split()).lower()
        if normalized_target in normalized_link or normalized_link in normalized_target:
            return True
    
    return False

def human_sleep(a=0.8, b=1.8):
    """사람처럼 랜덤 대기"""
    time.sleep(random.uniform(a, b))

def is_valid_content_link(href):
    """'일반 인기글' 로직을 위한 유효한 콘텐츠 링크인지 확인"""
    if not href:
        return False
    
    exclude_patterns = [
        'javascript:', '#', '/search.naver', 'tab=', 'mode=', 'option=', 
        'query=', 'where=', 'sm=', 'ssc=', '/my.naver', 'help.naver', 
        'shopping.naver', 'terms.naver.com', 'nid.naver.com'
    ]
    href_lower = href.lower()
    if any(pattern in href_lower for pattern in exclude_patterns):
        return False
    
    include_patterns = [
        'blog.naver.com', 'cafe.naver.com', 'post.naver.com', 'kin.naver.com',
        'smartplace.naver', 'tv.naver.com', 'news.naver.com'
    ]
    if any(pattern in href for pattern in include_patterns):
        return True
    
    return False

# --- 메인 실행 함수 ---
def run_check(keyword: str, post_url: str, post_title: str = None) -> tuple:
    """키워드마다 다른 구조를 동적으로 파악하여 순위 측정"""
    print(f"--- '{keyword}' 순위 확인 시작 ---")
    
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1280,2200")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
    
    driver = None
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        q = urllib.parse.quote(keyword)
        
        print(f"[{keyword}] 통합검색 페이지 접근 중...")
        driver.get(f"https://search.naver.com/search.naver?query={q}")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "main_pack")))
        human_sleep()
        
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1.5)

        all_sections = driver.find_elements(By.CSS_SELECTOR, ".sc_new, .view_wrap")
        print(f"[{keyword}] {len(all_sections)}개 섹션 발견")
        
        for section in all_sections:
            try:
                if not section.is_displayed() or section.size['height'] < 50:
                    continue
                
                section_title = extract_section_title(section, keyword)
                if "쇼핑" in section_title or "광고" in section_title:
                    continue

                print(f"[{keyword}] 섹션: '{section_title}' 확인 중...")
                
                content_links = extract_content_links(section)
                if not content_links:
                    print(f"[{keyword}] '{section_title}'에서 콘텐츠 링크를 찾지 못함")
                    continue
                
                print(f"[{keyword}] '{section_title}'에서 {len(content_links)}개 콘텐츠 링크 발견")
                
                # 중복 제거
                unique_links = []
                seen_hrefs = set()
                for link in content_links:
                    href = link.get_attribute('href')
                    if href not in seen_hrefs:
                        seen_hrefs.add(href)
                        unique_links.append(link)

                # 이 섹션 내에서만 순위 카운트
                for rank, link in enumerate(unique_links, 1):
                    if url_or_title_matches(post_url, post_title, link):
                        print(f"✅ [{keyword}] '{section_title}' 섹션 내 {rank}위에서 발견!")
                        return (section_title, rank, section_title)  # 섹션 내 순위만 반환
            
            except Exception:
                continue
        
        print(f"❌ [{keyword}] 통합검색 결과에서 URL을 찾지 못함")
        return ("노출X", 999, None)

    except Exception as e:
        print(f"🚨 [{keyword}] 순위 확인 중 심각한 오류 발생: {str(e)}")
        traceback.print_exc()
        return ("확인 실패", 999, None)
    finally:
        if driver:
            driver.quit()
        print(f"--- '{keyword}' 순위 확인 완료 ---\n")

def extract_section_title(section, keyword):
    """키워드, 텍스트, 클래스명 기반으로 섹션 제목 추출"""
    try:
        title_element = section.find_element(By.CSS_SELECTOR, "[class*='headline'], .title_area .title")
        if title_element and title_element.text and len(title_element.text.strip()) > 1:
            return title_element.text.strip()
            
        section_text = section.text[:200]
        if "인기글" in section_text:
            match = re.search(r'([\w·\s]+)?인기글', section_text)
            if match:
                title = match.group(0).strip()
                if len(title) < 30: return title
            return "인기글"

        class_name = section.get_attribute("class") or ""
        if "ad" in class_name or "power_link" in class_name: return "광고"
        if "blog" in class_name: return "블로그"
        if "cafe" in class_name: return "카페"

    except Exception:
        pass
    return "검색결과"

def extract_content_links(section):
    """(최종 결정판) 스마트블록을 먼저 시도하고, 실패 시 일반 인기글 로직으로 전환"""
    content_links = []
    
    # 1. 스마트블록 로직을 최우선으로 시도
    try:
        post_text_containers = section.find_elements(By.CSS_SELECTOR, "div[class*='text-container']")
        if post_text_containers:
            for container in post_text_containers:
                try:
                    title_link = container.find_element(By.CSS_SELECTOR, "a[class*='text-title']")
                    content_links.append(title_link)
                except Exception:
                    continue
            if content_links:
                return content_links
    except Exception:
        pass

    # 2. 스마트블록이 아니라고 판단되면, '일반 인기글' 원본 로직으로 fallback
    try:
        list_items = section.find_elements(By.CSS_SELECTOR, "li")
        if not list_items:
            # li가 없는 경우, 섹션 전체에서 a 태그를 찾음
            all_links = section.find_elements(By.TAG_NAME, "a")
            for link in all_links:
                href = link.get_attribute('href')
                if is_valid_content_link(href):
                    content_links.append(link)
        else:
            # li가 있는 경우, 각 li 내부에서 유효한 링크를 찾음
            for item in list_items:
                all_links_in_item = item.find_elements(By.TAG_NAME, 'a')
                for link in all_links_in_item:
                    href = link.get_attribute('href')
                    if is_valid_content_link(href):
                        content_links.append(link)
                        break # li당 하나의 유효 링크만 찾고 다음으로 넘어감
    except Exception:
        pass

    return content_links