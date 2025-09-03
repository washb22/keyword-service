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
    
    # 디버깅
    if target_title and "변비" in target_title:
        print(f"    [매칭 시도] 타겟: {target_title[:20]}, 링크: {link_text[:20]}")
    
    # URL 매칭
    if url_matches(target_url, href):
        return True
    
    # 제목 매칭
    if target_title and link_text:
        if target_title == link_text:
            return True
        if len(target_title) > 10 and len(link_text) > 10:
            if target_title[:15] in link_text or link_text[:15] in target_title:
                return True
    
    return False


def human_sleep(a=0.8, b=1.8):
    """사람처럼 랜덤 대기"""
    time.sleep(random.uniform(a, b))

# --- 메인 실행 함수 ---
def run_check(keyword: str, post_url: str, post_title: str = None) -> tuple:  # post_title 파라미터 추가
    """키워드마다 다른 구조를 동적으로 파악하여 순위 측정"""
    print(f"--- '{keyword}' 순위 확인 시작 ---")
    
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1280,2200")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    driver = None
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        q = urllib.parse.quote(keyword)
        
        # 통합검색 페이지 접근
        print(f"[{keyword}] 통합검색 페이지 접근 중...")
        driver.get(f"https://search.naver.com/search.naver?query={q}")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "main_pack")))
        human_sleep()
        
        # 페이지 스크롤하여 모든 콘텐츠 로드
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2)")
        time.sleep(1)
        
        # 모든 섹션 찾기 (AI 브리핑 관련 제외)
        section_selectors = [
            ".sc_new",              # 스마트블록
            ".group_wrap",          # 일반 그룹
            ".sp_wrap",             # 특별 섹션
            ".view_wrap",           # 인기글 등
            "[class*='_prs_']",     # 동적 생성 섹션
            ".total_wrap",          # 통합 섹션
            ".section_more",        # 더보기 섹션
            "[class*='_au_']:not([class*='ai_brief'])",  # 자동 생성 모듈 (AI 제외)
            ".blog_wrap",           # 블로그 섹션
            ".cafe_wrap",           # 카페 섹션
            ".keyword_challenge_wrap",  # 키워드 챌린지 (인기글)
            "[class*='review']"     # 리뷰 섹션
        ]
        
        all_sections = []
        for selector in section_selectors:
            sections = driver.find_elements(By.CSS_SELECTOR, selector)
            all_sections.extend(sections)
        
        # 중복 제거
        unique_sections = []
        seen = set()
        for section in all_sections:
            section_id = id(section)
            if section_id not in seen:
                seen.add(section_id)
                unique_sections.append(section)
        
        print(f"[{keyword}] {len(unique_sections)}개 고유 섹션 발견")
        
        # 각 섹션 순회
        for section_idx, section in enumerate(unique_sections, 1):
            try:
                # 섹션이 실제로 보이는지 확인
                if not section.is_displayed():
                    continue
                
                # AI 브리핑 섹션 스킵
                section_class = section.get_attribute("class") or ""
                section_text = section.text[:100] if section.text else ""
                
                # AI 브리핑 관련 패턴이면 스킵
                if any(skip in section_class.lower() for skip in ["ai_brief", "ai_summary", "ai_generate"]):
                    print(f"[{keyword}] AI 브리핑 섹션 스킵")
                    continue
                if any(skip in section_text for skip in ["AI 브리핑", "AI가 요약", "AI가 정리"]):
                    print(f"[{keyword}] AI 브리핑 섹션 스킵")
                    continue
                
                # 섹션 높이 체크 (너무 작은 섹션 제외)
                if section.size['height'] < 50:
                    continue
                
                # 섹션 제목 추출
                section_title = extract_section_title(section, keyword)
                print(f"[{keyword}] 섹션 {section_idx}: '{section_title}' 확인 중...")
                
                # 섹션 내 실제 콘텐츠 링크들만 추출
                content_links = extract_content_links(section)
                print(f"[{keyword}] '{section_title}'에서 {len(content_links)}개 콘텐츠 발견")
                
                # 순위 확인
                for rank, link in enumerate(content_links, 1):
                    if url_or_title_matches(post_url, post_title, link):
                        print(f"[{keyword}] '{section_title}' {rank}위에서 발견!")
                        return (section_title, rank, section_title)
                        
            except Exception as e:
                print(f"[{keyword}] 섹션 {section_idx} 처리 중 오류: {e}")
                continue
        
        # 통합검색에서 못 찾으면 카페 탭 확인
        print(f"[{keyword}] 통합검색에서 못 찾음. 카페 탭 확인...")
        driver.get(f"https://search.naver.com/search.naver?where=article&query={q}")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "main_pack")))
        human_sleep()
        
        cafe_items = driver.find_elements(By.CSS_SELECTOR, "#main_pack ul.lst_total > li")
        print(f"[{keyword}] 카페 탭에서 {len(cafe_items)}개 항목 발견")
        
        for rank, item in enumerate(cafe_items, 1):
            try:
                link = item.find_element(By.CSS_SELECTOR, 'a.total_dsc')
                href = link.get_attribute("href") or ""
                if url_matches(post_url, href):
                    print(f"[{keyword}] 카페 탭 {rank}위에서 발견!")
                    return ("카페", rank, "카페")
            except:
                continue
        
        print(f"[{keyword}] 모든 위치에서 URL을 찾지 못함")
        return ("노출X", None, None)
        
    except Exception as e:
        print(f"[{keyword}] 순위 확인 중 오류 발생: {str(e)}")
        traceback.print_exc()
        return ("확인 실패", None, None)
    finally:
        if driver:
            driver.quit()
        print(f"--- '{keyword}' 순위 확인 완료 ---")


def extract_section_title(section, keyword):
    """섹션 제목 추출 - 키워드 기반 개선"""
    try:
        section_text = section.text[:500] if section.text else ""
        
        # 1. 키워드가 포함된 구체적인 제목 우선 찾기
        lines = section_text.split('\n')
        for line in lines[:5]:  # 처음 5줄만 확인
            line = line.strip()
            # 키워드가 포함되고 적절한 길이의 제목
            if keyword in line and 5 < len(line) < 50:
                # URL이나 물음표가 없는 제목
                if not line.startswith('http') and '?' not in line:
                    return line
        
        # 2. 섹션 바로 위의 제목 찾기 (기존 로직 유지)
        try:
            prev_sibling = section.find_element(By.XPATH, "./preceding-sibling::*[1]")
            if prev_sibling and prev_sibling.is_displayed():
                text = prev_sibling.text.strip()
                # "육아·결혼 인기글" 같은 패턴
                if "인기글" in text and len(text) < 30:
                    return text
                # 다른 유효한 제목
                if len(text) < 30 and not any(skip in text for skip in ["더보기", "광고", "?"]):
                    return text
        except:
            pass
        
        # 3. 인기글 패턴 찾기
        if "인기글" in section_text:
            # "육아·결혼 인기글", "상품리뷰 인기글" 패턴
            if "육아" in section_text and "인기글" in section_text:
                return "육아·결혼 인기글"
            elif "상품리뷰" in section_text and "인기글" in section_text:
                return "상품리뷰 인기글"
            elif "인기글" in section_text:
                match = re.search(r'([\w·\s]+)?인기글', section_text)
                if match:
                    title = match.group(0).strip()
                    if len(title) < 30:
                        return title
                return "인기글"
        
        # 4. 클래스명 기반
        class_name = section.get_attribute("class") or ""
        
        # 파워링크/광고는 스킵
        if "power_link" in class_name or "ad" in class_name:
            return "광고"
        
        if "keyword_challenge" in class_name:
            return "인기글"
        elif "review" in class_name:
            return "상품리뷰"
        elif "blog" in class_name:
            return "블로그"
        elif "cafe" in class_name or "article" in class_name:
            return "카페"
        
        return "검색결과"
        
    except Exception as e:
        print(f"제목 추출 오류: {e}")
        return "검색결과"

def extract_content_links(section):
    """실제 보이는 게시물 링크만 정확히 추출"""
    content_links = []
    
    try:
        # 디버깅: 섹션 텍스트 확인
        section_text = section.text[:200] if section.text else ""
        if "인기글" in section_text:
            print(f"  [디버깅] 인기글 섹션 발견, 텍스트: {section_text[:100]}...")
        
        # 1. 리스트 아이템 방식
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


def is_valid_content_link(href):
    """유효한 콘텐츠 링크인지 확인"""
    if not href:
        return False
    
    # 제외할 패턴
    exclude_patterns = [
        'javascript:',
        '#',
        '/search.naver',
        'tab=',
        'mode=', 
        'option=',
        'query=',
        'where=',
        'sm=',
        'ssc=',
        '/my.naver',
        'help.naver',
        'shopping.naver',
    ]
    
    # 제외 패턴 체크
    href_lower = href.lower()
    for pattern in exclude_patterns:
        if pattern in href_lower:
            return False
    
    # 포함해야 할 패턴
    include_patterns = [
        'blog.naver.com',
        'cafe.naver.com', 
        'post.naver.com',
        'kin.naver.com',
        'smartplace.naver',
        'land.naver.com',
        'tv.naver.com',
        'news.naver.com',
        'sports.news.naver'
    ]
    
    # 콘텐츠 링크 패턴 확인
    for pattern in include_patterns:
        if pattern in href:
            return True
    
    return False