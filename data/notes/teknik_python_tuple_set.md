# Python: Demet (tuple) ve Küme (set) (ÖRNEK NOT)

## Demet
Demetler değiştirilemez (immutable) dizilerdir: `t = (1, 2, 3)`. Sözlük anahtarı olarak kullanılabilirler, çünkü hashlenebilirler. Tek elemanlı demet için virgül şart: `(5,)`.

## Küme
`s = {1, 2, 3}` sırasız ve tekrarsız elemanlar tutar. Üyelik testi `x in s` ortalama O(1) sürer, listede ise O(n). Kesişim `a & b`, birleşim `a | b`, fark `a - b`. Boş küme `{}` değil `set()` ile yazılır, çünkü `{}` boş sözlük oluşturur.

## Ne zaman hangisi
Sıra ve tekrar önemliyse liste, sabit kayıtsa demet, tekrarları atmak ya da hızlı üyelik testi için küme.
