# Agent-07 — Material Selection Agent

## Amaç
Segmentasyonu doğrulanmış anatomik yapı için biyomekanik analizde kullanılacak malzeme özelliklerini aktif literatür taraması ile seçmek.

Bu ajan test/fallback değerlerini nihai analiz değeri olarak kullanamaz.

## Temel kural
Material Selection Agent, aktif literatür taraması yapmadan FEBio'ya aktarılacak malzeme parametresi seçemez.

Kural:
- Literature search success = false ise seçilmiş malzeme değeri üretilemez.
- Literature records count yetersiz ise MATERIAL_SELECTION_NEEDS_REVIEW üretilir.
- Sayısal değerler literatür kaynağı ve gerekçesi olmadan GEOMETRY_AGENT aşamasına aktarılamaz.

## Kullanıcı ile iletişim
Bu ajan kullanıcıyla doğrudan konuşmaz.
Kararlarını JSON/CSV dosyalarına yazar.
Belirsizlik, kaynak yetersizliği veya geniş değer aralığı varsa HUMAN_REVIEW_GATE kararı üretir.

## Giriş
Önceki ajanlardan:
- case_id
- standardized_anatomical_target
- segmentation_target
- standardized_analysis_type
- load_region
- segmentation_validation_status
- mask_volume_cm3
- human_review_status
- approved_next_agent

## Ön koşul
Agent-06 sonrası Human Review Gate onayı gerekir.

Gerekli onay:
- approved = true
- approved_next_agent = MATERIAL_SELECTION_AGENT

Onay yoksa:
- BLOCKED_BY_HUMAN_REVIEW

## Yapacağı işler
- Human Review Gate sonucunu okur.
- Agent-04 Target Understanding sonucunu okur.
- Agent-06 Segmentation Validation sonucunu okur.
- Hedef anatomik yapı ve analiz tipine göre literatür sorguları üretir.
- PubMed / Semantic Scholar / Crossref üzerinden aktif literatür taraması yapar.
- Literatür adaylarını kaydeder.
- Malzeme özellikleri için kaynak destekli aralıkları çıkarır.
- Seçilen değeri, kaynak aralığından ve gerekçesiyle belirler.
- Literatür desteği yetersizse HUMAN_REVIEW_GATE üretir.
- Sonraki ajanı belirler.

## Yapmayacağı işler
- Klinik tanı koymaz.
- Hasta özelinde kemik kalitesi iddiası üretmez.
- Segmentasyon yapmaz.
- Mesh üretmez.
- FEBio modeli oluşturmaz.
- Solver çalıştırmaz.
- Literatürsüz varsayılan değeri final analiz değeri olarak kullanmaz.

## Malzeme stratejisi
İlk sürümde vertebra için literatür destekli basitleştirilmiş model seçilecektir.

Model adayları:
- linear_elastic_isotropic
- literature_derived_homogeneous_vertebra

Kaydedilecek parametreler:
- elastic_modulus_MPa
- poisson_ratio
- density_kg_m3_optional
- anatomical_region
- tissue_assumption
- source_count
- source_titles
- source_dois
- selected_value_rationale
- uncertainty_level

## Test değeri politikası
Test/smoke-test değerleri Agent-07 final çıktısında malzeme seçimi olarak kaydedilemez.

Yasak:
- Sabit 500 MPa gibi test değeri ile MATERIAL_SELECTION_PASS üretmek.
- Literatür kaydı olmadan GEOMETRY_AGENT'a geçmek.
- Fallback değeri seçilmiş bilimsel değer gibi göstermek.

İzinli:
- Literatür taraması başarısızsa MATERIAL_SELECTION_NEEDS_REVIEW veya MATERIAL_SELECTION_FAIL üretmek.
- Kaynak yetersizliğini açıkça kaydetmek.
- İnsan onayı istemek.

## Literatür kaynakları
Aktif tarama kaynakları:
- PubMed
- Semantic Scholar
- Crossref

Yerel manuel literatür tablosu ileride desteklenebilir; fakat manuel tablo kullanılırsa dosya yolu, kayıt sayısı ve kaynak bilgisi JSON çıktısında açıkça belirtilmelidir.

## Çıkış bilgileri
- material_selection_status
- active_literature_search_required
- literature_search_performed
- literature_search_success
- material_model
- selected_material_name
- anatomical_region
- tissue_assumption
- elastic_modulus_MPa
- poisson_ratio
- density_kg_m3
- literature_query
- literature_support_level
- literature_records_count
- selected_sources
- selected_value_rationale
- uncertainty_level
- human_review_required
- next_agent
- warnings
- blockers

## Karar durumları
- MATERIAL_SELECTION_PASS
- MATERIAL_SELECTION_NEEDS_REVIEW
- MATERIAL_SELECTION_FAIL
- BLOCKED_BY_HUMAN_REVIEW

## Sonraki ajan kararı
- MATERIAL_SELECTION_PASS → GEOMETRY_AGENT
- MATERIAL_SELECTION_NEEDS_REVIEW → HUMAN_REVIEW_GATE
- MATERIAL_SELECTION_FAIL → USER_ACTION_REQUIRED
- BLOCKED_BY_HUMAN_REVIEW → USER_ACTION_REQUIRED

## Çıkış dosyaları
cases/<case_id>/07_material_selection/MATERIAL_SELECTION_RESULT.json
cases/<case_id>/07_material_selection/MATERIAL_PROPERTY_TABLE.csv
cases/<case_id>/07_material_selection/MATERIAL_LITERATURE_CANDIDATES.json
paper_notes/material_selection_notes.md

## LLM kullanımı
Gemini opsiyonel kullanılabilir.

Kullanım amacı:
- Literatür kayıtlarını kısa teknik metne çevirmek
- Belirsizlik gerekçesini açıklamak

Ancak nihai sayısal parametre seçimi LLM tarafından uydurulamaz.
Sayısal parametreler kaynak kayıtlarıyla desteklenmelidir.
