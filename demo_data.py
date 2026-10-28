import os
import json
import datetime
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
import models
from auth import hash_password
from PIL import Image, ImageDraw, ImageFont
import numpy as np

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.join(BACKEND_DIR, "storage")
REPORTS_DIR = os.path.join(STORAGE_DIR, "reports")
SCANS_DIR = os.path.join(STORAGE_DIR, "scans")

os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(SCANS_DIR, exist_ok=True)

def generate_sample_scan_images():
    """Generates synthetic prior and current chest radiograph images for ScanCompare."""
    prior_path = os.path.join(SCANS_DIR, "chest_xray_prior_2025.png")
    current_path = os.path.join(SCANS_DIR, "chest_xray_current_2026.png")
    
    # 512x512 synthetic grayscale anatomical chest phantom
    if not os.path.exists(prior_path):
        img_prior = Image.new("L", (512, 512), color=18)
        draw = ImageDraw.Draw(img_prior)
        # Ribcage & thoracic outline
        draw.ellipse([80, 60, 432, 480], outline=110, width=8)
        # Spine
        draw.rectangle([244, 40, 268, 480], fill=90)
        # Left and Right Lung fields
        draw.ellipse([110, 100, 230, 420], fill=40, outline=90, width=3)
        draw.ellipse([282, 100, 402, 420], fill=40, outline=90, width=3)
        # Heart silhouette
        draw.ellipse([200, 240, 340, 410], fill=125, outline=160, width=4)
        # Clavicles & ribs
        draw.line([90, 120, 240, 150], fill=130, width=6)
        draw.line([272, 150, 422, 120], fill=130, width=6)
        for y in range(180, 400, 45):
            draw.arc([110, y, 235, y + 50], 190, 350, fill=85, width=4)
            draw.arc([277, y, 402, y + 50], 190, 350, fill=85, width=4)
        
        draw.text((20, 20), "SYNTHETIC CHEST PA - BASELINE (PREVIOUS)", fill=200)
        img_prior.save(prior_path)

    if not os.path.exists(current_path):
        img_curr = Image.new("L", (512, 512), color=18)
        draw = ImageDraw.Draw(img_curr)
        draw.ellipse([80, 60, 432, 480], outline=110, width=8)
        draw.rectangle([244, 40, 268, 480], fill=90)
        draw.ellipse([110, 100, 230, 420], fill=40, outline=90, width=3)
        draw.ellipse([282, 100, 402, 420], fill=40, outline=90, width=3)
        # Heart silhouette slightly enlarged (cardiomegaly)
        draw.ellipse([190, 230, 355, 420], fill=135, outline=170, width=4)
        draw.line([90, 120, 240, 150], fill=130, width=6)
        draw.line([272, 150, 422, 120], fill=130, width=6)
        for y in range(180, 400, 45):
            draw.arc([110, y, 235, y + 50], 190, 350, fill=85, width=4)
            draw.arc([277, y, 402, y + 50], 190, 350, fill=85, width=4)
        
        # New consolidation / infiltrate in right lower lung field
        draw.ellipse([130, 320, 220, 395], fill=115, outline=140, width=3)
        draw.text((20, 20), "SYNTHETIC CHEST PA - FOLLOW-UP (CURRENT)", fill=200)
        img_curr.save(current_path)

    return prior_path, current_path

def create_sample_pdf_report(file_path: str, title: str, patient_name: str, mrn: str, content: str):
    """Creates a synthetic text/report document on disk."""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"==========================================================\n")
        f.write(f"           MEDISPHERE HEALTH SYSTEM - CLINICAL REPORT     \n")
        f.write(f"==========================================================\n")
        f.write(f"DOCUMENT: {title}\n")
        f.write(f"PATIENT:  {patient_name}  |  MRN: {mrn}\n")
        f.write(f"DATE:     {datetime.date.today().strftime('%B %d, %Y')}\n")
        f.write(f"FACILITY: MediSphere University Medical Center, Metro Campus\n")
        f.write(f"----------------------------------------------------------\n\n")
        f.write(content)
        f.write(f"\n\n----------------------------------------------------------\n")
        f.write(f"Attending Reviewer: Dr. Sarah Jenkins, MD\n")
        f.write(f"Electronically signed at MediSphere Clinical Intelligence Core\n")
        f.write(f"NOTICE: Synthetic data for Hackathon demonstration only.\n")

def seed_database():
    """Initializes schema and seeds comprehensive demo data."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Check if already seeded
    if db.query(models.User).count() > 0:
        db.close()
        return

    print("Seeding MediSphere AI database with realistic synthetic records...")

    # 1. Create Patients
    p1 = models.Patient(
        mrn="MRN-8821",
        full_name="Elena Vance",
        dob="1978-04-12",
        gender="Female",
        blood_type="A+",
        phone="+1 (555) 234-8901",
        email="elena.vance@example.com",
        emergency_contact="Gordon Vance (Spouse) - +1 (555) 234-8902",
        primary_physician="Dr. Sarah Jenkins, MD",
        allergies_json=json.dumps(["Penicillin (Anaphylaxis)", "Sulfa Drugs"]),
        conditions_json=json.dumps(["Type 2 Diabetes Mellitus", "Essential Hypertension", "Mild Heart Failure"]),
        active_status="ACTIVE"
    )

    p2 = models.Patient(
        mrn="MRN-4190",
        full_name="Marcus Chen",
        dob="1964-11-23",
        gender="Male",
        blood_type="O+",
        phone="+1 (555) 876-5432",
        email="marcus.chen@example.com",
        emergency_contact="Linda Chen (Daughter) - +1 (555) 876-5433",
        primary_physician="Dr. Robert Hayes, MD",
        allergies_json=json.dumps(["Aspirin (Bronchospasm)"]),
        conditions_json=json.dumps(["Coronary Artery Disease", "Hyperlipidemia", "Chronic Kidney Disease Stage 2"]),
        active_status="ACTIVE"
    )

    p3 = models.Patient(
        mrn="MRN-9304",
        full_name="Sophia Rodriguez",
        dob="1992-07-19",
        gender="Female",
        blood_type="B+",
        phone="+1 (555) 432-1098",
        email="sophia.rodriguez@example.com",
        emergency_contact="Carlos Rodriguez - +1 (555) 432-1099",
        primary_physician="Dr. Sarah Jenkins, MD",
        allergies_json=json.dumps(["Latex"]),
        conditions_json=json.dumps(["Asthma", "Allergic Rhinitis"]),
        active_status="ACTIVE"
    )

    p4 = models.Patient(
        mrn="MRN-5512",
        full_name="David Kim",
        dob="1970-02-08",
        gender="Male",
        blood_type="AB-",
        phone="+1 (555) 654-9870",
        email="david.kim@example.com",
        emergency_contact="Hannah Kim - +1 (555) 654-9871",
        primary_physician="Dr. Robert Hayes, MD",
        allergies_json=json.dumps(["Iodinated Contrast Dye"]),
        conditions_json=json.dumps(["Chronic Kidney Disease Stage 3b", "Refractory Hypertension"]),
        active_status="ACTIVE"
    )

    db.add_all([p1, p2, p3, p4])
    db.commit()

    # 2. Create Users for all 5 roles
    default_hashed = hash_password("password123")
    users = [
        models.User(
            username="patient_elena",
            email="elena.vance@example.com",
            full_name="Elena Vance",
            role="PATIENT",
            hashed_password=default_hashed,
            patient_id=p1.id,
            department="Patient Portal"
        ),
        models.User(
            username="patient_marcus",
            email="marcus.chen@example.com",
            full_name="Marcus Chen",
            role="PATIENT",
            hashed_password=default_hashed,
            patient_id=p2.id,
            department="Patient Portal"
        ),
        models.User(
            username="dr_jenkins",
            email="sjenkins@medisphere.org",
            full_name="Dr. Sarah Jenkins, MD",
            role="DOCTOR",
            hashed_password=default_hashed,
            department="Internal Medicine & Cardiology"
        ),
        models.User(
            username="lab_tech_alex",
            email="arivera@medisphere.org",
            full_name="Alex Rivera, MLS",
            role="LAB_STAFF",
            hashed_password=default_hashed,
            department="Pathology & Clinical Laboratory"
        ),
        models.User(
            username="ops_jordan",
            email="jpatel@medisphere.org",
            full_name="Jordan Patel",
            role="OPERATIONS",
            hashed_password=default_hashed,
            department="Hospital Capacity & Patient Flow"
        ),
        models.User(
            username="admin",
            email="admin@medisphere.org",
            full_name="System Administrator",
            role="ADMIN",
            hashed_password=default_hashed,
            department="Clinical Informatics"
        ),
    ]
    db.add_all(users)
    db.commit()

    # 3. Create Sample Reports for Elena Vance (p1) and Marcus Chen (p2)
    rep1_file = os.path.join(REPORTS_DIR, "elena_vance_comprehensive_metabolic_panel.txt")
    rep1_content = """COMPREHENSIVE METABOLIC PANEL (CMP):
Fasting Blood Glucose: 114 mg/dL [Reference Range: 70 - 99 mg/dL] (ELEVATED)
Serum Creatinine: 1.05 mg/dL [Reference Range: 0.6 - 1.2 mg/dL] (NORMAL)
Potassium: 4.8 mEq/L [Reference Range: 3.5 - 5.1 mEq/L] (NORMAL)
Sodium: 139 mEq/L [Reference Range: 135 - 145 mEq/L] (NORMAL)
ALT (Alanine Aminotransferase): 38 U/L [Reference Range: 7 - 56 U/L] (NORMAL)
AST (Aspartate Aminotransferase): 32 U/L [Reference Range: 10 - 40 U/L] (NORMAL)
eGFR: 74 mL/min/1.73m2 [Reference: >60 mL/min/1.73m2]

CLINICAL COMMENT: Mild fasting hyperglycemia consistent with known Type 2 Diabetes management."""
    create_sample_pdf_report(rep1_file, "Comprehensive Metabolic Panel (CMP)", p1.full_name, p1.mrn, rep1_content)

    r1 = models.MedicalReport(
        patient_id=p1.id,
        report_title="Comprehensive Metabolic Panel (CMP)",
        report_type="LAB",
        file_name="elena_vance_comprehensive_metabolic_panel.txt",
        file_path=rep1_file,
        file_size=len(rep1_content),
        mime_type="text/plain",
        upload_date=datetime.datetime.utcnow() - datetime.timedelta(days=2),
        report_date=(datetime.date.today() - datetime.timedelta(days=2)).isoformat(),
        file_availability_status="AVAILABLE",
        ai_analysis_status="COMPLETED"
    )
    db.add(r1)
    db.commit()

    obs1 = [
        models.ExtractedObservation(report_id=r1.id, patient_id=p1.id, test_name="Fasting Blood Glucose", raw_value="114", numeric_value=114.0, unit="mg/dL", reference_min=70.0, reference_max=99.0, reference_range_str="70 - 99 mg/dL", flag="HIGH", source_excerpt="Fasting Blood Glucose: 114 mg/dL", page_number=1, confidence_score=0.98),
        models.ExtractedObservation(report_id=r1.id, patient_id=p1.id, test_name="Serum Creatinine", raw_value="1.05", numeric_value=1.05, unit="mg/dL", reference_min=0.6, reference_max=1.2, reference_range_str="0.6 - 1.2 mg/dL", flag="NORMAL", source_excerpt="Serum Creatinine: 1.05 mg/dL", page_number=1, confidence_score=0.99),
        models.ExtractedObservation(report_id=r1.id, patient_id=p1.id, test_name="Potassium", raw_value="4.8", numeric_value=4.8, unit="mEq/L", reference_min=3.5, reference_max=5.1, reference_range_str="3.5 - 5.1 mEq/L", flag="NORMAL", source_excerpt="Potassium: 4.8 mEq/L", page_number=1, confidence_score=0.97),
        models.ExtractedObservation(report_id=r1.id, patient_id=p1.id, test_name="Sodium", raw_value="139", numeric_value=139.0, unit="mEq/L", reference_min=135.0, reference_max=145.0, reference_range_str="135 - 145 mEq/L", flag="NORMAL", source_excerpt="Sodium: 139 mEq/L", page_number=1, confidence_score=0.97),
    ]
    db.add_all(obs1)

    ai1 = models.AIAnalysisResult(
        report_id=r1.id,
        patient_id=p1.id,
        summary_plain_text="Your metabolic panel results show stable renal function and normal electrolyte balance. Fasting glucose is mildly above target at 114 mg/dL, consistent with your ongoing diabetes management plan.",
        clinical_impressions="Stable renal parameters. Glycemic control stable but merits routine dietary check-in.",
        potential_inconsistencies_json=json.dumps([]),
        missing_information_json=json.dumps(["HbA1c correlation from this phlebotomy cycle not included in panel."]),
        recommended_questions_json=json.dumps([
            "Should we adjust the Metformin morning dose based on this fasting glucose level?",
            "When should my next routine HbA1c test be scheduled?"
        ]),
        is_reviewed=True,
        reviewed_by="Dr. Sarah Jenkins, MD",
        reviewed_at=datetime.datetime.utcnow() - datetime.timedelta(days=1)
    )
    db.add(ai1)

    # Report 2: Elena Vance CBC
    rep2_file = os.path.join(REPORTS_DIR, "elena_vance_cbc_differential.txt")
    rep2_content = """COMPLETE BLOOD COUNT (CBC):
Hemoglobin: 13.8 g/dL [Reference Range: 12.0 - 16.0 g/dL] (NORMAL)
WBC: 7.2 x10^3/uL [Reference Range: 4.0 - 11.0 x10^3/uL] (NORMAL)
Platelets: 260 x10^3/uL [Reference Range: 150 - 450 x10^3/uL] (NORMAL)
Hematocrit: 41.2% [Reference Range: 36.0 - 48.0%] (NORMAL)"""
    create_sample_pdf_report(rep2_file, "Complete Blood Count (CBC) with Diff", p1.full_name, p1.mrn, rep2_content)

    r2 = models.MedicalReport(
        patient_id=p1.id,
        report_title="Complete Blood Count (CBC) with Diff",
        report_type="LAB",
        file_name="elena_vance_cbc_differential.txt",
        file_path=rep2_file,
        file_size=len(rep2_content),
        mime_type="text/plain",
        upload_date=datetime.datetime.utcnow() - datetime.timedelta(days=14),
        report_date=(datetime.date.today() - datetime.timedelta(days=14)).isoformat(),
        file_availability_status="AVAILABLE",
        ai_analysis_status="COMPLETED"
    )
    db.add(r2)
    db.commit()

    obs2 = [
        models.ExtractedObservation(report_id=r2.id, patient_id=p1.id, test_name="Hemoglobin", raw_value="13.8", numeric_value=13.8, unit="g/dL", reference_min=12.0, reference_max=16.0, reference_range_str="12.0 - 16.0 g/dL", flag="NORMAL", source_excerpt="Hemoglobin: 13.8 g/dL", page_number=1, confidence_score=0.98),
        models.ExtractedObservation(report_id=r2.id, patient_id=p1.id, test_name="WBC", raw_value="7.2", numeric_value=7.2, unit="x10^3/uL", reference_min=4.0, reference_max=11.0, reference_range_str="4.0 - 11.0 x10^3/uL", flag="NORMAL", source_excerpt="WBC: 7.2 x10^3/uL", page_number=1, confidence_score=0.97),
        models.ExtractedObservation(report_id=r2.id, patient_id=p1.id, test_name="Platelets", raw_value="260", numeric_value=260.0, unit="x10^3/uL", reference_min=150.0, reference_max=450.0, reference_range_str="150 - 450 x10^3/uL", flag="NORMAL", source_excerpt="Platelets: 260 x10^3/uL", page_number=1, confidence_score=0.99),
    ]
    db.add_all(obs2)
    ai2 = models.AIAnalysisResult(
        report_id=r2.id,
        patient_id=p1.id,
        summary_plain_text="All red cell, white cell, and platelet counts are within normal reference ranges. No signs of anemia or infection.",
        clinical_impressions="Normal hematologic indices.",
        potential_inconsistencies_json=json.dumps([]),
        missing_information_json=json.dumps([]),
        recommended_questions_json=json.dumps(["Maintain standard follow-up schedule."]),
        is_reviewed=True,
        reviewed_by="Dr. Sarah Jenkins, MD",
        reviewed_at=datetime.datetime.utcnow() - datetime.timedelta(days=13)
    )
    db.add(ai2)

    # Report 3: Discharge Summary for Elena Vance (Under ACTION_REQUIRED status)
    rep3_file = os.path.join(REPORTS_DIR, "elena_vance_inpatient_discharge_summary.txt")
    rep3_content = """INPATIENT DISCHARGE SUMMARY:
Admission Date: October 18, 2026
Discharge Date: October 22, 2026
Primary Discharge Diagnosis: Acute decompensated heart failure with preserved ejection fraction (HFpEF).
Secondary Diagnoses: Type 2 Diabetes, Essential Hypertension.

HOSPITAL COURSE: Patient presented with worsening bilateral lower extremity edema and dyspnea on exertion. Treated with intravenous furosemide with brisk diuresis (total 4.2 kg fluid loss). Transitioned to oral torsemide 20mg daily.

DOCUMENTED POST-DISCHARGE CARE INSTRUCTIONS:
1. Schedule Outpatient Cardiology Follow-Up within 7 to 10 days (Target: November 01, 2026).
2. Repeat Basic Metabolic Panel (BMP) stat on Day 5 post-discharge to assess serum creatinine and potassium.
3. Daily morning weight check: Call clinic if weight increases by >3 lbs in 24 hours or >5 lbs in 1 week.
4. Dietary sodium restriction: < 2,000 mg/day. Fluid intake limit: 1.5 - 2.0 Liters/day.
5. Inpatient allergy record lists: 'No known allergies' (CAUTION: Contradicts chart allergy for Penicillin)."""
    create_sample_pdf_report(rep3_file, "Inpatient Discharge Summary", p1.full_name, p1.mrn, rep3_content)

    r3 = models.MedicalReport(
        patient_id=p1.id,
        report_title="Inpatient Discharge Summary - Heart Failure Unit",
        report_type="DISCHARGE",
        file_name="elena_vance_inpatient_discharge_summary.txt",
        file_path=rep3_file,
        file_size=len(rep3_content),
        mime_type="text/plain",
        upload_date=datetime.datetime.utcnow() - datetime.timedelta(days=4),
        report_date=(datetime.date.today() - datetime.timedelta(days=4)).isoformat(),
        file_availability_status="AVAILABLE",
        ai_analysis_status="COMPLETED"
    )
    db.add(r3)
    db.commit()

    ai3 = models.AIAnalysisResult(
        report_id=r3.id,
        patient_id=p1.id,
        summary_plain_text="Discharge summary following inpatient diuresis for heart failure. Documents specific follow-up appointments, mandatory 5-day lab check for electrolytes, daily weight tracking, and a noted record discrepancy regarding penicillin allergy.",
        clinical_impressions="High-risk post-discharge transition. Strict monitoring of renal function and weight required.",
        potential_inconsistencies_json=json.dumps([
            "Section 5 states 'No known allergies', which directly contradicts active chart documentation of Penicillin Anaphylaxis."
        ]),
        missing_information_json=json.dumps([
            "Specific outpatient cardiologist appointment time not finalized on discharge order."
        ]),
        recommended_questions_json=json.dumps([
            "Has the outpatient cardiology appointment been confirmed for next week?",
            "Do I have the lab requisition form ready for the 5-day electrolyte check?"
        ]),
        is_reviewed=False
    )
    db.add(ai3)

    # 4. MODULE 1: MedMismatch AI Conflicts
    conflicts = [
        models.ConflictRecord(
            patient_id=p1.id,
            title="Penicillin Allergy Status Discrepancy",
            category="ALLERGY",
            conflict_severity="HIGH",
            record_a_source="Inpatient Discharge Summary (Oct 22, 2026 - Line 14)",
            record_a_text="'Allergies: No Known Drug Allergies (NKDA)' recorded in hospital discharge header.",
            record_b_source="Patient Master Chart & EHR Registry (Recorded 2021)",
            record_b_text="'Penicillin: Severe Anaphylaxis with laryngeal edema requiring epinephrine (ICU admission 2021)'",
            discrepancy_explanation="Discharge summary lists patient as having NKDA, posing an extreme risk of inadvertent beta-lactam antibiotic prescription.",
            status="UNRESOLVED",
            reviewer_notes="",
            created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=6)
        ),
        models.ConflictRecord(
            patient_id=p1.id,
            title="Antihypertensive Medication Dosing Divergence",
            category="MEDICATION",
            conflict_severity="MEDIUM",
            record_a_source="Cardiology Outpatient Note (Sept 28, 2026)",
            record_a_text="'Continue Losartan 50 mg orally once daily in morning for hypertension.'",
            record_b_source="Emergency Admission Note (Oct 18, 2026)",
            record_b_text="'Patient states taking Losartan 100 mg orally once daily with Lisinopril 10 mg.'",
            discrepancy_explanation="Discrepancy in recorded daily Losartan dose (50 mg vs 100 mg) and possible dual ACE/ARB therapy reported at triage.",
            status="UNRESOLVED",
            reviewer_notes="",
            created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=18)
        ),
        models.ConflictRecord(
            patient_id=p2.id,
            title="Cardiac Stent Procedure Date Inconsistency",
            category="PROCEDURE",
            conflict_severity="LOW",
            record_a_source="Transfer Letter (St. Jude Medical)",
            record_a_text="'Drug-eluting stent placed in LAD in August 2023.'",
            record_b_source="Primary Care Baseline History",
            record_b_text="'Coronary angioplasty with stent documented as November 15, 2022.'",
            discrepancy_explanation="9-month discrepancy in documented date of stent placement affects required duration of dual antiplatelet therapy (DAPT).",
            status="CONFIRMED",
            reviewer_notes="Confirmed via cath lab imaging repository that stent was deployed November 2022.",
            reviewed_by="Dr. Sarah Jenkins, MD",
            created_at=datetime.datetime.utcnow() - datetime.timedelta(days=3),
            resolved_at=datetime.datetime.utcnow() - datetime.timedelta(days=1)
        )
    ]
    db.add_all(conflicts)

    # 5. MODULE 2: SilentSignal Vital Records & Alerts
    # Generate 24 hours of realistic vitals for Elena Vance
    base_time = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
    vital_points = [
        (72, 128, 82, 98, 16, 36.8),
        (74, 130, 84, 98, 16, 36.9),
        (78, 134, 86, 97, 17, 37.0),
        (82, 138, 88, 97, 17, 37.1),
        (85, 142, 90, 96, 18, 37.2),
        (90, 146, 92, 96, 18, 37.3),
        (96, 150, 94, 95, 19, 37.5),
        (102, 158, 96, 94, 20, 37.7),
        (110, 164, 98, 93, 22, 38.0), # Warning zone
        (118, 172, 102, 91, 24, 38.3), # Critical peak
        (114, 168, 100, 92, 23, 38.1),
        (105, 155, 95, 94, 21, 37.8),
        (98, 148, 92, 95, 20, 37.5),
        (92, 142, 88, 96, 19, 37.3),
        (88, 138, 86, 97, 18, 37.1),
        (84, 134, 84, 97, 17, 37.0),
        (80, 130, 82, 98, 16, 36.9),
        (78, 128, 80, 98, 16, 36.8),
        (76, 126, 80, 98, 16, 36.8),
        (75, 125, 80, 99, 15, 36.7),
        (74, 124, 78, 99, 15, 36.7),
        (72, 122, 78, 99, 15, 36.6),
        (72, 120, 76, 99, 14, 36.6),
        (70, 118, 76, 99, 14, 36.5),
    ]

    for i, (hr, sys, dia, spo2, rr, temp) in enumerate(vital_points):
        v = models.VitalRecord(
            patient_id=p1.id,
            timestamp=base_time + datetime.timedelta(hours=i),
            heart_rate=float(hr),
            systolic_bp=float(sys),
            diastolic_bp=float(dia),
            oxygen_saturation=float(spo2),
            respiratory_rate=float(rr),
            temperature_c=float(temp),
            recorded_by="Telemetry Ward Bed 304 Monitor"
        )
        db.add(v)

    vital_alerts = [
        models.VitalAlert(
            patient_id=p1.id,
            timestamp=base_time + datetime.timedelta(hours=9),
            alert_type="Multi-Parameter Early Warning Trigger (NEWS-2 > 7)",
            severity="CRITICAL",
            parameter_flagged="Heart Rate & SpO2 Desaturation",
            trigger_value="HR 118 bpm, SpO2 91%, RR 24/min",
            threshold_rule="Rule: HR > 110 AND SpO2 < 93% on room air indicates impending respiratory compromise",
            explanation="Simultaneous spike in cardiac rate with acute drops in oxygen saturation indicates possible fluid overload recurrence or pulmonary event.",
            status="ACTIVE"
        ),
        models.VitalAlert(
            patient_id=p1.id,
            timestamp=base_time + datetime.timedelta(hours=8),
            alert_type="Hypertensive Urgency Alert",
            severity="WARNING",
            parameter_flagged="Systolic Blood Pressure",
            trigger_value="BP 172/102 mmHg",
            threshold_rule="Rule: Systolic BP > 170 mmHg triggers nurse evaluation protocol",
            explanation="Systolic elevation sustained over 2 consecutive readings.",
            status="ACKNOWLEDGED",
            acknowledged_by="Dr. Sarah Jenkins, MD",
            acknowledged_at=datetime.datetime.utcnow() - datetime.timedelta(hours=14)
        )
    ]
    db.add_all(vital_alerts)

    # 6. MODULE 3: DoseGuard Medications & Flags
    meds = [
        models.MedicationRecord(
            patient_id=p1.id,
            drug_name="Torsemide",
            dosage="20 mg",
            route="Oral",
            frequency="Once daily in morning",
            start_date="2026-10-22",
            end_date="Ongoing",
            prescribing_doctor="Dr. Sarah Jenkins, MD",
            source_document="Discharge Medication Reconciliation",
            status="ACTIVE"
        ),
        models.MedicationRecord(
            patient_id=p1.id,
            drug_name="Losartan Potassium",
            dosage="50 mg",
            route="Oral",
            frequency="Once daily",
            start_date="2026-04-10",
            end_date="Ongoing",
            prescribing_doctor="Dr. Sarah Jenkins, MD",
            source_document="Outpatient Prescription Chart",
            status="ACTIVE"
        ),
        models.MedicationRecord(
            patient_id=p1.id,
            drug_name="Lisinopril",
            dosage="10 mg",
            route="Oral",
            frequency="Once daily",
            start_date="2026-10-18",
            end_date="Ongoing",
            prescribing_doctor="Dr. Kevin Miller, MD (Urgent Care)",
            source_document="Urgent Care Transfer Script",
            status="ACTIVE"
        ),
        models.MedicationRecord(
            patient_id=p1.id,
            drug_name="Metformin HCl",
            dosage="850 mg",
            route="Oral",
            frequency="Twice daily with meals",
            start_date="2025-01-15",
            end_date="Ongoing",
            prescribing_doctor="Dr. Sarah Jenkins, MD",
            source_document="Endocrinology Clinic Note",
            status="ACTIVE"
        ),
        models.MedicationRecord(
            patient_id=p1.id,
            drug_name="Potassium Chloride (K-Dur)",
            dosage="20 mEq",
            route="Oral",
            frequency="Once daily",
            start_date="2026-10-22",
            end_date="Ongoing",
            prescribing_doctor="Dr. Sarah Jenkins, MD",
            source_document="Discharge Orders",
            status="ACTIVE"
        )
    ]
    db.add_all(meds)

    med_flags = [
        models.MedicationFlag(
            patient_id=p1.id,
            flag_type="DUPLICATE_THERAPY",
            drug_a="Losartan Potassium 50 mg",
            drug_b="Lisinopril 10 mg",
            description="Dual Renin-Angiotensin-Aldosterone System (RAAS) Blockade: Concurrent Angiotensin Receptor Blocker (Losartan) and ACE Inhibitor (Lisinopril).",
            evidence_excerpt="Both agents active in EHR pharmacy record. Combination significantly elevates risk of acute hyperkalemia and renal failure without demonstrated mortality benefit.",
            severity="HIGH",
            status="UNRESOLVED",
            reviewer_notes="",
            created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=5)
        ),
        models.MedicationFlag(
            patient_id=p1.id,
            flag_type="INTERACTION",
            drug_a="Potassium Chloride 20 mEq",
            drug_b="Losartan + Lisinopril",
            description="Hyperkalemia Risk Potentiation: Supplemental potassium chloride combined with dual RAAS inhibition.",
            evidence_excerpt="Serum K+ currently 4.8 mEq/L. Risk of lethal cardiac arrhythmia if potassium supplementation continues alongside unadjusted dual inhibitors.",
            severity="HIGH",
            status="UNRESOLVED",
            reviewer_notes="",
            created_at=datetime.datetime.utcnow() - datetime.timedelta(hours=4)
        )
    ]
    db.add_all(med_flags)

    # 7. MODULE 4: LabLoop AI Critical Lab Follow-Up Tracking
    lab_res1 = models.LabResult(
        patient_id=p1.id,
        test_name="Serum Potassium (Stat Repeat)",
        category="Electrolytes",
        value="5.9",
        unit="mEq/L",
        reference_range="3.5 - 5.1 mEq/L",
        is_critical=True,
        order_date="2026-10-25 08:30",
        result_date="2026-10-25 09:15",
        ordering_physician="Dr. Sarah Jenkins, MD",
        performing_lab="Emergency Stat Chemistry Lab"
    )
    db.add(lab_res1)
    db.commit()

    followup1 = models.LabFollowUp(
        lab_result_id=lab_res1.id,
        patient_id=p1.id,
        priority="URGENT",
        assigned_team="Inpatient Cardiology / Renal Team",
        required_action="Verify repeat stat draw, discontinue potassium supplement immediately, obtain urgent 12-lead ECG to rule out peaked T waves.",
        due_date=(datetime.datetime.utcnow() + datetime.timedelta(hours=2)).strftime("%Y-%m-%d %H:%M"),
        status="PENDING",
        escalation_level=1,
        audit_trail_json=json.dumps([
            {"action": "CRITICAL_VALUE_FLAGGED", "timestamp": "2026-10-25 09:16", "user": "Alex Rivera, MLS"},
            {"action": "AUTOMATED_CARE_TEAM_PAGED", "timestamp": "2026-10-25 09:17", "system": "LabLoop AI Dispatch"},
            {"action": "ESCALATION_LEVEL_1_WARNING", "timestamp": "2026-10-25 09:45", "system": "LabLoop SLA Monitor"}
        ])
    )
    db.add(followup1)

    lab_res2 = models.LabResult(
        patient_id=p2.id,
        test_name="High-Sensitivity Cardiac Troponin I",
        category="Cardiac Biomarkers",
        value="0.68",
        unit="ng/mL",
        reference_range="< 0.04 ng/mL",
        is_critical=True,
        order_date="2026-10-24 14:00",
        result_date="2026-10-24 14:40",
        ordering_physician="Dr. Robert Hayes, MD",
        performing_lab="Central Cardiac Lab"
    )
    db.add(lab_res2)
    db.commit()

    followup2 = models.LabFollowUp(
        lab_result_id=lab_res2.id,
        patient_id=p2.id,
        priority="URGENT",
        assigned_team="Cardiology Acute Coronary Care",
        required_action="Immediate bedside clinical evaluation, serial ECGs at 0, 3, and 6 hours, initiation of acute coronary syndrome pathway.",
        due_date=(datetime.datetime.utcnow() - datetime.timedelta(hours=18)).strftime("%Y-%m-%d %H:%M"),
        status="ACKNOWLEDGED",
        escalation_level=0,
        audit_trail_json=json.dumps([
            {"action": "CRITICAL_RESULT_ENTERED", "timestamp": "2026-10-24 14:41", "user": "Alex Rivera, MLS"},
            {"action": "ACKNOWLEDGED_BY_PHYSICIAN", "timestamp": "2026-10-24 14:48", "user": "Dr. Robert Hayes, MD"}
        ]),
        acknowledged_by="Dr. Robert Hayes, MD",
        acknowledged_at=datetime.datetime.utcnow() - datetime.timedelta(hours=18)
    )
    db.add(followup2)

    # 8. MODULE 5: BedFlow Beds & Wards
    wards = [
        ("Intensive Care Unit (ICU)", "ICU", 12, 10, 1, 1),
        ("General Medicine A", "GENERAL_MED", 18, 14, 2, 2),
        ("General Medicine B", "GENERAL_MED", 18, 15, 2, 1),
        ("Surgical Stepdown", "SURGICAL", 16, 13, 2, 1),
        ("Emergency Short-Stay Observation", "EMERGENCY", 14, 11, 2, 1),
    ]

    bed_count = 1
    for ward_name, wtype, total, occ, clean, maint in wards:
        for i in range(1, total + 1):
            bed_num = f"{wtype[:3]}-{100 + i}"
            if i <= occ:
                status = "OCCUPIED"
                pat_id = p1.id if bed_num == "GEN-104" else (p2.id if bed_num == "ICU-102" else None)
                adm_time = datetime.datetime.utcnow() - datetime.timedelta(days=2, hours=i)
                disc_time = datetime.datetime.utcnow() + datetime.timedelta(days=1, hours=i)
            elif i <= occ + clean:
                status = "CLEANING"
                pat_id = None
                adm_time = None
                disc_time = None
            elif i <= occ + clean + maint:
                status = "MAINTENANCE"
                pat_id = None
                adm_time = None
                disc_time = None
            else:
                status = "AVAILABLE"
                pat_id = None
                adm_time = None
                disc_time = None

            b = models.BedRecord(
                ward_name=ward_name,
                ward_type=wtype,
                bed_number=bed_num,
                status=status,
                patient_id=pat_id,
                admission_time=adm_time,
                expected_discharge_time=disc_time,
                notes=f"Standard telemetry-equipped bed in {ward_name}."
            )
            db.add(b)

    # 9. MODULE 6: ScanCompare Imaging Sessions
    prior_scan, current_scan = generate_sample_scan_images()
    diff_scan = os.path.join(SCANS_DIR, "chest_xray_diff_annotated.png")

    img_session = models.ImagingSession(
        patient_id=p1.id,
        scan_type="CHEST_XRAY",
        prior_image_path=prior_scan,
        current_image_path=current_scan,
        diff_image_path=diff_scan,
        prior_scan_date="2025-10-15",
        current_scan_date="2026-10-20",
        findings_notes="Comparative radiograph analysis: Development of right lower lobe airspace opacification with increased bronchovascular markings, consistent with dependent consolidation vs resolving edema.",
        difference_score=14.8,
        alignment_status="ALIGNED",
        reviewer_notes="Interval focal density in right base flagged for clinical correlation with temperature and WBC count."
    )
    db.add(img_session)

    # 10. MODULE 7: FollowUp Shield Discharge Plan & Checklist
    dp = models.DischargePlan(
        patient_id=p1.id,
        admission_date="2026-10-18",
        discharge_date="2026-10-22",
        primary_diagnosis="Acute Decompensated Heart Failure (HFpEF)",
        discharge_summary_doc_id=r3.id,
        summary_text="Patient successfully diuresed and transitioned to oral maintenance loop diuretic. Outpatient follow-up and monitoring mandatory to avoid 30-day readmission."
    )
    db.add(dp)
    db.commit()

    tasks = [
        models.DischargeTask(
            discharge_plan_id=dp.id,
            patient_id=p1.id,
            task_title="In-Person Cardiology Follow-Up Appointment",
            category="APPOINTMENT",
            due_date=(datetime.date.today() + datetime.timedelta(days=6)).isoformat(),
            due_date_source="DOCUMENTED",
            priority="HIGH",
            status="PENDING",
            assigned_role="PATIENT",
            notes="Schedule with Dr. Sarah Jenkins at Heart Center Suite 400. Bring discharge medication list.",
            patient_visible=True
        ),
        models.DischargeTask(
            discharge_plan_id=dp.id,
            patient_id=p1.id,
            task_title="Basic Metabolic Panel (BMP) Blood Draw",
            category="LAB_TEST",
            due_date=(datetime.date.today() + datetime.timedelta(days=3)).isoformat(),
            due_date_source="DOCUMENTED",
            priority="HIGH",
            status="PENDING",
            assigned_role="CARE_COORDINATOR",
            notes="Stat electrolyte check (potassium and serum creatinine) post-initiation of oral Torsemide 20mg.",
            patient_visible=True
        ),
        models.DischargeTask(
            discharge_plan_id=dp.id,
            patient_id=p1.id,
            task_title="Daily Morning Weight Log (Prior to Breakfast)",
            category="LIFESTYLE",
            due_date="Daily",
            due_date_source="DOCUMENTED",
            priority="HIGH",
            status="PENDING",
            assigned_role="PATIENT",
            notes="Log weight daily. Call cardiology nurse line immediately if weight increases by > 3 lbs in 24 hours.",
            patient_visible=True
        ),
        models.DischargeTask(
            discharge_plan_id=dp.id,
            patient_id=p1.id,
            task_title="Medication Reconciliation and Allergy Verification",
            category="MEDICATION_RECONCILIATION",
            due_date=(datetime.date.today() + datetime.timedelta(days=2)).isoformat(),
            due_date_source="MANUALLY_ENTERED",
            priority="HIGH",
            status="PENDING",
            assigned_role="NURSE",
            notes="Resolve MedMismatch conflict regarding penicillin allergy and stop dual ACE/ARB overlap.",
            patient_visible=False
        ),
        models.DischargeTask(
            discharge_plan_id=dp.id,
            patient_id=p1.id,
            task_title="Dietary Sodium Restriction (< 2,000 mg/day) Adherence Check",
            category="LIFESTYLE",
            due_date=(datetime.date.today() + datetime.timedelta(days=5)).isoformat(),
            due_date_source="DOCUMENTED",
            priority="MEDIUM",
            status="COMPLETED",
            assigned_role="PATIENT",
            notes="Nutrition education package reviewed with clinical dietitian prior to discharge.",
            patient_visible=True
        )
    ]
    db.add_all(tasks)

    # 11. Cross-Cutting Notifications
    notifs = [
        models.Notification(
            role_target="DOCTOR",
            patient_id=p1.id,
            title="MedMismatch: Penicillin Allergy Conflict Detected",
            message="Discharge summary lists 'NKDA' while master record documents severe Penicillin Anaphylaxis.",
            category="CONFLICT",
            severity="CRITICAL",
            link_url="/conflicts"
        ),
        models.Notification(
            role_target="DOCTOR",
            patient_id=p1.id,
            title="DoseGuard: Duplicate RAAS Blockade Flagged",
            message="Concurrent prescriptions for Losartan 50mg and Lisinopril 10mg detected.",
            category="MEDICATION",
            severity="WARNING",
            link_url="/medications"
        ),
        models.Notification(
            role_target="LAB_STAFF",
            patient_id=p1.id,
            title="LabLoop: Stat Potassium 5.9 mEq/L Awaiting Escalation Action",
            message="Critical potassium value flagged in repeat draw. 12-lead ECG review required.",
            category="LAB",
            severity="CRITICAL",
            link_url="/labloop"
        ),
        models.Notification(
            role_target="OPERATIONS",
            patient_id=None,
            title="BedFlow: ICU Occupancy Alert at 83.3%",
            message="10 of 12 ICU beds occupied. Projected surge simulation suggests potential bottleneck within 12 hours.",
            category="BED",
            severity="WARNING",
            link_url="/bedflow"
        ),
        models.Notification(
            user_id=users[0].id, # Elena Vance
            role_target="PATIENT",
            patient_id=p1.id,
            title="Your Laboratory Report is Ready to View",
            message="Comprehensive Metabolic Panel (CMP) analysis is completed and available in My Reports.",
            category="REPORT",
            severity="INFO",
            link_url="/patient/reports"
        ),
        models.Notification(
            user_id=users[0].id, # Elena Vance
            role_target="PATIENT",
            patient_id=p1.id,
            title="Upcoming Care Task: 5-Day Electrolyte Blood Draw",
            message="Please complete your repeat lab check scheduled for this week.",
            category="FOLLOWUP",
            severity="WARNING",
            link_url="/patient/tasks"
        )
    ]
    db.add_all(notifs)

    # 12. Audit Logs
    audits = [
        models.AuditLog(username="system", action="DATABASE_SEEDED", entity_type="SYSTEM", details="Synthetic demo records seeded for Hackathon presentation."),
        models.AuditLog(username="dr_jenkins", action="VIEW_REPORT", entity_type="REPORT", entity_id=str(r1.id), details="Accessed CMP report for Elena Vance."),
        models.AuditLog(username="lab_tech_alex", action="LOG_CRITICAL_LAB", entity_type="LAB_RESULT", entity_id=str(lab_res1.id), details="Entered critical potassium 5.9 mEq/L."),
        models.AuditLog(username="patient_elena", action="LOGIN", entity_type="AUTH", details="Patient authenticated successfully into Patient Portal.")
    ]
    db.add_all(audits)

    db.commit()
    db.close()
    print("Database seeding completed successfully!")

if __name__ == "__main__":
    seed_database()
