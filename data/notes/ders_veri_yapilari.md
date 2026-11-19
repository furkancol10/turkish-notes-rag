# Veri Yapıları Ders Notları (ÖRNEK NOT)

## Diziler ve bağlı listeler
Dizide elemana indeksle erişim O(1) sürede yapılır, ancak ortaya eleman eklemek O(n) sürer çünkü elemanlar kaydırılır. Bağlı listede ekleme O(1)'dir ama i. elemana ulaşmak için baştan gezmek gerekir.

## İkili arama ağacı
İkili arama ağacında (BST) her düğümün solundaki değerler küçük, sağındakiler büyüktür. Dengeli bir ağaçta arama, ekleme ve silme ortalama O(log n) sürer. Ağaç dengesizse, örneğin sıralı veri eklenmişse, en kötü durumda O(n) olur. AVL ve kırmızı-siyah ağaçlar dengeyi otomatik korur.

## Yığın ve kuyruk
Yığın (stack) LIFO çalışır, kuyruk (queue) FIFO. Derin gezinme yığınla, geniş gezinme (BFS) kuyrukla yapılır. Vize 12 Aralık'ta, konular ağaçlar ve graflar.
