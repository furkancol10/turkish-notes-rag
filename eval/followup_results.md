# Takip sorusu eval (26 konuşma, 52 geçmişli tur)

Mod: **analyze**

- Intent doğruluğu (genel): 37/52 = 0.71

| Beklenen \ Tahmin | notes | followup | sources | meta | doğruluk |
|---|---|---|---|---|---|
| notes | 19 | 13 | 0 | 0 | 19/32 = 0.59 |
| followup | 0 | 12 | 0 | 0 | 12/12 = 1.00 |
| sources | 1 | 1 | 4 | 0 | 4/6 = 0.67 |
| meta | 0 | 0 | 0 | 2 | 2/2 = 1.00 |

- Sorgu niyet korunumu (anahtar kelime): 5/8 = 0.62

Geri getirme (32 notes turu):

| Sorgu | hit@3 | MRR |
|---|---|---|
| Ham soru | 0.88 | 0.835 |
| Analiz sorgusu | 0.84 | 0.807 |

- Ort. gecikme (karar+yoğunlaştırma): 0.708 sn

## Önce / sonra (analyze entegrasyonu)

Baz çizgi: kural router + condense (route + condense). Sonra: `rewriter.analyze` (tek LLM çağrısı, qwen3.5:4b). Aynı 26 konuşma / 52 tur.

| Metrik | Önce | Sonra (bu çalıştırma) |
|---|---|---|
| Intent genel | 0.77 | 0.71 |
| notes | 1.00 | 0.59 |
| followup | 0.58 | 1.00 |
| sources | 0.00 | 0.67 |
| meta | 0.50 | 1.00 |
| Anahtar kelime korunumu | 5/8 | 5/8 |
| hit@3 / MRR (yeniden yazılmış sorgu) | 0.88 / 0.835 | 0.84 / 0.807 |
| Gecikme | 0.37 sn | 0.71 sn |

Not: sources ve meta belirgin iyileşti; ancak 4B model kısa, eksiltili `notes` sorularını (ör. "peki kira?", "Kirası ne kadar?") 13 kez `followup` sandı ve genel doğruluk düştü. Önceki ölçümde bildirilen analyze sonucu (hit@3 0.91 / MRR 0.868) bu çalıştırmada yeniden üretilemedi; LLM çıktısı çalıştırmadan çalıştırmaya değişebilir. İyileştirme yolu: INTENT_SYSTEM prompt'unda `notes`/`followup` ayrımı.
