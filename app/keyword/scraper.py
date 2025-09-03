# app/keyword/scraper.py

import time
import random
import urllib.parse
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- 보조 함수들 ---
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

# --- 메인 실행 함수 ---
def run_check(keyword: str, post_url: str) -> tuple:
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1280,2200")
    options.add_argument("--disable-gpu"); options.add_argument("--no-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
    
    driver = None
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        q = urllib.parse.quote(keyword)
        driver.get(f"https://search.naver.com/search.naver?query={q}")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "main_pack")))
        human_sleep()

        result_items = driver.find_elements(By.CSS_SELECTOR, "#main_pack .total_area, #main_pack .fds-ugc-block-mod, #main_pack ._svp_content ul li")

        for index, item in enumerate(result_items):
            rank = index + 1
            links = item.find_elements(By.TAG_NAME, 'a')
            for link in links:
                href = link.get_attribute("href") or ""
                if url_matches(post_url, href):
                    return ("최상단 노출", rank)

        try:
            tab = driver.find_element(By.XPATH, '//a[contains(@role,"tab")][contains(normalize-space(.),"카페")]')
            driver.execute_script("arguments[0].click();", tab)
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href^='https://cafe.naver.com/']")))
            human_sleep()
            cafe_links = driver.find_elements(By.CSS_SELECTOR, "a[href^='https://cafe.naver.com/'], a[href^='https://m.cafe.naver.com/']")
            for a in cafe_links:
                href = a.get_attribute("href") or ""
                if url_matches(post_url, href):
                    return ("노출X", None)
        except Exception:
            pass
        
        return ("저품질", None)
    finally:
        if driver:
            driver.quit()