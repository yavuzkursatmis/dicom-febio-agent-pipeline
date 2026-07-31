from pydantic import BaseModel, Field
from typing import List, Optional


class GeometryPreparationInput(BaseModel):
    case_id: str
    segmentation_mask_path: Optional[str] = None
    material_law_package_path: Optional[str] = None


class GeometryPreparationResult(BaseModel):
    case_id: str
    geometry_status: str
    next_agent: str

    mask_path: str
    material_law_package_path: str

    mask_read_success: bool = False
    mask_is_empty: bool = True

    voxel_count: int = 0
    voxel_volume_mm3: float = 0.0
    object_volume_mm3: float = 0.0
    object_volume_cm3: float = 0.0

    spacing: List[float] = Field(default_factory=list)
    image_size: List[int] = Field(default_factory=list)

    surface_stl_path: str = ""
    surface_created: bool = False
    surface_vertices_count: int = 0
    surface_faces_count: int = 0
    surface_area_mm2: float = 0.0

    bounding_box_mm: List[float] = Field(default_factory=list)
    is_watertight: Optional[bool] = None
    euler_number: Optional[int] = None

    material_law_validated: bool = False

    warnings: List[str] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)
