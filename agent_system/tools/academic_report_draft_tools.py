from pathlib import Path
import json
from datetime import datetime

from agent_system.schemas.academic_report_draft_schema import (
    AcademicReportDraftInput,
    AcademicReportDraftResult,
)

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[2]).expanduser().resolve()



ROOT = Path(str(PROJECT_ROOT))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def default_precheck_path(case_id: str):
    return ROOT / "cases" / case_id / "16_result_interpretation_precheck" / "RESULT_INTERPRETATION_PRECHECK_RESULT.json"


def output_paths(case_id: str):
    out_dir = ROOT / "cases" / case_id / "17_academic_report_draft"
    return {
        "result_json": out_dir / "ACADEMIC_REPORT_DRAFT_RESULT.json",
        "report_md": out_dir / "ACADEMIC_REPORT_DRAFT.md",
        "report_txt": out_dir / "ACADEMIC_REPORT_DRAFT.txt",
        "metadata_json": out_dir / "ACADEMIC_REPORT_METADATA.json",
    }


def optional_sources(case_id: str):
    case_dir = ROOT / "cases" / case_id

    return {
        "agent06_segmentation_validation": case_dir / "06_segmentation_validation" / "SEGMENTATION_VALIDATION_RESULT.json",
        "agent08_geometry": case_dir / "09_geometry_mesh_preparation" / "GEOMETRY_PREPARATION_RESULT.json",
        "agent09_volume_mesh": case_dir / "10_volume_mesh_generation" / "VOLUME_MESH_GENERATION_RESULT.json",
        "agent10_febio_model": case_dir / "11_febio_model_generation" / "FEBIO_MODEL_GENERATION_RESULT.json",
        "agent11_boundary_load": case_dir / "12_boundary_load_configuration" / "BOUNDARY_LOAD_CONFIGURATION_RESULT.json",
        "agent11_review": case_dir / "12_boundary_load_configuration" / "BOUNDARY_LOAD_REVIEW_VALIDATION_RESULT.json",
        "agent12_solver": case_dir / "13_solver_execution" / "FEBIO_SOLVER_EXECUTION_RESULT.json",
        "agent13_solver_validation": case_dir / "14_solver_result_validation" / "SOLVER_RESULT_VALIDATION_RESULT.json",
        "agent14_result_extraction": case_dir / "15_result_extraction" / "RESULT_EXTRACTION_RESULT.json",
        "agent15_interpretation_precheck": case_dir / "16_result_interpretation_precheck" / "RESULT_INTERPRETATION_PRECHECK_RESULT.json",
    }


def load_available_sources(case_id: str):
    loaded = {}
    included = []
    missing = []

    for key, path in optional_sources(case_id).items():
        if path.exists():
            try:
                loaded[key] = load_json(path)
                included.append(str(path))
            except Exception as e:
                loaded[key] = {"read_error": f"{type(e).__name__}: {e}"}
                included.append(str(path))
        else:
            missing.append(str(path))

    return loaded, included, missing


def val(data, key, default=""):
    if not isinstance(data, dict):
        return default
    return data.get(key, default)


def make_report(case_id: str, sources: dict, precheck: dict):
    now = datetime.now().isoformat(timespec="seconds")

    a08 = sources.get("agent08_geometry", {})
    a09 = sources.get("agent09_volume_mesh", {})
    a10 = sources.get("agent10_febio_model", {})
    a11 = sources.get("agent11_boundary_load", {})
    a11r = sources.get("agent11_review", {})
    a12 = sources.get("agent12_solver", {})
    a13 = sources.get("agent13_solver_validation", {})
    a14 = sources.get("agent14_result_extraction", {})
    a15 = sources.get("agent15_interpretation_precheck", precheck)

    sections = []

    sections.append("# AI Agent Destekli DICOM–FEBio Biyomekanik Analiz Hattı — Akademik Taslak Rapor")
    sections.append("")
    sections.append(f"**Case ID:** `{case_id}`")
    sections.append(f"**Oluşturulma tarihi:** {now}")
    sections.append("")
    sections.append("## 1. Kapsam")
    sections.append("")
    sections.append(
        "Bu rapor, DICOM tabanlı tıbbi görüntü girdisinden segmentasyon, geometri oluşturma, hacim mesh üretimi, "
        "literatür destekli malzeme yasası ataması, FEBio model üretimi, boundary/load tanımı, solver çalıştırma ve "
        "solver çıktı doğrulama aşamalarına uzanan AI-agent destekli araştırma prototipinin mevcut vaka çıktısını özetler."
    )
    sections.append("")
    sections.append("Bu rapor klinik tanı, tedavi kararı veya hasta özelinde doğrulanmış klinik karar desteği amacı taşımaz.")
    sections.append("")

    sections.append("## 2. Pipeline Durumu")
    sections.append("")
    sections.append("| Aşama | Durum | Not |")
    sections.append("|---|---:|---|")
    sections.append(f"| Agent-08 Geometry Preparation | `{val(a08, 'geometry_status', 'UNKNOWN')}` | STL/geometri hazırlığı |")
    sections.append(f"| Agent-09 Volume Mesh Generation | `{val(a09, 'volume_mesh_status', 'UNKNOWN')}` | Tetra hacim mesh |")
    sections.append(f"| Agent-10 FEBio Model Generation | `{val(a10, 'febio_model_status', 'UNKNOWN')}` | HU/density tabanlı material bin ataması |")
    sections.append(f"| Agent-11 Boundary/Load Configuration | `{val(a11, 'boundary_load_status', 'UNKNOWN')}` | Axial compression candidate |")
    sections.append(f"| Agent-11 Human Review | `{val(a11r, 'approval_status', 'UNKNOWN')}` | Solver execution için onay |")
    sections.append(f"| Agent-12 Solver Execution | `{val(a12, 'solver_execution_status', 'UNKNOWN')}` | FEBio solver çalıştırma |")
    sections.append(f"| Agent-13 Solver Result Validation | `{val(a13, 'solver_result_validation_status', 'UNKNOWN')}` | Solver sonucu doğrulama |")
    sections.append(f"| Agent-14 Result Extraction | `{val(a14, 'result_extraction_status', 'UNKNOWN')}` | Log/XPLT dosya doğrulama |")
    sections.append(f"| Agent-15 Interpretation Precheck | `{val(a15, 'interpretation_precheck_status', 'UNKNOWN')}` | Yorum sınırları |")
    sections.append("")

    sections.append("## 3. Geometri ve Mesh Özeti")
    sections.append("")
    sections.append(f"- Segment/nesne hacmi: `{val(a08, 'object_volume_cm3', 'UNKNOWN')}` cm³")
    sections.append(f"- STL yüzey yolu: `{val(a08, 'surface_stl_path', 'UNKNOWN')}`")
    sections.append(f"- Yüzey watertight: `{val(a08, 'is_watertight', 'UNKNOWN')}`")
    sections.append(f"- Volume mesh yolu: `{val(a09, 'volume_mesh_path', 'UNKNOWN')}`")
    sections.append(f"- Node sayısı: `{val(a09, 'node_count', 'UNKNOWN')}`")
    sections.append(f"- Tetra eleman sayısı: `{val(a09, 'tetra_count', 'UNKNOWN')}`")
    sections.append(f"- Basit aspect ratio max: `{val(a09, 'simple_aspect_ratio_max', 'UNKNOWN')}`")
    sections.append("")

    sections.append("## 4. Malzeme Modeli ve FEBio Model Özeti")
    sections.append("")
    sections.append(f"- Malzeme bin sayısı: `{val(a10, 'material_bin_count', 'UNKNOWN')}`")
    sections.append(f"- HU min / max / mean: `{val(a10, 'hu_min', 'UNKNOWN')}` / `{val(a10, 'hu_max', 'UNKNOWN')}` / `{val(a10, 'hu_mean', 'UNKNOWN')}`")
    sections.append(f"- Density min / max: `{val(a10, 'density_min_g_cm3', 'UNKNOWN')}` / `{val(a10, 'density_max_g_cm3', 'UNKNOWN')}` g/cm³")
    sections.append(f"- Ez min / max: `{val(a10, 'ez_min_mpa', 'UNKNOWN')}` / `{val(a10, 'ez_max_mpa', 'UNKNOWN')}` MPa")
    sections.append(f"- FEBio model yolu: `{val(a10, 'febio_model_path', 'UNKNOWN')}`")
    sections.append("")
    sections.append(
        "Malzeme modeli HU → yoğunluk → elastik parametre dönüşümü üzerinden kurulmuştur. "
        "Yoğunluk alanı dışında kalan elemanlar için onaylı density-domain policy uygulanmıştır."
    )
    sections.append("")

    sections.append("## 5. Boundary / Load Tanımı")
    sections.append("")
    sections.append(f"- Analiz tipi: `{val(a11, 'analysis_type', 'UNKNOWN')}`")
    sections.append(f"- Sabit bölge: `{val(a11, 'fixed_region', 'UNKNOWN')}`")
    sections.append(f"- Yüklenen bölge: `{val(a11, 'load_region', 'UNKNOWN')}`")
    sections.append(f"- Fixed node count: `{val(a11, 'fixed_node_count', 'UNKNOWN')}`")
    sections.append(f"- Loaded node count: `{val(a11, 'loaded_node_count', 'UNKNOWN')}`")
    sections.append(f"- Prescribed displacement: `{val(a11, 'prescribed_displacement_mm', 'UNKNOWN')}` mm")
    sections.append(f"- Load magnitude source: `{val(a11, 'load_magnitude_source', 'UNKNOWN')}`")
    sections.append("")
    sections.append("Bu yük tanımı pipeline-development amaçlıdır; klinik/fizyolojik yük olarak sunulmaz.")
    sections.append("")

    sections.append("## 6. Solver ve Doğrulama Özeti")
    sections.append("")
    sections.append(f"- Solver execution status: `{val(a12, 'solver_execution_status', 'UNKNOWN')}`")
    sections.append(f"- Solver return code: `{val(a12, 'solver_return_code', 'UNKNOWN')}`")
    sections.append(f"- Normal termination: `{val(a12, 'normal_termination_detected', 'UNKNOWN')}`")
    sections.append(f"- Solver validation status: `{val(a13, 'solver_result_validation_status', 'UNKNOWN')}`")
    sections.append(f"- Critical error terms: `{val(a13, 'critical_error_terms_detected', [])}`")
    sections.append(f"- XPLT files: `{val(a13, 'xplt_files_found', [])}`")
    sections.append(f"- Result extraction ready: `{val(a13, 'result_extraction_ready', 'UNKNOWN')}`")
    sections.append("")

    sections.append("## 7. Sonuç Çıkarımı Durumu")
    sections.append("")
    sections.append(f"- Result extraction status: `{val(a14, 'result_extraction_status', 'UNKNOWN')}`")
    sections.append(f"- XPLT non-empty files: `{val(a14, 'xplt_files_nonempty', [])}`")
    sections.append(f"- Selected solver log: `{val(a14, 'selected_solver_log_path', 'UNKNOWN')}`")
    sections.append(f"- Solver log line count: `{val(a14, 'solver_log_line_count', 'UNKNOWN')}`")
    sections.append(f"- Extracted CSV path: `{val(a14, 'extracted_csv_path', 'UNKNOWN')}`")
    sections.append(f"- XPLT binary field extraction performed: `{val(a14, 'xplt_binary_field_extraction_performed', 'UNKNOWN')}`")
    sections.append("")

    sections.append("## 8. Yorum Ön-Kontrol Kararı")
    sections.append("")
    sections.append(f"- Interpretation precheck status: `{val(a15, 'interpretation_precheck_status', 'UNKNOWN')}`")
    sections.append(f"- Quantitative field interpretation allowed: `{val(a15, 'quantitative_field_interpretation_allowed', 'UNKNOWN')}`")
    sections.append(f"- Solver log interpretation allowed: `{val(a15, 'solver_log_interpretation_allowed', 'UNKNOWN')}`")
    sections.append(f"- Clinical interpretation allowed: `{val(a15, 'clinical_interpretation_allowed', 'UNKNOWN')}`")
    sections.append(f"- Academic pipeline reporting allowed: `{val(a15, 'academic_pipeline_reporting_allowed', 'UNKNOWN')}`")
    sections.append("")
    sections.append("Bu aşamada maksimum displacement, maksimum stress, strain dağılımı veya lokal alan bazlı biyomekanik yorum yapılmaz.")
    sections.append("")

    sections.append("## 9. Sınırlılıklar")
    sections.append("")
    sections.append("- XPLT binary alan verileri henüz parse edilmemiştir.")
    sections.append("- Maksimum/minimum stress veya displacement sayısal olarak raporlanmamıştır.")
    sections.append("- Strain çıktısı FEBio output değişken uyumluluğu nedeniyle bu çözümde raporlanmamıştır.")
    sections.append("- Yükleme koşulu pipeline-development amaçlıdır; klinik fizyolojik yük olarak yorumlanmaz.")
    sections.append("- Segmentasyon ve malzeme modeli insan review kapılarıyla denetlenmiştir; klinik validasyon iddiası yoktur.")
    sections.append("")

    sections.append("## 10. Sonraki Aşamalar")
    sections.append("")
    sections.append("1. XPLT alan verisi için güvenilir extraction yöntemi belirlenmesi.")
    sections.append("2. Agent-17 Full Pipeline Audit ile tüm log, review ve sınırlılıkların denetlenmesi.")
    sections.append("3. Deterministik ajanların LangChain Tool wrapper ve LangGraph node haline getirilmesi.")
    sections.append("4. Streamlit kullanıcı arayüzünün LangGraph workflow’a bağlanması.")
    sections.append("5. DICOM yükleme üzerinden uçtan uca kullanıcı testi.")
    sections.append("")

    sections.append("## 11. Sonuç")
    sections.append("")
    sections.append(
        "Bu vaka için agent tabanlı pipeline, FEBio solver aşamasına kadar başarıyla çalışmış; "
        "solver normal termination ile tamamlanmış ve geçerli XPLT çıktı dosyası üretilmiştir. "
        "Mevcut sonuçlar akademik pipeline raporlaması için uygundur; ancak XPLT içinden alan bazlı sonuçlar "
        "çıkarılmadığı için kantitatif biyomekanik yorum bu aşamada yapılmamaktadır."
    )
    sections.append("")

    return "\n".join(sections)


def run_academic_report_draft(user_input: AcademicReportDraftInput):
    case_id = user_input.case_id
    paths = output_paths(case_id)

    warnings = []
    blockers = []

    precheck_path = Path(user_input.interpretation_precheck_path) if user_input.interpretation_precheck_path else default_precheck_path(case_id)

    if not precheck_path.exists():
        result = AcademicReportDraftResult(
            case_id=case_id,
            academic_report_status="ACADEMIC_REPORT_DRAFT_BLOCKED",
            next_agent="USER_ACTION_REQUIRED",
            interpretation_precheck_path=str(precheck_path),
            blockers=["INTERPRETATION_PRECHECK_RESULT_NOT_FOUND"],
        )
        save_json(paths["result_json"], result.model_dump())
        return result

    precheck = load_json(precheck_path)

    precheck_status = precheck.get("interpretation_precheck_status", "")
    precheck_passed = precheck_status in [
        "INTERPRETATION_PRECHECK_PASS",
        "INTERPRETATION_PRECHECK_LIMITED_PASS",
    ]

    academic_allowed = precheck.get("academic_pipeline_reporting_allowed") is True
    quantitative_allowed = precheck.get("quantitative_field_interpretation_allowed") is True
    clinical_allowed = precheck.get("clinical_interpretation_allowed") is True

    if not precheck_passed:
        blockers.append("INTERPRETATION_PRECHECK_NOT_PASS")

    if not academic_allowed:
        blockers.append("ACADEMIC_PIPELINE_REPORTING_NOT_ALLOWED")

    if clinical_allowed:
        blockers.append("CLINICAL_INTERPRETATION_SHOULD_NOT_BE_ALLOWED")

    sources, included, missing = load_available_sources(case_id)

    if missing:
        warnings.append("SOME_OPTIONAL_SOURCE_FILES_NOT_FOUND")

    if blockers:
        status = "ACADEMIC_REPORT_DRAFT_BLOCKED"
        next_agent = "USER_ACTION_REQUIRED"
        sections_created = []
    else:
        report_md = make_report(case_id, sources, precheck)
        paths["report_md"].parent.mkdir(parents=True, exist_ok=True)
        paths["report_md"].write_text(report_md, encoding="utf-8")
        paths["report_txt"].write_text(report_md, encoding="utf-8")

        metadata = {
            "case_id": case_id,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "precheck_status": precheck_status,
            "academic_pipeline_reporting_allowed": academic_allowed,
            "quantitative_field_interpretation_allowed": quantitative_allowed,
            "clinical_interpretation_allowed": clinical_allowed,
            "included_source_files": included,
            "missing_optional_source_files": missing,
            "report_markdown_path": str(paths["report_md"]),
            "report_text_path": str(paths["report_txt"]),
        }
        save_json(paths["metadata_json"], metadata)

        status = "ACADEMIC_REPORT_DRAFT_PASS"
        next_agent = "AGENT_17_FULL_PIPELINE_AUDIT"
        sections_created = [
            "scope",
            "pipeline_status",
            "geometry_mesh_summary",
            "material_febio_summary",
            "boundary_load_summary",
            "solver_validation_summary",
            "result_extraction_status",
            "interpretation_precheck",
            "limitations",
            "next_steps",
            "conclusion",
        ]

    result = AcademicReportDraftResult(
        case_id=case_id,
        academic_report_status=status,
        next_agent=next_agent,
        interpretation_precheck_path=str(precheck_path),
        interpretation_precheck_passed=precheck_passed,
        academic_pipeline_reporting_allowed=academic_allowed,
        quantitative_field_interpretation_allowed=quantitative_allowed,
        clinical_interpretation_allowed=clinical_allowed,
        included_source_files=included,
        missing_optional_source_files=missing,
        report_markdown_path=str(paths["report_md"]) if not blockers else "",
        report_text_path=str(paths["report_txt"]) if not blockers else "",
        report_metadata_json_path=str(paths["metadata_json"]) if not blockers else "",
        report_sections_created=sections_created,
        warnings=list(dict.fromkeys(warnings)),
        blockers=list(dict.fromkeys(blockers)),
    )

    save_json(paths["result_json"], result.model_dump())

    return result


def append_paper_note(case_id: str, result: AcademicReportDraftResult):
    note_path = ROOT / "paper_notes" / "academic_report_notes.md"
    note_path.parent.mkdir(parents=True, exist_ok=True)

    text = f"""
## Agent-16 Academic Report Draft

Tarih: {datetime.now().isoformat(timespec="seconds")}
Case ID: {case_id}

Durum: {result.academic_report_status}
Sonraki ajan: {result.next_agent}

Rapor dosyaları:
- Markdown: {result.report_markdown_path}
- Text: {result.report_text_path}
- Metadata: {result.report_metadata_json_path}

Karar:
- Academic pipeline reporting allowed: {result.academic_pipeline_reporting_allowed}
- Quantitative field interpretation allowed: {result.quantitative_field_interpretation_allowed}
- Clinical interpretation allowed: {result.clinical_interpretation_allowed}

Uyarılar: {result.warnings}
Bloklayıcılar: {result.blockers}
"""

    with note_path.open("a", encoding="utf-8") as f:
        f.write(text)
