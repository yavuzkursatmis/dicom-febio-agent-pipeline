from pathlib import Path
from dotenv import load_dotenv
from google import genai
import os

PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[1]).expanduser().resolve()


ROOT = Path(str(PROJECT_ROOT))
ENV_PATH = ROOT / "agent_system" / ".env"

load_dotenv(ENV_PATH)

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("GEMINI_API_KEY bulunamadı. .env dosyasını kontrol edin.")

client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model="gemini-flash-latest",
    contents="Sadece şu cümleyi yaz: Gemini bağlantısı başarılı."
)

print(response.text)
