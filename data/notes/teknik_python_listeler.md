# Python: Liste ve Sözlük (ÖRNEK NOT)

## Liste üreteçleri
`[x*x for x in range(10) if x % 2 == 0]` çift sayıların karesini üretir. Okunaklı kaldığı sürece döngüden daha kısadır.

## Sözlük
`d.get("anahtar", varsayilan)` anahtar yoksa hata vermez. `collections.defaultdict(list)` gruplamada işe yarar.

## Sık hata
Varsayılan argüman olarak değiştirilebilir liste kullanmayın: `def f(x=[])` her çağrıda aynı listeyi paylaşır.
