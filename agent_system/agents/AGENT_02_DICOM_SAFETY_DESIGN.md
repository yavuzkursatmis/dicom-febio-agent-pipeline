# Agent-02 — DICOM Safety Agent

## Amaç
DICOM verisinin güvenli ve işlenebilir olup olmadığını kontrol etmek.

## Kullanıcı ile iletişim
Bu ajan kullanıcıyla doğrudan konuşmaz.
Uyarı ve kararlarını JSON/CSV dosyalarına yazar.
Kullanıcıya gösterilecek mesajları ileride arayüz katmanı gösterecektir.

## Görevler
- Agent-01 çıktısını okur.
- Veri tipi DICOM mu kontrol eder.
- DICOM dosyalarını tarar.
- Header bilgilerini inceler.
- CT verisi olup olmadığını kontrol eder.
- Kişisel veri / PHI riski arar.
- Burned-in annotation riskini kontrol eder.
- Güvenlik kararını üretir.
- Sonraki ajanı belirler.

## Yapmayacağı işler
- DICOM → NIfTI dönüşümü yapmaz.
- Görüntü kalite analizi yapmaz.
- Segmentasyon yapmaz.
- Malzeme seçmez.
- FEBio modeli oluşturmaz.
- Klinik yorum yapmaz.

## Giriş
Agent-01 çıktısı:
- case_id
- input_path
- detected_input_type
- data_status
- file_count
- anatomical_target
- analysis_type
- test_application_region

## Çıkış
- safety_status
- dicom_file_count
- readable_dicom_count
- modality_detected
- is_ct
- phi_risk_detected
- burned_in_annotation_risk
- human_review_required
- next_agent
- warnings
- blockers

## Çıkış dosyaları
cases/<case_id>/01_safety/DICOM_SAFETY_RESULT.json
cases/<case_id>/01_safety/DICOM_HEADER_SCAN.csv
paper_notes/dicom_safety_notes.md

## LLM kullanımı
Varsayılan olarak LLM kullanmaz.
Güvenlik kararı deterministik kontrollerle verilir.
Gemini sadece ileride kullanıcıya anlaşılır uyarı metni üretmek için kullanılabilir.

## Karar kuralları
- DICOM değilse: BLOCKED_NOT_DICOM
- DICOM okunamıyorsa: DICOM_READ_FAIL
- CT değilse: BLOCKED_NOT_CT
- PHI riski varsa: HUMAN_REVIEW_REQUIRED
- Temel kontroller geçerse: DICOM_SAFETY_PASS
