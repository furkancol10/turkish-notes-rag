# Eval sonuçları (24 soru, hit@1, hit@3 ve MRR)

| Model | Chunk boyutu | Parça sayısı | hit@1 | hit@3 | MRR |
|---|---|---|---|---|---|
| newmindai/Mursit-Large-TR-Retrieval | 256 | 115 | 0.88 | 1.00 | 0.938 |
| newmindai/Mursit-Large-TR-Retrieval | 512 | 60 | 0.79 | 1.00 | 0.875 |
| newmindai/Mursit-Large-TR-Retrieval | 1024 | 45 | 0.83 | 0.96 | 0.899 |
| trmteb/turkish-embedding-model | 256 | 115 | 0.71 | 0.92 | 0.827 |
| trmteb/turkish-embedding-model | 512 | 60 | 0.88 | 0.92 | 0.910 |
| trmteb/turkish-embedding-model | 1024 | 45 | 0.88 | 1.00 | 0.931 |
| BAAI/bge-m3 | 256 | 115 | 0.92 | 1.00 | 0.958 |
| BAAI/bge-m3 | 512 | 60 | 0.96 | 1.00 | 0.979 |
| BAAI/bge-m3 | 1024 | 45 | 0.92 | 1.00 | 0.958 |

Not: 24 cevaplanabilir soru (27 not üzerinde, 4 cevapsız soru metrik dışı). Sorular eşanlamlı/dolaylı ifadelerle, yakın-kopya notları (menemen/sucuklu yumurta, karnıyarık/imam bayıldı, Harari kitapları, Atlas/Nova) ve uzun notların ortasındaki bilgileri hedefliyor.

Yorum: Artık modeller ayrışıyor. BAAI/bge-m3 her chunk boyutunda hit@3=1.00 ve en yüksek MRR'yi (0.96-0.98) veriyor; Mursit en küçük chunk'ta iyi (256: 0.938) ama büyüdükçe düşüyor; trmteb ise tersine 1024'te en iyi, 256'da en kötü (hit@3 0.92, MRR 0.827). Chunk boyutu etkisi modele göre değişiyor, yani en iyi boyut modelden bağımsız seçilemez. 24 soruda tek bir soru yaklaşık 0.04 hit puanı eder, bu yüzden küçük farklar gürültü olabilir.
