# SQL JOIN Türleri (ÖRNEK NOT)

INNER JOIN iki tabloda eşleşen satırları getirir. LEFT JOIN soldaki tablonun tüm satırlarını, eşleşme yoksa sağ tarafı NULL döndürür. FULL OUTER JOIN iki tarafın hepsini getirir.

## İpucu
Sorguyu yavaşlatan çoğu şey eksik indekstir. JOIN'de kullanılan kolonlara indeks koymak gerekir. EXPLAIN ile plan kontrol edilir.
