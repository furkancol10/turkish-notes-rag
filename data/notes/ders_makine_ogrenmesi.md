# Ders Notu: Makine Öğrenmesi Temelleri (ÖRNEK NOT)

## Öğrenme türleri
Denetimli öğrenmede etiketli veri vardır ve model girdiden etikete eşleme öğrenir; sınıflandırma ve regresyon bu gruptadır. Denetimsiz öğrenmede etiket yoktur, model yapıyı kendisi bulur: kümeleme ve boyut indirgeme örnekleridir. Pekiştirmeli öğrenmede ajan, ödül sinyaline göre deneme yanılmayla davranış öğrenir.

## Aşırı öğrenme
Model eğitim verisini ezberlediğinde yeni veride kötü sonuç verir; buna aşırı öğrenme (overfitting) denir. Eğitim hatası düşük, doğrulama hatası yüksektir. Çözümler: daha fazla veri, daha basit model, düzenlileştirme (regularization), erken durdurma ve dropout. Tersi, yani modelin veriyi hiç yakalayamaması, yetersiz öğrenmedir (underfitting).

## Veri bölme
Veri genellikle eğitim, doğrulama ve test olarak bölünür; tipik oran yüzde 70, 15 ve 15. Test kümesine model seçimi sırasında asla bakılmaz, yoksa sonuçlar iyimser çıkar. Veri azsa k-katlı çapraz doğrulama kullanılır; k genelde 5 ya da 10 seçilir.

## Metrikler
Doğruluk (accuracy) dengesiz sınıflarda yanıltıcıdır. Hassasiyet (precision) pozitif dediklerimizin ne kadarının gerçekten pozitif olduğunu, duyarlılık (recall) gerçek pozitiflerin ne kadarını yakaladığımızı ölçer. F1 skoru ikisinin harmonik ortalamasıdır. Örneğin yüzde 1 hastalık oranında her şeye "sağlıklı" diyen model yüzde 99 doğruluk alır ama duyarlılığı sıfırdır.

## Gradyan inişi
Kayıp fonksiyonunun türevi alınıp parametreler eğimin ters yönünde güncellenir. Öğrenme oranı (learning rate) adım büyüklüğünü belirler: çok büyükse kayıp salınır ya da patlar, çok küçükse eğitim çok yavaş ilerler. Mini-batch yöntemi her adımda verinin küçük bir parçasını kullanır; tam veri yerine 32 ya da 64 örneklik gruplar yaygındır. Adam optimizasyonu momentum ve adaptif öğrenme oranını birleştirir.

## Özellik mühendisliği
Ham veriden model için anlamlı girdiler üretme işidir. Kategorik değişkenler one-hot kodlanır; sayısal değişkenler ölçeklenir, çünkü mesafe tabanlı yöntemler ve gradyan inişi ölçeğe duyarlıdır. Eksik değerler için ortalama ya da medyan doldurma yapılır. Veri sızıntısı (data leakage) en tehlikeli hatadır: test verisinden gelen bilgi eğitime karışırsa sonuçlar gerçek dışı iyi çıkar. Ölçekleme parametreleri yalnızca eğitim kümesinden hesaplanmalı.

## Karar ağaçları ve topluluklar
Karar ağacı veriyi özellik eşiklerine göre böler; yorumlaması kolaydır ama aşırı öğrenmeye meyillidir. Rastgele orman, birçok ağacın oyunu birleştirerek varyansı düşürür. Gradyan artırma (boosting) ise ağaçları sırayla ekler ve her biri öncekinin hatasını düzeltir.
