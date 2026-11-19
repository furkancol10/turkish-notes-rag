# Yapılacaklar

## Kullanıcı tercihleri (kalıcı)
LLM konuşmadan öğrenmez; tercihler prompt'a ya da koda konmalı.
- [ ] **Atıf numaraları ayarı:** Ayarlar penceresine "Atıf numaralarını göster [açık/kapalı]". Kapalıysa cevaptaki `[1]`, `[2]` kodla temizlenir; kaynaklar "Kaynakları göster" altında kalır. Kayıtlı sohbetlerde de uygulanır.
- [ ] **Kişisel talimatlar:** Ayarlarda serbest metin kutusu ("Kısa cevap ver, madde madde yaz" gibi). Her sohbette `SYSTEM` prompt'una eklenir; uzunluk sınırı ve token bütçesine dahil edilir. Deterministik cevaplar (kaynak listesi) etkilenmez.
- [ ] "Bundan sonra … yapma" gibi sohbet içi talimatları yönlendiricide tanıyıp kişisel talimatlara kaydetmeyi önermek (onay ile).

## Arama kalitesi
- [ ] **Metadata filtresi:** Soruda dosya/rapor adı geçerse ("chatgpt ne önermiş", "deepseekRag.pdf'te…") aramayı o dosyayla sınırla. (Katalogdaki sonraki proje konusu.)
- [ ] **Yinelenen kaynaklar:** Aynı içerik hem `.pdf` hem `.html` ise parçaları tekilleştir.
- [ ] **Varlık karışması:** "Proje Nova" → "peki kira?" gibi durumlarda başka nottaki bilgiyi vermek yerine "notlarda yok" demesi için ek kontrol (ör. sorgudaki varlık adı bulunan parçada geçiyor mu).

## Arayüz
- [ ] Örnek soruları indeksleme sırasında LLM ile üretip saklamak (daha doğal sorular).
- [ ] Geliştirme modu: `watchfiles` ile kod değişince uygulamayı otomatik yeniden başlatma.
- [ ] Ayarlardaki seçeneklerin yanına ⓘ açıklama ipuçları.
