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
driverpath = r"D:\chromedriver-win64\chromedriver.exe"
service = Service(driverpath)
driver = webdriver.Chrome(service=service)

# ==================== MỞ TRANG ====================
driver.get("https://www.thegioididong.com/dtdd#c=42&o=13&pi=2")
time.sleep(random.randint(5, 8))

data_all = []

# ==================== BƯỚC 1: LẤY LINK SẢN PHẨM ====================
print("🔎 Đang tìm sản phẩm...")
WebDriverWait(driver, 40).until(
    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "ul.listproduct li a.main-contain"))
)

elem_link = driver.find_elements(By.CSS_SELECTOR, "ul.listproduct li a.main-contain")
link_all = [elem.get_attribute("href") for elem in elem_link 
            if elem.get_attribute("href") and "dtdd" in elem.get_attribute("href")]

product_links = list(set([link for link in link_all if link]))
print(f"✅ Tìm thấy {len(product_links)} sản phẩm")

# ==================== BƯỚC 2: VÀO TỪNG LINK CRAWL ====================
for i, link in enumerate(product_links[:5]):  # Giới hạn 5 sản phẩm để test
    print(f"\n📌 Đang crawl sản phẩm {i+1}/{len(product_links)}: {link}")
    try:
        driver.get(link)
        time.sleep(random.randint(3, 6))

        product_info = {"link": link}

        # Tên sản phẩm
        try:
            name = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1.detail-name"))
            ).text.strip()
        except:
            try:
                name = driver.find_element(By.TAG_NAME, "h1").text.strip()
            except:
                print("❌ Không lấy được tên sản phẩm, bỏ qua...")
                continue

        product_info["name"] = name
        print(f"📱 Tên sản phẩm: {name}")

        # Phiên bản và giá
        versions = []
        try:
            memory_options = driver.find_elements(By.CSS_SELECTOR, "ul.list-box li, ul.flex li, li.item")
            for option in memory_options:
                try:
                    gb = option.find_element(By.TAG_NAME, "span").text.strip()
                    price = option.find_element(By.CSS_SELECTOR, "strong").text.strip()
                    versions.append({"gb": gb, "price": price})
                except:
                    continue
        except:
            pass

        if not versions:
            try:
                price = driver.find_element(By.CSS_SELECTOR, "strong.price").text.strip()
                versions.append({"gb": "Mặc định", "price": price})
            except:
                versions.append({"gb": "Mặc định", "price": "Không có giá"})

        product_info["versions"] = versions

        try:
            product_info["price_current"] = driver.find_element(By.CSS_SELECTOR, "strong.price").text.strip()
        except:
            product_info["price_current"] = "Không có giá hiện tại"

        try:
            product_info["price_old"] = driver.find_element(By.CSS_SELECTOR, "p.old-price").text.strip()
        except:
            product_info["price_old"] = "Không có giá gốc"

        # ==================== CRAWL URL ẢNH ====================
        img_urls = []
        try:
            gallery_images = driver.find_elements(By.CSS_SELECTOR, "div.gallery img, img.medium-img, picture img")
            for img in gallery_images:
                src = img.get_attribute("src") or img.get_attribute("data-src")
                if src and "http" in src:
                    if src.startswith("//"):
                        src = "https:" + src
                    if src not in img_urls:
                        img_urls.append(src)

            if not img_urls:
                img_elements = driver.find_elements(By.XPATH, "//img[contains(@src, 'Products/') or contains(@src, 'product')]")
                for img in img_elements:
                    src = img.get_attribute("src") or img.get_attribute("data-src")
                    if src and "http" in src:
                        if src.startswith("//"):
                            src = "https:" + src
                        if src not in img_urls:
                            img_urls.append(src)

            if not img_urls:
                all_images = driver.find_elements(By.TAG_NAME, "img")
                for img in all_images:
                    src = img.get_attribute("src") or img.get_attribute("data-src")
                    if src and "http" in src and any(x in src for x in ["400x400", "300x300", "500x500"]):
                        if src.startswith("//"):
                            src = "https:" + src
                        if src not in img_urls:
                            img_urls.append(src)

            print(f" Tìm thấy {len(img_urls)} ảnh URL")
        except Exception as e:
            print(f" Lỗi khi tìm ảnh: {e}")

        product_info["image_urls"] = img_urls

        # ==================== LƯU VÀ GỬI ====================
        data_all.append(product_info)
        with open("products.json", "w", encoding="utf-8") as f:
            json.dump(data_all, f, ensure_ascii=False, indent=4)

        producer.send('tgdd-topic', value=product_info)
        print(f"📤 Đã gửi sản phẩm '{name}' lên Kafka topic tgdd-topic")

    except Exception as e:
        print(f"❌ Lỗi với sản phẩm {link}: {str(e)}")
        continue

# ==================== HOÀN THÀNH ====================
driver.quit()
producer.flush()
print(f"\n🎯 Đã hoàn thành crawl {len(data_all)} sản phẩm")
print("📁 Dữ liệu đã lưu vào products.json")
print("✅ Dữ liệu đã gửi lên Kafka topic tgdd-topic")
