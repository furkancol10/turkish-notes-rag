# Skor eşiği kalibrasyonu (bge-m3, kosinüs)

Tuning: 49 soru, dondurulmuş: 34 soru. Kural: yanlış-ret <= %5, sonra en çok doğru-ret (eşit ise yüksek eşik). Ret = top-1 skoru < eşik.

## Arka uç ölçeği
Chroma vs numpy top-1 skor farkı: maks 0.00000; aynı top-1 kaynak: 83/83. Aynı ölçek (kosinüs).

## Arka uç: chroma

### Top-1 skor histogramı (tuning)

| Aralık | Cevaplanabilir | Cevaplanamaz |
|---|---|---|
| [0.30, 0.40) | 1 | 6 |
| [0.40, 0.45) | 1 | 3 |
| [0.45, 0.50) | 0 | 1 |
| [0.50, 0.55) | 3 | 6 |
| [0.55, 0.60) | 10 | 4 |
| [0.60, 0.65) | 5 | 3 |
| [0.65, 0.70) | 4 | 1 |
| [0.70, 0.75) | 1 | 0 |
| [0.75, 0.80) | 0 | 0 |
| [0.80, 1.00) | 0 | 0 |

### Süpürme özeti (tuning, her 0.05)

| Eşik | Yanlış-ret | Doğru-ret | Dengeli doğruluk | F1 (ret) |
|---|---|---|---|---|
| 0.30 | 0.0% | 0.0% | 50.0% | 0.000 |
| 0.35 | 0.0% | 0.0% | 50.0% | 0.000 |
| 0.40 | 4.0% | 25.0% | 60.5% | 0.387 |
| 0.44 **seçilen** | 4.0% | 37.5% | 66.8% | 0.529 |
| 0.45 | 8.0% | 37.5% | 64.8% | 0.514 |
| 0.50 | 8.0% | 41.7% | 66.8% | 0.556 |
| 0.55 | 20.0% | 66.7% | 73.3% | 0.711 |
| 0.60 | 60.0% | 83.3% | 61.7% | 0.678 |
| 0.65 | 80.0% | 95.8% | 57.9% | 0.687 |
| 0.70 | 96.0% | 100.0% | 52.0% | 0.667 |
| 0.75 | 100.0% | 100.0% | 50.0% | 0.658 |
| 0.80 | 100.0% | 100.0% | 50.0% | 0.658 |

Tuning dengeli doğruluğu en yüksek eşik: 0.55 (73.3%, yanlış-ret 20.0%) - bilgi amaçlı.

### Seçilen eşik: **0.44**

| Küme | Yanlış-ret | Doğru-ret | Dengeli doğruluk | F1 |
|---|---|---|---|---|
| tuning | 4.0% | 37.5% | 66.8% | 0.529 |
| dondurulmuş (tek değerlendirme) | 12.5% | 22.2% | 54.9% | 0.333 |

### Kategori bazında ret oranı (eşik 0.44)

| Kategori | tuning | dondurulmuş |
|---|---|---|
| cevaplanabilir (yanlış ret) | 1/25 | 2/16 |
| off-topic | 7/8 | 4/6 |
| near-miss | 0/8 | 0/6 |
| entity-swap | 2/8 | 0/6 |

Ortalama top-1: cevaplanabilir 0.589, cevaplanamaz 0.500. Ortalama top1-top2 marjı: cevaplanabilir 0.1141, cevaplanamaz 0.0416.

Dondurulmuşta yanlış cevaplanacak (ret edilemeyen) sorular:

- (off-topic, 0.464) Euro bugün kaç lira?
- (off-topic, 0.509) Yarın İstanbul'da hava nasıl olacak?
- (near-miss, 0.585) İstanbul gezisinde hangi otelde kalmıştım?
- (near-miss, 0.522) Git'te rebase ile merge farkını nasıl not almıştım?
- (near-miss, 0.551) Makine öğrenmesinde sinir ağı katman sayısını nasıl seçiyorum?
- (near-miss, 0.550) Atomic Habits'te alışkanlık takibi için hangi uygulamayı önermiş?
- (near-miss, 0.582) Pilav tarifim var mı, kaç ölçü su koyuyorum?
- (near-miss, 0.613) Proje Nova'nın aylık kirası ne kadar?
- (entity-swap, 0.654) İstanbul gezisinde balon turu kaç euro?
- (entity-swap, 0.530) Sapiens'te günlük meditasyondan bahsediliyor mu, kaç saat?
- (entity-swap, 0.517) Homo Deus'ta hangi dört beceri öğretilmeli deniyor?
- (entity-swap, 0.574) Proje Atlas'ın ana riski nedir?
- (entity-swap, 0.541) Kapadokya'a hızlı trenle ne kadar sürede gidilir?
- (entity-swap, 0.564) Mercimek çorbası kaç derece fırında pişer?

Dondurulmuşta yanlış ret edilen sorular:

- (0.409) Karbon vergisi hangi kavrama örnek gösterilmişti?
- (0.408) Kapadokya'da yeraltı şehri hangisiydi?

## Arka uç: numpy

### Top-1 skor histogramı (tuning)

| Aralık | Cevaplanabilir | Cevaplanamaz |
|---|---|---|
| [0.30, 0.40) | 1 | 6 |
| [0.40, 0.45) | 1 | 3 |
| [0.45, 0.50) | 0 | 1 |
| [0.50, 0.55) | 3 | 6 |
| [0.55, 0.60) | 10 | 4 |
| [0.60, 0.65) | 5 | 3 |
| [0.65, 0.70) | 4 | 1 |
| [0.70, 0.75) | 1 | 0 |
| [0.75, 0.80) | 0 | 0 |
| [0.80, 1.00) | 0 | 0 |

### Süpürme özeti (tuning, her 0.05)

| Eşik | Yanlış-ret | Doğru-ret | Dengeli doğruluk | F1 (ret) |
|---|---|---|---|---|
| 0.30 | 0.0% | 0.0% | 50.0% | 0.000 |
| 0.35 | 0.0% | 0.0% | 50.0% | 0.000 |
| 0.40 | 4.0% | 25.0% | 60.5% | 0.387 |
| 0.44 **seçilen** | 4.0% | 37.5% | 66.8% | 0.529 |
| 0.45 | 8.0% | 37.5% | 64.8% | 0.514 |
| 0.50 | 8.0% | 41.7% | 66.8% | 0.556 |
| 0.55 | 20.0% | 66.7% | 73.3% | 0.711 |
| 0.60 | 60.0% | 83.3% | 61.7% | 0.678 |
| 0.65 | 80.0% | 95.8% | 57.9% | 0.687 |
| 0.70 | 96.0% | 100.0% | 52.0% | 0.667 |
| 0.75 | 100.0% | 100.0% | 50.0% | 0.658 |
| 0.80 | 100.0% | 100.0% | 50.0% | 0.658 |

Tuning dengeli doğruluğu en yüksek eşik: 0.55 (73.3%, yanlış-ret 20.0%) - bilgi amaçlı.

### Seçilen eşik: **0.44**

| Küme | Yanlış-ret | Doğru-ret | Dengeli doğruluk | F1 |
|---|---|---|---|---|
| tuning | 4.0% | 37.5% | 66.8% | 0.529 |
| dondurulmuş (tek değerlendirme) | 12.5% | 22.2% | 54.9% | 0.333 |

### Kategori bazında ret oranı (eşik 0.44)

| Kategori | tuning | dondurulmuş |
|---|---|---|
| cevaplanabilir (yanlış ret) | 1/25 | 2/16 |
| off-topic | 7/8 | 4/6 |
| near-miss | 0/8 | 0/6 |
| entity-swap | 2/8 | 0/6 |

Ortalama top-1: cevaplanabilir 0.589, cevaplanamaz 0.500. Ortalama top1-top2 marjı: cevaplanabilir 0.1141, cevaplanamaz 0.0416.

Dondurulmuşta yanlış cevaplanacak (ret edilemeyen) sorular:

- (off-topic, 0.464) Euro bugün kaç lira?
- (off-topic, 0.509) Yarın İstanbul'da hava nasıl olacak?
- (near-miss, 0.585) İstanbul gezisinde hangi otelde kalmıştım?
- (near-miss, 0.522) Git'te rebase ile merge farkını nasıl not almıştım?
- (near-miss, 0.551) Makine öğrenmesinde sinir ağı katman sayısını nasıl seçiyorum?
- (near-miss, 0.550) Atomic Habits'te alışkanlık takibi için hangi uygulamayı önermiş?
- (near-miss, 0.582) Pilav tarifim var mı, kaç ölçü su koyuyorum?
- (near-miss, 0.613) Proje Nova'nın aylık kirası ne kadar?
- (entity-swap, 0.654) İstanbul gezisinde balon turu kaç euro?
- (entity-swap, 0.530) Sapiens'te günlük meditasyondan bahsediliyor mu, kaç saat?
- (entity-swap, 0.517) Homo Deus'ta hangi dört beceri öğretilmeli deniyor?
- (entity-swap, 0.574) Proje Atlas'ın ana riski nedir?
- (entity-swap, 0.541) Kapadokya'a hızlı trenle ne kadar sürede gidilir?
- (entity-swap, 0.564) Mercimek çorbası kaç derece fırında pişer?

Dondurulmuşta yanlış ret edilen sorular:

- (0.409) Karbon vergisi hangi kavrama örnek gösterilmişti?
- (0.408) Kapadokya'da yeraltı şehri hangisiydi?
