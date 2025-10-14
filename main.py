import threading
import subprocess
import time


def run_consumer():
    print("[INFO] Starting consumer...")
    subprocess.run(["python", "consumer.py"])

def run_producers():
    scripts = ["cell-phone.py", "lazada.py", "tiki.py"]
    threads = []
    for s in scripts:
        t = threading.Thread(target=lambda: subprocess.run(["python", s]))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    print("[INFO] All producers finished.")

# Chạy consumer trước
t1 = threading.Thread(target=run_consumer)
t1.start()

# Chạy producer song song
t2 = threading.Thread(target=run_producers)
t2.start()

# Đợi cả hai hoàn thành
t1.join()
t2.join()
