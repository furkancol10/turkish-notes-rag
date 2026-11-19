# Belgeler arası karışma değerlendirmesi

k=10; üretim: açık. Saflık = top-k parçanın izinli belgelerden payı; kirlenme = atıf yapılan kaynaklardan izinli olmayanların payı; yabancı atıflı = en az 1 izinsiz belgeye atıf yapan cevap oranı; anahtar bilgi = beklenen anahtar kelimelerin kapsaması (sadece tek belgelik sorular). Mod off = doc_filter=None (belge filtresi kapalı, baz çizgi); mod auto = doc_filter="auto". Üretim her iki modda da MEVCUT generator (gruplu prompt) ile yapılır; eski generator ayrı ölçülemez, yani off kolonu 'filtresiz arama + yeni prompt' demektir. Arama saflığı kolonu sadece arama değişikliğini ölçer.

| Mod | Korpus | Tür | N | Arama saflığı | Kirlenme | Yabancı atıflı cevap | Anahtar bilgi |
|---|---|---|---|---|---|---|---|
| off | notes | tek belge | 21 | 13% | 0% | 0% | 98% |
| off | notes | karşılaştırma | 4 | 22% | 0% | 0% | - |
| off | notes | tümü | 25 | 14% | 0% | 0% | 98% |
| off | docs | tek belge | 10 | 39% | 0% | 0% | 85% |
| off | docs | karşılaştırma | 2 | 60% | 22% | 50% | - |
| off | docs | tümü | 12 | 42% | 4% | 8% | 85% |
| auto | notes | tek belge | 21 | 82% | 2% | 5% | 95% |
| auto | notes | karşılaştırma | 4 | 100% | 0% | 0% | - |
| auto | notes | tümü | 25 | 85% | 2% | 4% | 95% |
| auto | docs | tek belge | 10 | 100% | 0% | 0% | 100% |
| auto | docs | karşılaştırma | 2 | 100% | 0% | 0% | - |
| auto | docs | tümü | 12 | 100% | 0% | 0% | 100% |

## En kötü 5 örnek (yabancı atıflı)

- **Docker'da port yönlendirme nasıl yapılır?** (notes; izinli: teknik_docker.md; kirlenme 50%)
  - atıflar: teknik_docker.md, teknik_docker_compose.md
  - cevap: Docker'da port yönlendirmesi için `-p` bayrağı kullanılır; örneğin `docker run -p 8080:80 nginx` komutuyla ana makinenin 8080 portu konteynerin 80 portuna bağlanır [1]. Docker Compose'da ise port eşlemesini tırnak içinde (`"8080:80"`) yazmak gerekir, çünkü bazı değerler YAML'da sayı olarak yorumlana

## Genel soru seti (dondurulmuş)

Belirli belgeye işaret eden sorularda filtre isabeti: **80%** (N=25, notes). Genel sorularda yanlış filtre oranı: **25%** (8/32; hedef 0%). Ölçüm: f09fd80 (düzeltmelerden sonra).

Set: `eval/general_frozen.json` (dondurulmuş, kurallar bu sete göre ayarlanmaz). Yalnız arama, LLM yok.

Yanlış filtre alan genel sorular:

- Veri nedir? -> ders_veri_yapilari.md
- Veri analizi nereden başlanır? -> ders_veri_yapilari.md
- Bütçe nasıl hazırlanır? -> kisisel_butce.md
- Aylık bütçeyi aşmamak için ne yapmalı? -> kisisel_butce.md
- Ders programı nasıl düzenlenir? -> spor_kosu_programi.md
- İyi bir film nasıl seçilir? -> film_inception.md
- Film izlerken ne yenir? -> film_inception.md
- Spor yapmak için en iyi saat hangisi? -> spor_kosu_programi.md

Filtre isabetsiz belge soruları:

- Aylık tasarruf hedefim kaç TL? -> None
- 21 Ders kitabında eğitim için önerilen dört K nedir? -> None
- 21 Ders'te Harari günde kaç saat meditasyon yapıyor? -> None
- Docker'da port yönlendirme nasıl yapılır? -> ['teknik_docker.md', 'teknik_docker_compose.md']
- Docker Compose'ta depends_on servisin hazır olmasını bekler mi? -> ['teknik_docker.md', 'teknik_docker_compose.md']

