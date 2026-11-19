# Python: Dekoratörler ve Üreteçler (ÖRNEK NOT)

## Giriş
Dekoratör, bir fonksiyonu alıp onu saran yeni bir fonksiyon döndüren fonksiyondur. `@ad` sözdizimi `f = ad(f)` işleminin kısaltmasıdır. Günlük kullanımda zamanlama, önbellekleme, yetki kontrolü ve günlükleme için kullanılır. Önce temel mantığı anlamak gerekiyor; iç içe fonksiyonlar ve kapanışlar (closure) bunun zemini.

## Kapanışlar
İç fonksiyon, dış fonksiyonun değişkenlerini dış fonksiyon bitse bile hatırlar. Dekoratörün sarmalayıcısı bu sayede asıl fonksiyona erişir. Sarmalayıcı genellikle `*args, **kwargs` alır ki her imzayla çalışsın. Bunu atlayınca farklı parametreli fonksiyonlarda TypeError alırsın.

## Metadata kaybı
Sarmalayıcı yazınca asıl fonksiyonun adı ve docstring'i kaybolur. Çözüm: sarmalayıcıyı `functools.wraps(f)` ile süslemek. Bunu unutmak hata ayıklamayı zorlaştırır, çünkü her fonksiyon "wrapper" adıyla görünür.

## Parametreli dekoratör
Dekoratöre argüman vermek için bir katman daha gerekir: dış fonksiyon argümanı alır, ortadaki dekoratörü döndürür, en içteki sarmalayıcı işi yapar. Üç seviyeli iç içe yapı ilk bakışta karışık görünür. Örneğin `@tekrar(3)` bir fonksiyonu üç kez çalıştırabilir. Okunabilirlik için sınıf tabanlı dekoratör de yazılabilir, `__call__` metodu sarmalayıcı görevini üstlenir.

## Önbellekleme
`functools.lru_cache(maxsize=128)` hazır bir dekoratördür; aynı argümanlarla çağrıda sonucu hafızadan verir. Özyinelemeli Fibonacci gibi tekrar eden hesaplarda üstel süreyi doğrusala indirir. Argümanlar hashlenebilir olmalıdır, yani liste verilemez. Python 3.9 ile gelen `functools.cache` sınırsız boyutlu daha basit bir kardeşidir.

## Üreteçler
`yield` içeren fonksiyon üreteç döndürür ve değerleri tembel (lazy) üretir. Büyük dosyaları satır satır okurken belleği korur. Üreteç ifadesi `(x*x for x in range(10**6))` liste üretecinin parantezli halidir ve tüm listeyi belleğe koymaz. Bir üreteç yalnızca bir kez tüketilebilir; ikinci döngüde boş gelir. Bu en sık düşülen tuzaklardan biri.

## Kendime not
Dekoratörlerde sıralama önemli: en alttaki önce uygulanır. `@a` üstte, `@b` altta ise `a(b(f))` elde edilir. Bunu bir kez ters anlayıp bir yetki kontrolünü önbelleğin arkasında bırakmıştım; yetkisiz kullanıcı önbellekten cevap alıyordu.
