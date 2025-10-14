from kafka import KafkaConsumer
import json
import os
import requests
import time
import hashlib



# Danh sách topic muốn download ảnh
topics = ["lazada-topic", "tiki-topic", "cellphone-topic"]

# Tạo thư mục lưu ảnh cho từng topic
for topic in topics:
    os.makedirs(f"images-{topic}", exist_ok=True)

# Tập hợp URL ảnh đã tải để tránh trùng lặp
downloaded_urls = set()

# Tạo Kafka Consumer
consumer = KafkaConsumer(
    *topics,
    bootstrap_servers=['localhost:9092'],
    auto_offset_reset='earliest',
    group_id='image-consumer',
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)

print("[INFO] Consumer started, listening to topics:", topics)

for msg in consumer:
    try:
        data = msg.value
        topic = msg.topic

        # Kiểm tra dữ liệu rỗng
        if not data:
            print(f"[WARN] Nhận được message rỗng từ topic {topic}")
            continue

        img_url = data.get("image_url")
        title = str(data.get("title") or "product").replace(" ", "_")

        # Bỏ qua ảnh không hợp lệ (base64 hoặc rỗng)
        if not img_url or img_url.startswith("data:image"):
            print(f"[WARN] Bỏ qua ảnh không hợp lệ từ topic {topic}")
            continue

        # Bỏ qua ảnh đã tải trước đó
        if img_url in downloaded_urls:
            print(f"[INFO] Bỏ qua ảnh trùng lặp: {img_url}")
            continue

        # Tải ảnh về
        try:
            response = requests.get(img_url, timeout=10)
            if response.status_code == 200:
                # Hash URL để tạo tên file duy nhất
                url_hash = hashlib.md5(img_url.encode()).hexdigest()[:8]
                filename = f"{title}_{url_hash}.jpg"
                filepath = os.path.join(f"images-{topic}", filename)

                with open(filepath, "wb") as f:
                    f.write(response.content)

                downloaded_urls.add(img_url)
                print(f"[{topic}] Saved image: {filepath}")

            else:
                print(f"[{topic}] HTTP {response.status_code} error for {img_url}")
        except Exception as e:
            print(f"[{topic}] Error downloading image: {e}")

    except Exception as e:
        # Bắt toàn bộ lỗi còn sót lại để consumer không bị dừng
        print(f"[ERROR] Unexpected error while processing message: {e}")
