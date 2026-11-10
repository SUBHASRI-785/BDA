from pathlib import Path
import csv
import json
import re
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# ============================================================
# MARKETMART P01-P50 REAL PRODUCT IMAGE DOWNLOADER - V2
# ============================================================
# Put this script in:
# C:\Users\SUBHA\OneDrive\Desktop\MARKETMART
#
# Then run:
# python download_real_images_v2.py
#
# Images are saved directly to:
# MARKETMART\static\images\
#
# Existing images are NOT overwritten by default.
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent
IMAGE_DIR = PROJECT_ROOT / "static" / "images"
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "MarketMart-Educational-Project/2.0"
REQUEST_DELAY = 2.5
MAX_RETRIES = 4

PRODUCTS = [
    ("P01", "Laptop", ["laptop computer", "laptop notebook computer", "Acer laptop computer"]),
    ("P02", "Smartphone", ["smartphone mobile phone", "Android smartphone", "mobile phone"]),
    ("P03", "Tablet", ["tablet computer", "tablet device", "iPad tablet"]),
    ("P04", "Headphones", ["headphones", "stereo headphones", "over ear headphones"]),
    ("P05", "Mouse", ["computer mouse", "computer optical mouse", "USB computer mouse"]),
    ("P06", "Keyboard", ["computer keyboard", "USB keyboard", "PC keyboard"]),
    ("P07", "USB Hub", ["USB hub", "USB port hub", "computer USB hub"]),
    ("P08", "Power Bank", ["power bank charger", "portable power bank", "USB power bank"]),
    ("P09", "Smart Watch", ["smart watch", "smartwatch", "digital smart watch"]),
    ("P10", "Bluetooth Speaker", ["Bluetooth speaker", "portable Bluetooth speaker", "wireless speaker"]),
    ("P11", "Laptop Stand", ["laptop stand", "notebook computer stand", "laptop holder"]),
    ("P12", "Webcam", ["computer webcam", "USB webcam", "web camera"]),
    ("P13", "Phone Case", ["smartphone case", "mobile phone case", "phone protective case"]),
    ("P14", "Screen Protector", ["phone screen protector", "smartphone screen protector", "tempered glass screen protector"]),
    ("P15", "USB Cable", ["USB cable", "USB data cable", "USB charging cable"]),
    ("P16", "Backpack", ["backpack", "back pack bag", "school backpack"]),
    ("P17", "T-Shirt", ["t shirt", "T-shirt clothing", "cotton T-shirt"]),
    ("P18", "Jeans", ["jeans trousers", "blue jeans", "denim jeans"]),
    ("P19", "Hoodie", ["hoodie sweatshirt", "hooded sweatshirt", "hoodie clothing"]),
    ("P20", "Sneakers", ["sneakers shoes", "athletic sneakers", "sports sneakers"]),
    ("P21", "Handbag", ["handbag", "women handbag", "leather handbag"]),
    ("P22", "Sports Watch", ["sports watch", "sport watch", "digital sports watch"]),
    ("P23", "Water Bottle", ["water bottle", "reusable water bottle", "sports water bottle"]),
    ("P24", "Yoga Mat", ["yoga mat", "exercise yoga mat", "fitness mat"]),
    ("P25", "Running Shoes", ["running shoes", "running footwear", "athletic running shoes"]),
    ("P26", "Table Lamp", ["table lamp", "desk lamp", "reading table lamp"]),
    ("P27", "Coffee Mug", ["coffee mug", "ceramic coffee mug", "coffee cup mug"]),
    ("P28", "Storage Box", ["storage box", "plastic storage box", "home storage container"]),
    ("P29", "Bedsheet", ["bed sheet", "bedsheet", "bed linen sheet"]),
    ("P30", "Pillow", ["pillow", "bed pillow", "sleep pillow"]),
    ("P31", "Face Wash", ["face wash", "facial cleanser", "face cleanser bottle"]),
    ("P32", "Shampoo", ["shampoo bottle", "hair shampoo", "shampoo product"]),
    ("P33", "Moisturizer", ["moisturizer cream", "face moisturizer", "skin moisturizer bottle"]),
    ("P34", "Sunscreen", ["sunscreen lotion", "sunscreen bottle", "sun cream"]),
    ("P35", "Perfume", ["perfume bottle", "fragrance perfume", "perfume product"]),
    ("P36", "Python Programming", ["Python programming book", "Python book programming", "Python programming textbook"]),
    ("P37", "Data Science", ["data science book", "data science textbook", "data science programming book"]),
    ("P38", "Machine Learning", ["machine learning book", "machine learning textbook", "machine learning programming book"]),
    ("P39", "Web Development", ["web development book", "web development textbook", "HTML CSS web development book"]),
    ("P40", "AI Fundamentals", ["artificial intelligence book", "AI fundamentals book", "artificial intelligence textbook"]),
    ("P41", "Camera", ["digital camera", "digital still camera", "DSLR camera"]),
    ("P42", "Memory Card", ["SD memory card", "microSD memory card", "flash memory card"]),
    ("P43", "Camera Bag", ["camera bag", "photography camera bag", "camera carrying bag"]),
    ("P44", "External SSD", ["external SSD", "portable SSD drive", "external solid state drive"]),
    ("P45", "Power Strip", ["power strip", "electrical power strip", "extension power strip"]),
    ("P46", "Desk Organizer", ["desk organizer", "office desk organizer", "desktop organizer"]),
    ("P47", "Fitness Band", ["fitness band", "fitness tracker band", "activity tracker band"]),
    ("P48", "Sports T-Shirt", ["sports T-shirt", "athletic T-shirt", "sports shirt"]),
    ("P49", "Laptop Bag", ["laptop bag", "notebook computer bag", "laptop carrying bag"]),
    ("P50", "Wireless Charger", ["wireless charger", "Qi wireless charger", "wireless charging pad"]),
]

BAD_WORDS = {
    "diagram", "logo", "icon", "symbol", "map", "chart", "screenshot",
    "event", "concert", "store", "shop", "booth", "vending", "keyboard and mouse",
    "teacher", "classroom", "target", "flag", "gasoline", "fuel"
}

def request_json(params):
    params = dict(params)
    params["format"] = "json"
    params["origin"] = "*"
    url = API + "?" + urlencode(params)

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(req, timeout=40) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as e:
            last_error = e
            if e.code == 429:
                wait = 8 * (attempt + 1)
                print(f"      Wikimedia rate limit. Waiting {wait}s...")
                time.sleep(wait)
            else:
                time.sleep(3)
        except (URLError, TimeoutError) as e:
            last_error = e
            time.sleep(4)

    raise last_error

def clean_html(text):
    return re.sub(r"<[^>]*>", "", text or "")

def relevance_score(title, query_terms):
    text = title.lower()
    score = 0

    for term in query_terms:
        words = [w for w in re.findall(r"[a-z0-9]+", term.lower()) if len(w) > 2]
        matches = sum(1 for w in words if w in text)
        score += matches * 10

    for bad in BAD_WORDS:
        if bad in text:
            score -= 100

    return score

def search_images(query):
    data = request_json({
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,
        "gsrlimit": 20,
        "prop": "imageinfo",
        "iiprop": "url|mime|extmetadata",
        "iiurlwidth": 1000,
    })

    pages = list((data.get("query", {}).get("pages", {}) or {}).values())
    results = []

    for page in pages:
        info = (page.get("imageinfo") or [{}])[0]
        mime = (info.get("mime") or "").lower()
        url = info.get("thumburl") or info.get("url")
        title = page.get("title", "")

        if not url:
            continue

        if mime not in {"image/jpeg", "image/png", "image/webp"}:
            continue

        # Skip obvious non-product material.
        low = title.lower()
        if any(word in low for word in BAD_WORDS):
            continue

        results.append({
            "title": title,
            "url": url,
            "mime": mime,
            "page_url": "https://commons.wikimedia.org/wiki/" + title.replace(" ", "_"),
            "meta": info.get("extmetadata") or {},
        })

    return results

def choose_best(results, query):
    if not results:
        return None

    query_terms = [query]
    ranked = sorted(
        results,
        key=lambda x: relevance_score(x["title"], query_terms),
        reverse=True
    )

    # Do not accept a result with a strongly negative score.
    for item in ranked:
        if relevance_score(item["title"], query_terms) >= 10:
            return item

    return None

def download_image(url, destination):
    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(req, timeout=60) as response:
                data = response.read()

            if len(data) < 5000:
                raise ValueError("Downloaded file is unusually small")

            destination.write_bytes(data)
            return True

        except HTTPError as e:
            last_error = e
            if e.code == 429:
                wait = 10 * (attempt + 1)
                print(f"      Download rate limited. Waiting {wait}s...")
                time.sleep(wait)
            else:
                time.sleep(4)

        except Exception as e:
            last_error = e
            time.sleep(4)

    print(f"      Download failed: {last_error}")
    return False

def metadata_value(meta, key):
    return clean_html(meta.get(key, {}).get("value", ""))

def main():
    source_rows = []
    report_rows = []

    print("=" * 65)
    print(" MARKETMART REAL PRODUCT IMAGE DOWNLOADER - V2")
    print("=" * 65)
    print(f"Saving images to: {IMAGE_DIR}")
    print("Existing JPG files will NOT be overwritten.")
    print()

    for number, (pid, product_name, queries) in enumerate(PRODUCTS, 1):
        destination = IMAGE_DIR / f"{pid}.jpg"

        print(f"[{number:02d}/50] {pid} - {product_name}")

        # Keep an already-downloaded image.
        if destination.exists() and destination.stat().st_size > 5000:
            print("      Already exists - skipped")
            report_rows.append([pid, product_name, "EXISTING", destination.name])
            continue

        found = None

        for query in queries:
            print(f"      Searching: {query}")

            try:
                results = search_images(query)
                found = choose_best(results, query)

                if found:
                    print(f"      Candidate: {found['title']}")
                    break

            except Exception as e:
                print(f"      Search error: {e}")

            time.sleep(REQUEST_DELAY)

        if not found:
            print("      FAILED - no suitable image found")
            report_rows.append([
                pid, product_name, "FAILED",
                "No suitable image found after all search queries"
            ])
            time.sleep(REQUEST_DELAY)
            continue

        # The Wikimedia thumbnail is normally JPEG/PNG. We save using the
        # .jpg filename expected by the MarketMart template.
        success = download_image(found["url"], destination)

        if success:
            meta = found["meta"]

            source_rows.append([
                pid,
                product_name,
                found["title"],
                found["page_url"],
                metadata_value(meta, "Artist"),
                metadata_value(meta, "LicenseShortName"),
                metadata_value(meta, "LicenseUrl"),
                found["url"],
            ])

            report_rows.append([
                pid, product_name, "OK", found["title"]
            ])
            print(f"      SAVED: {destination}")
        else:
            report_rows.append([
                pid, product_name, "FAILED",
                "Image download failed after retries"
            ])

        time.sleep(REQUEST_DELAY)

    with (PROJECT_ROOT / "image_sources_v2.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
        writer = csv.writer(f)
        writer.writerow([
            "ProductID", "ProductName", "WikimediaFile", "SourcePage",
            "Author", "License", "LicenseURL", "ImageURL"
        ])
        writer.writerows(source_rows)

    with (PROJECT_ROOT / "download_report_v2.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
        writer = csv.writer(f)
        writer.writerow(["ProductID", "ProductName", "Status", "Details"])
        writer.writerows(report_rows)

    ok = sum(1 for r in report_rows if r[2] in {"OK", "EXISTING"})
    failed = sum(1 for r in report_rows if r[2] == "FAILED")

    print()
    print("=" * 65)
    print(f"Finished: {ok}/50 available, {failed} failed")
    print(f"Images: {IMAGE_DIR}")
    print(f"Sources: {PROJECT_ROOT / 'image_sources_v2.csv'}")
    print(f"Report: {PROJECT_ROOT / 'download_report_v2.csv'}")
    print("=" * 65)

if __name__ == "__main__":
    main()
