# Takip sorusu eval (26 konuşma, 52 geçmişli tur)

Mod: **route+condense (yedek; analyze: pending)**

- Intent doğruluğu (genel): 40/52 = 0.77

| Beklenen \ Tahmin | notes | followup | sources | meta | doğruluk |
|---|---|---|---|---|---|
| notes | 32 | 0 | 0 | 0 | 32/32 = 1.00 |
| followup | 5 | 7 | 0 | 0 | 7/12 = 0.58 |
| sources | 6 | 0 | 0 | 0 | 0/6 = 0.00 |
| meta | 1 | 0 | 0 | 1 | 1/2 = 0.50 |

- Sorgu niyet korunumu (anahtar kelime): 5/8 = 0.62

Geri getirme (32 notes turu):

| Sorgu | hit@3 | MRR |
|---|---|---|
| Ham soru | 0.88 | 0.835 |
| Analiz sorgusu | 0.91 | 0.868 |

- Ort. gecikme (karar+yoğunlaştırma): 0.369 sn
- analyze: pending (src.rewriter.analyze henüz yok; route(q, True) + condense ile ölçüldü, route 'sources' üretemez)
