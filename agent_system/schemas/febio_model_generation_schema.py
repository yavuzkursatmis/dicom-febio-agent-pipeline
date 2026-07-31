from pydantic import BaseModel, Field
from typing import List


class FebioModelGenerationInput(BaseModel):
    case_id: str
    volume_mesh_result_path: str = ""
    volume_mesh_path: str = ""
    material_law_package_path: str = ""
    reference_ct_path: str = ""
    material_bin_count: int = 20


class FebioModelGenerationResult(BaseModel):
    case_id: str
    febio_model_status: str
    next_agent: str

    volume_mesh_result_path: str = ""
    volume_mesh_path: str = ""
    material_law_package_path: str = ""
    reference_ct_path: str = ""

    volume_mesh_passed: bool = False
    material_law_validated: bool = False
    ct_read_success: bool = False

    febio_model_path: str = ""
    febio_model_created: bool = False

    node_count: int = 0
    tetra_count: int = 0
    material_bin_count: int = 0

    hu_min: float = 0.0
    hu_max: float = 0.0
    hu_mean: float = 0.0

    density_min_g_cm3: float = 0.0
    density_max_g_cm3: float = 0.0
    ez_min_mpa: float = 0.0
    ez_max_mpa: float = 0.0

    material_bins_csv: str = ""
    element_material_assignments_csv: str = ""

    solver_ready: bool = False
    boundary_conditions_included: bool = False
    loads_included: bool = False

    warnings: List[str] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)
