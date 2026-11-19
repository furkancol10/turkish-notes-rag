# Yapılacaklar

## Kullanıcı tercihleri (kalıcı)
LLM konuşmadan öğrenmez; tercihler prompt'a ya da koda konmalı.
- [ ] **Atıf numaraları ayarı:** Ayarlar penceresine "Atıf numaralarını göster [açık/kapalı]". Kapalıysa cevaptaki `[1]`, `[2]` kodla temizlenir; kaynaklar "Kaynakları göster" altında kalır. Kayıtlı sohbetlerde de uygulanır.
- [ ] **Kişisel talimatlar:** Ayarlarda serbest metin kutusu ("Kısa cevap ver, madde madde yaz" gibi). Her sohbette `SYSTEM` prompt'una eklenir; uzunluk sınırı ve token bütçesine dahil edilir. Deterministik cevaplar (kaynak listesi) etkilenmez.
- [ ] "Bundan sonra … yapma" gibi sohbet içi talimatları yönlendiricide tanıyıp kişisel talimatlara kaydetmeyi önermek (onay ile).

## Arama kalitesi
- [x] **Metadata filtresi:** Soruda dosya/rapor adı geçerse ("chatgpt ne önermiş", "deepseekRag.pdf'te…") aramayı o dosyayla sınırla. (Katalogdaki sonraki proje konusu.)
- [x] **Yinelenen kaynaklar:** Aynı içerik hem `.pdf` hem `.html` ise parçaları tekilleştir.
- [ ] **Varlık karışması:** "Proje Nova" → "peki kira?" gibi durumlarda başka nottaki bilgiyi vermek yerine "notlarda yok" demesi için ek kontrol (ör. sorgudaki varlık adı bulunan parçada geçiyor mu).

## Değerlendirme ve sağlamlık
- [x] **Retrieval skor eşiği:** En iyi parçanın skoru eşiğin altındaysa LLM'e gitmeden "Bu bilgi notlarda yok" de. Yeni regex yamaları yerine belirsiz soruları bu eşikle çöz; eşiği eval ile seç.
- [ ] **Gerçekçi korpus:** Örnek notlar küçük ve sorular onlara göre yazıldı, eval doymuş durumda. Gerçek notlara benzeyen, daha büyük ve dağınık bir not seti hazırla.
- [x] **Dondurulmuş test seti:** Ayarlamada hiç görülmeyen, sonradan değiştirilmeyen ayrı bir soru seti; sonuçlar yalnız bu sette raporlanır.
- [ ] **Cevap metrikleri:** Yalnız retrieval (hit@k/MRR) değil; cevabın doğruluğu, kaynağa sadakat (faithfulness) ve "notlarda yok" isabeti ölçülsün.

## Arayüz
- [ ] Örnek soruları indeksleme sırasında LLM ile üretip saklamak (daha doğal sorular).
- [ ] Geliştirme modu: `watchfiles` ile kod değişince uygulamayı otomatik yeniden başlatma.
- [ ] Ayarlardaki seçeneklerin yanına ⓘ açıklama ipuçları.
