from pydantic import BaseModel, Field
from typing import List


class BoundaryLoadConfigurationInput(BaseModel):
    case_id: str
    febio_model_result_path: str = ""
    febio_model_path: str = ""
    volume_mesh_path: str = ""
    endplate_band_fraction: float = 0.08
    development_engineering_strain: float = 0.005
    prescribed_displacement_mm: float = 0.0
    load_protocol_path: str = ""


class BoundaryLoadConfigurationResult(BaseModel):
    case_id: str
    boundary_load_status: str
    next_agent: str

    febio_model_result_path: str = ""
    febio_model_base_path: str = ""
    febio_model_boundary_candidate_path: str = ""
    volume_mesh_path: str = ""

    febio_model_generation_passed: bool = False
    base_model_read_success: bool = False
    mesh_read_success: bool = False

    analysis_type: str = ""
    load_region: str = ""
    fixed_region: str = "inferior_endplate"

    z_min_mm: float = 0.0
    z_max_mm: float = 0.0
    height_mm: float = 0.0

    endplate_band_fraction: float = 0.0
    inferior_threshold_z_mm: float = 0.0
    superior_threshold_z_mm: float = 0.0

    fixed_node_count: int = 0
    loaded_node_count: int = 0

    prescribed_displacement_mm: float = 0.0
    load_protocol_path: str = ""
    development_engineering_strain: float = 0.0
    load_magnitude_source: str = ""

    node_sets_csv: str = ""
    boundary_candidate_created: bool = False
    solver_ready: bool = False
    human_review_required: bool = True

    warnings: List[str] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)

