"""Tüm ayarlar tek yerde. Denemek için sadece bu dosyayı değiştir."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTES_DIR = ROOT / "data" / "notes"      # varsayılan (örnek) notlar; etkin klasör: src.settings.notes_dir()
INDEX_DIR = ROOT / "data" / "index"      # index buraya yazılır (git'e girmez)

# --- Embedding modelleri ---
EMBED_MODELS = [
    "newmindai/Mursit-Large-TR-Retrieval",
    "trmteb/turkish-embedding-model",
    "BAAI/bge-m3",
]
EMBED_MODEL = "BAAI/bge-m3"  # varsayılan: 24 soruluk testte en iyi (hit@1 .96, MRR .979, chunk 512)
# Model kartlarına göre üçü de sorgu/pasaj öneki GEREKTİRMİYOR (bge-m3 kartı: "no instructions").
# Başka bir model eklersen (ör. e5: "query: " / "passage: ") buraya yaz.
QUERY_PREFIX = {m: "" for m in EMBED_MODELS}
PASSAGE_PREFIX = {m: "" for m in EMBED_MODELS}

# --- Embedding cihazı ---
EMBED_DEVICE_INDEX = "auto"   # toplu embedding (indeksleme, eval): "auto" = CUDA varsa GPU, yoksa CPU; "cpu" / "cuda"
EMBED_DEVICE_QUERY = "cpu"    # tek soru embedding'i: CPU (GPU'yu LLM'e bırakır)
EMBED_INDEX_DTYPE = "float16" # GPU'da indeksleme hassasiyeti ("float16" / "float32"); CPU hep float32
EMBED_BATCH_SIZE = 32

# --- Parçalama ---
CHUNK_STRATEGY = "fixed"   # "fixed" (sabit boyut + örtüşme) veya "heading" (başlık bazlı)
CHUNK_SIZE = 512           # karakter
CHUNK_OVERLAP = 64         # karakter

# --- Arama ---
INDEX_BACKEND = "chroma"   # "chroma" (varsayılan, vektör DB) veya "numpy" (elle kosinüs, öğrenme amaçlı)
SCORE_THRESHOLD = 0.40     # en iyi parçanın kosinüs skoru bunun altındaysa LLM çağrılmaz ("notlarda yok"); kalibre edildi
SCORE_THRESHOLD_ENABLED = True
ENTITY_GUARD_ENABLED = True  # soruda özel ad var ve getirilen hiçbir parçada geçmiyorsa LLM çağrılmaz ("notlarda yok")
TOP_K = 10                # 10 parça ≈ 2000 token; num_ctx 4096 içinde rahat sığar

# --- LLM (Ollama, GPU) ---
LLM_MODEL = "qwen3.5:4b"
# use_mmap: Ollama bellek sıkışınca modeli RAM'e kopyalıyor (5+ GB); mmap ile ağırlıklar dosyadan okunur, RAM geri alınabilir
LLM_OPTIONS = {"num_ctx": 4096, "temperature": 0.2, "use_mmap": True}
LLM_KEEP_ALIVE = "2m"
LLM_THINK = False
