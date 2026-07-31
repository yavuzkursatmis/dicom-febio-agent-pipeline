# Agent-07B — General Tissue Material Extractor Design

## Purpose

Agent-07B extracts material property candidates from academic/scientific literature records obtained by Agent-07.

This agent is not limited to vertebra or bone.

## Core rule

Manual material value entry is not allowed in the final pipeline.

The system must derive material candidates from literature text, tables, abstracts, PDFs, or structured metadata.

The human reviewer may only approve, reject, or request more literature search.

## Inputs

- case_id
- Agent-07 MATERIAL_SELECTION_RESULT.json
- Agent-07 MATERIAL_LITERATURE_CANDIDATES.json
- material_domain from Agent-07
- anatomical_region from Agent-07
- analysis_type from Agent-04 / Agent-07
- candidate literature records

## Supported material domains

Initial supported domains:

- bone
- cartilage
- tendon
- ligament
- muscle
- soft_tissue
- implant_material
- unknown_requires_review

The system must not hard-code vertebra as the only supported target.

## Supported material model families

Agent-07B must be able to search for candidate parameters for:

1. linear_elastic_isotropic
   - elastic_modulus_MPa
   - poisson_ratio

2. orthotropic_linear_elastic
   - E1 / E2 / E3
   - nu12 / nu23 / nu13
   - G12 / G23 / G13

3. hyperelastic
   - Neo-Hookean parameters
   - Mooney-Rivlin parameters
   - Ogden parameters

4. viscoelastic
   - relaxation modulus
   - Prony series parameters
   - time constants

5. density_based_heterogeneous
   - density
   - density-modulus relation
   - HU-density relation
   - density-elastic modulus relation

6. implant_material
   - elastic modulus
   - poisson ratio
   - yield strength
   - density
   - fatigue/corrosion notes when available

## Domain-specific search logic

Agent-07B may use domain-specific keyword profiles, but it must not restrict analysis to one anatomical region.

Examples:

bone:
- cortical bone
- cancellous bone
- trabecular bone
- vertebral bone
- elastic modulus
- Poisson ratio
- finite element

cartilage:
- articular cartilage
- aggregate modulus
- compressive modulus
- Poisson ratio
- biphasic
- hyperelastic

tendon:
- tendon
- Young modulus
- tensile modulus
- viscoelastic
- stress relaxation

ligament:
- ligament
- tensile modulus
- nonlinear elastic
- viscoelastic
- toe region

muscle:
- skeletal muscle
- passive muscle
- hyperelastic
- Ogden
- Mooney-Rivlin

soft_tissue:
- soft tissue
- hyperelastic
- viscoelastic
- shear modulus

implant_material:
- titanium
- tantalum
- Ti6Al4V
- elastic modulus
- Poisson ratio
- density

## Extraction policy

Agent-07B must extract only source-linked values.

For every candidate value, it must record:

- candidate_id
- material_domain
- anatomical_region
- material_model_family
- property_name
- value
- unit
- normalized_value
- normalized_unit
- source_title
- source_doi
- source_url
- context_excerpt
- extraction_method
- confidence_score
- uncertainty_level
- clinical_use = false

## Decision rules

If no source-linked candidate is found:
- status = MATERIAL_CANDIDATE_EXTRACTION_NEEDS_MORE_EVIDENCE
- next_agent = HUMAN_REVIEW_GATE or USER_ACTION_REQUIRED
- no geometry allowed

If candidates are found:
- status = MATERIAL_CANDIDATES_AVAILABLE_FOR_REVIEW
- next_agent = HUMAN_REVIEW_GATE
- no geometry allowed until reviewer approves one candidate_id

If reviewer approves a valid agent-derived candidate_id:
- Approval Validator may allow GEOMETRY_AGENT

## Forbidden behavior

Agent-07B must not:

- assign fallback material values
- assign test/default values
- ask the user to manually type elastic modulus or Poisson ratio
- assume bone-only behavior
- pass GEOMETRY_AGENT without source-linked candidate approval
- silently convert uncertain values into final parameters

## Human role

The human reviewer may:

- approve an agent-derived candidate
- reject an agent-derived candidate
- request more literature
- request a different material model family

The human reviewer must not manually create material values.
