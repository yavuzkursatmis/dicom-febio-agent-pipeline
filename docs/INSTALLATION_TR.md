# Kurulum

```powershell
py -3.11 -m venv .venv
& ".\.venv\Scripts\Activate.ps1"
python -m pip install --upgrade pip
pip install -r requirements-publication.in
```

İsteğe bağlı haricî model bağlantısı:

```powershell
pip install -r requirements-optional-ai.in
```

`.env.example` dosyasını `.env` olarak kopyalayın. `.env` Git'e eklenmemelidir.

Gerekirse:

```powershell
$env:DICOM_FEBIO_PROJECT_ROOT = "D:\research\dicom_febio"
```

Release öncesi:

```powershell
python -m pip freeze | Out-File requirements-lock.txt -Encoding utf8
```
