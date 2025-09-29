import re
import cv2
import requests
import numpy as np
from selenium import webdriver
import time, random, json
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from itertools import zip_longest
import os
from PIL import Image
from io import BytesIO

# Setup Selenium
driver_path = r"D:\chromedriver-win64\chromedriver.exe"

service = Service(driver_path)
options = Options()
options.add_argument("start-maximized")

driver = webdriver.Chrome(service=service, options=options)

# Mở trang Lazada
driver.get("https://www.lazada.vn/catalog/?q=iphone")
time.sleep(random.randint(5,8))

# Scroll xuống để load sản phẩm
for i in range(5):
    driver.execute_script("window.scrollBy(0, 1500);")
    time.sleep(2)

# Chờ sản phẩm xuất hiện
WebDriverWait(driver, 20).until(
    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[title][href]"))
)

# ======= Crawl dữ liệu
elems = driver.find_elements(By.CSS_SELECTOR,"a[title][href]")
title = [elem.get_attribute("title") for elem in elems]
links = [elem.get_attribute('href') for elem in elems]

elems_price = driver.find_elements(By.CSS_SELECTOR,".aBrP0")
price = [elem.text for elem in elems_price]

elems_discount = driver.find_elements(By.CSS_SELECTOR,".WNoq3")
discount_all = [elem.text for elem in elems_discount]

elems_review = driver.find_elements(By.CSS_SELECTOR,"._6uN7R")
review_all = [elem.text for elem in elems_review]

# Sửa CSS selector cho ảnh - tìm thẻ img trong container
elems_img_containers = driver.find_elements(By.CSS_SELECTOR, ".picture-wrapper")
images = []
for container in elems_img_containers:
    try:
        img_element = container.find_element(By.TAG_NAME, "img")
        img_url = img_element.get_attribute("src")
        
        # Chuyển đổi URL ảnh AVIF sang định dạng JPG/PNG bằng cách xóa phần _80x80q80.avif
        if img_url and ".avif" in img_url:
            # Lấy URL gốc không có kích thước và định dạng AVIF
            img_url = img_url.split('_')[0] + '.jpg'
            
        images.append(img_url)
    except:
        images.append(None)

# Gom dữ liệu
raw_data = list(zip_longest(title, price, discount_all, review_all, links, images, fillvalue=None))

data = []
for idx, item in enumerate(raw_data, start=1):
    d = {
        "title": item[0],
        "price": item[1],
        "discount": item[2],
        "review": item[3],
        "link_item": item[4],
        "image_url": item[5],
        "index_": idx
    }
    data.append(d)

# ======== Lọc dữ liệu không hợp lệ
cleaned_data = []
for item in data:
    if not item["title"]:
        continue
    if "thắc mắc" in item["title"].lower():
        continue
    if item["link_item"] and "faq" in item["link_item"].lower():
        continue

    # ====== Tính giá gốc
    try:
        price_num = int(re.sub(r"[^\d]", "", item["price"]))
        if item["discount"]:
            match = re.search(r"(\d+)%", item["discount"])
            if match:
                percent = int(match.group(1))
                original_price = round(price_num / (1 - percent/100))
                item["original_price"] = f"{original_price:,} ₫"
            else:
                item["original_price"] = None
        else:
            item["original_price"] = None
    except:
        item["original_price"] = None

    cleaned_data.append(item)

# ====== Tạo folder ảnh
os.makedirs("product_images", exist_ok=True)

# ====== Lưu ảnh bằng PIL thay vì OpenCV trực tiếp
for item in cleaned_data:
    if item["image_url"] and "http" in item["image_url"]:
        try:
            # Tải ảnh từ URL
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(item["image_url"], headers=headers, timeout=10)
            
            # Sử dụng PIL để đọc ảnh (hỗ trợ nhiều định dạng hơn)
            img = Image.open(BytesIO(response.content))
            
            # Chuyển đổi sang định dạng OpenCV (BGR)
            if img.mode == 'RGBA':
                # Nếu ảnh có kênh alpha, chuyển đổi thành RGB
                img = img.convert('RGB')
            
            # Chuyển đổi sang numpy array và sau đó sang OpenCV format
            img_array = np.array(img)
            opencv_image = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            
            # Lưu ảnh
            filename = f"product_images/{item['index_']}.jpg"
            cv2.imwrite(filename, opencv_image)
            item["image_file"] = filename
            print(f"Đã lưu ảnh: {filename}")
                
        except Exception as e:
            item["image_file"] = None
            print(f"Lỗi khi tải ảnh {item['image_url']}: {e}")
    else:
        item["image_file"] = None

# Xuất JSON
with open("products.json", "w", encoding="utf-8") as f:
    json.dump(cleaned_data, f, ensure_ascii=False, indent=4)

print(f"Đã lưu {len(cleaned_data)} sản phẩm sạch + ảnh vào products.json và thư mục product_images/")

# Đóng trình duyệt
driver.quit()