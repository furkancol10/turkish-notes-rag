# Varlık koruması ölçümü

Küme: threshold_questions.json + threshold_frozen.json; answerable (41), near-miss (14), entity-swap (14). Gerçek arama + gerçek LLM (qwen3.5:4b), `services.ask`, geçmiş boş, eşik 0.40 açık. Betik: `eval/run_entity_eval.py --guard off|on`. Tek çalıştırma, LLM çıktısı çalıştırmalar arasında değişir.

"Yanlış cevap" iki sezgiyle sayıldı: sıkı (cevap "notlarda yok" değilse; "bağlamda belirtilmemiştir" gibi doğru ret ifadelerini de yanlış sayar, abartılı) ve gevşek (ret benzeri ifadeler de ret sayılır).

| | koruma kapalı | koruma açık |
|---|---|---|
| cevaplanamaz (28) yanlış, sıkı | 16 | 15 |
| cevaplanamaz yanlış, gevşek | 5 | 6 |
| entity-swap (14) gevşek | 5 | 5 |
| cevaplanabilir yanlış ret | 3/41 | 3/41 |
| koruma tetiklenen | - | 1 (cevaplanamaz, "Swarm") |

## Yorum (dürüst)
- Koruma güvenli: cevaplanabilirde sıfır ek yanlış ret. Ama etkisi ölçülemeyecek kadar küçük: 28 cevaplanamaz sorudan yalnızca 1'inde tetiklendi. Sıkı/gevşek farkları LLM değişkenliğidir, korumanın etkisi değil.
- Sebep: kalan yanlış cevapların çoğunda varlık notlarda gerçekten geçiyor (Proje Nova, Proje Atlas, Sapiens...) ama sorulan olgu başka bir notta. Bu tür karışma içerik-varlık kontrolüyle yakalanamaz; ayrı bir çözüm gerekir (ör. varlık + olgu birlikte doğrulama).
- Cümle başı sözcükler özel ad sayılmaz (kesme işaretli olanlar hariç), bu yüzden "Python demetlerde..." gibi sorular kapsanmaz.
- Küçük küme (N=69), tek çalıştırma; anlamlı güven aralığı yok.
- run_mixing_eval.py `services.ask` kullanmaz (retrieve + answer), koruma o hatta olmadığından sonuçları değişmez; ayrıca çalıştırılmadı (bellek nedeniyle ağır çalıştırmalar durduruldu).
