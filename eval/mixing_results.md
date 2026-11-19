# Belgeler arası karışma değerlendirmesi

k=10; üretim: açık. Saflık = top-k parçanın izinli belgelerden payı; kirlenme = atıf yapılan kaynaklardan izinli olmayanların payı; yabancı atıflı = en az 1 izinsiz belgeye atıf yapan cevap oranı; anahtar bilgi = beklenen anahtar kelimelerin kapsaması (sadece tek belgelik sorular). Mod off = doc_filter=None (belge filtresi kapalı, baz çizgi); mod auto = doc_filter="auto". Üretim her iki modda da MEVCUT generator (gruplu prompt) ile yapılır; eski generator ayrı ölçülemez, yani off kolonu 'filtresiz arama + yeni prompt' demektir. Arama saflığı kolonu sadece arama değişikliğini ölçer.

| Mod | Korpus | Tür | N | Arama saflığı | Kirlenme | Yabancı atıflı cevap | Anahtar bilgi |
|---|---|---|---|---|---|---|---|
| off | notes | tek belge | 21 | 13% | 2% | 5% | 98% |
| off | notes | karşılaştırma | 4 | 22% | 0% | 0% | - |
| off | notes | tümü | 25 | 14% | 2% | 4% | 98% |
| off | docs | tek belge | 10 | 39% | 3% | 10% | 85% |
| off | docs | karşılaştırma | 2 | 60% | 57% | 100% | - |
| off | docs | tümü | 12 | 42% | 12% | 25% | 85% |
| auto | notes | tek belge | 21 | 78% | 2% | 5% | 95% |
| auto | notes | karşılaştırma | 4 | 100% | 0% | 0% | - |
| auto | notes | tümü | 25 | 81% | 2% | 4% | 95% |
| auto | docs | tek belge | 10 | 100% | 0% | 0% | 100% |
| auto | docs | karşılaştırma | 2 | 80% | 0% | 0% | - |
| auto | docs | tümü | 12 | 97% | 0% | 0% | 100% |

## En kötü 5 örnek (yabancı atıflı)

- **Docker'da port yönlendirme nasıl yapılır?** (notes; izinli: teknik_docker.md; kirlenme 50%)
  - atıflar: teknik_docker.md, teknik_docker_compose.md
  - cevap: Docker'da port yönlendirmek için `-p` bayrağı kullanılır. Örneğin, `docker run -p 8080:80 nginx` komutuyla ana makinenin 8080 portu konteynerin 80 portuna bağlanır [1]. Docker Compose'da ise port eşlemesini tırnak içinde (`"8080:80"`) yazmak gerekir, çünkü bazı değerler YAML'da sayı olarak yorumlana
