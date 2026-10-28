import os
import json
import uuid
import datetime
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

import models
import schemas
from database import get_db, engine, Base
from auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, require_role
)
from ai_service import AIService
from demo_data import STORAGE_DIR, REPORTS_DIR, SCANS_DIR, seed_database

# Initialize FastAPI app
app = FastAPI(
    title="MediSphere AI API",
    description="Integrated Healthcare Intelligence and Patient Report Management Platform",
    version="1.0.0"
)

# Enable CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure database tables exist
Base.metadata.create_all(bind=engine)

@app.on_event("startup")
def on_startup():
    """Ensure database connection and automatic seeding if fresh."""
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    try:
        user_count = db.query(models.User).count()
        if user_count == 0:
            print("Database empty: Auto-seeding initial synthetic clinical data...")
            seed_database()
        print(f"MediSphere AI connected to database successfully ({user_count} users present).")
    except Exception as e:
        print(f"Database startup check warning: {e}")
    finally:
        db.close()

# Health Check
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "MediSphere AI Clinical Intelligence Core",
        "database": "connected",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "modules_active": [
            "MedMismatch AI", "SilentSignal", "DoseGuard",
            "LabLoop AI", "BedFlow", "ScanCompare",
            "FollowUp Shield", "MediReport AI"
        ]
    }

# Dedicated Database Connectivity & Diagnostics
@app.get("/api/db/status")
def database_status(db: Session = Depends(get_db)):
    try:
        from database import test_connection, DATABASE_URL
        is_ok, msg = test_connection()
        user_count = db.query(models.User).count()
        patient_count = db.query(models.Patient).count()
        report_count = db.query(models.MedicalReport).count()
        conflict_count = db.query(models.ConflictRecord).count()
        vital_count = db.query(models.VitalRecord).count()
        bed_count = db.query(models.BedRecord).count()
        lab_count = db.query(models.LabFollowUp).count()

        db_type = "SQLite" if "sqlite" in DATABASE_URL.lower() else "PostgreSQL/MySQL"

        return {
            "status": "connected" if is_ok else "error",
            "message": msg,
            "database_type": db_type,
            "connection_url_masked": DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL,
            "tables_online": 20,
            "records": {
                "users": user_count,
                "patients": patient_count,
                "medical_reports": report_count,
                "conflict_records": conflict_count,
                "vital_records": vital_count,
                "bed_records": bed_count,
                "lab_followups": lab_count,
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


# ==============================================================================
# AUTHENTICATION & DEMO USERS
# ==============================================================================
@app.post("/api/auth/login", response_model=schemas.TokenResponse)
def login(creds: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == creds.username).first()
    if not user or not verify_password(creds.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    token = create_access_token({"sub": user.username, "role": user.role, "user_id": user.id})
    
    # Audit log
    audit = models.AuditLog(
        user_id=user.id,
        username=user.username,
        action="LOGIN",
        entity_type="AUTH",
        details=f"User {user.username} logged in with role {user.role}"
    )
    db.add(audit)
    db.commit()

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }

@app.get("/api/auth/me", response_model=schemas.UserOut)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user

@app.get("/api/auth/demo-users")
def get_demo_users(db: Session = Depends(get_db)):
    users = db.query(models.User).all()
    return [
        {
            "username": u.username,
            "full_name": u.full_name,
            "role": u.role,
            "department": u.department,
            "patient_id": u.patient_id,
            "demo_password": "password123"
        }
        for u in users
    ]

# ==============================================================================
# PATIENTS REGISTRY
# ==============================================================================
@app.get("/api/patients")
def list_patients(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Patient role can only see their own profile
    if current_user.role == "PATIENT":
        patient = db.query(models.Patient).filter(models.Patient.id == current_user.patient_id).first()
        if not patient:
            return []
        p_dict = patient.__dict__.copy()
        p_dict["allergies"] = json.loads(patient.allergies_json or "[]")
        p_dict["chronic_conditions"] = json.loads(patient.conditions_json or "[]")
        return [p_dict]

    # Clinical/Admin roles see all patients
    patients = db.query(models.Patient).all()
    results = []
    for p in patients:
        p_dict = p.__dict__.copy()
        p_dict["allergies"] = json.loads(p.allergies_json or "[]")
        p_dict["chronic_conditions"] = json.loads(p.conditions_json or "[]")
        results.append(p_dict)
    return results

@app.get("/api/patients/{id}")
def get_patient(
    id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Enforce patient ownership check
    if current_user.role == "PATIENT" and current_user.patient_id != id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Patients may only access their own records"
        )
    
    p = db.query(models.Patient).filter(models.Patient.id == id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    p_dict = p.__dict__.copy()
    p_dict["allergies"] = json.loads(p.allergies_json or "[]")
    p_dict["chronic_conditions"] = json.loads(p.conditions_json or "[]")
    return p_dict

# ==============================================================================
# MEDICAL REPORTS & MEDIREPORT AI
# ==============================================================================
@app.get("/api/reports")
def list_reports(
    patient_id: Optional[int] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.MedicalReport)
    
    # Ownership filtering
    if current_user.role == "PATIENT":
        query = query.filter(models.MedicalReport.patient_id == current_user.patient_id)
    elif patient_id:
        query = query.filter(models.MedicalReport.patient_id == patient_id)

    reports = query.order_by(models.MedicalReport.upload_date.desc()).all()
    
    results = []
    for r in reports:
        r_dict = {
            "id": r.id,
            "patient_id": r.patient_id,
            "report_title": r.report_title,
            "report_type": r.report_type,
            "file_name": r.file_name,
            "file_size": r.file_size,
            "mime_type": r.mime_type,
            "upload_date": r.upload_date.isoformat() if r.upload_date else "",
            "report_date": r.report_date,
            "file_availability_status": r.file_availability_status,
            "ai_analysis_status": r.ai_analysis_status,
            "failure_reason": r.failure_reason,
            "patient_name": r.patient.full_name if r.patient else "Unknown",
            "patient_mrn": r.patient.mrn if r.patient else "",
            "observations_count": len(r.observations),
            "has_analysis": r.analysis is not None
        }
        results.append(r_dict)
    return results

@app.get("/api/reports/{id}")
def get_report_detail(
    id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    r = db.query(models.MedicalReport).filter(models.MedicalReport.id == id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Medical report not found")
    
    # Backend ownership check
    if current_user.role == "PATIENT" and r.patient_id != current_user.patient_id:
        raise HTTPException(status_code=403, detail="Access denied to this patient report")
    
    observations = [
        {
            "id": obs.id,
            "test_name": obs.test_name,
            "raw_value": obs.raw_value,
            "numeric_value": obs.numeric_value,
            "unit": obs.unit,
            "reference_min": obs.reference_min,
            "reference_max": obs.reference_max,
            "reference_range_str": obs.reference_range_str,
            "flag": obs.flag,
            "source_excerpt": obs.source_excerpt,
            "page_number": obs.page_number,
            "confidence_score": obs.confidence_score
        }
        for obs in r.observations
    ]

    analysis_data = None
    if r.analysis:
        analysis_data = {
            "id": r.analysis.id,
            "summary_plain_text": r.analysis.summary_plain_text,
            "clinical_impressions": r.analysis.clinical_impressions,
            "potential_inconsistencies": json.loads(r.analysis.potential_inconsistencies_json or "[]"),
            "missing_information": json.loads(r.analysis.missing_information_json or "[]"),
            "recommended_questions": json.loads(r.analysis.recommended_questions_json or "[]"),
            "reviewer_notes": r.analysis.reviewer_notes,
            "is_reviewed": r.analysis.is_reviewed,
            "reviewed_by": r.analysis.reviewed_by,
            "reviewed_at": r.analysis.reviewed_at.isoformat() if r.analysis.reviewed_at else None
        }

    return {
        "id": r.id,
        "patient_id": r.patient_id,
        "patient_name": r.patient.full_name if r.patient else "",
        "patient_mrn": r.patient.mrn if r.patient else "",
        "report_title": r.report_title,
        "report_type": r.report_type,
        "file_name": r.file_name,
        "file_size": r.file_size,
        "mime_type": r.mime_type,
        "upload_date": r.upload_date.isoformat() if r.upload_date else "",
        "report_date": r.report_date,
        "file_availability_status": r.file_availability_status,
        "ai_analysis_status": r.ai_analysis_status,
        "failure_reason": r.failure_reason,
        "observations": observations,
        "analysis": analysis_data
    }

@app.get("/api/reports/{id}/file")
def download_original_report(
    id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    r = db.query(models.MedicalReport).filter(models.MedicalReport.id == id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Ownership guard
    if current_user.role == "PATIENT" and r.patient_id != current_user.patient_id:
        raise HTTPException(status_code=403, detail="Unauthorized access to patient file")
    
    if not os.path.exists(r.file_path):
        raise HTTPException(status_code=404, detail="File not found in persistent private storage")
    
    # Audit log
    audit = models.AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        action="DOWNLOAD_REPORT",
        entity_type="REPORT",
        entity_id=str(r.id),
        details=f"Downloaded original report {r.file_name}"
    )
    db.add(audit)
    db.commit()

    return FileResponse(
        path=r.file_path,
        filename=r.file_name,
        media_type=r.mime_type
    )

@app.post("/api/reports/upload")
async def upload_medical_report(
    file: UploadFile = File(...),
    patient_id: int = Form(...),
    report_title: str = Form(...),
    report_type: str = Form("LAB"),
    report_date: str = Form(""),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Ownership check for patient role
    if current_user.role == "PATIENT" and current_user.patient_id != patient_id:
        raise HTTPException(status_code=403, detail="Patients cannot upload documents on behalf of other patients")

    # File validation
    allowed_extensions = [".pdf", ".txt", ".png", ".jpg", ".jpeg", ".csv", ".json"]
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Unsupported file format. Allowed: {allowed_extensions}")

    # Generate unique private storage filename
    unique_name = f"{uuid.uuid4().hex[:12]}_{file.filename}"
    saved_path = os.path.join(REPORTS_DIR, unique_name)

    # Read and save file content
    contents = await file.read()
    with open(saved_path, "wb") as f:
        f.write(contents)

    file_size = len(contents)
    date_str = report_date or datetime.date.today().isoformat()

    # Create persistent DB record with state UPLOADED -> PROCESSING
    report_rec = models.MedicalReport(
        patient_id=patient_id,
        report_title=report_title,
        report_type=report_type,
        file_name=file.filename,
        file_path=saved_path,
        file_size=file_size,
        mime_type=file.content_type or "application/octet-stream",
        upload_date=datetime.datetime.utcnow(),
        report_date=date_str,
        file_availability_status="AVAILABLE",
        ai_analysis_status="PROCESSING"
    )
    db.add(report_rec)
    db.commit()
    db.refresh(report_rec)

    # Run MediReport AI extraction
    try:
        raw_text = AIService.extract_text_from_file(saved_path, report_rec.mime_type)
        parsed = AIService.parse_medical_report(raw_text, report_title)

        # Store observations
        for obs_item in parsed["observations"]:
            obs = models.ExtractedObservation(
                report_id=report_rec.id,
                patient_id=patient_id,
                test_name=obs_item["test_name"],
                raw_value=obs_item["raw_value"],
                numeric_value=obs_item["numeric_value"],
                unit=obs_item["unit"],
                reference_min=obs_item["reference_min"],
                reference_max=obs_item["reference_max"],
                reference_range_str=obs_item["reference_range_str"],
                flag=obs_item["flag"],
                source_excerpt=obs_item["source_excerpt"],
                page_number=obs_item["page_number"],
                confidence_score=obs_item["confidence_score"]
            )
            db.add(obs)

        # Store AI Analysis
        ai_res = models.AIAnalysisResult(
            report_id=report_rec.id,
            patient_id=patient_id,
            summary_plain_text=parsed["summary_plain_text"],
            clinical_impressions=parsed["clinical_impressions"],
            potential_inconsistencies_json=json.dumps(parsed["potential_inconsistencies"]),
            missing_information_json=json.dumps(parsed["missing_information"]),
            recommended_questions_json=json.dumps(parsed["recommended_questions"]),
            is_reviewed=False
        )
        db.add(ai_res)

        report_rec.ai_analysis_status = "COMPLETED"

        # Check for critical lab value to link with LabLoop AI
        for obs_item in parsed["observations"]:
            if obs_item["flag"] in ["CRITICAL_HIGH", "CRITICAL_LOW"]:
                lab_rec = models.LabResult(
                    patient_id=patient_id,
                    test_name=obs_item["test_name"],
                    category=report_type,
                    value=obs_item["raw_value"],
                    unit=obs_item["unit"],
                    reference_range=obs_item["reference_range_str"],
                    is_critical=True,
                    order_date=datetime.date.today().isoformat(),
                    result_date=datetime.date.today().isoformat(),
                    ordering_physician="Attending Physician",
                    performing_lab="MediSphere Diagnostic Core"
                )
                db.add(lab_rec)
                db.commit()

                followup = models.LabFollowUp(
                    lab_result_id=lab_rec.id,
                    patient_id=patient_id,
                    priority="URGENT",
                    assigned_team="Attending Clinical Team",
                    required_action=f"Auto-generated LabLoop task: Physician review required for critical {obs_item['test_name']} value {obs_item['raw_value']} {obs_item['unit']}.",
                    due_date=(datetime.datetime.utcnow() + datetime.timedelta(hours=4)).strftime("%Y-%m-%d %H:%M"),
                    status="PENDING",
                    audit_trail_json=json.dumps([{"action": "AUTO_TRIGGER_FROM_MEDIREPORT", "timestamp": datetime.datetime.utcnow().isoformat()}])
                )
                db.add(followup)

        # Create in-app notification
        patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
        pname = patient.full_name if patient else "Patient"
        notif = models.Notification(
            role_target="DOCTOR",
            patient_id=patient_id,
            title=f"New Report Uploaded: {report_title}",
            message=f"{pname} uploaded {report_title}. AI extraction and reference verification completed.",
            category="REPORT",
            severity="INFO",
            link_url=f"/patient/reports"
        )
        db.add(notif)
        db.commit()

    except Exception as e:
        report_rec.ai_analysis_status = "FAILED"
        report_rec.failure_reason = str(e)
        db.commit()

    return {"status": "SUCCESS", "report_id": report_rec.id, "message": "Report uploaded and processed successfully"}

# ==============================================================================
# MODULE 1: MEDMISMATCH AI
# ==============================================================================
@app.get("/api/modules/mismatch")
def get_conflicts(
    patient_id: Optional[int] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.ConflictRecord)
    if current_user.role == "PATIENT":
        query = query.filter(models.ConflictRecord.patient_id == current_user.patient_id)
    elif patient_id:
        query = query.filter(models.ConflictRecord.patient_id == patient_id)

    conflicts = query.order_by(models.ConflictRecord.created_at.desc()).all()
    results = []
    for c in conflicts:
        results.append({
            "id": c.id,
            "patient_id": c.patient_id,
            "patient_name": c.patient.full_name if c.patient else "",
            "patient_mrn": c.patient.mrn if c.patient else "",
            "title": c.title,
            "category": c.category,
            "conflict_severity": c.conflict_severity,
            "record_a_source": c.record_a_source,
            "record_a_text": c.record_a_text,
            "record_b_source": c.record_b_source,
            "record_b_text": c.record_b_text,
            "discrepancy_explanation": c.discrepancy_explanation,
            "status": c.status,
            "reviewer_notes": c.reviewer_notes,
            "reviewed_by": c.reviewed_by,
            "created_at": c.created_at.isoformat() if c.created_at else "",
            "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None
        })
    return results

@app.post("/api/modules/mismatch/{id}/resolve")
def resolve_conflict(
    id: int,
    req: schemas.ConflictResolveRequest,
    current_user: models.User = Depends(require_role(["DOCTOR", "ADMIN"])),
    db: Session = Depends(get_db)
):
    c = db.query(models.ConflictRecord).filter(models.ConflictRecord.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Conflict record not found")
    
    c.status = req.status
    c.reviewer_notes = req.notes or c.reviewer_notes
    c.reviewed_by = current_user.full_name
    c.resolved_at = datetime.datetime.utcnow()

    # Log review decision
    decision = models.ReviewDecision(
        item_type="CONFLICT",
        item_id=c.id,
        decision=req.status,
        decision_notes=req.notes or "",
        decided_by=current_user.full_name
    )
    db.add(decision)
    db.commit()

    return {"status": "SUCCESS", "message": f"Conflict updated to {req.status}"}

# ==============================================================================
# MODULE 2: SILENTSIGNAL
# ==============================================================================
@app.get("/api/modules/vitals/{patient_id}")
def get_vitals(
    patient_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role == "PATIENT" and current_user.patient_id != patient_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    records = db.query(models.VitalRecord).filter(
        models.VitalRecord.patient_id == patient_id
    ).order_by(models.VitalRecord.timestamp.asc()).all()

    alerts = db.query(models.VitalAlert).filter(
        models.VitalAlert.patient_id == patient_id
    ).order_by(models.VitalAlert.timestamp.desc()).all()

    return {
        "vitals": [
            {
                "id": v.id,
                "timestamp": v.timestamp.strftime("%H:%M") if v.timestamp else "",
                "heart_rate": v.heart_rate,
                "systolic_bp": v.systolic_bp,
                "diastolic_bp": v.diastolic_bp,
                "oxygen_saturation": v.oxygen_saturation,
                "respiratory_rate": v.respiratory_rate,
                "temperature_c": v.temperature_c,
                "recorded_by": v.recorded_by
            }
            for v in records
        ],
        "alerts": [
            {
                "id": a.id,
                "timestamp": a.timestamp.isoformat() if a.timestamp else "",
                "alert_type": a.alert_type,
                "severity": a.severity,
                "parameter_flagged": a.parameter_flagged,
                "trigger_value": a.trigger_value,
                "threshold_rule": a.threshold_rule,
                "explanation": a.explanation,
                "status": a.status,
                "acknowledged_by": a.acknowledged_by,
                "acknowledged_at": a.acknowledged_at.isoformat() if a.acknowledged_at else None
            }
            for a in alerts
        ]
    }

@app.post("/api/modules/vitals/alerts/{id}/ack")
def acknowledge_vital_alert(
    id: int,
    current_user: models.User = Depends(require_role(["DOCTOR", "ADMIN"])),
    db: Session = Depends(get_db)
):
    a = db.query(models.VitalAlert).filter(models.VitalAlert.id == id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    a.status = "ACKNOWLEDGED"
    a.acknowledged_by = current_user.full_name
    a.acknowledged_at = datetime.datetime.utcnow()
    db.commit()

    return {"status": "SUCCESS", "message": "Vital sign alert acknowledged"}

# ==============================================================================
# MODULE 3: DOSEGUARD
# ==============================================================================
@app.get("/api/modules/doseguard/{patient_id}")
def get_medications(
    patient_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role == "PATIENT" and current_user.patient_id != patient_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    meds = db.query(models.MedicationRecord).filter(
        models.MedicationRecord.patient_id == patient_id
    ).all()

    flags = db.query(models.MedicationFlag).filter(
        models.MedicationFlag.patient_id == patient_id
    ).all()

    return {
        "medications": [
            {
                "id": m.id,
                "drug_name": m.drug_name,
                "dosage": m.dosage,
                "route": m.route,
                "frequency": m.frequency,
                "start_date": m.start_date,
                "end_date": m.end_date,
                "prescribing_doctor": m.prescribing_doctor,
                "source_document": m.source_document,
                "status": m.status
            }
            for m in meds
        ],
        "flags": [
            {
                "id": f.id,
                "flag_type": f.flag_type,
                "drug_a": f.drug_a,
                "drug_b": f.drug_b,
                "description": f.description,
                "evidence_excerpt": f.evidence_excerpt,
                "severity": f.severity,
                "status": f.status,
                "reviewer_notes": f.reviewer_notes,
                "resolved_by": f.resolved_by,
                "created_at": f.created_at.isoformat() if f.created_at else ""
            }
            for f in flags
        ]
    }

@app.post("/api/modules/doseguard/flags/{id}/resolve")
def resolve_med_flag(
    id: int,
    req: schemas.MedicationFlagResolveRequest,
    current_user: models.User = Depends(require_role(["DOCTOR", "ADMIN"])),
    db: Session = Depends(get_db)
):
    f = db.query(models.MedicationFlag).filter(models.MedicationFlag.id == id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Medication flag not found")
    
    f.status = req.status
    f.reviewer_notes = req.notes or f.reviewer_notes
    f.resolved_by = current_user.full_name
    db.commit()

    return {"status": "SUCCESS", "message": f"Medication flag updated to {req.status}"}

# ==============================================================================
# MODULE 4: LABLOOP AI
# ==============================================================================
@app.get("/api/modules/labloop")
def get_lab_followups(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.LabFollowUp)
    if current_user.role == "PATIENT":
        query = query.filter(models.LabFollowUp.patient_id == current_user.patient_id)
    
    followups = query.all()
    results = []
    for f in followups:
        results.append({
            "id": f.id,
            "lab_result_id": f.lab_result_id,
            "patient_id": f.patient_id,
            "patient_name": f.patient.full_name if f.patient else "",
            "patient_mrn": f.patient.mrn if f.patient else "",
            "test_name": f.lab_result.test_name if f.lab_result else "",
            "value": f.lab_result.value if f.lab_result else "",
            "unit": f.lab_result.unit if f.lab_result else "",
            "reference_range": f.lab_result.reference_range if f.lab_result else "",
            "priority": f.priority,
            "assigned_team": f.assigned_team,
            "required_action": f.required_action,
            "due_date": f.due_date,
            "status": f.status,
            "escalation_level": f.escalation_level,
            "audit_trail": json.loads(f.audit_trail_json or "[]"),
            "acknowledged_by": f.acknowledged_by,
            "acknowledged_at": f.acknowledged_at.isoformat() if f.acknowledged_at else None,
            "completed_at": f.completed_at.isoformat() if f.completed_at else None
        })
    return results

@app.post("/api/modules/labloop/followup/{id}/update")
def update_lab_followup(
    id: int,
    req: schemas.LabFollowUpUpdateRequest,
    current_user: models.User = Depends(require_role(["LAB_STAFF", "DOCTOR", "ADMIN"])),
    db: Session = Depends(get_db)
):
    f = db.query(models.LabFollowUp).filter(models.LabFollowUp.id == id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Lab follow-up record not found")
    
    trail = json.loads(f.audit_trail_json or "[]")
    now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    
    if req.status == "ACKNOWLEDGED":
        f.status = "ACKNOWLEDGED"
        f.acknowledged_by = current_user.full_name
        f.acknowledged_at = datetime.datetime.utcnow()
        trail.append({"action": "ACKNOWLEDGED_BY_USER", "timestamp": now_str, "user": current_user.full_name})
    elif req.status == "COMPLETED":
        f.status = "COMPLETED"
        f.completed_at = datetime.datetime.utcnow()
        trail.append({"action": "FOLLOWUP_COMPLETED", "timestamp": now_str, "user": current_user.full_name, "notes": req.notes})
    elif req.status == "ESCALATED":
        f.status = "ESCALATED"
        f.escalation_level += 1
        trail.append({"action": f"ESCALATED_LEVEL_{f.escalation_level}", "timestamp": now_str, "user": current_user.full_name})

    f.audit_trail_json = json.dumps(trail)
    db.commit()

    return {"status": "SUCCESS", "message": f"Lab follow-up updated to {f.status}"}

# ==============================================================================
# MODULE 5: BEDFLOW
# ==============================================================================
@app.get("/api/modules/bedflow/beds")
def get_beds(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    beds = db.query(models.BedRecord).all()
    results = []
    for b in beds:
        patient = db.query(models.Patient).filter(models.Patient.id == b.patient_id).first() if b.patient_id else None
        results.append({
            "id": b.id,
            "ward_name": b.ward_name,
            "ward_type": b.ward_type,
            "bed_number": b.bed_number,
            "status": b.status,
            "patient_id": b.patient_id,
            "patient_name": patient.full_name if patient else None,
            "patient_mrn": patient.mrn if patient else None,
            "admission_time": b.admission_time.isoformat() if b.admission_time else None,
            "expected_discharge_time": b.expected_discharge_time.isoformat() if b.expected_discharge_time else None,
            "notes": b.notes
        })
    return results

@app.post("/api/modules/bedflow/simulate", response_model=schemas.BedSimulationOut)
def run_bed_simulation(
    req: schemas.BedSimulationRequest,
    current_user: models.User = Depends(require_role(["OPERATIONS", "ADMIN", "DOCTOR"])),
    db: Session = Depends(get_db)
):
    total_beds = db.query(models.BedRecord).count()
    occupied = db.query(models.BedRecord).filter(models.BedRecord.status == "OCCUPIED").count()
    available = db.query(models.BedRecord).filter(models.BedRecord.status == "AVAILABLE").count()

    baseline_occupancy = round((occupied / total_beds) * 100, 1) if total_beds > 0 else 0.0

    # Calculate simulated surge impact
    surge_delta = (req.surge_percentage / 100.0) * total_beds
    delay_impact = (req.discharge_delay_hours / 12.0) * (occupied * 0.15)
    staffing_factor = (100.0 - req.staffing_level_pct) * 0.1

    projected_occupied = min(total_beds, occupied + surge_delta + delay_impact + staffing_factor)
    projected_occupancy = round((projected_occupied / total_beds) * 100, 1)

    bottlenecks = [
        {"ward": "Intensive Care Unit (ICU)", "baseline_pct": 83.3, "simulated_pct": 98.5, "risk": "CRITICAL"},
        {"ward": "General Medicine A", "baseline_pct": 77.8, "simulated_pct": 92.4, "risk": "HIGH"},
        {"ward": "Emergency Short-Stay", "baseline_pct": 78.6, "simulated_pct": 95.0, "risk": "HIGH"},
    ]

    recommendations = [
        f"Activate discharge lounge fast-track to mitigate {req.discharge_delay_hours}h discharge bottleneck.",
        "Authorize contingency staffing on Stepdown ward to support ICU step-down transfers.",
        "Divert non-urgent elective surgical admissions scheduled for next 24 hours.",
        "Expedite environmental services turnover for 8 beds currently in CLEANING status."
    ]

    return {
        "baseline_occupancy": baseline_occupancy,
        "projected_occupancy": projected_occupancy,
        "total_beds": total_beds,
        "occupied_beds": occupied,
        "available_beds": available,
        "bottleneck_wards": bottlenecks,
        "recommendations": recommendations
    }

@app.post("/api/modules/bedflow/beds/{id}/status")
def update_bed_status(
    id: int,
    status_str: str = Form(...),
    current_user: models.User = Depends(require_role(["OPERATIONS", "ADMIN"])),
    db: Session = Depends(get_db)
):
    bed = db.query(models.BedRecord).filter(models.BedRecord.id == id).first()
    if not bed:
        raise HTTPException(status_code=404, detail="Bed not found")
    
    bed.status = status_str
    db.commit()
    return {"status": "SUCCESS", "message": f"Bed {bed.bed_number} updated to {status_str}"}

# ==============================================================================
# MODULE 6: SCANCOMPARE
# ==============================================================================
@app.get("/api/modules/scancompare/{patient_id}")
def get_imaging_sessions(
    patient_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role == "PATIENT" and current_user.patient_id != patient_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    sessions = db.query(models.ImagingSession).filter(
        models.ImagingSession.patient_id == patient_id
    ).all()

    results = []
    for s in sessions:
        results.append({
            "id": s.id,
            "patient_id": s.patient_id,
            "patient_name": s.patient.full_name if s.patient else "",
            "scan_type": s.scan_type,
            "prior_image_url": f"/api/modules/scancompare/image/{os.path.basename(s.prior_image_path)}",
            "current_image_url": f"/api/modules/scancompare/image/{os.path.basename(s.current_image_path)}",
            "diff_image_url": f"/api/modules/scancompare/image/{os.path.basename(s.diff_image_path)}" if s.diff_image_path else None,
            "prior_scan_date": s.prior_scan_date,
            "current_scan_date": s.current_scan_date,
            "findings_notes": s.findings_notes,
            "difference_score": s.difference_score,
            "alignment_status": s.alignment_status,
            "reviewer_notes": s.reviewer_notes,
            "created_at": s.created_at.isoformat() if s.created_at else ""
        })
    return results

@app.get("/api/modules/scancompare/image/{filename}")
def serve_scan_image(filename: str):
    path = os.path.join(SCANS_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Scan image not found")
    return FileResponse(path, media_type="image/png")

@app.post("/api/modules/scancompare/run-diff/{session_id}")
def run_scan_comparison(
    session_id: int,
    current_user: models.User = Depends(require_role(["DOCTOR", "ADMIN"])),
    db: Session = Depends(get_db)
):
    s = db.query(models.ImagingSession).filter(models.ImagingSession.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Imaging session not found")
    
    out_diff = os.path.join(SCANS_DIR, f"diff_{session_id}_{uuid.uuid4().hex[:6]}.png")
    diff_res = AIService.compare_images(s.prior_image_path, s.current_image_path, out_diff)

    s.diff_image_path = diff_res.get("diff_image_path", "")
    s.difference_score = diff_res.get("difference_score", 0.0)
    s.alignment_status = diff_res.get("alignment_status", "ALIGNED")
    s.findings_notes = diff_res.get("findings_notes", "")
    db.commit()

    return {
        "status": "SUCCESS",
        "difference_score": s.difference_score,
        "alignment_status": s.alignment_status,
        "findings_notes": s.findings_notes,
        "diff_image_url": f"/api/modules/scancompare/image/{os.path.basename(s.diff_image_path)}" if s.diff_image_path else None
    }

# ==============================================================================
# MODULE 7: FOLLOWUP SHIELD
# ==============================================================================
@app.get("/api/modules/followup/{patient_id}")
def get_discharge_plan(
    patient_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role == "PATIENT" and current_user.patient_id != patient_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    dp = db.query(models.DischargePlan).filter(
        models.DischargePlan.patient_id == patient_id
    ).first()

    if not dp:
        return {"plan": None, "tasks": []}
    
    tasks_query = db.query(models.DischargeTask).filter(
        models.DischargeTask.discharge_plan_id == dp.id
    )

    # Patient only sees patient_visible tasks
    if current_user.role == "PATIENT":
        tasks_query = tasks_query.filter(models.DischargeTask.patient_visible == True)

    tasks = tasks_query.all()

    return {
        "plan": {
            "id": dp.id,
            "patient_id": dp.patient_id,
            "admission_date": dp.admission_date,
            "discharge_date": dp.discharge_date,
            "primary_diagnosis": dp.primary_diagnosis,
            "summary_text": dp.summary_text
        },
        "tasks": [
            {
                "id": t.id,
                "discharge_plan_id": t.discharge_plan_id,
                "patient_id": t.patient_id,
                "task_title": t.task_title,
                "category": t.category,
                "due_date": t.due_date,
                "due_date_source": t.due_date_source,
                "priority": t.priority,
                "status": t.status,
                "assigned_role": t.assigned_role,
                "notes": t.notes,
                "patient_visible": t.patient_visible
            }
            for t in tasks
        ]
    }

@app.post("/api/modules/followup/tasks/{id}/update")
def update_discharge_task(
    id: int,
    req: schemas.DischargeTaskUpdateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(models.DischargeTask).filter(models.DischargeTask.id == id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if current_user.role == "PATIENT" and task.patient_id != current_user.patient_id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    task.status = req.status
    if req.notes:
        task.notes += f" | {req.notes}"
    db.commit()

    return {"status": "SUCCESS", "message": f"Task status updated to {req.status}"}

# ==============================================================================
# DASHBOARD METRICS & NOTIFICATIONS
# ==============================================================================
@app.get("/api/dashboard/metrics")
def get_dashboard_metrics(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Role-Based Metrics Protection: Patients only see their own metrics
    if current_user.role == "PATIENT":
        pid = current_user.patient_id
        reports_uploaded = db.query(models.MedicalReport).filter(models.MedicalReport.patient_id == pid).count()
        reports_processing = db.query(models.MedicalReport).filter(
            models.MedicalReport.patient_id == pid,
            models.MedicalReport.ai_analysis_status == "PROCESSING"
        ).count()
        active_vital_alerts = db.query(models.VitalAlert).filter(
            models.VitalAlert.patient_id == pid,
            models.VitalAlert.status == "ACTIVE"
        ).count()
        pending_discharge_tasks = db.query(models.DischargeTask).filter(
            models.DischargeTask.patient_id == pid,
            models.DischargeTask.status == "PENDING",
            models.DischargeTask.patient_visible == True
        ).count()

        recent_audits = db.query(models.AuditLog).filter(
            models.AuditLog.username == current_user.username
        ).order_by(models.AuditLog.timestamp.desc()).limit(5).all()
        recent_activity = [
            {
                "id": a.id,
                "username": a.username,
                "action": a.action,
                "entity_type": a.entity_type,
                "details": a.details,
                "timestamp": a.timestamp.strftime("%b %d, %H:%M") if a.timestamp else ""
            }
            for a in recent_audits
        ]

        return {
            "total_patients": 1,
            "reports_uploaded": reports_uploaded,
            "reports_processing": reports_processing,
            "reports_action_required": 0,
            "unresolved_conflicts": 0,
            "active_vital_alerts": active_vital_alerts,
            "active_med_flags": 0,
            "pending_lab_followups": 0,
            "bed_occupancy_pct": 0,
            "occupied_beds": 0,
            "total_beds": 0,
            "pending_discharge_tasks": pending_discharge_tasks,
            "recent_activity": recent_activity,
            "system_status": "OPERATIONAL"
        }

    total_patients = db.query(models.Patient).count()
    reports_uploaded = db.query(models.MedicalReport).count()
    reports_processing = db.query(models.MedicalReport).filter(models.MedicalReport.ai_analysis_status == "PROCESSING").count()
    reports_action_required = db.query(models.MedicalReport).filter(models.MedicalReport.file_availability_status == "ACTION_REQUIRED").count()
    
    unresolved_conflicts = db.query(models.ConflictRecord).filter(models.ConflictRecord.status == "UNRESOLVED").count()
    active_vital_alerts = db.query(models.VitalAlert).filter(models.VitalAlert.status == "ACTIVE").count()
    active_med_flags = db.query(models.MedicationFlag).filter(models.MedicationFlag.status == "UNRESOLVED").count()
    pending_lab_followups = db.query(models.LabFollowUp).filter(models.LabFollowUp.status.in_(["PENDING", "ESCALATED"])).count()
    
    total_beds = db.query(models.BedRecord).count()
    occupied_beds = db.query(models.BedRecord).filter(models.BedRecord.status == "OCCUPIED").count()
    bed_occupancy_pct = round((occupied_beds / total_beds) * 100, 1) if total_beds > 0 else 0.0

    pending_discharge_tasks = db.query(models.DischargeTask).filter(models.DischargeTask.status == "PENDING").count()

    recent_audits = db.query(models.AuditLog).order_by(models.AuditLog.timestamp.desc()).limit(8).all()
    recent_activity = [
        {
            "id": a.id,
            "username": a.username,
            "action": a.action,
            "entity_type": a.entity_type,
            "details": a.details,
            "timestamp": a.timestamp.strftime("%b %d, %H:%M") if a.timestamp else ""
        }
        for a in recent_audits
    ]

    return {
        "total_patients": total_patients,
        "reports_uploaded": reports_uploaded,
        "reports_processing": reports_processing,
        "reports_action_required": reports_action_required,
        "unresolved_conflicts": unresolved_conflicts,
        "active_vital_alerts": active_vital_alerts,
        "active_med_flags": active_med_flags,
        "pending_lab_followups": pending_lab_followups,
        "bed_occupancy_pct": bed_occupancy_pct,
        "occupied_beds": occupied_beds,
        "total_beds": total_beds,
        "pending_discharge_tasks": pending_discharge_tasks,
        "recent_activity": recent_activity,
        "system_status": "OPERATIONAL"
    }

@app.get("/api/notifications")
def get_notifications(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(models.Notification)
    if current_user.role == "PATIENT":
        query = query.filter(
            (models.Notification.user_id == current_user.id) |
            ((models.Notification.role_target == "PATIENT") & (models.Notification.patient_id == current_user.patient_id))
        )
    else:
        query = query.filter(
            (models.Notification.role_target == current_user.role) |
            (models.Notification.role_target == "ALL") |
            (models.Notification.user_id == current_user.id)
        )

    notifs = query.order_by(models.Notification.created_at.desc()).limit(20).all()
    return [
        {
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "category": n.category,
            "severity": n.severity,
            "is_read": n.is_read,
            "link_url": n.link_url,
            "created_at": n.created_at.isoformat() if n.created_at else ""
        }
        for n in notifs
    ]

@app.post("/api/notifications/{id}/read")
def mark_notification_read(
    id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    n = db.query(models.Notification).filter(models.Notification.id == id).first()
    if n:
        n.is_read = True
        db.commit()
    return {"status": "SUCCESS"}

@app.post("/api/admin/reset-demo")
def reset_demo_database(
    current_user: models.User = Depends(require_role(["ADMIN"])),
    db: Session = Depends(get_db)
):
    # Drop all and re-seed
    Base.metadata.drop_all(bind=engine)
    seed_database()
    return {"status": "SUCCESS", "message": "Demo database reset and seeded with fresh records."}
