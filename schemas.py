from pydantic import BaseModel, EmailStr
from typing import Optional, List, Any
import datetime

# User & Auth
class UserLogin(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    role: str
    patient_id: Optional[int] = None
    department: Optional[str] = None

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

# Patient
class PatientOut(BaseModel):
    id: int
    mrn: str
    full_name: str
    dob: str
    gender: str
    blood_type: str
    phone: str
    email: str
    emergency_contact: str
    primary_physician: str
    allergies: List[str] = []
    chronic_conditions: List[str] = []
    active_status: str

    class Config:
        from_attributes = True

# Medical Report & Extracted Observations
class ObservationOut(BaseModel):
    id: int
    test_name: str
    raw_value: str
    numeric_value: Optional[float]
    unit: str
    reference_min: Optional[float]
    reference_max: Optional[float]
    reference_range_str: str
    flag: str
    source_excerpt: str
    page_number: int
    confidence_score: float

    class Config:
        from_attributes = True

class AIAnalysisOut(BaseModel):
    id: int
    summary_plain_text: str
    clinical_impressions: str
    potential_inconsistencies: List[str] = []
    missing_information: List[str] = []
    recommended_questions: List[str] = []
    reviewer_notes: str
    is_reviewed: bool
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime.datetime]

    class Config:
        from_attributes = True

class MedicalReportOut(BaseModel):
    id: int
    patient_id: int
    report_title: str
    report_type: str
    file_name: str
    file_size: int
    mime_type: str
    upload_date: datetime.datetime
    report_date: str
    file_availability_status: str
    ai_analysis_status: str
    failure_reason: Optional[str]
    observations: List[ObservationOut] = []
    analysis: Optional[AIAnalysisOut] = None

    class Config:
        from_attributes = True

# MedMismatch AI
class ConflictOut(BaseModel):
    id: int
    patient_id: int
    patient_name: Optional[str] = None
    patient_mrn: Optional[str] = None
    title: str
    category: str
    conflict_severity: str
    record_a_source: str
    record_a_text: str
    record_b_source: str
    record_b_text: str
    discrepancy_explanation: str
    status: str
    reviewer_notes: str
    reviewed_by: Optional[str]
    created_at: datetime.datetime
    resolved_at: Optional[datetime.datetime]

    class Config:
        from_attributes = True

class ConflictResolveRequest(BaseModel):
    status: str # CONFIRMED, DISMISSED, RESOLVED
    notes: Optional[str] = ""

# SilentSignal
class VitalRecordOut(BaseModel):
    id: int
    patient_id: int
    timestamp: datetime.datetime
    heart_rate: float
    systolic_bp: float
    diastolic_bp: float
    oxygen_saturation: float
    respiratory_rate: float
    temperature_c: float
    recorded_by: str

    class Config:
        from_attributes = True

class VitalAlertOut(BaseModel):
    id: int
    patient_id: int
    patient_name: Optional[str] = None
    patient_mrn: Optional[str] = None
    timestamp: datetime.datetime
    alert_type: str
    severity: str
    parameter_flagged: str
    trigger_value: str
    threshold_rule: str
    explanation: str
    status: str
    acknowledged_by: Optional[str]
    acknowledged_at: Optional[datetime.datetime]

    class Config:
        from_attributes = True

class VitalAlertAckRequest(BaseModel):
    status: str = "ACKNOWLEDGED"
    notes: Optional[str] = ""

# DoseGuard
class MedicationRecordOut(BaseModel):
    id: int
    patient_id: int
    drug_name: str
    dosage: str
    route: str
    frequency: str
    start_date: str
    end_date: str
    prescribing_doctor: str
    source_document: str
    status: str

    class Config:
        from_attributes = True

class MedicationFlagOut(BaseModel):
    id: int
    patient_id: int
    patient_name: Optional[str] = None
    patient_mrn: Optional[str] = None
    flag_type: str
    drug_a: str
    drug_b: str
    description: str
    evidence_excerpt: str
    severity: str
    status: str
    reviewer_notes: str
    resolved_by: Optional[str]
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class MedicationFlagResolveRequest(BaseModel):
    status: str # CONFIRMED, RESOLVED, DISMISSED
    notes: Optional[str] = ""

# LabLoop AI
class LabResultOut(BaseModel):
    id: int
    patient_id: int
    test_name: str
    category: str
    value: str
    unit: str
    reference_range: str
    is_critical: bool
    order_date: str
    result_date: str
    ordering_physician: str
    performing_lab: str

    class Config:
        from_attributes = True

class LabFollowUpOut(BaseModel):
    id: int
    lab_result_id: int
    patient_id: int
    patient_name: Optional[str] = None
    patient_mrn: Optional[str] = None
    test_name: Optional[str] = None
    value: Optional[str] = None
    unit: Optional[str] = None
    priority: str
    assigned_team: str
    required_action: str
    due_date: str
    status: str
    escalation_level: int
    audit_trail: List[Any] = []
    acknowledged_by: Optional[str]
    acknowledged_at: Optional[datetime.datetime]
    completed_at: Optional[datetime.datetime]

    class Config:
        from_attributes = True

class LabFollowUpUpdateRequest(BaseModel):
    status: str # ACKNOWLEDGED, COMPLETED, ESCALATED
    notes: Optional[str] = ""
    assigned_team: Optional[str] = None

# BedFlow
class BedRecordOut(BaseModel):
    id: int
    ward_name: str
    ward_type: str
    bed_number: str
    status: str
    patient_id: Optional[int]
    patient_name: Optional[str] = None
    admission_time: Optional[datetime.datetime]
    expected_discharge_time: Optional[datetime.datetime]
    notes: str

    class Config:
        from_attributes = True

class BedSimulationRequest(BaseModel):
    surge_percentage: float = 20.0
    discharge_delay_hours: float = 4.0
    staffing_level_pct: float = 90.0

class BedSimulationOut(BaseModel):
    baseline_occupancy: float
    projected_occupancy: float
    total_beds: int
    occupied_beds: int
    available_beds: int
    bottleneck_wards: List[dict]
    recommendations: List[str]

# ScanCompare
class ImagingSessionOut(BaseModel):
    id: int
    patient_id: int
    patient_name: Optional[str] = None
    scan_type: str
    prior_image_url: str
    current_image_url: str
    diff_image_url: Optional[str] = None
    prior_scan_date: str
    current_scan_date: str
    findings_notes: str
    difference_score: float
    alignment_status: str
    reviewer_notes: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True

# FollowUp Shield
class DischargeTaskOut(BaseModel):
    id: int
    discharge_plan_id: int
    patient_id: int
    task_title: str
    category: str
    due_date: str
    due_date_source: str
    priority: str
    status: str
    assigned_role: str
    notes: str
    patient_visible: bool

    class Config:
        from_attributes = True

class DischargePlanOut(BaseModel):
    id: int
    patient_id: int
    admission_date: str
    discharge_date: str
    primary_diagnosis: str
    summary_text: str
    tasks: List[DischargeTaskOut] = []

    class Config:
        from_attributes = True

class DischargeTaskUpdateRequest(BaseModel):
    status: str # PENDING, COMPLETED, OVERDUE
    notes: Optional[str] = ""

# Shared
class NotificationOut(BaseModel):
    id: int
    title: str
    message: str
    category: str
    severity: str
    is_read: bool
    link_url: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class DashboardMetricsOut(BaseModel):
    total_patients: int
    reports_uploaded: int
    reports_processing: int
    reports_action_required: int
    unresolved_conflicts: int
    active_vital_alerts: int
    active_med_flags: int
    pending_lab_followups: int
    bed_occupancy_pct: float
    occupied_beds: int
    total_beds: int
    pending_discharge_tasks: int
    recent_activity: List[dict]
    system_status: str = "OPERATIONAL"
