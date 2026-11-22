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

md("## 2. Repoyu indir (varsa güncelle)\nÜstteki iki parametreyi değiştir: `REPO_URL` (herkese açık ya da özel repo) ve `BRANCH`. Özel repo için Colab Secrets'a `GITHUB_TOKEN` ekle; token ekrana yazılmaz, URL'ye ve .git/config'e hiç girmez.")
code("""
# --- PARAMETRELER ---
REPO_URL = "https://github.com/furkancol10/turkish-notes-rag.git"
BRANCH = "colab"
# --------------------
import os, subprocess, base64
DIR = "/content/KisiselNotArama"
try:
    from google.colab import userdata
    def secret(k):
        try: return (userdata.get(k) or "").strip() or None
        except Exception: return None
except ImportError:
    secret = lambda k: (os.environ.get(k) or "").strip() or None

# Token URL'ye ve .git/config'e yazılmaz: yalnız bu git süreçlerinin ortamında http.extraheader olarak gider.
_tok = secret("GITHUB_TOKEN")
_env = os.environ.copy()
if _tok:
    _hdr = "Authorization: Basic " + base64.b64encode(f"x-access-token:{_tok}".encode()).decode()
    _env.update(GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="http.extraheader", GIT_CONFIG_VALUE_0=_hdr)

def git(*args):
    r = subprocess.run(["git", *args], capture_output=True, text=True, env=_env)
    if r.returncode:
        err = r.stderr or ""
        if _tok:
            err = err.replace(_tok, "***").replace(_hdr.split()[-1], "***")
        raise RuntimeError("git hatası: " + err)
    return r.stdout

try:
    if os.path.isdir(DIR + "/.git"):
        git("-C", DIR, "fetch", REPO_URL, BRANCH)
        git("-C", DIR, "checkout", BRANCH)
        git("-C", DIR, "pull", "--ff-only", REPO_URL, BRANCH)
    else:
        git("clone", "-b", BRANCH, REPO_URL, DIR)
finally:
    _tok = _hdr = None
    _env.pop("GIT_CONFIG_VALUE_0", None)
    del _env
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

md("## 4. (İsteğe bağlı) Google Drive önbelleği\nModeller ve indeks yerel diskte çalışır; Drive'a yalnız yedeklenir (model çekildikten ve indekslendikten sonra), sonraki oturumda başta geri kopyalanır. Varsayılan kapalı: VS Code Colab eklentisinde Drive bağlanmaz. Tarayıcıdaki Colab'da açmak için `USE_DRIVE = True`.")
code("""
USE_DRIVE = False  # VS Code Colab eklentisinde drive.mount çalışmaz; yalnız tarayıcıdaki Colab'da True yap
# Chroma/SQLite ve Ollama modelleri Drive (FUSE) üzerinde ÇALIŞMAZ: yerel diske çalışır, Drive yalnız yedek.
LOCAL = "/content/cache"
for _d in ("hf", "ollama"):
    os.makedirs(f"{LOCAL}/{_d}", exist_ok=True)
os.environ["HF_HOME"] = LOCAL + "/hf"
os.environ["OLLAMA_MODELS"] = LOCAL + "/ollama"
PAIRS = [("hf", LOCAL + "/hf"), ("ollama", LOCAL + "/ollama"), ("index", DIR + "/data/index")]
CACHE = "/content/drive/MyDrive/KisiselNotArama_cache"

def _cp(src, dst):
    os.makedirs(dst, exist_ok=True)
    subprocess.run(["cp", "-a", src + "/.", dst], check=True)

def sync_from_drive():
    for name, local in PAIRS:
        if os.path.isdir(f"{CACHE}/{name}"):
            _cp(f"{CACHE}/{name}", local)

def sync_to_drive():
    if not USE_DRIVE:
        return
    for name, local in PAIRS:
        if os.path.isdir(local):
            _cp(local, f"{CACHE}/{name}")
    print("Drive'a yedeklendi:", CACHE)

if USE_DRIVE:
    try:
        if not os.path.ismount("/content/drive"):
            from google.colab import drive
            drive.mount("/content/drive")
        sync_from_drive()
        print("Drive önbelleği yerel diske kopyalandı")
    except Exception as e:
        USE_DRIVE = False
        print("Drive bağlanamadı, önbelleksiz devam:", e)
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

def ollama_up():
    try:
        urllib.request.urlopen("http://127.0.0.1:11434", timeout=2); return True
    except Exception:
        return False

if BACKEND == "ollama":
    if not shutil.which("ollama"):
        subprocess.run("set -o pipefail; apt-get update -qq && apt-get install -y -qq zstd && curl -fsSL https://ollama.com/install.sh | sh",
                       shell=True, check=True, executable="/bin/bash")
    if ollama_up():
        print("ollama zaten çalışıyor, başlatma atlandı")
    else:
        OLLAMA_PROC = subprocess.Popen(["ollama", "serve"], stdout=open("/content/ollama.log", "w"), stderr=subprocess.STDOUT, env=os.environ.copy())
        for _ in range(60):
            if OLLAMA_PROC.poll() is not None:
                raise RuntimeError(f"ollama kapandı (kod {OLLAMA_PROC.returncode}), /content/ollama.log dosyasına bak")
            if ollama_up():
                break
            time.sleep(1)
        else:
            raise RuntimeError("ollama açılmadı, /content/ollama.log dosyasına bak")
    from src import config
    subprocess.run(["ollama", "pull", config.LLM_MODEL], check=True)
    sync_to_drive()
else:
    print("API backend: ollama atlandı")
""")

md("## 7. İndeksi oluştur (yoksa)\nNotlar `data/notes` altındadır (kendi notlarını Drive'dan/yükleyerek oraya koyabilirsin).")
code("""
from src import config
from src.index import index_name
_f = config.INDEX_DIR / "numpy" / index_name(config.EMBED_MODEL, config.CHUNK_STRATEGY, config.CHUNK_SIZE) / "vecs.npy"
if not _f.exists():
    subprocess.run([sys.executable, "-m", "src.cli", "index"], check=True)
    sync_to_drive()
else:
    print("İndeks hazır, atlandı")
""")

md("## 8. Streamlit + cloudflared tüneli\nÇıkan `https://...trycloudflare.com` adresini ekibe ver.")
code("""
import re, urllib.request

def stop(name):
    p = globals().get(name)
    if p is not None and p.poll() is None:
        p.terminate()
        try: p.wait(10)
        except subprocess.TimeoutExpired: p.kill()

def tail(path, n=15):
    try: return "".join(open(path).readlines()[-n:])
    except OSError: return "(log yok)"

stop("ST_PROC"); stop("TUN_PROC")
if not shutil.which("cloudflared"):
    subprocess.run("curl -fsSL -o /usr/local/bin/cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 && chmod +x /usr/local/bin/cloudflared", shell=True, check=True)
ST_PROC = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless", "true", "--server.port", "8501",
                  "--server.address", "0.0.0.0", "--server.enableCORS", "false", "--server.enableXsrfProtection", "false"],
                 stdout=open("/content/streamlit.log", "w"), stderr=subprocess.STDOUT, env=os.environ.copy())
for _ in range(90):
    if ST_PROC.poll() is not None:
        raise RuntimeError(f"streamlit kapandı (kod {ST_PROC.returncode}):\\n" + tail("/content/streamlit.log"))
    try:
        if urllib.request.urlopen("http://127.0.0.1:8501/_stcore/health", timeout=2).status == 200:
            break
    except Exception:
        pass
    time.sleep(1)
else:
    stop("ST_PROC")
    raise RuntimeError("streamlit 90 sn'de hazır olmadı:\\n" + tail("/content/streamlit.log"))

TUN_PROC = subprocess.Popen(["cloudflared", "tunnel", "--url", "http://localhost:8501"],
                            stdout=subprocess.DEVNULL, stderr=open("/content/cloudflared.log", "w"))
url = None
for _ in range(60):
    if TUN_PROC.poll() is not None:
        raise RuntimeError(f"cloudflared kapandı (kod {TUN_PROC.returncode}):\\n" + tail("/content/cloudflared.log"))
    m = re.search(r"https://[-a-z0-9]+[.]trycloudflare[.]com", open("/content/cloudflared.log").read())
    if m:
        url = m.group(0); break
    time.sleep(1)
if not url:
    stop("TUN_PROC")
    raise RuntimeError("Tünel adresi 60 sn'de çıkmadı:\\n" + tail("/content/cloudflared.log"))
print("\\n" + "=" * 60 + "\\nUYGULAMA ADRESİ:  " + url + "\\n" + "=" * 60)
""")

nb = nbf.v4.new_notebook(cells=C, metadata={"accelerator": "GPU", "colab": {"provenance": []},
                                            "kernelspec": {"name": "python3", "display_name": "Python 3"}})
nbf.write(nb, Path(__file__).with_name("colab_run.ipynb"))
