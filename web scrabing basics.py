import time
import re
from logging import exception
from operator import truediv

import pandas as pd
from IPython.core.page import page
from jupyter_server.auth import passwd
from pandas import describe_option
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.devtools.v142.debugger import continue_to_location
from selenium.webdriver.support.expected_conditions import element_selection_state_to_be
from unicodedata import category
from webdriver_manager.chrome import ChromeDriverManager    "Mobiles": "https://www.snapdeal.com/search?keyword=mobile",
    "Men's Clothing": "https://www.snapdeal.com/search?keyword=mens%20clothing",
}

def human_sleep(sec=2):
    time.sleep(sec)



OUTPUT_CSV = "snapdeal_products.csv"
HEADLESS = False
PAGE_WAIT = 3
SCROLL_PAUSE = 2

BASE_URLS = {
    "Accessories": "https://www.snapdeal.com/search?keyword=accessories",
    "Mobiles": "https://www.snapdeal.com/search?keyword=mobile",
    "Men's Clothing": "https://www.snapdeal.com/search?keyword=mens%20clothing",
}

def human_sleep(sec=2):
    time.sleep(sec)
def scroll_to_bottom(driver, max_scrolls=5):
    last_height = driver.execute_script("return document.body.scrollHeight")
    for _ in range(max_scrolls):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        human_sleep(SCROLL_PAUSE)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        try:
            for category, url in BASE_URLS.items():
                print(f"Scraping category: {category}")
                driver.get(url)
                human_sleep(PAGE_WAIT)
                scroll_to_bottom(driver)

                products = driver.find_elements(By.CLASS_NAME, "product-tuple-listing")
                for product in products:
                    name = safe_text(
                        product.find_element(By.CLASS_NAME, "product-title")
                    ) if product.find_elements(By.CLASS_NAME, "product-title") else ""

                    price = safe_text(
                        product.find_element(By.CLASS_NAME, "product-price")
                    ) if product.find_elements(By.CLASS_NAME, "product-price") else ""

                    link = safe_attr(
                        product.find_element(By.TAG_NAME, "a"),
                        "href"
                    ) if product.find_elements(By.TAG_NAME, "a") else ""

                    data.append({
                        "Category": category,
                        "Product Name": name,
                        "Price": price,
                        "Product Link": link
                    })

            finally:
            driver.quit()

        df = pd.DataFrame(data)
        df.to_csv(OUTPUT_CSV, index=False)
        last_height = new_height


chrome_options = Options()
if HEADLESS:
    chrome_options.add_argument("--headless=new")

chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=chrome_options
)


def safe_text(el):
    try:
        return el.text.strip()
    except:
        return ""


def safe_attr(el, attr):
    try:
        return el.get_attribute(attr)
    except:
        return ""


def get_left_sub_category_links(
        driver,
        left_x_threshold=400
):
    subcards = []
    seen = set()

    EXCLUDE_KEYWORDS = {
        "price", "brand", "rating", "size", "colour", "color",
        "discount", "customer", "ship", "cod", "delivery",
        "availability", "seller", "apply", "clear", "sort",
        "view", "more", "less", "newest",
        "fourstar", "threestar", "twostar", "onestar"
    }

    try:
        anchors = driver.find_elements(By.XPATH, "//a[@href]")

        for a in anchors:
            try:
                text = a.text.strip()
                if not text or len(text) < 3 or len(text) > 60:
                    continue

                href = a.get_attribute("href")
                if not href:
                    continue

                # ---- URL validation ----
                parsed = urlparse(href)
                netloc = parsed.netloc.lower()

                if "snapdeal" not in netloc:
                    continue

                if ("search" not in href) and ("products" not in href):
                    continue

                # ---- Position check (left panel) ----
                loc = a.location
                if not loc or loc.get("x", 9999) > left_x_threshold:
                    continue

                key = (text.lower(), href)
                if key in seen:
                    continue

                # ---- Keyword filtering ----
                lower_text = text.lower()
                if any(kw in lower_text for kw in EXCLUDE_KEYWORDS):
                    continue

                # ---- Remove numeric / junk labels ----
                if re.fullmatch(r"[\d\W_]+", text):
                    continue

                subcards.append({
                    "subcategory": text,
                    "url": href
                })
                seen.add(key)

            except Exception:
                continue

    except Exception:
        pass

    return subcards


def click_next_page():
    selectors = [
        "a[rel='next']",
        "a.pagination_number.next",
        "a.next",
        "//a[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'next')]"
    ]

    cur_url = driver.current_url

    for selenium in selectors:
        if selenium.startswith("//"):
            cand = driver.find_element(By.XPATH, selenium)
        else:
            cand = driver.find_element(By.CSS_SELECTOR, selenium)

        cand.click()
        time.sleep(1.2)


try:
    WebDriverWait(driver, 6).until(EC.url_changes(current_url))
except:
    pass

if driver.current_url != current_url:
    return True
else:
    return False


def deep_scrape_product_url(driver, url):
    data = {"brand": "", "full_description": "", "seller": "", "availability": "", "rating": "", "review_count": 0,
            "breadcrumb": "", "image_urls": []}
    if not url:
        return data

    parent = driver.current_window_handle

    try:
        driver.execute_script("window.open(arguments[0], '_blank');", url)
        WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))

        for h in driver.window_handles:
            if h != parent:
                driver.switch_to.window(h)
                break

        data["brand"] = driver.find_element(
            By.CSS_SELECTOR,
            "a.pd-brand, .pdp-brand, .brand-name"
        ).text.strip()
    rating_val = find_first((".fan-item-crop .rating-value", ".pdp-pi-rating"))
    if not rating_val:
        rating_style = find_first((".filled-stars", "[style*='width']"))
        rating_val = parse_rating_from_style(rating_style) if rating_style else None
    data["rating"] = rating_val

    rc_text = find_first((
        ".pdp-review-count span",
        ".pdp-review-count",
        ".p-product-review-count",







