from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time, os, json, requests, re
import numpy as np
import cv2

# Hàm lấy link ảnh từ 1 product element
def get_detail_image(product):
    try:
        img_element = product.find_element(By.CSS_SELECTOR, "img")
        img_url = img_element.get_attribute("src")

        # Nếu src trống, thử srcset hoặc data-src
        if not img_url or img_url.startswith(("data:", "blob:")):
            img_url = img_element.get_attribute("srcset")
            if img_url:
                img_url = img_url.split(" ")[0]
            else:
                img_url = img_element.get_attribute("data-src")

        if not img_url or img_url.startswith(("data:", "blob:")):
            print(" Không tìm được link ảnh hợp lệ, bỏ qua.")
            return None

        return img_url
    except Exception as e:
        print(f"Lỗi lấy ảnh: {e}")
        return None


# Khởi tạo driver
driver = webdriver.Chrome()
driver.get("https://tiki.vn/thiet-bi-kts-phu-kien-so/c1815")

# Đợi trang load và đóng popup nếu có
time.sleep(5)
try:
    close_btn = driver.find_element(By.CSS_SELECTOR, "button[class*='close']")
    close_btn.click()
    time.sleep(2)
except:
    pass

# Scroll để load sản phẩm
for i in range(3):
    driver.execute_script(f"window.scrollTo(0, {1500 * (i+1)});")
    time.sleep(2)

last_height = driver.execute_script("return document.body.scrollHeight")
while True:
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    new_height = driver.execute_script("return document.body.scrollHeight")
    if new_height == last_height:
        break
    last_height = new_height

# Tìm sản phẩm
try:
    products = WebDriverWait(driver, 20).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.product-item, div[data-view-id*='product_list_item']"))
    )
except:
    products = driver.find_elements(By.CSS_SELECTOR, "a.product-item, div[data-view-id*='product_list_item']")

os.makedirs("images", exist_ok=True)
data = []

for idx, p in enumerate(products, start=1):
    try:
        title = p.find_element(By.CSS_SELECTOR, "h3, .name, .title").text
    except:
        title = ""

    try:
        link = p.get_attribute("href")
        if not link:
            link = p.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
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

    # Lấy link ảnh sản phẩm
    img_url = get_detail_image(p)

    img_path = ""
    if img_url:
        try:
            response = requests.get(img_url, timeout=10)
            if response.status_code == 200:
                img_array = np.asarray(bytearray(response.content), dtype=np.uint8)
                img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

                if img is not None:
                    img_path = f"images/product_{idx}.jpg"
                    cv2.imwrite(img_path, img)
                    print(f"Đã lưu ảnh {idx}: {img_path}")
        except Exception as e:
            print(f"❌ Lỗi tải ảnh {idx}: {e}")

    # Lưu data thô
    data.append({
        "title": title,
        "link": link,
        "price_after": price_after,
        "discount": discount,
        "image_file": img_path
    })

# Xử lý giá gốc
cleaned_data = []
for item in data:
    try:
        price_num = int(re.sub(r"[^\d]", "", item["price_after"]))
        if item["discount"]:
            match = re.search(r"(\d+)%", item["discount"])
            if match:
                percent = int(match.group(1))
                original_price = round(price_num / (1 - percent/100))
                item["original_price"] = f"{original_price:,} ₫".replace(",", ".")
            else:
                item["original_price"] = None
        else:
            item["original_price"] = None
    except:
        item["original_price"] = None
    cleaned_data.append(item)

with open("tiki_products.json", "w", encoding="utf-8") as f:
    json.dump(cleaned_data, f, ensure_ascii=False, indent=4)

print(f"Đã lưu dữ liệu {len(cleaned_data)} sản phẩm vào tiki_products.json")
print(f"Đã tải {sum(1 for item in cleaned_data if item['image_file'])} ảnh vào thư mục images/")

driver.quit()
