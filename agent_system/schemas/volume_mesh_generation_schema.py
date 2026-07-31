from pydantic import BaseModel, Field
from typing import List


class VolumeMeshGenerationInput(BaseModel):
    case_id: str
    geometry_result_path: str = ""
    surface_stl_path: str = ""
    gmsh_exe_path: str = ""
    mesh_size_min: float = 0.75
    mesh_size_max: float = 3.0


class VolumeMeshGenerationResult(BaseModel):
    case_id: str
    volume_mesh_status: str
    next_agent: str

    geometry_result_path: str = ""
    surface_stl_path: str = ""
    gmsh_exe_path: str = ""

    gmsh_run_success: bool = False
    gmsh_template_used: str = ""
    gmsh_return_code: int = -1
    gmsh_stdout_path: str = ""
    gmsh_stderr_path: str = ""

    volume_mesh_path: str = ""
    volume_mesh_vtk_path: str = ""
    mesh_created: bool = False

    node_count: int = 0
    tetra_count: int = 0
    triangle_count: int = 0

    tetra_volume_min_mm3: float = 0.0
    tetra_volume_max_mm3: float = 0.0
    tetra_volume_mean_mm3: float = 0.0
    tetra_volume_total_mm3: float = 0.0
    tetra_volume_total_cm3: float = 0.0

    edge_length_min_mm: float = 0.0
    edge_length_max_mm: float = 0.0
    edge_length_mean_mm: float = 0.0
    simple_aspect_ratio_max: float = 0.0
    simple_aspect_ratio_mean: float = 0.0

    material_law_validated: bool = False
    geometry_passed: bool = False

    warnings: List[str] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)
