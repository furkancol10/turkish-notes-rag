# Kişisel Not Arama (naive RAG)

Türkçe kişisel notların üzerinde, framework kullanmadan (LangChain yok) yazılmış küçük bir RAG projesi.
`data/notes/` altındaki notlar **örnek** notlardır; kendi notlarınla değiştir.

## Kurulum
```bash
export PATH=$HOME/.local/bin:$PATH
uv sync                      # Python 3.12, CPU-only torch, sentence-transformers, chromadb...
ollama pull qwen3.5:4b       # LLM (GPU)
```
Embedding modelleri ilk çalıştırmada `~/.cache/huggingface` altına iner.

## Komutlar
```bash
uv run python -m src.cli index                  # notları oku, parçala, embed et, indeksle
uv run python -m src.cli ask "Soru?"            # cevap + kaynak parçalar
uv run python -m src.cli ask "Soru?" --backend chroma
uv run streamlit run app.py                     # sohbet arayüzü (not yükleme, yeniden indeksleme, top_k/backend ayarı)
uv run python -m eval.run_eval                  # chunk boyutu ve model karşılaştırması -> eval/results.md
```

## Masaüstü uygulaması (PySide6)
```bash
uv run python -m desktop.main            # yerel pencere (Streamlit'e alternatif)
bash scripts/install_desktop_entry.sh    # uygulama menüsüne kısayol ekler (yol kurulum anında hesaplanır)
```
Sohbet, kaynakları açılır liste olarak gösterme, not ekleme, yeniden indeksleme, top_k ve backend ayarı.
Ağır işler (model yükleme, indeksleme, LLM) arka planda çalışır; arayüz donmaz. Ollama çalışmalıdır.

## Kendi notlarını ekleme
`.md` veya `.txt` (UTF-8) dosyalarını `data/notes/` içine koy (örnekleri silebilirsin), sonra yeniden `index` çalıştır.
Başlıklar (`# `, `## `) kaynak gösterirken kullanılır, bu yüzden notları başlıkla yapılandırmak yardımcı olur.

## Her adım ne öğretiyor?
| Dosya | RAG adımı | Öğrenilen |
|---|---|---|
| `src/loader.py` | Yükleme | Veri + metadata (dosya adı) birlikte tutulur |
| `src/chunker.py` | Parçalama | Sabit boyut+örtüşme ile başlık bazlı parçalama farkı |
| `src/embedder.py` | Embedding | Metin -> vektör; sorgu/pasaj önekleri (bu 3 model için gerekmiyor) |
| `src/index.py` | İndeksleme | Numpy kosinüs (şeffaf) ve ChromaDB (kalıcı vektör DB) |
| `src/retriever.py` | Geri getirme | Soruyu embed et, top-k en benzer parça |
| `src/generator.py` | Üretim | Sadece bağlama dayalı prompt, "bilmiyorum" davranışı, kaynak atfı |
| `eval/` | Değerlendirme | hit@k ve MRR ile ayar yapmayı ölçerek öğrenme |

Tüm ayarlar (model, chunk boyutu, top_k, yollar) `src/config.py` içinde. Chunk stratejisini veya modeli
değiştirirsen `index`'i yeniden çalıştır.

## Lisans
MIT (bkz. `LICENSE`).
