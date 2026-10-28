import datetime
from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
)
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False) # PATIENT, DOCTOR, LAB_STAFF, OPERATIONS, ADMIN
    hashed_password = Column(String(200), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    department = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    patient = relationship("Patient", back_populates="user_account", foreign_keys=[patient_id])


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    mrn = Column(String(50), unique=True, index=True, nullable=False) # Medical Record Number e.g. MRN-7842
    full_name = Column(String(100), nullable=False)
    dob = Column(String(20), nullable=False)
    gender = Column(String(20), nullable=False)
    blood_type = Column(String(10), default="Unknown")
    phone = Column(String(30), default="")
    email = Column(String(100), default="")
    emergency_contact = Column(String(100), default="")
    primary_physician = Column(String(100), default="Dr. Sarah Jenkins, MD")
    allergies_json = Column(Text, default="[]") # JSON list of allergies
    conditions_json = Column(Text, default="[]") # JSON list of chronic conditions
    active_status = Column(String(20), default="ACTIVE")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user_account = relationship("User", back_populates="patient", uselist=False)
    reports = relationship("MedicalReport", back_populates="patient", cascade="all, delete-orphan")
    conflicts = relationship("ConflictRecord", back_populates="patient", cascade="all, delete-orphan")
    vitals = relationship("VitalRecord", back_populates="patient", cascade="all, delete-orphan")
    vital_alerts = relationship("VitalAlert", back_populates="patient", cascade="all, delete-orphan")
    medications = relationship("MedicationRecord", back_populates="patient", cascade="all, delete-orphan")
    medication_flags = relationship("MedicationFlag", back_populates="patient", cascade="all, delete-orphan")
    lab_results = relationship("LabResult", back_populates="patient", cascade="all, delete-orphan")
    lab_followups = relationship("LabFollowUp", back_populates="patient", cascade="all, delete-orphan")
    discharge_plans = relationship("DischargePlan", back_populates="patient", cascade="all, delete-orphan")
    imaging_sessions = relationship("ImagingSession", back_populates="patient", cascade="all, delete-orphan")


class MedicalReport(Base):
    __tablename__ = "medical_reports"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    report_title = Column(String(200), nullable=False)
    report_type = Column(String(50), default="LAB") # LAB, RADIOLOGY, DISCHARGE, PRESCRIPTION, CARDIOLOGY, CLINICAL_NOTE
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False) # Server-side private storage path
    file_size = Column(Integer, default=0) # bytes
    mime_type = Column(String(100), default="application/pdf")
    upload_date = Column(DateTime, default=datetime.datetime.utcnow)
    report_date = Column(String(50), default="") # extracted date from document
    file_availability_status = Column(String(30), default="AVAILABLE") # UPLOADED, PROCESSING, AVAILABLE, ACTION_REQUIRED, FAILED
    ai_analysis_status = Column(String(30), default="COMPLETED") # PENDING, PROCESSING, COMPLETED, FAILED
    failure_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    patient = relationship("Patient", back_populates="reports")
    observations = relationship("ExtractedObservation", back_populates="report", cascade="all, delete-orphan")
    analysis = relationship("AIAnalysisResult", back_populates="report", uselist=False, cascade="all, delete-orphan")


class ExtractedObservation(Base):
    __tablename__ = "extracted_observations"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("medical_reports.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    test_name = Column(String(150), nullable=False)
    raw_value = Column(String(100), nullable=False)
    numeric_value = Column(Float, nullable=True)
    unit = Column(String(50), default="")
    reference_min = Column(Float, nullable=True)
    reference_max = Column(Float, nullable=True)
    reference_range_str = Column(String(100), default="")
    flag = Column(String(30), default="NORMAL") # NORMAL, HIGH, LOW, CRITICAL_HIGH, CRITICAL_LOW, UNVERIFIED
    source_excerpt = Column(Text, default="")
    page_number = Column(Integer, default=1)
    confidence_score = Column(Float, default=0.95)

    report = relationship("MedicalReport", back_populates="observations")


class AIAnalysisResult(Base):
    __tablename__ = "ai_analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("medical_reports.id"), nullable=False, unique=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    summary_plain_text = Column(Text, nullable=False)
    clinical_impressions = Column(Text, default="")
    potential_inconsistencies_json = Column(Text, default="[]")
    missing_information_json = Column(Text, default="[]")
    recommended_questions_json = Column(Text, default="[]")
    reviewer_notes = Column(Text, default="")
    is_reviewed = Column(Boolean, default=False)
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    report = relationship("MedicalReport", back_populates="analysis")


# Module 1: MedMismatch AI (Medical Record Conflict Detection)
class ConflictRecord(Base):
    __tablename__ = "conflict_records"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    title = Column(String(200), nullable=False)
    category = Column(String(50), default="ALLERGY") # ALLERGY, MEDICATION, DIAGNOSIS, DATE, PROCEDURE
    conflict_severity = Column(String(20), default="HIGH") # HIGH, MEDIUM, LOW
    record_a_source = Column(String(200), nullable=False)
    record_a_text = Column(Text, nullable=False)
    record_b_source = Column(String(200), nullable=False)
    record_b_text = Column(Text, nullable=False)
    discrepancy_explanation = Column(Text, nullable=False)
    status = Column(String(30), default="UNRESOLVED") # UNRESOLVED, CONFIRMED, DISMISSED, RESOLVED
    reviewer_notes = Column(Text, default="")
    reviewed_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    patient = relationship("Patient", back_populates="conflicts")


# Module 2: SilentSignal (Vital Sign Pattern Monitoring)
class VitalRecord(Base):
    __tablename__ = "vital_records"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    heart_rate = Column(Float, nullable=False) # bpm
    systolic_bp = Column(Float, nullable=False) # mmHg
    diastolic_bp = Column(Float, nullable=False) # mmHg
    oxygen_saturation = Column(Float, nullable=False) # SpO2 %
    respiratory_rate = Column(Float, nullable=False) # breaths/min
    temperature_c = Column(Float, nullable=False) # deg C
    recorded_by = Column(String(100), default="Automated Bedside Monitor")

    patient = relationship("Patient", back_populates="vitals")


class VitalAlert(Base):
    __tablename__ = "vital_alerts"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    alert_type = Column(String(100), nullable=False)
    severity = Column(String(20), default="WARNING") # WARNING, CRITICAL
    parameter_flagged = Column(String(50), nullable=False)
    trigger_value = Column(String(50), nullable=False)
    threshold_rule = Column(String(150), nullable=False)
    explanation = Column(Text, nullable=False)
    status = Column(String(30), default="ACTIVE") # ACTIVE, ACKNOWLEDGED, RESOLVED
    acknowledged_by = Column(String(100), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)

    patient = relationship("Patient", back_populates="vital_alerts")


# Module 3: DoseGuard (Medication Schedule Conflict Detection)
class MedicationRecord(Base):
    __tablename__ = "medication_records"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    drug_name = Column(String(150), nullable=False)
    dosage = Column(String(100), nullable=False)
    route = Column(String(50), default="Oral")
    frequency = Column(String(100), nullable=False)
    start_date = Column(String(50), default="")
    end_date = Column(String(50), default="")
    prescribing_doctor = Column(String(100), default="Dr. Robert Hayes, MD")
    source_document = Column(String(200), default="Admission Chart")
    status = Column(String(30), default="ACTIVE") # ACTIVE, DISCONTINUED, COMPLETED

    patient = relationship("Patient", back_populates="medications")


class MedicationFlag(Base):
    __tablename__ = "medication_flags"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    flag_type = Column(String(50), default="DUPLICATE_THERAPY") # DUPLICATE_THERAPY, SCHEDULE_CONFLICT, DOSING_ANOMALY, INTERACTION
    drug_a = Column(String(150), nullable=False)
    drug_b = Column(String(150), default="")
    description = Column(Text, nullable=False)
    evidence_excerpt = Column(Text, default="")
    severity = Column(String(20), default="HIGH") # HIGH, MODERATE
    status = Column(String(30), default="UNRESOLVED") # UNRESOLVED, CONFIRMED, RESOLVED, DISMISSED
    reviewer_notes = Column(Text, default="")
    resolved_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    patient = relationship("Patient", back_populates="medication_flags")


# Module 4: LabLoop AI (Critical Laboratory Result Follow-Up Tracking)
class LabResult(Base):
    __tablename__ = "lab_results"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    test_name = Column(String(150), nullable=False)
    category = Column(String(100), default="Hematology")
    value = Column(String(50), nullable=False)
    unit = Column(String(50), default="")
    reference_range = Column(String(100), default="")
    is_critical = Column(Boolean, default=False)
    order_date = Column(String(50), default="")
    result_date = Column(String(50), default="")
    ordering_physician = Column(String(100), default="Dr. Sarah Jenkins, MD")
    performing_lab = Column(String(100), default="Central Pathology Lab")

    patient = relationship("Patient", back_populates="lab_results")
    followup = relationship("LabFollowUp", back_populates="lab_result", uselist=False, cascade="all, delete-orphan")


class LabFollowUp(Base):
    __tablename__ = "lab_followups"

    id = Column(Integer, primary_key=True, index=True)
    lab_result_id = Column(Integer, ForeignKey("lab_results.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    priority = Column(String(30), default="URGENT") # URGENT, HIGH, ROUTINE
    assigned_team = Column(String(100), default="Cardiology Care Team")
    required_action = Column(Text, nullable=False)
    due_date = Column(String(50), nullable=False)
    status = Column(String(30), default="PENDING") # PENDING, ACKNOWLEDGED, COMPLETED, ESCALATED
    escalation_level = Column(Integer, default=0) # 0=normal, 1=level 1, 2=level 2
    audit_trail_json = Column(Text, default="[]") # JSON array of audit events
    acknowledged_by = Column(String(100), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    patient = relationship("Patient", back_populates="lab_followups")
    lab_result = relationship("LabResult", back_populates="followup")


# Module 5: BedFlow (Hospital Bed Capacity and Flow Optimization)
class BedRecord(Base):
    __tablename__ = "bed_records"

    id = Column(Integer, primary_key=True, index=True)
    ward_name = Column(String(100), nullable=False)
    ward_type = Column(String(50), default="GENERAL_MED") # ICU, GENERAL_MED, SURGICAL, EMERGENCY, PEDIATRICS
    bed_number = Column(String(20), nullable=False)
    status = Column(String(30), default="AVAILABLE") # OCCUPIED, AVAILABLE, CLEANING, MAINTENANCE
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    admission_time = Column(DateTime, nullable=True)
    expected_discharge_time = Column(DateTime, nullable=True)
    notes = Column(Text, default="")


class BedSimulation(Base):
    __tablename__ = "bed_simulations"

    id = Column(Integer, primary_key=True, index=True)
    simulation_name = Column(String(150), nullable=False)
    baseline_occupancy = Column(Float, default=78.5)
    surge_percentage = Column(Float, default=15.0)
    discharge_delay_hours = Column(Float, default=4.0)
    projected_occupancy = Column(Float, default=94.2)
    bottleneck_wards_json = Column(Text, default="[]")
    recommendations_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


# Module 6: ScanCompare (Medical Imaging Change Comparison)
class ImagingSession(Base):
    __tablename__ = "imaging_sessions"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    scan_type = Column(String(100), default="CHEST_XRAY") # CHEST_XRAY, BRAIN_CT, KNEE_MRI
    prior_image_path = Column(String(500), nullable=False)
    current_image_path = Column(String(500), nullable=False)
    prior_scan_date = Column(String(50), default="")
    current_scan_date = Column(String(50), default="")
    findings_notes = Column(Text, default="")
    difference_score = Column(Float, default=0.0) # 0 to 100 percentage variation
    alignment_status = Column(String(50), default="ALIGNED") # ALIGNED, FALLBACK, UNALIGNED
    diff_image_path = Column(String(500), default="")
    reviewer_notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    patient = relationship("Patient", back_populates="imaging_sessions")


# Module 7: FollowUp Shield (Post-Discharge Care Gap Detection)
class DischargePlan(Base):
    __tablename__ = "discharge_plans"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    admission_date = Column(String(50), default="")
    discharge_date = Column(String(50), default="")
    primary_diagnosis = Column(String(200), default="")
    discharge_summary_doc_id = Column(Integer, ForeignKey("medical_reports.id"), nullable=True)
    summary_text = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    patient = relationship("Patient", back_populates="discharge_plans")
    tasks = relationship("DischargeTask", back_populates="discharge_plan", cascade="all, delete-orphan")


class DischargeTask(Base):
    __tablename__ = "discharge_tasks"

    id = Column(Integer, primary_key=True, index=True)
    discharge_plan_id = Column(Integer, ForeignKey("discharge_plans.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    task_title = Column(String(200), nullable=False)
    category = Column(String(50), default="APPOINTMENT") # APPOINTMENT, LAB_TEST, MEDICATION_RECONCILIATION, LIFESTYLE, RED_FLAG_MONITORING
    due_date = Column(String(50), default="")
    due_date_source = Column(String(50), default="DOCUMENTED") # DOCUMENTED, MANUALLY_ENTERED
    priority = Column(String(20), default="HIGH") # HIGH, MEDIUM
    status = Column(String(30), default="PENDING") # PENDING, COMPLETED, OVERDUE
    assigned_role = Column(String(50), default="PATIENT") # PATIENT, CARE_COORDINATOR, NURSE, PHYSICIAN
    notes = Column(Text, default="")
    patient_visible = Column(Boolean, default=True)

    discharge_plan = relationship("DischargePlan", back_populates="tasks")


# Shared Cross-Cutting Records
class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True) # None = all users with role_target
    role_target = Column(String(30), default="ALL") # ALL, PATIENT, DOCTOR, LAB_STAFF, OPERATIONS, ADMIN
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    category = Column(String(50), default="REPORT") # REPORT, CONFLICT, VITAL, MEDICATION, LAB, BED, FOLLOWUP
    severity = Column(String(20), default="INFO") # INFO, WARNING, CRITICAL
    is_read = Column(Boolean, default=False)
    link_url = Column(String(255), default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class ReviewDecision(Base):
    __tablename__ = "review_decisions"

    id = Column(Integer, primary_key=True, index=True)
    item_type = Column(String(50), nullable=False) # CONFLICT, VITAL_ALERT, MED_FLAG, LAB_FOLLOWUP, DISCHARGE_TASK, REPORT_ANALYSIS
    item_id = Column(Integer, nullable=False)
    decision = Column(String(50), nullable=False) # CONFIRMED, DISMISSED, RESOLVED, OVERRIDDEN
    decision_notes = Column(Text, default="")
    decided_by = Column(String(100), nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)
    username = Column(String(100), default="system")
    action = Column(String(100), nullable=False) # LOGIN, VIEW_REPORT, DOWNLOAD_REPORT, UPLOAD_REPORT, RESOLVE_CONFLICT, ACK_ALERT
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(50), default="")
    ip_address = Column(String(50), default="127.0.0.1")
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    details = Column(Text, default="")
