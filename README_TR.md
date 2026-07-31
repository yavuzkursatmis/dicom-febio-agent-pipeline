# CT/DICOM'dan FEBio'ya İnsan Denetimli Ajan İş Akışı

> **Yayın durumu:** bilimsel yazılım için yayın öncesi repository.  
> **Klinik durum:** yalnızca araştırma amaçlıdır; tıbbi cihaz, tanı sistemi, tedavi planlama aracı veya klinik karar destek sistemi değildir.

## Amaç

Bu repository, hastane arşivinden alınan retrospektif CT/DICOM verisini sonlu elemanlar tabanlı biyomekanik modele taşıyan modüler otonom/yarı-otonom iş akışının yayına esas kaynak kodunu ve teknik dokümantasyonunu içerir.

Doğrulanan teknik vaka, T1 vertebranın aksiyel kompresyon analizidir.

## Doğrulanmış iş akışı sınırı

Yayında, tek bir LangGraph çalıştırmasının ham DICOM'dan başlayarak Agent01–17'nin tamamını yürüttüğü iddia edilmeyecektir.

Gerçekte doğrulanan sıra şöyledir:

1. Agent01–07 üst akışta tamamlanmış ve incelenmiştir: veri alımı, DICOM güvenliği, görüntü kalitesi, hedef tanımı, segmentasyon/ön işleme, segmentasyon doğrulaması ve malzeme incelemesi.
2. Başarılı canlı LangGraph çalışması Agent08'den başlamıştır.
3. Graph; geometri, hacim mesh, FEBio modeli, sınır/yük koşulları ve incelemesi, solver yürütmesi, solver doğrulaması, sınırlı veri çıkarımı, yorumlama ön kontrolü, rapor taslağı, tam hat denetimi ve üst-akış kanıt denetimini orkestre etmiştir.

Tarihsel yayın checkpoint'i:

```text
b58acf034 — Pass LangGraph clean T1 limited live run
```

## Bilimsel iddia sınırı

Repository şu iddiaları destekler:

- doğrulanmış üst-akış kanıtlarından FEBio çalıştırmasına teknik uygulanabilirlik;
- izlenebilir insan denetimi kapıları;
- solver normal sonlanma kontrolü;
- güvenlik sınırları uygulanmış sınırlı raporlama.

Şu iddiaları desteklemez:

- klinik tanısal başarı;
- T1 modelinin deneysel biyomekanik validasyonu;
- hasta-özel klinik öngörü;
- doğrulanmış uzamsal gerilme, gerinim ve yer değiştirme alan yorumu;
- sınırsız tam otonom kullanım.

## Üst düzey akış

```text
Retrospektif CT/DICOM
→ güvenlik ve kalite kontrolleri
→ hedef tanımı
→ TotalSegmentator destekli segmentasyon
→ 3D Slicer üzerinde insan incelemesi
→ yüzey geometrisi
→ tetrahedral hacim mesh
→ CT/HU bilgili malzeme ataması
→ FEBio modeli ve aksiyel kompresyon protokolü
→ solver yürütmesi ve sonlanma doğrulaması
→ sınırlı bilimsel raporlama
```

## Repository düzeni

```text
agent_system/       Yayına esas kaynak kod
docs/               Mimari, kurulum, iş akışı, etik ve provenance belgeleri
scripts/            Repository doğrulama ve bakım araçları
examples/           Veri içermeyen örnek ve beklenen çıktı açıklamaları
tests/              Test stratejisi ve haricî yazılıma bağlı testler
.github/workflows/  Statik yayın kontrolleri
```

## Veri ve mahremiyet

Ham DICOM, NIfTI/NRRD hacimler, hastadan türetilmiş geometri, mesh, FEBio binary çıktıları, PHI, erişim bilgileri ve özel yerel yollar açık repository'ye eklenmez.

Ayrıntılar için `DATA_AVAILABILITY.md`, `ETHICS_AND_PRIVACY.md` ve `SECURITY.md` belgelerine bakınız.

## Kurulum

- `docs/INSTALLATION_TR.md`
- `docs/CONFIGURATION.md`
- `docs/WORKFLOW_TR.md`

Kesin yazılım/build sürümleri `docs/SOFTWARE_VERSIONS.csv` içinde tamamlanana kadar release blocker olarak kalacaktır.

## Tekrar üretilebilirlik

Kaynak kod provenance'ı, kurtarılan kaynakların hash değerleri, insan denetimi sınırları ve yayın kapsamı sınırlamaları korunur. Retrospektif klinik CT verisi açık biçimde dağıtılamadığından bağımsız yürütme, uygun yetkiyle edinilmiş ve kimliksizleştirilmiş bir veri seti gerektirir.

## Atıf ve sürüm

GitHub ve arşiv sürümü oluşturulduktan sonra şu alanlar tamamlanacaktır:

- repository URL;
- değişmez commit hash;
- `v1.0.0-publication` release;
- Zenodo DOI;
- atıf yazar bilgileri.

`CITATION.cff.template` yer tutucular doldurulmadan `CITATION.cff` adına çevrilmemelidir.

## Lisans

Bu repository Apache License, Version 2.0 altında lisanslanmıştır. Ayrıntılar
için `LICENSE` dosyasına bakınız.

Üçüncü taraf yazılımlar ve kütüphaneler kendi lisanslarına tabidir. Bu
repository üzerinden üçüncü taraf bilimsel yazılım binary dosyaları
dağıtılmaz.
