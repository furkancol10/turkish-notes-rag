"""colab/colab_run.ipynb dosyasını üretir:  python colab/make_notebook.py"""
from pathlib import Path

import nbformat as nbf

C = []
md = lambda s: C.append(nbf.v4.new_markdown_cell(s.strip()))
code = lambda s: C.append(nbf.v4.new_code_cell(s.strip()))

md("""
# Kişisel Not Arama - Colab'da çalıştır
Hücreleri sırayla çalıştır. **Çalışma zamanı > Çalışma zamanı türünü değiştir > T4 GPU** seç (GPU yoksa API anahtarı gerekir).
Colab **Secrets** (anahtar simgesi) içinde isteğe bağlı: `GITHUB_TOKEN` (özel repo), `GEMINI_API_KEY`, `GROQ_API_KEY`.
""")

md("## 1. GPU kontrolü")
code("""
import subprocess, shutil
HAS_GPU = shutil.which("nvidia-smi") is not None and subprocess.run(["nvidia-smi"], capture_output=True).returncode == 0
print("GPU var" if HAS_GPU else "GPU YOK")
if HAS_GPU:
    print(subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"], capture_output=True, text=True).stdout)
""")

md("## 2. Repoyu indir (varsa güncelle)\nÜstteki iki parametreyi değiştir: `REPO_URL` (herkese açık ya da özel repo) ve `BRANCH`. Özel repo için Colab Secrets'a `GITHUB_TOKEN` ekle; token ekrana yazılmaz ve işlem sonunda git remote adresinden silinir.")
code("""
# --- PARAMETRELER ---
REPO_URL = "https://github.com/furkancol10/turkish-notes-rag.git"
BRANCH = "colab"
# --------------------
import os, subprocess
DIR = "/content/KisiselNotArama"
try:
    from google.colab import userdata
    def secret(k):
        try: return userdata.get(k)
        except Exception: return None
except ImportError:
    secret = lambda k: os.environ.get(k)

tok = secret("GITHUB_TOKEN")
auth_url = REPO_URL.replace("https://", f"https://{tok}@", 1) if tok else REPO_URL

def git(*args):
    r = subprocess.run(["git", *args], capture_output=True, text=True)
    if r.returncode:
        err = (r.stderr or "").replace(tok, "***") if tok else r.stderr
        raise RuntimeError("git hatası: " + err)
    return r.stdout

if os.path.isdir(DIR + "/.git"):
    git("-C", DIR, "remote", "set-url", "origin", auth_url)
    try:
        git("-C", DIR, "fetch", "origin", BRANCH)
        git("-C", DIR, "checkout", BRANCH)
        git("-C", DIR, "pull", "--ff-only", "origin", BRANCH)
    finally:
        git("-C", DIR, "remote", "set-url", "origin", REPO_URL)
else:
    try:
        git("clone", "-b", BRANCH, auth_url, DIR)
    finally:
        if os.path.isdir(DIR + "/.git"):
            git("-C", DIR, "remote", "set-url", "origin", REPO_URL)
os.chdir(DIR)
print(git("log", "--oneline", "-1"))
""")

md("## 3. Bağımlılıklar\npyproject'teki paketler kurulur; `torch` (Colab'da hazır) ve `pyside6` (masaüstü arayüzü) atlanır.")
code("""
import tomllib, re, subprocess, sys
deps = tomllib.load(open("pyproject.toml", "rb"))["project"]["dependencies"]
deps = [d for d in deps if not re.match(r"(torch|pyside6)\\b", d, re.I)]
subprocess.run([sys.executable, "-m", "pip", "install", "-q", *deps], check=True)
print("kuruldu:", len(deps), "paket")
""")

md("## 4. (İsteğe bağlı) Google Drive önbelleği\nModeller ve indeks Drive'a yazılır; sonraki oturumlar hızlı açılır. İstemiyorsan `USE_DRIVE = False`.")
code("""
USE_DRIVE = True
if USE_DRIVE:
    from google.colab import drive
    drive.mount("/content/drive")
    CACHE = "/content/drive/MyDrive/KisiselNotArama_cache"
    os.makedirs(CACHE + "/hf", exist_ok=True); os.makedirs(CACHE + "/ollama", exist_ok=True); os.makedirs(CACHE + "/index", exist_ok=True)
    os.environ["HF_HOME"] = CACHE + "/hf"
    os.environ["OLLAMA_MODELS"] = CACHE + "/ollama"
    idx = DIR + "/data/index"
    if not os.path.islink(idx):
        if os.path.isdir(idx):
            import shutil as _sh; _sh.rmtree(idx)
        os.makedirs(DIR + "/data", exist_ok=True)
        os.symlink(CACHE + "/index", idx)
    print("Drive önbelleği:", CACHE)
""")

md("## 5. Backend seçimi\nGPU varsa **ollama**; GPU yok + `GEMINI_API_KEY`/`GROQ_API_KEY` varsa **api**; yoksa CPU'da ollama (çok yavaş).")
code("""
for k in ("GEMINI_API_KEY", "GROQ_API_KEY"):
    v = secret(k)
    if v: os.environ[k] = v
has_key = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GROQ_API_KEY"))
if HAS_GPU:
    BACKEND = "ollama"
elif has_key:
    BACKEND = "api"
else:
    BACKEND = "ollama"
    print("UYARI: GPU ve API anahtarı yok, ollama CPU'da çalışacak (çok yavaş). T4 GPU seçmeni öneririm.")
os.environ["LLM_BACKEND"] = BACKEND
print("Backend:", BACKEND)
""")

md("## 6. Ollama kurulumu ve model (yalnız backend=ollama)")
code("""
import time, urllib.request
if BACKEND == "ollama":
    if not shutil.which("ollama"):
        subprocess.run("apt-get install -y -qq zstd && curl -fsSL https://ollama.com/install.sh | sh", shell=True, check=True)
    subprocess.Popen(["ollama", "serve"], stdout=open("/content/ollama.log", "w"), stderr=subprocess.STDOUT, env=os.environ.copy())
    for _ in range(60):
        try:
            urllib.request.urlopen("http://127.0.0.1:11434"); break
        except Exception:
            time.sleep(1)
    else:
        raise RuntimeError("ollama açılmadı, /content/ollama.log dosyasına bak")
    from src import config
    subprocess.run(["ollama", "pull", config.LLM_MODEL], check=True)
else:
    print("API backend: ollama atlandı")
""")

md("## 7. İndeksi oluştur (yoksa)\nNotlar `data/notes` altındadır (kendi notlarını Drive'dan/yükleyerek oraya koyabilirsin).")
code("""
if not os.path.isdir(DIR + "/data/index/chroma"):
    subprocess.run([sys.executable, "-m", "src.cli", "index"], check=True)
else:
    print("İndeks hazır, atlandı")
""")

md("## 8. Streamlit + cloudflared tüneli\nÇıkan `https://...trycloudflare.com` adresini ekibe ver.")
code("""
import re
subprocess.run("pkill -f streamlit; pkill -f cloudflared", shell=True)
if not shutil.which("cloudflared"):
    subprocess.run("curl -fsSL -o /usr/local/bin/cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 && chmod +x /usr/local/bin/cloudflared", shell=True, check=True)
subprocess.Popen([sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless", "true", "--server.port", "8501",
                  "--server.address", "0.0.0.0", "--server.enableCORS", "false", "--server.enableXsrfProtection", "false"],
                 stdout=open("/content/streamlit.log", "w"), stderr=subprocess.STDOUT, env=os.environ.copy())
time.sleep(8)
tun = subprocess.Popen(["cloudflared", "tunnel", "--url", "http://localhost:8501"], stderr=subprocess.PIPE, text=True)
for line in tun.stderr:
    m = re.search(r"https://[-a-z0-9]+\\.trycloudflare\\.com", line)
    if m:
        print("\\n" + "=" * 60 + "\\nUYGULAMA ADRESİ:  " + m.group(0) + "\\n" + "=" * 60)
        break
""")

nb = nbf.v4.new_notebook(cells=C, metadata={"accelerator": "GPU", "colab": {"provenance": []},
                                            "kernelspec": {"name": "python3", "display_name": "Python 3"}})
nbf.write(nb, Path(__file__).with_name("colab_run.ipynb"))
