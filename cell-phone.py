import os
import json
import requests
import random
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

# ====================== Kết nối Kafka ======================
for _ in range(5):
    try:
        producer = KafkaProducer(
            bootstrap_servers=['localhost:9092'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        print(" Kết nối Kafka thành công")
        break
    except NoBrokersAvailable:
        print("Kafka chưa sẵn sàng, thử lại sau 5s...")
        time.sleep(5)
else:
    raise Exception(" Không thể kết nối Kafka sau nhiều lần thử")

# ====================== Cấu hình WebDriver ======================
driverpath = r"D:\chromedriver-win64\chromedriver.exe"
service = Service(driverpath)
driver = webdriver.Chrome(service=service)

# ====================== Truy cập trang web ======================
driver.get("https://cellphones.com.vn/mobile/dien-thoai-pin-trau.html")
time.sleep(random.randint(5, 20))

# ====================== Crawl dữ liệu sản phẩm ======================
# Tên sản phẩm
elems = WebDriverWait(driver, 60).until(
    EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".product__name"))
)
elems = driver.find_elements(By.CSS_SELECTOR, ".product__name")
title_all = [elem.text for elem in elems]

# Link sản phẩm
elems = driver.find_elements(By.CSS_SELECTOR, "[href]")
links_all = [elem.get_attribute("href") for elem in elems]

# Giá sản phẩm
try:
    prices_show = driver.find_elements(By.CSS_SELECTOR, ".product__price--show")
    prices_through = driver.find_elements(By.CSS_SELECTOR, ".product__price--through")
    all_price1 = [elem.text for elem in prices_show]
    all_price2 = [elem.text for elem in prices_through]
except Exception:
    all_price1 = []
    all_price2 = []

# Badge
try:
    elems = driver.find_elements(By.CSS_SELECTOR, ".product__badge")
    product = [elem.text for elem in elems]
except Exception:
    product = []

# Giảm giá
try:
    elems = driver.find_elements(By.CSS_SELECTOR, ".product__price--percent-detail")
    discount_all = [elem.text for elem in elems]
except Exception:
    discount_all = []

# Link ảnh
images = driver.find_elements(By.CSS_SELECTOR, ".product__img")
img_links = [img.get_attribute("src") for img in images]

# ====================== Gửi dữ liệu lên Kafka ======================
data = []
for i in range(len(title_all)):
    item = {
        "title": title_all[i] if i < len(title_all) else "",
        "link": links_all[i] if i < len(links_all) else "",
        "price_after": all_price1[i] if i < len(all_price1) else "",
        "price_before": all_price2[i] if i < len(all_price2) else "",
        "badge": product[i] if i < len(product) else "",
        "discount": discount_all[i] if i < len(discount_all) else "",
        "image_url": img_links[i] if i < len(img_links) else ""
    }
    data.append(item)
    #  Gửi message lên Kafka topic
    producer.send('cellphone-topic', value=item)

producer.flush()
print(f" Đã gửi {len(data)} sản phẩm lên Kafka topic 'cellphone-topic'")

# ====================== Lưu ra file JSON ======================
with open("cellphone_products.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print(f" Đã lưu {len(data)} sản phẩm vào cellphone_products.json")

# ====================== Đóng driver ======================
driver.quit()
