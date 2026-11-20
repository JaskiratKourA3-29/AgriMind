"""
Decision Planning Agent for AgriMind (Week 5).
Converts diagnostic investigation and risk assessment findings into structured,
evidence-grounded management plans along the Integrated Pest Management (IPM) hierarchy.
"""
import uuid
from typing import Dict, Any, List, Optional

from src.agents.schemas import (
    InvestigationResult,
    RiskAssessmentResult,
    DecisionPlan,
    ManagementAction,
    PlanUrgency,
    SeverityLevel,
    EvidenceStatus
)
from src.agents.risk_assessment import MANDATORY_PESTICIDE_SAFETY_NOTICE


class DecisionPlanningAgent:
    """
    Generates structured, traceable agronomic management plans.
    Strictly aligns with the IPM hierarchy:
    Sanitation/Cultural -> Resistant Varieties -> Chemical/Biological -> Monitoring.
    """

    def plan_decision(
        self,
        investigation: InvestigationResult,
        risk: RiskAssessmentResult
    ) -> DecisionPlan:
        """
        Synthesizes an actionable DecisionPlan from investigation and risk results.
        """
        plan_id = f"PLN-{uuid.uuid4().hex[:8].upper()}"
        disease = investigation.primary_diagnosis
        severity = risk.assigned_severity
        status = investigation.evidence_status

        cultural_controls: List[ManagementAction] = []
        resistant_varieties: List[ManagementAction] = []
        chemical_controls: List[ManagementAction] = []
        monitoring_actions: List[ManagementAction] = []
        uncertainty_disclosures: List[str] = list(risk.uncertainty_factors)

        citations = investigation.citations
        citation_nums = [c.get("citation_number", 1) for c in citations] if citations else [1]

        # -------------------------------------------------------------
        # Case 0: Healthy Tomato Foliage
        # -------------------------------------------------------------
        if "healthy" in disease.lower():
            urgency = PlanUrgency.LOW
            expert_review_required = False
            uncertainty_disclosures.append(
                "Plant foliage appears healthy with no characteristic symptoms of Bacterial Spot, Early Blight, or Late Blight."
            )
            cultural_controls.append(
                ManagementAction(
                    category="cultural",
                    action_summary="Maintain balanced cultivation, drip irrigation, and canopy airflow",
                    details=(
                        "Continue standard agronomic practices. Use drip irrigation to keep foliage dry, "
                        "maintain adequate plant spacing for ventilation, and follow balanced N-P-K fertilization."
                    ),
                    is_chemical=False,
                    citation_numbers=[]
                )
            )
            monitoring_actions.append(
                ManagementAction(
                    category="monitoring",
                    action_summary="Routine weekly crop scouting",
                    details=(
                        "Inspect lower canopy leaves weekly, especially after rainfall or high humidity events, "
                        "to catch any early pathogen symptoms."
                    ),
                    is_chemical=False,
                    citation_numbers=[]
                )
            )
            return DecisionPlan(
                plan_id=plan_id,
                assessment_id=risk.assessment_id,
                investigation_id=investigation.investigation_id,
                disease=disease,
                urgency=urgency,
                cultural_controls=cultural_controls,
                resistant_varieties=resistant_varieties,
                chemical_controls=[],
                monitoring_actions=monitoring_actions,
                uncertainty_disclosures=uncertainty_disclosures,
                expert_review_required=expert_review_required,
                pesticide_safety_notice=None,
                citations=citations
            )

        # -------------------------------------------------------------
        # Case 1: Conflicting Evidence or Unsupported Disease
        # -------------------------------------------------------------
        if status in [EvidenceStatus.CONFLICTING, EvidenceStatus.UNSUPPORTED_DISEASE]:
            urgency = PlanUrgency.DEFERRED
            expert_review_required = True
            uncertainty_disclosures.append(
                "Diagnostic certainty is unverified. Automated chemical guidance is withheld pending physical expert review."
            )

            cultural_controls.append(
                ManagementAction(
                    category="cultural",
                    action_summary="Quarantine symptomatic plants and sanitize field equipment",
                    details=(
                        "Isolate affected rows where feasible. Clean and sanitize all pruning shears, stakes, "
                        "and footwear with 10% bleach or quaternary ammonium solution to prevent potential mechanical spread."
                    ),
                    is_chemical=False,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )
            monitoring_actions.append(
                ManagementAction(
                    category="monitoring",
                    action_summary="Submit fresh physical tissue samples to University Diagnostic Clinic",
                    details=(
                        "Collect 3-5 leaves showing transitional lesion margins, place in dry paper bag, "
                        "and submit immediately to your county agricultural extension diagnostic laboratory for microscopic/PCR confirmation."
                    ),
                    is_chemical=False,
                    citation_numbers=[]
                )
            )

            return DecisionPlan(
                plan_id=plan_id,
                assessment_id=risk.assessment_id,
                investigation_id=investigation.investigation_id,
                disease=disease,
                urgency=urgency,
                cultural_controls=cultural_controls,
                resistant_varieties=resistant_varieties,
                chemical_controls=chemical_controls,
                monitoring_actions=monitoring_actions,
                uncertainty_disclosures=uncertainty_disclosures,
                expert_review_required=expert_review_required,
                pesticide_safety_notice=None,
                citations=citations
            )

        # -------------------------------------------------------------
        # Determine Plan Urgency from Severity
        # -------------------------------------------------------------
        is_late_blight = "Late_blight" in disease
        is_early_blight = "Early_blight" in disease
        is_bacterial_spot = "Bacterial_spot" in disease
        is_septoria = "Septoria" in disease
        is_leaf_mold = "Leaf_Mold" in disease
        is_target_spot = "Target_Spot" in disease
        is_spider_mites = "Spider_mites" in disease
        is_mosaic_virus = "mosaic_virus" in disease
        is_tylcv = "Yellow_Leaf_Curl" in disease

        if severity == SeverityLevel.CRITICAL:
            urgency = PlanUrgency.CRITICAL
        elif severity == SeverityLevel.HIGH:
            urgency = PlanUrgency.HIGH
        elif severity == SeverityLevel.MODERATE:
            urgency = PlanUrgency.MODERATE
        elif severity == SeverityLevel.LOW:
            urgency = PlanUrgency.LOW
        else:  # INDETERMINATE
            if is_late_blight and risk.requires_immediate_action:
                urgency = PlanUrgency.HIGH
            else:
                urgency = PlanUrgency.MODERATE

        expert_review_required = risk.requires_human_expert_review

        # -------------------------------------------------------------
        # Disease-Specific Grounded Management Actions
        # -------------------------------------------------------------
        if is_late_blight:
            # 1. Cultural Controls
            cultural_controls.append(
                ManagementAction(
                    category="cultural",
                    action_summary="Immediate rogueing of initial hot-spot plants (Cornell Extension)",
                    details=(
                        "When initial hot-spot plants are detected, bag entire plants in plastic during dry, sunny midday, "
                        "cut at soil line, seal, and destroy to eliminate billions of airborne sporangia."
                    ),
                    is_chemical=False,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )
            cultural_controls.append(
                ManagementAction(
                    category="cultural",
                    action_summary="Eliminate volunteer solanaceous hosts and avoid overhead irrigation (UC IPM)",
                    details=(
                        "Destroy all volunteer potato and tomato plants and cull piles within 1 mile. "
                        "Irrigate exclusively via drip lines beneath plastic mulch to prevent canopy wetness."
                    ),
                    is_chemical=False,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )

            # 2. Resistant Varieties
            resistant_varieties.append(
                ManagementAction(
                    category="resistant_variety",
                    action_summary="Deploy dual-gene resistant cultivars (Ph-2 + Ph-3) (Cornell Extension)",
                    details=(
                        "Select cultivars carrying both Ph-2 and Ph-3 late blight resistance genes "
                        "(e.g., Iron Lady, Mountain Magic, Defiant PHR, Plum Regal) for future plantings."
                    ),
                    is_chemical=False,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )

            # 3. Chemical Controls (Fungicide Mode of Action strictly grounded)
            chemical_controls.append(
                ManagementAction(
                    category="chemical",
                    action_summary="Preventative broad-spectrum protectant barrier (UC IPM & Cornell)",
                    details=(
                        "Apply protectant fungicides (chlorothalonil, mancozeb, or fixed copper) on a strict 5-day schedule "
                        "during cool, overcast, rainy weather. Protectant sprays must be applied BEFORE infection occurs."
                    ),
                    is_chemical=True,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )
            chemical_controls.append(
                ManagementAction(
                    category="chemical",
                    action_summary="Targeted systemic oomycides with verified modes of action (Cornell Extension)",
                    details=(
                        "Where infection is suspected within 24-48 hours, apply Cymoxanil (Curzate) for post-infection "
                        "kickback activity (tank-mixed with a protectant fungicide per Cornell Extension). Apply Mandipropamid "
                        "(Revus) for preventative and anti-sporulant protection (Mandipropamid does NOT have curative kickback activity)."
                    ),
                    is_chemical=True,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )

            # 4. Monitoring & Scouting
            monitoring_actions.append(
                ManagementAction(
                    category="monitoring",
                    action_summary="Daily whole-planting scouting and national network tracking",
                    details=(
                        "Inspect leaf undersides daily in early morning for white cottony sporulation. "
                        "Track local epidemic occurrences via USABlight and notify regional extension specialists immediately."
                    ),
                    is_chemical=False,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )

        elif is_early_blight:
            # 1. Cultural Controls
            cultural_controls.append(
                ManagementAction(
                    category="cultural",
                    action_summary="Pruning, staking, and drip irrigation beneath mulch (Cornell & Purdue)",
                    details=(
                        "Prune lower 12-18 inches of foliage once fruit sets to eliminate ground contact. "
                        "Trellis plants to maximize airflow. Use drip irrigation beneath plastic mulch to prevent soil splashing."
                    ),
                    is_chemical=False,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )
            cultural_controls.append(
                ManagementAction(
                    category="cultural",
                    action_summary="Strict 2-3 year crop rotation with non-solanaceous crops (Purdue Extension)",
                    details=(
                        "Rotate fields out of tomatoes, potatoes, eggplants, and peppers for at least 2 to 3 years. "
                        "Deeply plow under or remove crop debris following harvest to bury overwintering fungal mycelium."
                    ),
                    is_chemical=False,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )

            # 2. Resistant Varieties
            resistant_varieties.append(
                ManagementAction(
                    category="resistant_variety",
                    action_summary="Utilize cultivars with documented tolerance (Purdue Extension)",
                    details=(
                        "Select early blight tolerant tomato cultivars (e.g., Mountain Supreme, Defiant PHR, Mountain Fresh Plus) "
                        "to slow foliar lesion expansion and delay defoliation."
                    ),
                    is_chemical=False,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )

            # 3. Chemical Controls
            chemical_controls.append(
                ManagementAction(
                    category="chemical",
                    action_summary="Preventative protectant fungicide application (Cornell & Purdue Extension)",
                    details=(
                        "Apply broad-spectrum protectant fungicides (chlorothalonil or mancozeb) starting at first lower-leaf lesions. "
                        "Repeat every 7 to 10 days during warm, humid conditions. Maintain complete coverage of lower canopy."
                    ),
                    is_chemical=True,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )

            # 4. Monitoring & Scouting
            monitoring_actions.append(
                ManagementAction(
                    category="monitoring",
                    action_summary="Twice-weekly canopy scouting for vertical progression",
                    details=(
                        "Scout lower leaves for expanding brown lesions with concentric bullseye rings surrounded by yellow halos. "
                        "Inspect stems for dark, sunken collar rot lesions and monitor fruit calyxes for black leathery rot."
                    ),
                    is_chemical=False,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )

        elif is_bacterial_spot:
            # 1. Cultural Controls
            cultural_controls.append(
                ManagementAction(
                    category="cultural",
                    action_summary="Avoid overhead irrigation and wet foliage contact (UF/IFAS Extension)",
                    details=(
                        "Bacteria spread mechanically via water droplets and equipment. Irrigate with drip systems. "
                        "Never work, cultivate, or harvest when foliage is wet with morning dew or rain."
                    ),
                    is_chemical=False,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )
            cultural_controls.append(
                ManagementAction(
                    category="cultural",
                    action_summary="Crop rotation and prompt crop residue destruction (UF/IFAS & UC IPM)",
                    details=(
                        "Rotate fields away from solanaceous hosts for a minimum of 1 year (2 years preferred). "
                        "Disk and bury crop residues immediately following final harvest to accelerate bacterial decomposition."
                    ),
                    is_chemical=False,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )

            # 2. Resistant Varieties
            resistant_varieties.append(
                ManagementAction(
                    category="resistant_variety",
                    action_summary="Certified pathogen-free seed and race-resistant varieties (UF/IFAS)",
                    details=(
                        "Plant only hot-water treated or certified disease-free seed. In transplant production, inspect "
                        "flats for water-soaked greasy specks and discard infected trays before field planting."
                    ),
                    is_chemical=False,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )

            # 3. Chemical Controls
            chemical_controls.append(
                ManagementAction(
                    category="chemical",
                    action_summary="Copper + Mancozeb tank mix or Actigard systemic inducer (UF/IFAS)",
                    details=(
                        "Apply fixed copper bactericides tank-mixed with mancozeb to overcome copper-tolerant bacterial strains. "
                        "Where systemic acquired resistance is recommended, apply Actigard (acibenzolar-S-methyl) according to label directions."
                    ),
                    is_chemical=True,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )

            # 4. Monitoring & Scouting
            monitoring_actions.append(
                ManagementAction(
                    category="monitoring",
                    action_summary="Routine foliar and fruit scouting after rain events",
                    details=(
                        "Inspect upper and lower leaf surfaces for small (1/8 inch), water-soaked, angular dark lesions. "
                        "Inspect green fruit for small, raised, brown blister-like scab lesions."
                    ),
                    is_chemical=False,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )

        elif is_septoria:
            # 1. Cultural Controls
            cultural_controls.append(
                ManagementAction(
                    category="cultural",
                    action_summary="Bottom-leaf pruning, mulching, and solanaceous weed eradication (Cornell Extension)",
                    details=(
                        "Prune lower 12-18 inches of foliage after fruit set. Mulch beds with clean straw or plastic to block rain-splashed "
                        "spores from soil. Eliminate horsenettle and solanaceous weed reservoirs within and around the field."
                    ),
                    is_chemical=False,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )
            cultural_controls.append(
                ManagementAction(
                    category="cultural",
                    action_summary="Strict 2-3 year crop rotation with non-solanaceous crops (Purdue Extension)",
                    details=(
                        "Rotate fields out of tomatoes and solanaceous crops for 2-3 years. Deeply plow or bury all crop debris "
                        "immediately after harvest to decompose overwintering pycnidia."
                    ),
                    is_chemical=False,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )

            # 2. Resistant Varieties
            resistant_varieties.append(
                ManagementAction(
                    category="resistant_variety",
                    action_summary="Select vigorous hybrids with strong foliar tolerance",
                    details=(
                        "Plant indeterminate, disease-tolerant hybrids with vigorous canopy development (e.g. Jasper, Iron Lady). "
                        "Avoid planting susceptible heirloom cultivars in fields with past Septoria history."
                    ),
                    is_chemical=False,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )

            # 3. Chemical Controls
            chemical_controls.append(
                ManagementAction(
                    category="chemical",
                    action_summary="Preventative broad-spectrum protectant fungicide (Cornell Extension)",
                    details=(
                        "Apply chlorothalonil, mancozeb, or copper hydroxide starting at first sighting of lower-canopy circular lesions. "
                        "Repeat at 7-10 day intervals during wet periods. Alternate with FRAC 11 (azoxystrobin) to manage resistance."
                    ),
                    is_chemical=True,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )

            # 4. Monitoring & Differential Diagnosis
            monitoring_actions.append(
                ManagementAction(
                    category="monitoring",
                    action_summary="Hand-lens examination for pycnidia; differentiate from Early Blight",
                    details=(
                        "Inspect lower leaves using 10x hand lens: Septoria shows small circular spots (1.5-3mm) with gray/tan centers and "
                        "tiny black specks (pycnidia). Unlike Early Blight, Septoria lesions lack large concentric bullseye target rings."
                    ),
                    is_chemical=False,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )

        elif is_leaf_mold:
            cultural_controls.append(
                ManagementAction(
                    category="cultural",
                    action_summary="Maximize canopy ventilation and keep relative humidity below 85%",
                    details="Increase spacing and vent tunnels. Avoid overhead watering to keep leaf surfaces dry.",
                    is_chemical=False,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )
            resistant_varieties.append(
                ManagementAction(
                    category="resistant_variety",
                    action_summary="Plant Cf-gene resistant tomato cultivars",
                    details="Deploy varieties bearing Cf-2, Cf-4, or Cf-9 resistance genes for greenhouse or high tunnel production.",
                    is_chemical=False,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )
            chemical_controls.append(
                ManagementAction(
                    category="chemical",
                    action_summary="Preventative copper or chlorothalonil foliar spray",
                    details="Apply protectant fungicides when persistent humidity exceeds 85% in closed structures.",
                    is_chemical=True,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )
            monitoring_actions.append(
                ManagementAction(
                    category="monitoring",
                    action_summary="Inspect leaf undersides for olive-brown velvety sporulation",
                    details="Check for corresponding chlorotic yellow patches on upper leaf surfaces.",
                    is_chemical=False,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )

        elif is_target_spot:
            cultural_controls.append(
                ManagementAction(
                    category="cultural",
                    action_summary="Improve canopy airflow and prune lower infected foliage",
                    details="Trellis plants and ensure adequate spacing. Remove lower symptomatic leaves to reduce inoculum.",
                    is_chemical=False,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )
            chemical_controls.append(
                ManagementAction(
                    category="chemical",
                    action_summary="Targeted fungicide spray (azoxystrobin or chlorothalonil)",
                    details="Apply protectant fungicides at first sign of circular necrotic lesions with subtle target rings.",
                    is_chemical=True,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )
            monitoring_actions.append(
                ManagementAction(
                    category="monitoring",
                    action_summary="Distinguish Target Spot from Early Blight and Septoria",
                    details="Target Spot lesions are typically 4-10mm with subtle concentric zonation but lack pycnidia (unlike Septoria).",
                    is_chemical=False,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )

        elif is_spider_mites:
            cultural_controls.append(
                ManagementAction(
                    category="cultural",
                    action_summary="Suppress dust on field borders and avoid broad-spectrum pyrethroids",
                    details="Water field perimeters to reduce dust. Avoid broad pyrethroids that destroy natural predatory mites.",
                    is_chemical=False,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )
            chemical_controls.append(
                ManagementAction(
                    category="chemical",
                    action_summary="Apply horticultural neem oil, insecticidal soap, or selective acaricides",
                    details="Spray neem oil or abamectin with thorough coverage of leaf undersides during early infestation.",
                    is_chemical=True,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )
            monitoring_actions.append(
                ManagementAction(
                    category="monitoring",
                    action_summary="Inspect leaf undersides for stippling, bronzing, and fine webbing",
                    details="Tap leaves over white paper to identify tiny moving spider mites.",
                    is_chemical=False,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )

        elif is_mosaic_virus:
            cultural_controls.append(
                ManagementAction(
                    category="cultural",
                    action_summary="Strict sanitation, hand washing with soap/milk, and rogueing",
                    details="Immediately remove and bag infected plants. Disinfect hands and tools; prohibit tobacco use near crop.",
                    is_chemical=False,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )
            resistant_varieties.append(
                ManagementAction(
                    category="resistant_variety",
                    action_summary="Deploy Tm-2 or Tm-2^2 virus-resistant hybrids",
                    details="Plant certified virus-free seed with genetic resistance to Tobacco/Tomato Mosaic Virus.",
                    is_chemical=False,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )
            monitoring_actions.append(
                ManagementAction(
                    category="monitoring",
                    action_summary="Scout for foliar mosaic mottling and shoestring leaf distortion",
                    details="Inspect young foliage for alternating dark and light green patterns.",
                    is_chemical=False,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )

        elif is_tylcv:
            cultural_controls.append(
                ManagementAction(
                    category="cultural",
                    action_summary="Install 50-mesh netting in nurseries and deploy yellow sticky traps",
                    details="Prevent whitefly (Bemisia tabaci) feeding. Rogue infected seedlings before transplanting.",
                    is_chemical=False,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )
            resistant_varieties.append(
                ManagementAction(
                    category="resistant_variety",
                    action_summary="Plant TYLCV-resistant hybrids carrying Ty-1 or Ty-3 genes",
                    details="Utilize modern commercial hybrids bred specifically with Tomato Yellow Leaf Curl Virus resistance.",
                    is_chemical=False,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )
            chemical_controls.append(
                ManagementAction(
                    category="chemical",
                    action_summary="Targeted vector control with neem-based azadirachtin or systemic insecticides",
                    details="Control whitefly populations early before virus inoculation occurs.",
                    is_chemical=True,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )
            monitoring_actions.append(
                ManagementAction(
                    category="monitoring",
                    action_summary="Monitor for upward cupping, severe chlorosis, and stunted growth",
                    details="Scout weekly for whiteflies on leaf undersides and early leaf cupping symptoms.",
                    is_chemical=False,
                    citation_numbers=citation_nums[:1] if citation_nums else []
                )
            )

        # Attach pesticide safety notice if chemical controls exist
        pesticide_notice = MANDATORY_PESTICIDE_SAFETY_NOTICE if chemical_controls else None

        return DecisionPlan(
            plan_id=plan_id,
            assessment_id=risk.assessment_id,
            investigation_id=investigation.investigation_id,
            disease=disease,
            urgency=urgency,
            cultural_controls=cultural_controls,
            resistant_varieties=resistant_varieties,
            chemical_controls=chemical_controls,
            monitoring_actions=monitoring_actions,
            uncertainty_disclosures=uncertainty_disclosures,
            expert_review_required=expert_review_required,
            pesticide_safety_notice=pesticide_notice,
            citations=citations
        )
