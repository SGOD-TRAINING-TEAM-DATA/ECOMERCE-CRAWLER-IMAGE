import re
import time
import json
import random
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from itertools import zip_longest
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

# ================== Kết nối Kafka ==================
for _ in range(5):
    try:
        producer = KafkaProducer(
            bootstrap_servers=['localhost:9092'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        print(" Kết nối Kafka thành công")
        break
    except NoBrokersAvailable:
        print(" Kafka chưa sẵn sàng, thử lại sau 5s...")
        time.sleep(5)
else:
    raise Exception(" Không thể kết nối Kafka")

# ================== Setup Selenium ==================
driver_path = r"D:\chromedriver-win64\chromedriver.exe"
service = Service(driver_path)
options = Options()
options.add_argument("start-maximized")
driver = webdriver.Chrome(service=service, options=options)

# Mở trang Lazada
driver.get("https://www.lazada.vn/catalog/?q=iphone")
time.sleep(random.randint(5, 10))

# Scroll xuống để load sản phẩm
for _ in range(5):
    driver.execute_script("window.scrollBy(0, 1500);")
    time.sleep(2)

# Chờ sản phẩm xuất hiện
WebDriverWait(driver, 60).until(
    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[title][href]"))
)

# Crawl dữ liệu
elems = driver.find_elements(By.CSS_SELECTOR, "a[title][href]")
title = [elem.get_attribute("title") for elem in elems]
links = [elem.get_attribute('href') for elem in elems]

elems_price = driver.find_elements(By.CSS_SELECTOR, ".aBrP0")
price = [elem.text for elem in elems_price]

elems_discount = driver.find_elements(By.CSS_SELECTOR, ".WNoq3")
discount_all = [elem.text for elem in elems_discount]

elems_review = driver.find_elements(By.CSS_SELECTOR, "._6uN7R")
review_all = [elem.text for elem in elems_review]

# Ảnh sản phẩm
elems_img_containers = driver.find_elements(By.CSS_SELECTOR, ".picture-wrapper")
images = []
for container in elems_img_containers:
    try:
        img_element = container.find_element(By.TAG_NAME, "img")
        img_url = img_element.get_attribute("src") or img_element.get_attribute("data-src")
        if img_url.endswith(".avif"):
          img_url = img_url.replace(".avif", ".png")
        images.append(img_url)
    except:
        images.append(None)

# Gom dữ liệu
raw_data = list(zip_longest(title, price, discount_all, review_all, links, images, fillvalue=None))

cleaned_data = []
for idx, item in enumerate(raw_data, start=1):
    if not item[0] or "thắc mắc" in item[0].lower():
        continue
    if item[4] and "faq" in item[4].lower():
        continue

    # Tính giá gốc nếu có giảm giá
    try:
        price_num = int(re.sub(r"[^\d]", "", item[1])) if item[1] else None
        if item[2]:
            match = re.search(r"(\d+)%", item[2])
            if match and price_num:
                percent = int(match.group(1))
                original_price = round(price_num / (1 - percent/100))
                original_price_str = f"{original_price:,} ₫"
            else:
                original_price_str = None
        else:
            original_price_str = None
    except:
        original_price_str = None

    cleaned_data.append({
        "index_": idx,
        "title": item[0],
        "price": item[1],
        "discount": item[2],
        "review": item[3],
        "link_item": item[4],
        "image_url": item[5],
        "original_price": original_price_str
    })

# Gửi dữ liệu lên Kafka
for item in cleaned_data:
    producer.send('lazada-topic', value=item)
producer.flush()
print(f" Đã gửi {len(cleaned_data)} sản phẩm lên Kafka topic 'lazada-topic'")

# Xuất JSON để backup
with open("lazada_products.json", "w", encoding="utf-8") as f:
    json.dump(cleaned_data, f, ensure_ascii=False, indent=4)

driver.quit()
print(" Đã hoàn thành crawl Lazada")
