# Belgeler arası karışma değerlendirmesi

k=10; üretim: açık. Saflık = top-k parçanın izinli belgelerden payı; kirlenme = atıf yapılan kaynaklardan izinli olmayanların payı; yabancı atıflı = en az 1 izinsiz belgeye atıf yapan cevap oranı; anahtar bilgi = beklenen anahtar kelimelerin kapsaması (sadece tek belgelik sorular). Mod off = doc_filter=None (belge filtresi kapalı, baz çizgi); mod auto = doc_filter="auto". Üretim her iki modda da MEVCUT generator (gruplu prompt) ile yapılır; eski generator ayrı ölçülemez, yani off kolonu 'filtresiz arama + yeni prompt' demektir. Arama saflığı kolonu sadece arama değişikliğini ölçer.

| Mod | Korpus | Tür | N | Arama saflığı | Kirlenme | Yabancı atıflı cevap | Anahtar bilgi |
|---|---|---|---|---|---|---|---|
| off | notes | tek belge | 21 | 13% | 0% | 0% | 98% |
| off | notes | karşılaştırma | 4 | 22% | 0% | 0% | - |
| off | notes | tümü | 25 | 14% | 0% | 0% | 98% |
| off | docs | tek belge | 10 | 39% | 3% | 10% | 85% |
| off | docs | karşılaştırma | 2 | 60% | 52% | 100% | - |
| off | docs | tümü | 12 | 42% | 11% | 25% | 85% |
| auto | notes | tek belge | 21 | 82% | 2% | 5% | 95% |
| auto | notes | karşılaştırma | 4 | 100% | 0% | 0% | - |
| auto | notes | tümü | 25 | 85% | 2% | 4% | 95% |
| auto | docs | tek belge | 10 | 100% | 0% | 0% | 100% |
| auto | docs | karşılaştırma | 2 | 80% | 12% | 50% | - |
| auto | docs | tümü | 12 | 97% | 2% | 8% | 100% |

## En kötü 5 örnek (yabancı atıflı)

- **Docker'da port yönlendirme nasıl yapılır?** (notes; izinli: teknik_docker.md; kirlenme 50%)
  - atıflar: teknik_docker.md, teknik_docker_compose.md
  - cevap: Docker'da port yönlendirme yapmak için `-p` bayrağı kullanılır; bu bayrak ana makinenin belirli portunu konteynerin bir portuna bağlar. Örneğin, `docker run -p 8080:80 nginx` komutuyla ana makinenin 8080 portu konteynerin 80 portuna yönlendirilir [1]. Docker Compose kullanıldığında ise port eşlemesi
- **DeepSeek ve Qwen raporlarında değerlendirme projesi nasıl ele alınmış?** (docs; izinli: deepseekRag, qwenRag; kirlenme 25%)
  - atıflar: deepseekRag.html, gptRag.pdf, deepseekRag.pdf, deepseekRag.pdf
  - cevap: DeepSeek ve Qwen raporları, RAG sistemini ölçmeyi öğrenmek amacıyla "Değerlendirme (Evaluation)" adlı ileri seviye bir proje önermişlerdir [1][9]. Bu projede amaç, en çok atlanan ama kritik adım olan sistemin ölçülmesi için 20-30 soruluk bir test seti oluşturmak ve her soru için altın standart cevab
