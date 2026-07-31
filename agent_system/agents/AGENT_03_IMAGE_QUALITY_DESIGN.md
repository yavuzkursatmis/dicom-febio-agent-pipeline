# Agent-03 — Image Quality Agent

## Amaç
DICOM güvenlik kontrolünden geçen görüntünün teknik olarak analiz için uygun olup olmadığını kontrol etmek.

## Kullanıcı ile iletişim
Bu ajan kullanıcıyla doğrudan konuşmaz.
Kararlarını JSON/CSV dosyalarına yazar.
Uyarılar ileride kullanıcı arayüzünde gösterilecektir.

## Görevler
- Agent-02 sonucunu okur.
- DICOM_SAFETY_PASS durumunu kontrol eder.
- DICOM serisini okumaya çalışır.
- Slice sayısını kontrol eder.
- Pixel spacing değerlerini kontrol eder.
- Slice thickness değerini kontrol eder.
- Görüntü boyutlarını kontrol eder.
- Voxel anisotropy hesaplar.
- Intensity / HU aralığını özetler.
- Görüntü kalite kararını üretir.
- Sonraki ajanı belirler.

## Yapmayacağı işler
- Segmentasyon yapmaz.
- Hedef anatomik bölgeyi yorumlamaz.
- Test uygulanacak bölgeyi analiz etmez.
- Malzeme seçmez.
- FEBio modeli oluşturmaz.
- Klinik yorum yapmaz.

## Giriş
Agent-02 çıktısı:
- case_id
- input_path
- safety_status
- is_ct
- dicom_file_count
- readable_dicom_count

## Çıkış
- image_quality_status
- series_read_success
- slice_count
- image_size
- spacing
- slice_thickness
- voxel_anisotropy
- intensity_min
- intensity_max
- intensity_mean
- next_agent
- warnings
- blockers

## Karar durumları
- IMAGE_QUALITY_PASS
- IMAGE_QUALITY_WARNING
- IMAGE_QUALITY_FAIL
- BLOCKED_BY_DICOM_SAFETY
- DICOM_SERIES_READ_FAIL

## Çıkış dosyaları
cases/<case_id>/02_image_quality/IMAGE_QUALITY_RESULT.json
cases/<case_id>/02_image_quality/IMAGE_QUALITY_PROFILE.csv
paper_notes/image_quality_notes.md

## LLM kullanımı
Gemini kullanılmaz.
Bu ajan sayısal ve deterministik kontrol yapar.

## Sonraki ajan kararı
- IMAGE_QUALITY_PASS → TARGET_UNDERSTANDING_AGENT
- IMAGE_QUALITY_WARNING → TARGET_UNDERSTANDING_AGENT
- IMAGE_QUALITY_FAIL → USER_ACTION_REQUIRED
- BLOCKED_BY_DICOM_SAFETY → USER_ACTION_REQUIRED
