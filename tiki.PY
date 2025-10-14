from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time, json, re
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

# ==================== KẾT NỐI KAFKA ====================
for _ in range(5):
    try:
        producer = KafkaProducer(
            bootstrap_servers=['localhost:9092'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        break
    except NoBrokersAvailable:
        print("⚠️ Kafka chưa sẵn sàng, retry sau 5s...")
        time.sleep(5)

# ==================== KHỞI TẠO DRIVER ====================
driver = webdriver.Chrome()
detail_driver = webdriver.Chrome()

driver.get("https://tiki.vn/thiet-bi-kts-phu-kien-so/c1815")
time.sleep(5)

# ==================== ĐÓNG POPUP ====================
try:
    driver.find_element(By.CSS_SELECTOR, "button[class*='close']").click()
    time.sleep(2)
except:
    pass

# ==================== SCROLL LOAD ====================
for i in range(3):
    driver.execute_script(f"window.scrollTo(0, {1500 * (i+1)});")
    time.sleep(5)

last_height = driver.execute_script("return document.body.scrollHeight")
while True:
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(5)
    new_height = driver.execute_script("return document.body.scrollHeight")
    if new_height == last_height:
        break
    last_height = new_height

# ==================== LẤY SẢN PHẨM ====================
try:
    products = WebDriverWait(driver, 60).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.product-item, div[data-view-id*='product_list_item']"))
    )
except:
    products = driver.find_elements(By.CSS_SELECTOR, "a.product-item, div[data-view-id*='product_list_item']")

data = []

# ==================== HÀM LẤY ẢNH ====================
def get_image_from_list(p):
    try:
        img = p.find_element(By.CSS_SELECTOR, "img")
        url = img.get_attribute("src") or img.get_attribute("srcset") or img.get_attribute("data-src")
        if url:
            url = url.split(" ")[0]
            if url.startswith("//"):
                url = "https:" + url
            if not url.startswith(("data:", "blob:")):
                return url
        return None
    except:
        return None

def get_image_from_detail(link):
    if not link:
        return None
    try:
        detail_driver.get(link)
        WebDriverWait(detail_driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "img"))
        )
        img = detail_driver.find_element(By.CSS_SELECTOR, "img")
        url = img.get_attribute("src")
        if url and not url.startswith(("data:", "blob:")):
            if url.startswith("//"):
                url = "https:" + url
            return url
    except:
        return None
    return None

# ==================== VÒNG LẶP CRAWL ====================
for idx, p in enumerate(products, start=1):
    try:
        title = p.find_element(By.CSS_SELECTOR, "h3, .name, .title").text
    except:
        title = ""

    try:
        link = p.get_attribute("href") or p.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
    except:
        link = ""

    try:
        price_after = p.find_element(By.CSS_SELECTOR, ".price-discount__price, .final-price").text
    except:
        price_after = ""

    try:
        discount = p.find_element(By.CSS_SELECTOR, ".price-discount__percent, .discount-percent").text
    except:
        discount = ""

    img_url = get_image_from_list(p)
    if not img_url:
        img_url = get_image_from_detail(link)

    original_price = None
    try:
        price_num = int(re.sub(r"[^\d]", "", price_after))
        if discount:
            match = re.search(r"(\d+)%", discount)
            if match:
                percent = int(match.group(1))
                original_price = round(price_num / (1 - percent / 100))
    except:
        original_price = None

    item = {
        "title": title,
        "link": link,
        "price_after": price_after,
        "discount": discount,
        "original_price": original_price,
        "image_url": img_url
    }
    data.append(item)
    producer.send('tiki-topic', value=item)

    print(f" Gửi sản phẩm {idx}: {title}")

# ==================== LƯU JSON ====================
with open("tiki_products.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

driver.quit()
detail_driver.quit()
producer.flush()

print(f"\n Đã crawl {len(data)} sản phẩm.")
print(f" Dữ liệu lưu vào tiki_products.json")
print(f" Đã gửi toàn bộ dữ liệu lên Kafka topic tiki-topic")
