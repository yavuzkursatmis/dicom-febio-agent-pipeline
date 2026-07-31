# CT/DICOM'dan FEBio'ya İnsan Denetimli Ajan İş Akışı

> **Yayın durumu:** bilimsel yazılım için yayın öncesi repository.  
> **Klinik durum:** yalnızca araştırma amaçlıdır; tıbbi cihaz, tanı sistemi, tedavi planlama aracı veya klinik karar destek sistemi değildir.

## Amaç

Bu repository, retrospektif hastane arşivi CT/DICOM verilerini sonlu elemanlar biyomekanik modeline dönüştüren modüler, insan denetimli bir ajan iş akışının yayın kapsamındaki kaynak kodunu ve teknik dokümantasyonunu içerir. Doğrulanan teknik vaka, T1 vertebranın aksiyel kompresyon analizidir.

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

Doğrulanmış kesin yazılım ve build sürümleri
`docs/SOFTWARE_VERSIONS.csv` dosyasında kayıtlıdır. Kesin Python bağımlılıkları
`requirements-core-lock.txt` içinde tutulur; opsiyonel haricî AI bağlantısı
`requirements-optional-ai-lock.txt` içinde ayrı olarak tanımlanır.

## Tekrar üretilebilirlik

Kaynak kod provenance'ı, kurtarılan kaynakların hash değerleri, insan denetimi sınırları ve yayın kapsamı sınırlamaları korunur. Retrospektif klinik CT verisi açık biçimde dağıtılamadığından bağımsız yürütme, uygun yetkiyle edinilmiş ve kimliksizleştirilmiş bir veri seti gerektirir.

## Atıf ve sürüm

Yazılım atıf metadata'sı repository kökündeki `CITATION.cff` dosyasında
etkindir.

Mevcut yazılım atıf kaydı şunları içerir:

- Yavuz Kürşat MİS;
- Kocaeli Üniversitesi Tıp Fakültesi Anatomi Ana Bilim Dalı;
- ORCID: https://orcid.org/0009-0007-7601-8628;
- açık kaynak kod repository adresi;
- Apache-2.0 lisansı.

İlişkili bilimsel makalenin yazar listesi ayrı olarak yönetilir ve yazılım
yazarı kaydından bağımsız biçimde değişebilir.

Aşağıdaki alanlar publication release aşamasına kadar beklemededir:

- yazılım sürümü;
- release tarihi;
- değişmez release commit hash'i;
- `v1.0.0-publication` release adresi;
- Zenodo DOI;
- ilişkili bilimsel makalenin tercih edilen atıf kaydı.

## Lisans

Bu repository Apache License, Version 2.0 altında lisanslanmıştır. Ayrıntılar
için `LICENSE` dosyasına bakınız.

Üçüncü taraf yazılımlar ve kütüphaneler kendi lisanslarına tabidir. Bu
repository üzerinden üçüncü taraf bilimsel yazılım binary dosyaları
dağıtılmaz.
