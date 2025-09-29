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

# Kết nối tới driver
driverpath = r"D:\chromedriver-win64\chromedriver.exe"
service = Service(driverpath)
driver = webdriver.Chrome(service=service)

# Mở trang Thế Giới Di Động
driver.get("https://www.thegioididong.com/dtdd#c=42&o=13&pi=2")
time.sleep(random.randint(5, 8))

# Folder lưu ảnh
os.makedirs("images", exist_ok=True)

# Danh sách chứa thông tin sản phẩm
data_all = []

# ========== BƯỚC 1: CRAWL TẤT CẢ LINK SẢN PHẨM TRÊN TRANG ==========
print("Đang tìm sản phẩm...")

# Chờ sản phẩm load
WebDriverWait(driver, 20).until(
    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "ul.listproduct li a.main-contain"))
)

# Craw link sản phẩm
elem_link = driver.find_elements(By.CSS_SELECTOR, "ul.listproduct li a.main-contain")
link_all = [elem.get_attribute("href") for elem in elem_link 
            if elem.get_attribute("href") and "dtdd" in elem.get_attribute("href")]

# Loại bỏ trùng và None
product_links = list(set([link for link in link_all if link]))
print(f"Tìm thấy {len(product_links)} sản phẩm")

# ========== HÀM TẢI ẢNH ĐƠN GIẢN ==========
def download_image(url, filename):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.thegioididong.com/',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8'
        }
        
        response = requests.get(url, headers=headers, timeout=30, stream=True)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return True
    except Exception as e:
        print(f"Lỗi tải ảnh: {e}")
    return False

# ========== BƯỚC 2: VÀO TỪNG LINK ĐỂ CRAWL THÔNG TIN ==========
for i, link in enumerate(product_links[:5]):  # Giới hạn 5 sản phẩm để test
    print(f"\nĐang crawl sản phẩm {i+1}/{len(product_links)}: {link}")
    
    try:
        driver.get(link)
        time.sleep(random.randint(3, 6))

        product_info = {"link": link}

        # Tên sản phẩm
        try:
            name = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1.detail-name"))
            ).text.strip()
            product_info["name"] = name
        except:
            try:
                name = driver.find_element(By.TAG_NAME, "h1").text.strip()
                product_info["name"] = name
            except:
                product_info["name"] = "Không lấy được tên"
                print("Không lấy được tên sản phẩm, bỏ qua...")
                continue

        print(f"Đang xử lý: {name}")

        # Phiên bản và giá
        versions = []
        try:
            # Thử tìm các phiên bản bộ nhớ
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

        # Nếu không có phiên bản, lấy giá chính
        if not versions:
            try:
                price = driver.find_element(By.CSS_SELECTOR, "strong.price").text.strip()
                versions.append({"gb": "Mặc định", "price": price})
            except:
                versions.append({"gb": "Mặc định", "price": "Không có giá"})

        product_info["versions"] = versions

        # Thông tin giá
        try:
            product_info["price_current"] = driver.find_element(By.CSS_SELECTOR, "strong.price").text.strip()
        except:
            product_info["price_current"] = "Không có giá hiện tại"

        try:
            product_info["price_old"] = driver.find_element(By.CSS_SELECTOR, "p.old-price").text.strip()
        except:
            product_info["price_old"] = "Không có giá gốc"

        # ========== CRAWL ẢNH SẢN PHẨM - PHƯƠNG PHÁP MỚI ==========
        img_urls = []
        local_imgs = []

        try:
            # CÁCH 1: Tìm ảnh trong gallery chính
            gallery_images = driver.find_elements(By.CSS_SELECTOR, "div.gallery img, img.medium-img, picture img")
            for img in gallery_images:
                src = img.get_attribute("src") or img.get_attribute("data-src")
                if src and "http" in src:
                    if "//cdn.tgdd.vn/" in src or "//images.fpt.shop" in src:
                        if src not in img_urls:
                            # Chuyển thành URL đầy đủ nếu cần
                            if src.startswith("//"):
                                src = "https:" + src
                            img_urls.append(src)
            
            # CÁCH 2: Nếu không tìm thấy ảnh, thử tìm bằng XPath
            if not img_urls:
                img_elements = driver.find_elements(By.XPATH, "//img[contains(@src, 'Products/') or contains(@src, 'product')]")
                for img in img_elements:
                    src = img.get_attribute("src") or img.get_attribute("data-src")
                    if src and "http" in src and src not in img_urls:
                        if src.startswith("//"):
                            src = "https:" + src
                        img_urls.append(src)
            
            # CÁCH 3: Tìm tất cả ảnh có kích thước lớn (có thể là ảnh sản phẩm)
            if not img_urls:
                all_images = driver.find_elements(By.TAG_NAME, "img")
                for img in all_images:
                    src = img.get_attribute("src") or img.get_attribute("data-src")
                    if src and "http" in src and ("400x400" in src or "300x300" in src or "500x500" in src):
                        if src.startswith("//"):
                            src = "https:" + src
                        if src not in img_urls:
                            img_urls.append(src)
            
            print(f"Tìm thấy {len(img_urls)} ảnh tiềm năng")

        except Exception as e:
            print(f"Lỗi khi tìm ảnh: {e}")

        # Tải ảnh về local
        successful_downloads = 0
        for idx, img_url in enumerate(img_urls[:3]):  # Giới hạn 3 ảnh mỗi sản phẩm
            try:
                # Tạo tên file an toàn
                safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else "_" for c in name)
                safe_name = safe_name.replace(" ", "_")[:50]  # Giới hạn độ dài
                img_name = f"images/{safe_name}_{idx+1}.jpg"
                
                print(f"Đang tải ảnh {idx+1}: {img_url[:100]}...")
                
                # Tải ảnh
                if download_image(img_url, img_name):
                    local_imgs.append(img_name)
                    successful_downloads += 1
                    print(f"✓ Đã tải thành công ảnh {idx+1}")
                else:
                    print(f"✗ Lỗi tải ảnh {idx+1}")
                    
            except Exception as e:
                print(f"Lỗi khi xử lý ảnh {idx+1}: {str(e)}")
                continue

        product_info["image_urls"] = img_urls
        product_info["image_local"] = local_imgs

        # Thêm vào danh sách chung
        data_all.append(product_info)
        print(f"✓ Hoàn thành: {name} - {successful_downloads}/{len(img_urls[:3])} ảnh")

        # Lưu tạm sau mỗi sản phẩm
        with open("products.json", "w", encoding="utf-8") as f:
            json.dump(data_all, f, ensure_ascii=False, indent=4)

    except Exception as e:
        print(f"✗ Lỗi với sản phẩm {link}: {str(e)}")
        continue

# ========== HOÀN THÀNH ==========
driver.quit()
print(f"\nĐã hoàn thành crawl {len(data_all)} sản phẩm")
print("Dữ liệu đã lưu vào products.json và folder images/")