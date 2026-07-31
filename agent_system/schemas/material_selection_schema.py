from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


MaterialSelectionStatus = Literal[
    "MATERIAL_SELECTION_PASS",
    "MATERIAL_SELECTION_NEEDS_REVIEW",
    "MATERIAL_SELECTION_FAIL",
    "BLOCKED_BY_HUMAN_REVIEW"
]


class MaterialSelectionInput(BaseModel):
    case_id: str = Field(..., description="Analiz adı")
    target_understanding_json: Optional[str] = Field(default=None)
    segmentation_validation_json: Optional[str] = Field(default=None)
    human_review_json: Optional[str] = Field(default=None)
    max_records_per_source: int = Field(default=5)


class MaterialSelectionResult(BaseModel):
    case_id: str
    material_selection_status: MaterialSelectionStatus

    active_literature_search_required: bool
    literature_search_performed: bool
    literature_search_success: bool

    material_model: str
    selected_material_name: str
    anatomical_region: str
    material_domain: str
    tissue_assumption: str

    elastic_modulus_MPa: Optional[float] = None
    poisson_ratio: Optional[float] = None
    density_kg_m3: Optional[float] = None

    literature_query: List[str] = Field(default_factory=list)
    literature_support_level: str
    literature_records_count: int
    selected_sources: List[Dict[str, Any]] = Field(default_factory=list)

    selected_value_rationale: str
    uncertainty_level: str

    human_review_required: bool
    next_agent: str

    warnings: List[str] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)

    output_json: str
    property_table_csv: str
    literature_candidates_json: str
