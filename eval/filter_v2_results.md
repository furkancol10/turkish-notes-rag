# Filtre v2 sonuçları (tek ölçüm, dondurulmuş setler)

Setler: `eval/general_frozen_v2.json`, `eval/doc_targeted_v2.json` (kurallar bu sete göre ayarlanmaz).

Hit tanımı: filtre boş değil, beklenen belgelerin tümünü içerir ve en fazla 1 fazla belge içerir.

- Genel sorularda yanlış filtre: **1/40** (hedef 0)
- Hedefli isabet: **25/26** (96%)
- Hedefli kaçırılan (None): 1; yanlış belge: 0

Yanlış filtre alan genel sorular:
- Makine öğrenmesi nedir kısaca? -> ['ders_makine_ogrenmesi.md']

Kaçırılan (None):
- baklava tarifinde kaç kat yufka kullanılıyor?
