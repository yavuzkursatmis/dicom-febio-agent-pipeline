from pathlib import Path
import json
import re
import html
import requests

import os
PROJECT_ROOT = Path(os.getenv("DICOM_FEBIO_PROJECT_ROOT") or Path(__file__).resolve().parents[2]).expanduser().resolve()



ROOT = Path(str(PROJECT_ROOT))


def load_config():
    path = ROOT / "agent_system" / "configs" / "material_selection_config.json"
    return json.loads(path.read_text(encoding="utf-8-sig"))


def normalize_text(text: str) -> str:
    if text is None:
        return ""
    text = str(text).strip().lower()
    replacements = {
        "ı": "i",
        "ğ": "g",
        "ü": "u",
        "ş": "s",
        "ö": "o",
        "ç": "c",
    }
    for tr, en in replacements.items():
        text = text.replace(tr, en)
    text = re.sub(r"\s+", " ", text)
    return text


def strip_html(text: str) -> str:
    if not text:
        return ""
    text = html.unescape(str(text))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def infer_material_domain(target: str) -> str:
    t = normalize_text(target)

    bone_terms = [
        "vertebra", "omur", "bone", "kemik", "femur", "tibia",
        "humerus", "radius", "ulna", "mandible", "skull", "pelvis"
    ]
    cartilage_terms = ["cartilage", "kikirdak", "meniscus", "meniskus"]
    tendon_terms = ["tendon"]
    ligament_terms = ["ligament", "bag"]
    muscle_terms = ["muscle", "kas"]

    if any(x in t for x in bone_terms):
        return "bone"
    if any(x in t for x in cartilage_terms):
        return "cartilage"
    if any(x in t for x in tendon_terms):
        return "tendon"
    if any(x in t for x in ligament_terms):
        return "ligament"
    if any(x in t for x in muscle_terms):
        return "muscle"

    return "unknown_requires_review"


def generate_literature_queries(target: str, analysis_type: str, material_domain: str, config: dict):
    templates = config.get("literature_search_policy", {}).get("query_templates", [])
    queries = []

    for template in templates:
        q = template.replace("{target}", target)
        q = q.replace("{analysis_type}", analysis_type)
        q = q.replace("{material_domain}", material_domain)
        queries.append(q)

    cleaned = []
    for q in queries:
        q = re.sub(r"\s+", " ", q).strip()
        if q and q not in cleaned:
            cleaned.append(q)

    return cleaned


def make_record(source, title="", year="", abstract="", doi="", url="", authors=None):
    return {
        "source": source,
        "title": strip_html(title),
        "year": str(year) if year else "",
        "abstract": strip_html(abstract),
        "doi": str(doi) if doi else "",
        "url": str(url) if url else "",
        "authors": authors or [],
    }


def search_semantic_scholar(query: str, limit: int):
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,year,abstract,authors,externalIds,url"
    }

    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()

    records = []
    for item in data.get("data", []):
        external = item.get("externalIds") or {}
        authors = [a.get("name", "") for a in item.get("authors", []) if a.get("name")]
        records.append(make_record(
            source="Semantic Scholar",
            title=item.get("title", ""),
            year=item.get("year", ""),
            abstract=item.get("abstract", ""),
            doi=external.get("DOI", ""),
            url=item.get("url", ""),
            authors=authors,
        ))

    return records


def search_crossref(query: str, limit: int):
    url = "https://api.crossref.org/works"
    params = {
        "query": query,
        "rows": limit,
        "select": "title,DOI,published-print,published-online,author,URL,abstract"
    }

    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()

    records = []
    items = data.get("message", {}).get("items", [])

    for item in items:
        title_list = item.get("title", [])
        title = title_list[0] if title_list else ""

        year = ""
        for key in ["published-print", "published-online"]:
            parts = item.get(key, {}).get("date-parts", [])
            if parts and parts[0]:
                year = str(parts[0][0])
                break

        authors = []
        for a in item.get("author", []):
            name = " ".join([a.get("given", ""), a.get("family", "")]).strip()
            if name:
                authors.append(name)

        records.append(make_record(
            source="Crossref",
            title=title,
            year=year,
            abstract=item.get("abstract", ""),
            doi=item.get("DOI", ""),
            url=item.get("URL", ""),
            authors=authors,
        ))

    return records


def search_pubmed(query: str, limit: int):
    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

    search_params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": limit
    }

    r = requests.get(search_url, params=search_params, timeout=20)
    r.raise_for_status()
    data = r.json()

    ids = data.get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []

    summary_params = {
        "db": "pubmed",
        "id": ",".join(ids),
        "retmode": "json"
    }

    r2 = requests.get(summary_url, params=summary_params, timeout=20)
    r2.raise_for_status()
    summary = r2.json().get("result", {})

    records = []
    for pmid in ids:
        item = summary.get(pmid, {})
        title = item.get("title", "")
        year = str(item.get("pubdate", "")).split(" ")[0]
        authors = [a.get("name", "") for a in item.get("authors", []) if a.get("name")]
        records.append(make_record(
            source="PubMed",
            title=title,
            year=year,
            abstract="",
            doi="",
            url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            authors=authors,
        ))

    return records


def deduplicate_records(records):
    seen = set()
    unique = []

    for r in records:
        key = (r.get("doi") or r.get("title") or "").lower().strip()
        if not key:
            continue
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)

    return unique


def active_literature_search(queries, limit_per_source=5):
    all_records = []
    source_errors = []

    for q in queries:
        for source_name, func in [
            ("Semantic Scholar", search_semantic_scholar),
            ("Crossref", search_crossref),
            ("PubMed", search_pubmed),
        ]:
            try:
                records = func(q, limit_per_source)
                for r in records:
                    r["query"] = q
                all_records.extend(records)
            except Exception as e:
                source_errors.append({
                    "source": source_name,
                    "query": q,
                    "error": f"{type(e).__name__}: {e}"
                })

    return {
        "records": deduplicate_records(all_records),
        "source_errors": source_errors,
    }


def extract_numeric_material_candidates(records):
    """
    Bu fonksiyon literatür metninden açıkça görünen sayısal ifadeleri aday olarak yakalar.
    Nihai malzeme değeri üretmez.
    Sadece kaynakla ilişkilendirilmiş adayları kaydeder.
    """
    candidates = []

    elastic_patterns = [
        r"young'?s modulus[^.]{0,80}?(\d+(?:\.\d+)?)\s*(gpa|mpa)",
        r"elastic modulus[^.]{0,80}?(\d+(?:\.\d+)?)\s*(gpa|mpa)",
        r"\bE\s*=\s*(\d+(?:\.\d+)?)\s*(gpa|mpa)",
    ]

    poisson_patterns = [
        r"poisson'?s ratio[^.]{0,80}?(\d+(?:\.\d+)?)",
        r"\bnu\s*=\s*(0\.\d+)",
        r"\bν\s*=\s*(0\.\d+)",
    ]

    density_patterns = [
        r"density[^.]{0,80}?(\d+(?:\.\d+)?)\s*(kg/m3|kg/m\^3|g/cm3|g/cm\^3)",
    ]

    for r in records:
        text = " ".join([
            r.get("title", ""),
            r.get("abstract", ""),
        ])
        text_l = normalize_text(text)

        for pat in elastic_patterns:
            for m in re.finditer(pat, text_l):
                value = float(m.group(1))
                unit = m.group(2).lower()
                if unit == "gpa":
                    value = value * 1000.0
                candidates.append({
                    "property": "elastic_modulus_MPa",
                    "value": value,
                    "unit": "MPa",
                    "source_title": r.get("title", ""),
                    "source_doi": r.get("doi", ""),
                    "source_url": r.get("url", ""),
                })

        for pat in poisson_patterns:
            for m in re.finditer(pat, text_l):
                value = float(m.group(1))
                candidates.append({
                    "property": "poisson_ratio",
                    "value": value,
                    "unit": "",
                    "source_title": r.get("title", ""),
                    "source_doi": r.get("doi", ""),
                    "source_url": r.get("url", ""),
                })

        for pat in density_patterns:
            for m in re.finditer(pat, text_l):
                value = float(m.group(1))
                unit = m.group(2).lower()
                if unit in ["g/cm3", "g/cm^3"]:
                    value = value * 1000.0
                candidates.append({
                    "property": "density_kg_m3",
                    "value": value,
                    "unit": "kg/m3",
                    "source_title": r.get("title", ""),
                    "source_doi": r.get("doi", ""),
                    "source_url": r.get("url", ""),
                })

    return candidates


def summarize_literature_support(records_count: int, config: dict):
    policy = config.get("literature_search_policy", {})
    min_pass = int(policy.get("minimum_records_for_pass", 2))
    min_review = int(policy.get("minimum_records_for_review", 1))

    if records_count >= min_pass:
        return "candidate_literature_available"
    if records_count >= min_review:
        return "limited_literature_available"
    return "insufficient_literature"


def select_values_only_if_source_backed(candidates, records_count, config):
    """
    Kaynak destekli açık sayısal aday yoksa değer seçmez.
    Test/fallback değeri üretmez.
    """
    policy = config.get("literature_search_policy", {})
    min_pass = int(policy.get("minimum_records_for_pass", 2))

    result = {
        "elastic_modulus_MPa": None,
        "poisson_ratio": None,
        "density_kg_m3": None,
        "selected_sources": [],
        "selected_value_rationale": "No source-backed numerical material parameters were selected.",
        "uncertainty_level": "high",
        "can_pass": False,
    }

    if records_count < min_pass:
        result["selected_value_rationale"] = (
            "Literature record count is below the minimum required for pass."
        )
        return result

    by_property = {}
    for c in candidates:
        by_property.setdefault(c["property"], []).append(c)

    if "elastic_modulus_MPa" not in by_property:
        result["selected_value_rationale"] = (
            "Literature records were found, but no explicit source-backed elastic modulus value was extracted."
        )
        return result

    elastic_values = [x["value"] for x in by_property["elastic_modulus_MPa"]]
    selected_elastic = sorted(elastic_values)[len(elastic_values) // 2]

    result["elastic_modulus_MPa"] = round(float(selected_elastic), 6)

    if "poisson_ratio" in by_property:
        poisson_values = [x["value"] for x in by_property["poisson_ratio"] if 0.0 < x["value"] < 0.5]
        if poisson_values:
            selected_poisson = sorted(poisson_values)[len(poisson_values) // 2]
            result["poisson_ratio"] = round(float(selected_poisson), 6)

    if "density_kg_m3" in by_property:
        density_values = [x["value"] for x in by_property["density_kg_m3"]]
        if density_values:
            selected_density = sorted(density_values)[len(density_values) // 2]
            result["density_kg_m3"] = round(float(selected_density), 6)

    selected_sources = []
    for c in candidates:
        if c["property"] in ["elastic_modulus_MPa", "poisson_ratio", "density_kg_m3"]:
            selected_sources.append({
                "property": c["property"],
                "value": c["value"],
                "unit": c["unit"],
                "title": c["source_title"],
                "doi": c["source_doi"],
                "url": c["source_url"],
            })

    result["selected_sources"] = selected_sources[:10]

    if result["poisson_ratio"] is None:
        result["selected_value_rationale"] = (
            "Elastic modulus was source-backed, but Poisson ratio was not extracted. Human review is required."
        )
        result["uncertainty_level"] = "high"
        result["can_pass"] = False
        return result

    result["selected_value_rationale"] = (
        "Values were selected only from explicitly extracted, source-backed numerical candidates."
    )
    result["uncertainty_level"] = "medium"
    result["can_pass"] = True

    return result
