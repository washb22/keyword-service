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
    """(개선) XPath와 텍스트 분석을 통해 더욱 정교하게 섹션 제목 추출"""
    try:
        # 1. (기존 로직) 스마트블록/신규 섹션의 명시적 헤드라인 우선 탐색
        # 섹션 내부에 h2, h3, a 태그 중에 title 클래스를 가진게 있는지 확인
        title_element = section.find_element(By.CSS_SELECTOR, "h2.title, h3.title, a.title, [class*='headline']")
        if title_element and title_element.text and len(title_element.text.strip()) > 1:
            title_text = title_element.text.strip()
            # "더보기" 같은 불필요한 텍스트 제거
            if "더보기" in title_text:
                title_text = title_text.split("더보기")[0].strip()
            return title_text

        # 2. (✨신규 로직✨) XPath를 사용해 섹션 바로 '이전' 요소에서 제목 탐색
        # "건강·의학 인기글" 같은 제목은 섹션 밖에 위치하는 경우가 많습니다.
        try:
            # 바로 직전의 형제 요소(div, h2 등)를 찾습니다.
            prev_sibling = section.find_element(By.XPATH, "./preceding-sibling::*[1]")
            prev_text = prev_sibling.text.strip()
            if "인기글" in prev_text and len(prev_text) < 50:
                 return prev_text
        except Exception:
            pass # 이전 요소가 없으면 그냥 넘어갑니다.

        # 3. (기존 로직 개선) 섹션 내부 텍스트에서 '인기글' 패턴 찾기
        section_text = section.text[:200]
        if "인기글" in section_text:
            match = re.search(r'([\w·\s]+)?인기글', section_text)
            if match:
                title = match.group(0).strip()
                if len(title) < 30: return title
            return "인기글"

        # 4. (기존 로직) 클래스명 기반으로 섹션 종류 추론
        class_name = section.get_attribute("class") or ""
        if "ad" in class_name or "power_link" in class_name: return "광고"
        if "blog" in class_name: return "블로그"
        if "cafe" in class_name: return "카페"

    except Exception:
        pass
    return "검색결과" # 최후의 보루


def extract_content_links(section):
    """실제 보이는 게시물 링크만 정확히 추출"""
    content_links = []
    
    try:
        # 0. 스마트블록 우선 확인 (추가)
        post_text_containers = section.find_elements(By.CSS_SELECTOR, "div[class*='text-container']")
        if post_text_containers:
            for container in post_text_containers:
                try:
                    title_link = container.find_element(By.CSS_SELECTOR, "a[class*='text-title']")
                    content_links.append(title_link)
                except:
                    continue
            # 실제로 링크를 찾았을 때만 return
            if content_links:
                return content_links
        
        # 1. 일반 인기글 처리 (원본 그대로)
        # 디버깅: 섹션 텍스트 확인
        section_text = section.text[:200] if section.text else ""
        if "인기글" in section_text:
            print(f"  [디버깅] 인기글 섹션 발견, 텍스트: {section_text[:100]}...")
        
        # 리스트 아이템 방식
        list_items = section.find_elements(By.CSS_SELECTOR, "li")
        
        # 리스트 아이템이 없으면 모든 링크 시도
        if not list_items:
            print(f"  [디버깅] li 요소 없음, 모든 a 태그 검색")
            all_links = section.find_elements(By.TAG_NAME, "a")
            for link in all_links:
                href = link.get_attribute("href") or ""
                text = link.text.strip()
                if ("blog.naver" in href or "cafe.naver" in href) and len(text) > 5:
                    print(f"    -> 링크 발견: {text[:30]}...")
                    content_links.append(link)

        # 2. 리스트 구조가 아닌 경우
        if not content_links:
            link_selectors = [
                "a.title_link",
                "a.api_txt_lines",
                "a.link_tit",
                "a.total_tit",
                "a.name",
                "a.dsc_link",
                "a[href*='blog.naver']",
                "a[href*='cafe.naver']",
            ]
            
            for selector in link_selectors:
                links = section.find_elements(By.CSS_SELECTOR, selector)
                for link in links:
                    if link.is_displayed() and link not in content_links:
                        href = link.get_attribute("href") or ""
                        text = link.text.strip()
                        
                        if is_valid_content_link(href) and len(text) > 5:
                            content_links.append(link)
        
        # 3. 그래도 없으면 모든 링크 확인 (최후 수단)
        if not content_links:
            all_links = section.find_elements(By.TAG_NAME, 'a')
            
            for link in all_links:
                if not link.is_displayed():
                    continue
                
                # 너무 작은 링크 제외
                if link.size['height'] < 10 or link.size['width'] < 10:
                    continue
                
                href = link.get_attribute("href") or ""
                text = link.text.strip()
                
                # 유효한 콘텐츠 링크이고 충분한 텍스트
                if is_valid_content_link(href) and len(text) > 5:
                    # UI 요소 제외
                    if not any(skip in text for skip in ["더보기", "설정", "옵션", "필터", "전체"]):
                        if link not in content_links:
                            content_links.append(link)
        
    except Exception as e:
        print(f"링크 추출 오류: {e}")
    
    return content_links