"""Tüm ayarlar tek yerde. Denemek için sadece bu dosyayı değiştir."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTES_DIR = ROOT / "data" / "notes"      # varsayılan (örnek) notlar; etkin klasör: src.settings.notes_dir()
INDEX_DIR = ROOT / "data" / "index"      # index buraya yazılır (git'e girmez)

# --- Embedding modelleri (hepsi CPU'da çalışır) ---
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

# --- Parçalama ---
CHUNK_STRATEGY = "fixed"   # "fixed" (sabit boyut + örtüşme) veya "heading" (başlık bazlı)
CHUNK_SIZE = 512           # karakter
CHUNK_OVERLAP = 64         # karakter

# --- Arama ---
INDEX_BACKEND = "chroma"   # "chroma" (varsayılan, vektör DB) veya "numpy" (elle kosinüs, öğrenme amaçlı)
TOP_K = 3

# --- LLM (Ollama, GPU) ---
LLM_MODEL = "qwen3.5:4b"
LLM_OPTIONS = {"num_ctx": 4096, "temperature": 0.2}
LLM_KEEP_ALIVE = "2m"
LLM_THINK = False
