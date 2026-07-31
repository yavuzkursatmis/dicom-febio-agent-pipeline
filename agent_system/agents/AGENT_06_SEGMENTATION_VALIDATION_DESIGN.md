# Agent-06 — Segmentation Validation Agent

## Amaç
Agent-05 tarafından üretilen segmentasyon maskesinin teknik olarak kullanılabilir olup olmadığını kontrol etmek.

Bu ajan segmentasyon üretmez.
Sadece mevcut maskeyi doğrular.

## Kullanıcı ile iletişim
Bu ajan kullanıcıyla doğrudan konuşmaz.
Kararlarını JSON/CSV dosyalarına yazar.
Ancak segmentasyon doğrulama uyarısı varsa HUMAN_REVIEW_GATE kararı üretir.
Bu karar ileride Streamlit arayüzünde kullanıcıya gösterilecektir.

## Giriş
Agent-05 çıktısından:
- case_id
- segmentation_status
- segmentation_target
- segmentation_mask_path
- original_volume_path
- resampled_volume_path
- original_spacing
- resampled_spacing
- resampling_applied
- warnings
- blockers

## Yapacağı işler
- Agent-05 segmentasyon sonucunu okur.
- Segmentasyon başarı durumunu kontrol eder.
- segmentation_mask.nii.gz dosyası var mı kontrol eder.
- Maskeyi okur.
- Maskenin boş olup olmadığını kontrol eder.
- Maske voxel sayısını hesaplar.
- Maske hacmini mm3 ve cm3 olarak hesaplar.
- Görüntü ve maske boyut uyumunu kontrol eder.
- Görüntü ve maske spacing uyumunu kontrol eder.
- Resampling uygulanmışsa doğrulama notuna ekler.
- Segmentasyonun insan onayına hazır olup olmadığını belirler.
- Sonraki ajanı belirler.

## Yapmayacağı işler
- Yeni segmentasyon yapmaz.
- Segmentasyonu düzeltmez.
- Görüntü resampling yapmaz.
- Mesh üretmez.
- Malzeme seçmez.
- FEBio modeli oluşturmaz.
- Solver çalıştırmaz.
- Klinik tanı koymaz.

## Kontrol kriterleri
- Mask path mevcut olmalı.
- Maske okunabilir olmalı.
- Maske boş olmamalı.
- Maske voxel sayısı sıfırdan büyük olmalı.
- Maske hacmi makul aralıkta olmalı.
- Maske ve referans görüntü aynı boyutta olmalı.
- Maske ve referans görüntü spacing değerleri uyumlu olmalı.

## Uyarı durumları
- Resampling uygulanmışsa doğrulama uyarısı olarak kaydedilir.
- HIGH_VOXEL_ANISOTROPY_RESAMPLED varsa not edilir.
- Maske hacmi çok küçük veya çok büyükse warning üretilir.
- Teknik kontroller geçse bile insan onayı önerilir.

## Karar durumları
- SEGMENTATION_VALIDATION_PASS
- SEGMENTATION_VALIDATION_WARNING
- SEGMENTATION_VALIDATION_FAIL
- BLOCKED_BY_SEGMENTATION

## Sonraki ajan kararı
- SEGMENTATION_VALIDATION_PASS → MATERIAL_SELECTION_AGENT
- SEGMENTATION_VALIDATION_WARNING → HUMAN_REVIEW_GATE
- SEGMENTATION_VALIDATION_FAIL → USER_ACTION_REQUIRED
- BLOCKED_BY_SEGMENTATION → USER_ACTION_REQUIRED

## İnsan onayı
Bu sistemde segmentasyon maskesi FEBio geometrisinin temelidir.
Bu nedenle warning durumunda otomatik olarak malzeme seçimine geçilmez.
Önce insan onayı gerekir.

## Çıkış bilgileri
- segmentation_validation_status
- mask_exists
- mask_read_success
- mask_is_empty
- mask_voxel_count
- mask_volume_mm3
- mask_volume_cm3
- reference_image_path
- image_mask_size_match
- image_mask_spacing_match
- resampling_applied
- human_review_required
- next_agent
- warnings
- blockers

## Çıkış dosyaları
cases/<case_id>/05_segmentation_validation/SEGMENTATION_VALIDATION_RESULT.json
cases/<case_id>/05_segmentation_validation/MASK_VALIDATION_PROFILE.csv
paper_notes/segmentation_validation_notes.md

## LLM kullanımı
Gemini kullanılmaz.
Bu ajan sayısal ve deterministik doğrulama yapar.
