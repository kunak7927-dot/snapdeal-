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
from webdriver_manager.chrome import ChromeDriverManager

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
    data = {"brand": "","full_description": "","seller": "","availability": "","rating": "","review_count": 0,"breadcrumb": "","image_urls": []}
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
    ".rating-count"
))
data["review_count"] = clean_int(rc_text) if rc_text else 0

aval = find_first((
    ".sold-out-error",
    ".codm-message",
    ".availability-message"
))
data["availability"] = aval if aval else "In Stock"

data["seller"] = find_first((
    ".pdp-seller-name",
    ".pdp-seller-info a",
    ".pdp-seller-info"
))

desc_candidates = (
    ".description",
    ".product-description",
    ".dir-tab-content",
    ".content-dir-spec",
    "body"
)

body = ""
for sel in desc_candidates:
    text = find_first(sel)
    if text and len(text) > len(body):
        body = text

data["description"] = body[:40]


scrumbs = soup.select("ul.breadcrumb li")
if scrumbs:
    data["breadcrumb"] = "<".join(li.get_text(strip=True) for li in scrumbs if li.get_text(strip=True))


detailed_images = []

for image in find_all("cloudsoon"):
    src = image.get_attribute("src")
    datasrc = image.get_attribute("datasrc")
    if src:
        detailed_images.append(src)
    if datasrc:
        detailed_images.append(datasrc)

if not detailed_images:
    for image in find_all("image"):
        s = image.get_attribute("src") or ""
        if s and "snapdeal" in s and ("images" in s or "image" in s):
            detailed_images.append(s)

data["image_urls_details"] = ",".join(dict.fromkeys(detailed_images))[:2000]

except Exception:
    try:
        driver.close()
        driver.switch_to.window(parent)
    except:
        pass

def scrape_listing_cards(category_name, page_num, max_token, max_take=None):
    items = []

    cards = find_all("div.product-tuple-listing")
    if not cards:
        cards = find_all("div.product-tuple")

    for idx, card in enumerate(cards, start=1):
        if max_take and len(items) >= max_take:
            break

        name = find_first(("div.product-title",), ln=card) or ""
        price = find_first(("span.product-price",), ln=card) or ""
        original_price = find_first(("span.product-desc-price.strike","span.lfloat.product-desc-price.strike",),ln=card,)
        discount = find_first(("div.product-discount", "span.product-discount"),ln=card,)
        rating_list = find_first(("div.product-rating", ".rating"),ln=card,)
    view_text = find_first(("p.product-rating-count,.rating-count",), ln=card)
    review_count = clean_int(view_text)


    image = find_first(("img.product-image",), ln=card, attr="src")
    if not image:
        image = find_first(("img",), ln=card, attr="src")


    url = find_first(("a.dp-regret-link",), ln=card, attr="href")
    if not url:
        try:
            url = card.find_element(By.TAG_NAME, "a").get_attribute("href")
        except:
            url = ""

    rating_style = find_first((".filled-stars",),ln=card,attr="style",))
    if not rating_list and rating_style:
        rating_list = parse_rating_from_style(rating_style)

        short description=find_first(("p.product discription rating,in_l=card or """))

    text_for_audiance = f"{name_short_description.lower()}"

    if any(k in text_for_audiance for k in ["woman", "girl", "ladies", "female"]):
        audiance = "female"
    elif any(k in text_for_audiance for k in ["men", "boy", "male"]):
        audiance = "male"
    elif any(k in text_for_audiance for k in ["kid", "child", "children"]):
        audiance = "children"
    else:
        audiance = "unspecified"


    extra = deep_scrap_product_url(url) if deep_scrap and url
    else {"brand": "","full description": "","seller": "","availability": "","rating": "","reviews count": 0,"breadscrump": "","image url": ""}

if not extra.get("brand"):
    extra["brand"] = name.split()[0] if name else ""

    row = {
    "scrape_datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "top_section": category_name,
    "sub_category": sub_cards_name,
    "product_name": product_name,
    "brand_name": brand_name or extra.get("brand", ""),
    "price": price,
    "original_price": original_price,
    "discount_percent": discount_percent,
    "rating": rating,
    "rating_detail": extra.get("rating", ""),
    "reviews_count": reviews_count,
    "reviews_count_detail": extra.get("reviews_count", 0),
    "target_audience": audience,
    "availability": extra.get("availability", ""),
    "seller": extra.get("seller", ""),
    "product_url": product_url,
    "short_description": short_desc,
    "full_description": extra.get("full_description", ""),
    "breadcrumbs": extra.get("breadcrumbs", ""),
    "page_name": page_name,
    }

    items.append(row)
    return items

all_rows = []

for section_name, base_url in base_sections.items():
    print(f"\n=== section: {section_name} ===")
    try:
        driver.get(base_url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "def.product.tuple.listing")))
    except Exception:
        pass

subcards = get_left_sub_category_links()

seen_sc = set()
cleaned_subcards = []

for sc in subcards:
    key = (sc.get("sub_category"), sc.get("url"), base_url)
    if key not in seen_sc:
        cleaned_subcards.append(sc)
        seen_sc.add(key)

if not cleaned_subcards:
    cleaned_subcards = sub_category or base_url

print("found length cleaned sub cards sub category", len(cleaned_subcards))


for sc in cleaned_subcards:
    sub_name = sc.get("sub_category")
    sub_url = sc.get("url")
    print("an a sub category sub name", sub_name)

    driver.get(sub_url)
    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, def_product_tuple_listing)))
    except Exception:
        pass

total_sub = 0
all_rows = []

for page in range(1, max_pages_per_sub_cards + 1):
    print(f"page {page}")
    scroll_to_auto()
    items = scrape_list_in_cards(section,name,subname,page,maxpeek=max_products_per_subcards)
    if not items:
        print("no product found in this page")
        break

    all_rows.extend(items)
    total_sub += len(items)


    moved = click_next_page()
    if not moved:
        print("no next button or this is the last page")
        break
print(f"collected total {total_sub} products for sub category {subname}")

columns = ["created_at","top_section","sub_category","product_name","brand_heuristic_listing","price","original_price","discount","rating_listing","rating_detail","reviews_count_listing","reviews_count_detail","target_audience","availability","seller","product_url","image_url_listing","image_url_detail","short_description","full_description","bread_crumbs","page"]
df = pd.DataFrame(all_rows, columns=columns)
df.to_csv(output_csv, index=False, encoding="utf-8-sig")
print(f"done rows {len(df)}")
driver.quit()
