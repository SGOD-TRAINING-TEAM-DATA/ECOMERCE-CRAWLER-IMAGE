import threading
import subprocess

# Danh sách script crawler và topic
scripts = {
    "cell-phone.py": "cellphone-topic",
    "lazada.py": "lazada-topic",
    #"TGDD.py": "tgdd-topic",
    "tiki.py": "tiki-topic"
}

def run_script(script):
    print(f"[INFO] Running {script} ...", flush=True)
    try:
        subprocess.run(["python", script], check=True)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Script {script} failed: {e}", flush=True)

threads = []
for script in scripts.keys():
    t = threading.Thread(target=run_script, args=(script,))
    t.start()
    threads.append(t)

for t in threads:
    t.join()

print("[INFO] All crawlers finished.")
