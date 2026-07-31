# Agent-01 — Data Intake Agent

## Amaç
Kullanıcının yüklediği veriyi almak, tanımak ve analize hazır hale getirmek.

## Kullanıcıdan alınacak bilgiler
1. Analiz adı
2. Veri dosyası veya klasörü
3. Analiz edilecek bölge
4. Uygulanacak test
5. Testin uygulanacağı yer
6. İsteğe bağlı not

## Görevler
- Veri yolunu kontrol eder.
- DICOM / NIfTI / manuel maske ayrımı yapar.
- Dosya sayısını belirler.
- Boş klasör kontrolü yapar.
- Case klasörünü oluşturur.
- İlk kayıt dosyasını üretir.
- Sonraki ajanı belirler.

## Yapmayacağı işler
- DICOM güvenlik kontrolü yapmaz.
- Segmentasyon yapmaz.
- Malzeme seçmez.
- FEBio modeli kurmaz.
- Akademik sonuç üretmez.

## LLM Kullanımı
Varsayılan olarak LLM kullanmaz.
Sadece kullanıcı girişi belirsizse Gemini ile açıklama/ek bilgi isteme yapılabilir.

## Çıkış dosyası
cases/<case_id>/00_input_manifest/DATA_INTAKE_RESULT.json
