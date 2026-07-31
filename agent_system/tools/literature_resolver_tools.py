from pathlib import Path
import json
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import urljoin

import requests

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[2]).expanduser().resolve()



ROOT = Path(str(PROJECT_ROOT))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def default_filtered_json(case_id: str):
    return ROOT / "cases" / case_id / "07_material_selection" / "MATERIAL_LITERATURE_CANDIDATES_TARGETED_FILTERED.json"


def default_targeted_json(case_id: str):
    return ROOT / "cases" / case_id / "07_material_selection" / "MATERIAL_LITERATURE_CANDIDATES_TARGETED.json"


def resolved_json(case_id: str):
    return ROOT / "cases" / case_id / "07_material_selection" / "MATERIAL_LITERATURE_CANDIDATES_RESOLVED.json"


def clean_text(text: str):
    if not text:
        return ""
    text = str(text)
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"<script.*?</script>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"</(tr|p|div|li|table|section|h1|h2|h3|h4)>", "\n", text, flags=re.I)
    text = re.sub(r"<(br|br/|br\s*/)>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def truncate_text(text: str, max_chars: int = 250000):
    text = clean_text(text)
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


def text_from_xml_node(node):
    if node is None:
        return ""
    return clean_text(" ".join(node.itertext()))


def extract_pmid(record: dict):
    url = str(record.get("url", ""))
    m = re.search(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)", url)
    if m:
        return m.group(1)

    for key in ["pmid", "pubmed_id", "PMID"]:
        if record.get(key):
            return str(record.get(key)).strip()

    return ""


def extract_doi(record: dict):
    doi = str(record.get("doi", "")).strip()
    if doi:
        return doi

    text = " ".join([
        str(record.get("url", "")),
        str(record.get("title", "")),
        str(record.get("abstract", "")),
    ])

    m = re.search(r"(10\.\d{4,9}/[-._;()/:A-Z0-9]+)", text, flags=re.I)
    if m:
        return m.group(1).rstrip(".;, ")

    return ""


def request_get(url: str, timeout: int = 25, accept: str = None):
    headers = {
        "User-Agent": "dicom-febio-agent-literature-resolver/0.1"
    }
    if accept:
        headers["Accept"] = accept

    r = requests.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r


def fetch_pubmed_xml(pmid: str):
    if not pmid:
        return None, "NO_PMID"

    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {
        "db": "pubmed",
        "id": pmid,
        "retmode": "xml"
    }

    try:
        r = requests.get(url, params=params, timeout=25)
        r.raise_for_status()
        return r.text, ""
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def parse_pubmed_xml(xml_text: str):
    result = {
        "title": "",
        "abstract": "",
        "doi": "",
        "pmcid": "",
        "pmid": "",
        "journal": "",
        "year": "",
    }

    if not xml_text:
        return result

    try:
        root = ET.fromstring(xml_text)

        title_node = root.find(".//ArticleTitle")
        result["title"] = text_from_xml_node(title_node)

        abstract_parts = []
        for node in root.findall(".//Abstract/AbstractText"):
            label = node.attrib.get("Label", "")
            txt = text_from_xml_node(node)
            if txt:
                if label:
                    abstract_parts.append(f"{label}: {txt}")
                else:
                    abstract_parts.append(txt)

        result["abstract"] = clean_text("\n".join(abstract_parts))

        journal_node = root.find(".//Journal/Title")
        result["journal"] = text_from_xml_node(journal_node)

        year_node = root.find(".//PubDate/Year")
        if year_node is not None and year_node.text:
            result["year"] = year_node.text.strip()

        for article_id in root.findall(".//ArticleIdList/ArticleId"):
            id_type = article_id.attrib.get("IdType", "").lower()
            value = text_from_xml_node(article_id)

            if id_type == "doi":
                result["doi"] = value
            elif id_type == "pmc":
                result["pmcid"] = value
            elif id_type == "pubmed":
                result["pmid"] = value

        return result

    except Exception:
        return result


def elink_pubmed_to_pmc(pmid: str):
    if not pmid:
        return ""

    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"
    params = {
        "dbfrom": "pubmed",
        "db": "pmc",
        "id": pmid,
        "retmode": "json"
    }

    try:
        r = requests.get(url, params=params, timeout=25)
        r.raise_for_status()
        data = r.json()

        linksets = data.get("linksets", [])
        for linkset in linksets:
            for linkdb in linkset.get("linksetdbs", []):
                for link in linkdb.get("links", []):
                    if link:
                        return "PMC" + str(link)

    except Exception:
        return ""

    return ""


def fetch_pmc_fulltext(pmcid: str):
    if not pmcid:
        return "", "NO_PMCID"

    pmc_id_param = str(pmcid).upper().replace("PMC", "")

    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {
        "db": "pmc",
        "id": pmc_id_param,
        "retmode": "xml"
    }

    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        root = ET.fromstring(r.text)

        body = root.find(".//body")
        if body is not None:
            return truncate_text(text_from_xml_node(body), 250000), ""

        return truncate_text(text_from_xml_node(root), 250000), ""

    except Exception as e:
        return "", f"{type(e).__name__}: {e}"


def extract_pdf_links(html: str, base_url: str, max_links: int = 3):
    if not html:
        return []

    links = []
    for m in re.finditer(r'href=["\']([^"\']+)["\']', html, flags=re.I):
        href = m.group(1)
        if ".pdf" in href.lower():
            full = urljoin(base_url, href)
            if full not in links:
                links.append(full)

    return links[:max_links]


def extract_pdf_text(content: bytes, max_pages: int = 30):
    try:
        from io import BytesIO
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(content))
        pages = []

        for page in reader.pages[:max_pages]:
            try:
                pages.append(page.extract_text() or "")
            except Exception:
                continue

        return truncate_text("\n".join(pages), 250000)

    except Exception:
        return ""


def fetch_publisher_or_doi_text(doi: str, url: str):
    result = {
        "status": "NOT_ATTEMPTED",
        "resolved_url": "",
        "html_text": "",
        "pdf_links": [],
        "pdf_texts_count": 0,
        "error": "",
    }

    target = ""
    if doi:
        target = "https://doi.org/" + doi
    elif url:
        target = url

    if not target:
        result["status"] = "NO_DOI_OR_URL"
        return result

    try:
        r = request_get(target, timeout=25, accept="text/html,application/pdf")
        result["resolved_url"] = r.url

        content_type = r.headers.get("content-type", "").lower()

        if "pdf" in content_type or r.url.lower().endswith(".pdf"):
            result["html_text"] = extract_pdf_text(r.content)
            result["status"] = "PDF_FETCHED"
            return result

        html = r.text
        result["html_text"] = truncate_text(clean_text(html), 250000)
        result["pdf_links"] = extract_pdf_links(html, r.url, max_links=3)
        result["status"] = "HTML_FETCHED"

        pdf_texts = []
        for pdf_url in result["pdf_links"]:
            try:
                pr = request_get(pdf_url, timeout=25, accept="application/pdf")
                pdf_text = extract_pdf_text(pr.content)
                if pdf_text:
                    pdf_texts.append(pdf_text)
            except Exception:
                continue

        if pdf_texts:
            result["html_text"] = truncate_text(result["html_text"] + "\n\n" + "\n\n".join(pdf_texts), 250000)
            result["pdf_texts_count"] = len(pdf_texts)

        return result

    except Exception as e:
        result["status"] = "FETCH_FAILED"
        result["error"] = f"{type(e).__name__}: {e}"
        return result


def merge_record_texts(record: dict, pubmed: dict, pmc_text: str, publisher_text: str):
    pieces = []

    for part in [
        record.get("title", ""),
        record.get("abstract", ""),
        pubmed.get("title", ""),
        pubmed.get("abstract", ""),
        pmc_text,
        publisher_text,
    ]:
        part = clean_text(part)
        if part:
            pieces.append(part)

    seen = set()
    unique = []
    for p in pieces:
        key = p[:500]
        if key in seen:
            continue
        seen.add(key)
        unique.append(p)

    return truncate_text("\n\n".join(unique), 300000)


def resolve_literature_records(case_id: str, input_json: str = None, max_records: int = 60, sleep_seconds: float = 0.2):
    source_path = Path(input_json) if input_json else default_filtered_json(case_id)

    if not source_path.exists():
        alt = default_targeted_json(case_id)
        source_path = alt if alt.exists() else source_path

    output_path = resolved_json(case_id)

    if not source_path.exists():
        result = {
            "case_id": case_id,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "status": "SOURCE_LITERATURE_JSON_NOT_FOUND",
            "records": [],
            "records_count": 0,
            "resolved_records_count": 0,
            "blockers": ["SOURCE_LITERATURE_JSON_NOT_FOUND"],
            "clinical_use": False
        }
        save_json(output_path, result)
        return result

    source = load_json(source_path)
    records = source.get("records", [])
    records_to_process = records[:max_records]

    resolved_records = []
    resolution_log = []

    for idx, record in enumerate(records_to_process, start=1):
        pmid = extract_pmid(record)
        doi = extract_doi(record)

        pubmed_xml = None
        pubmed_error = ""
        pubmed_data = {
            "title": "",
            "abstract": "",
            "doi": "",
            "pmcid": "",
            "pmid": "",
            "journal": "",
            "year": "",
        }

        if pmid:
            pubmed_xml, pubmed_error = fetch_pubmed_xml(pmid)
            if pubmed_xml:
                pubmed_data = parse_pubmed_xml(pubmed_xml)

        if not doi and pubmed_data.get("doi"):
            doi = pubmed_data.get("doi")

        pmcid = pubmed_data.get("pmcid", "")
        if not pmcid and pmid:
            pmcid = elink_pubmed_to_pmc(pmid)

        pmc_text = ""
        pmc_error = ""
        if pmcid:
            pmc_text, pmc_error = fetch_pmc_fulltext(pmcid)

        publisher = fetch_publisher_or_doi_text(doi=doi, url=record.get("url", ""))

        combined_text = merge_record_texts(
            record=record,
            pubmed=pubmed_data,
            pmc_text=pmc_text,
            publisher_text=publisher.get("html_text", "")
        )

        enriched = dict(record)

        if pubmed_data.get("title") and not enriched.get("title"):
            enriched["title"] = pubmed_data["title"]

        if doi:
            enriched["doi"] = doi

        if pmid:
            enriched["pmid"] = pmid

        if pmcid:
            enriched["pmcid"] = pmcid

        enriched["abstract"] = combined_text
        enriched["resolved_text_length"] = len(combined_text)
        enriched["resolution_sources"] = {
            "pubmed_efetch_used": bool(pubmed_xml),
            "pubmed_abstract_length": len(pubmed_data.get("abstract", "")),
            "pmcid": pmcid,
            "pmc_fulltext_length": len(pmc_text),
            "publisher_status": publisher.get("status", ""),
            "publisher_resolved_url": publisher.get("resolved_url", ""),
            "publisher_text_length": len(publisher.get("html_text", "")),
            "publisher_pdf_links": publisher.get("pdf_links", []),
            "publisher_pdf_texts_count": publisher.get("pdf_texts_count", 0),
        }

        resolved_records.append(enriched)

        resolution_log.append({
            "index": idx,
            "title": enriched.get("title", ""),
            "url": enriched.get("url", ""),
            "pmid": pmid,
            "doi": doi,
            "pmcid": pmcid,
            "pubmed_error": pubmed_error,
            "pmc_error": pmc_error,
            "publisher_status": publisher.get("status", ""),
            "publisher_error": publisher.get("error", ""),
            "resolved_text_length": len(combined_text),
            "pubmed_abstract_length": len(pubmed_data.get("abstract", "")),
            "pmc_fulltext_length": len(pmc_text),
            "publisher_text_length": len(publisher.get("html_text", "")),
        })

        if sleep_seconds:
            time.sleep(sleep_seconds)

    result = {
        "case_id": case_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "status": "LITERATURE_RECORDS_RESOLVED",
        "source_json": str(source_path),
        "records_count": len(records),
        "processed_records_count": len(records_to_process),
        "resolved_records_count": len(resolved_records),
        "records": resolved_records,
        "source_errors": source.get("source_errors", []),
        "resolution_log": resolution_log,
        "clinical_use": False,
        "rules": [
            "This resolver enriches literature records with PubMed abstracts, PMC full text, and publisher/DOI text when accessible.",
            "It does not assign material values.",
            "Agent-07C must still extract source-linked values from the resolved text.",
            "GEOMETRY_AGENT remains blocked until a target-relevant agent-derived candidate set is validated."
        ],
        "blockers": [] if resolved_records else ["NO_RESOLVED_LITERATURE_RECORDS"]
    }

    save_json(output_path, result)
    return result
