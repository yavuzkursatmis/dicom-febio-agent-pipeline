# Agent-04 — Target Understanding Agent

## Amaç
Kullanıcının doğal dilde verdiği anatomik hedef, analiz tipi ve test uygulanacak bölge bilgisini standart teknik forma çevirmek.

## Kullanıcı ile iletişim
Bu ajan doğrudan kullanıcıyla konuşmaz.
Ancak belirsizlik varsa HUMAN_REVIEW_GATE kararı üretir.
Uyarılar ve onay istekleri ileride Streamlit arayüzünde gösterilecektir.

## Giriş
Agent-01 ve Agent-03 sonrası gelen bilgiler:
- case_id
- anatomical_target
- analysis_type
- test_application_region
- image_quality_status
- warnings
- blockers

## Yapacağı işler
- Anatomik hedefi yorumlar.
- Segmentasyon hedefini belirler.
- Test tipini sınıflandırır.
- Yük uygulanacak bölgeyi standartlaştırır.
- Sınır şartları için ön bilgi üretir.
- Belirsizlik seviyesini değerlendirir.
- Sonraki ajanı belirler.

## Yapmayacağı işler
- Segmentasyon yapmaz.
- Görüntü işlemez.
- Resampling yapmaz.
- Mesh üretmez.
- Malzeme seçmez.
- FEBio modeli kurmaz.
- Solver çalıştırmaz.
- Klinik tanı koymaz.

## Çıkış bilgileri
- target_understanding_status
- standardized_anatomical_target
- segmentation_target
- standardized_analysis_type
- standardized_test_application_region
- load_region
- boundary_condition_hint
- confidence_level
- human_review_required
- next_agent
- warnings
- blockers

## Karar durumları
- TARGET_UNDERSTANDING_PASS
- TARGET_UNDERSTANDING_NEEDS_REVIEW
- TARGET_UNDERSTANDING_FAIL
- BLOCKED_BY_IMAGE_QUALITY

## LLM kullanımı
Bu ajan Gemini kullanabilir.
Sebep: Kullanıcı hedefleri doğal dilde yazabilir ve teknik forma çevrilmesi gerekebilir.

Örnek:
- "bel omuruna üstten basma"
- "L1 vertebra superior endplate aksiyel yük"
- "omur gövdesine kompresyon testi"

## Sonraki ajan kararı
- TARGET_UNDERSTANDING_PASS → SEGMENTATION_AGENT
- TARGET_UNDERSTANDING_NEEDS_REVIEW → HUMAN_REVIEW_GATE
- TARGET_UNDERSTANDING_FAIL → USER_ACTION_REQUIRED
- BLOCKED_BY_IMAGE_QUALITY → USER_ACTION_REQUIRED

## Not
HIGH_VOXEL_ANISOTROPY uyarısı bu ajanda çözülmez.
Bu sorun Agent-05 Segmentation / Preprocessing Agent aşamasında resampling ile ele alınacaktır.
Mesh ve sonuç doğrulama ajanlarında da ek kontrol yapılacaktır.
