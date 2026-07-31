# Agent-05 — Segmentation / Preprocessing Agent

## Amaç
DICOM/CT hacmini segmentasyona hazır hale getirmek ve hedef anatomik yapının segmentasyonunu üretmek.

Bu ajan, görüntü üzerinde ilk aktif işlem yapan ajandır.

## Kullanıcı ile iletişim
Bu ajan kullanıcıyla doğrudan konuşmaz.
Kararlarını JSON dosyalarına yazar.
Uyarılar ve manuel onay gerektiren durumlar ileride Streamlit arayüzünde gösterilecektir.

## Giriş
Önceki ajanlardan gelen bilgiler:
- case_id
- input_path
- image_quality_status
- spacing
- voxel_anisotropy
- warnings
- segmentation_target
- standardized_anatomical_target
- standardized_analysis_type
- load_region

## Yapacağı işler
- Agent-03 görüntü kalite sonucunu okur.
- Agent-04 hedef anlama sonucunu okur.
- DICOM serisini hacim olarak okur.
- Orijinal hacmi NIfTI olarak kaydeder.
- HIGH_VOXEL_ANISOTROPY uyarısını kontrol eder.
- Gerekirse resampling kararı üretir.
- Gerekirse near-isotropic spacing'e resampling uygular.
- Orijinal spacing ve yeni spacing değerlerini kaydeder.
- Segmentasyon hedefini belirler.
- Segmentasyon aracını seçer.
- Segmentasyon maskesini üretir.
- Segmentasyon sonucunu dosyaya kaydeder.
- Sonraki ajanı belirler.

## Yapmayacağı işler
- Segmentasyon doğrulaması yapmaz.
- Segmentasyon kalitesini nihai olarak onaylamaz.
- Mesh üretmez.
- Malzeme seçmez.
- FEBio modeli oluşturmaz.
- Solver çalıştırmaz.
- Klinik tanı koymaz.

## HIGH_VOXEL_ANISOTROPY işlemi
Bu uyarı bu ajanda ele alınacaktır.

Kural:
- Eğer voxel_anisotropy yüksekse preprocessing_required=True olur.
- DICOM hacmi near-isotropic spacing'e yeniden örneklenir.
- Orijinal spacing ve resampled spacing kayıt altına alınır.
- Segmentasyon resampled hacim üzerinde çalıştırılır.

Önemli not:
Resampling yeni anatomik bilgi üretmez.
Sadece segmentasyon, yüzey çıkarımı ve mesh üretimi için daha düzenli 3B hacim sağlar.

## İlk hedef
L1 vertebra segmentasyonu.

## Segmentasyon yöntemi
İlk sürümde desteklenecek modlar:
- AUTO_SEGMENTATION
- MANUAL_MASK_INPUT

AUTO_SEGMENTATION için ilk aday araç:
- TotalSegmentator

MANUAL_MASK_INPUT için:
- Kullanıcı daha önce hazırlanmış maske verisi sağlayabilir.

## Çıkış bilgileri
- segmentation_status
- preprocessing_required
- resampling_applied
- original_spacing
- target_spacing
- resampled_spacing
- segmentation_mode
- segmentation_tool
- segmentation_target
- original_volume_path
- resampled_volume_path
- segmentation_mask_path
- next_agent
- warnings
- blockers

## Karar durumları
- SEGMENTATION_PASS
- SEGMENTATION_WARNING
- SEGMENTATION_FAIL
- BLOCKED_BY_TARGET_UNDERSTANDING
- PREPROCESSING_REQUIRED
- SEGMENTATION_TOOL_NOT_AVAILABLE

## Sonraki ajan kararı
- SEGMENTATION_PASS → SEGMENTATION_VALIDATION_AGENT
- SEGMENTATION_WARNING → SEGMENTATION_VALIDATION_AGENT
- SEGMENTATION_FAIL → USER_ACTION_REQUIRED
- BLOCKED_BY_TARGET_UNDERSTANDING → USER_ACTION_REQUIRED

## Çıkış dosyaları
cases/<case_id>/04_segmentation/PREPROCESSING_RESULT.json
cases/<case_id>/04_segmentation/SEGMENTATION_RESULT.json
cases/<case_id>/04_segmentation/volume_original.nii.gz
cases/<case_id>/04_segmentation/volume_resampled.nii.gz
cases/<case_id>/04_segmentation/segmentation_mask.nii.gz
paper_notes/segmentation_notes.md

## LLM kullanımı
Bu ajanda Gemini kullanılmaz.

Sebep:
Preprocessing ve segmentasyon araç çağrıları deterministik yürütülmelidir.
Hedef bilgisi Agent-04 tarafından standartlaştırılmış olarak gelir.

## Validasyon notu
Bu ajan segmentasyon üretir; segmentasyonu doğrulamaz.
Segmentasyon doğrulaması Agent-06 tarafından yapılacaktır.
