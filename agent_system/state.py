from typing import TypedDict, Any, Dict, List, Optional


class CaseState(TypedDict, total=False):
    case_id: str
    input_path: str
    anatomical_target: str
    analysis_type: str
    test_application_region: str
    user_notes_optional: str

    current_agent: str
    next_agent: str

    data_status: str
    detected_input_type: str
    file_count: int
    supported_format: bool
    data_intake_result: Dict[str, Any]

    safety_status: str
    dicom_file_count: int
    readable_dicom_count: int
    modality_detected: str
    is_ct: bool
    phi_risk_detected: bool
    burned_in_annotation_risk: bool
    dicom_safety_result: Dict[str, Any]

    image_quality_status: str
    series_read_success: bool
    slice_count: int
    image_size: str
    spacing: str
    slice_thickness: float
    voxel_anisotropy: float
    intensity_min: float
    intensity_max: float
    intensity_mean: float
    image_quality_result: Dict[str, Any]

    target_understanding_status: str
    standardized_anatomical_target: str
    segmentation_target: str
    standardized_analysis_type: str
    standardized_test_application_region: str
    load_region: str
    boundary_condition_hint: str
    confidence_level: str
    llm_confidence_level: str
    llm_human_review_required: bool
    human_review_required: bool
    llm_used: bool
    canonicalization_applied: bool
    validation_notes: List[str]
    target_understanding_result: Dict[str, Any]

    segmentation_status: str
    preprocessing_required: bool
    resampling_applied: bool
    original_spacing: str
    target_spacing: str
    resampled_spacing: str
    segmentation_mode: str
    segmentation_tool: str
    segmentation_mask_path: str
    raw_segmentation_output_dir: str
    segmentation_result: Dict[str, Any]

    segmentation_validation_status: str
    mask_exists: bool
    mask_read_success: bool
    mask_is_empty: bool
    mask_voxel_count: int
    mask_volume_cm3: float
    image_mask_size_match: bool
    image_mask_spacing_match: bool
    segmentation_validation_result: Dict[str, Any]

    human_review_status: str
    human_review_result: Dict[str, Any]

    material_selection_status: str
    active_literature_search_required: bool
    literature_search_performed: bool
    literature_search_success: bool
    literature_records_count: int
    material_domain: str
    material_model: str
    elastic_modulus_MPa: Optional[float]
    poisson_ratio: Optional[float]
    uncertainty_level: str
    material_selection_result: Dict[str, Any]

    material_review_status: str
    material_review_result: Dict[str, Any]

    material_review_approval_status: str
    material_review_approval_result: Dict[str, Any]

    warnings: List[str]
    blockers: List[str]
