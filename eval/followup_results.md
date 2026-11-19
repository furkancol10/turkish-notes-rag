# Takip sorusu eval (26 konuşma, 52 geçmişli tur)

Mod: **analyze**

- Intent doğruluğu (genel): 52/52 = 1.00

| Beklenen \ Tahmin | notes | followup | sources | meta | doğruluk |
|---|---|---|---|---|---|
| notes | 32 | 0 | 0 | 0 | 32/32 = 1.00 |
| followup | 0 | 12 | 0 | 0 | 12/12 = 1.00 |
| sources | 0 | 0 | 6 | 0 | 6/6 = 1.00 |
| meta | 0 | 0 | 0 | 2 | 2/2 = 1.00 |

- Sorgu niyet korunumu (anahtar kelime): 8/8 = 1.00

Geri getirme (32 notes turu):

| Sorgu | hit@3 | MRR |
|---|---|---|
| Ham soru | 0.88 | 0.835 |
| Analiz sorgusu | 0.94 | 0.907 |

- Ort. gecikme (karar+yoğunlaştırma): 0.443 sn

## Önce / sonra (aynı 26 konuşma / 52 tur, qwen3.5:4b)

| Metrik | Kural router + condense | analyze (ilk) | analyze + kapı + yeni prompt (son) |
|---|---|---|---|
| Intent genel | 0.77 | 0.71 | 1.00 |
| notes | 1.00 | 0.59 | 1.00 |
| followup | 0.58 | 1.00 | 1.00 |
| sources | 0.00 | 0.67 | 1.00 |
| meta | 0.50 | 1.00 | 1.00 |
| Anahtar kelime korunumu | 5/8 | 5/8 | 8/8 |
| hit@3 / MRR (yeniden yazılmış sorgu) | 0.88 / 0.835 | 0.84 / 0.807 | 0.94 / 0.907 |
| Gecikme | 0.37 sn | 0.71 sn | 0.44 sn |

Yinelemeler (genel doğruluk / notes): ilk analyze 0.71 / 0.59 -> yalnız kapı (`router.has_new_content`: LLM "followup" dese de kapalı takip sözcükleri dışında yeni içerik sözcüğü varsa notes; kesin followup kalıpları LLM'den önce) 0.92 / 1.00 -> kaynak/takip kalıpları ("sayfa kaçta", "bunları hangi notta tutmuşum", "emin misin bundan", "özetini çıkar") + prompt (tanımlar, karşıt örnekler, "şüphede notes", soru kalıbını koru) 1.00 / 1.00. Gecikme düştü çünkü kural kalıpları LLM çağrısını atlıyor.

Değerlendirme düzeltmesi: anahtar kelime karşılaştırması Python `lower()` yerine `router.normalize` kullanıyor (`lower()` "İndeks"i "i̇ndeks" yapıp yanlış ıskalıyordu). Veri seti etiketleri değişmedi.

Held-out (ayarlamada kullanılmayan 9 tur, `eval/heldout_intent.json`, `uv run python -m eval.run_heldout_intent`): ayarlamadan önce 6/9 (3 notes -> followup); sonra 8/9 = 0.89 (kalan miss: "neden kalıcı oluyor?" followup -> notes, güvenli yön). Bir önceki çalıştırmada 9/9 çıktı; LLM çıktısı çalıştırmalar arasında oynayabilir. Not: bu set bir kez ayarlama öncesi görüldüğü ve kapıdaki "oluyor" gibi bazı sözcükler sonradan eklendiği için tam bağımsız değildir.
