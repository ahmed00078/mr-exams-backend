from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models.schemas import BulkUploadResponse, BulkUploadStatus, WilayaResponse, SerieResponse, SessionResponse
from services.upload_service import UploadService
from core.security import get_current_user, require_permission
from models.database import AdminUser, RefWilaya, RefSerie, ExamSession

router = APIRouter(prefix="/admin", tags=["Administration"])

@router.post("/upload", response_model=BulkUploadResponse)
async def upload_bulk_results(
    file: UploadFile = File(..., description="Fichier CSV ou Excel avec les résultats"),
    session_id: int = Form(..., description="ID de la session d'examen"),
    db: Session = Depends(get_db),
    # current_user: AdminUser = Depends(require_permission("publish_results"))
):
    """Upload en masse des résultats d'examens"""
    
    # Vérifier le type de fichier
    if not file.filename.endswith(('.csv', '.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="Format de fichier non supporté. Utilisez CSV ou Excel."
        )
    
    # Vérifier la taille du fichier
    if file.size > 50 * 1024 * 1024:  # 50MB
        raise HTTPException(
            status_code=400,
            detail="Fichier trop volumineux. Taille maximale: 50MB"
        )
    
    service = UploadService(db)
    try:
        return await service.process_bulk_upload(file, session_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement: {str(e)}")

@router.get("/upload/{task_id}/status", response_model=BulkUploadStatus)
async def get_upload_status(
    task_id: str,
    db: Session = Depends(get_db),
    # current_user: AdminUser = Depends(get_current_user)
):
    """Récupère le statut d'un upload en cours"""
    
    service = UploadService(db)
    status = service.get_upload_status(task_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="Tâche d'upload non trouvée")
    
    return status

@router.post("/wilayas", response_model=WilayaResponse)
async def create_wilaya(
    code: str = Form(..., description="Code de la wilaya (ex: 01)"),
    name_fr: str = Form(..., description="Nom en français"),
    name_ar: str = Form(..., description="Nom en arabe"),
    db: Session = Depends(get_db),
    # current_user: AdminUser = Depends(get_current_user)
):
    """Créer une nouvelle wilaya"""
    
    # Vérifier si existe déjà
    existing = db.query(RefWilaya).filter(RefWilaya.code == code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Wilaya avec ce code existe déjà")
    
    wilaya = RefWilaya(code=code, name_fr=name_fr, name_ar=name_ar)
    db.add(wilaya)
    db.commit()
    db.refresh(wilaya)
    
    return WilayaResponse.from_orm(wilaya)

@router.post("/series", response_model=SerieResponse)
async def create_serie(
    code: str = Form(..., description="Code de la série (ex: SN)"),
    name_fr: str = Form(..., description="Nom en français"),
    name_ar: str = Form(..., description="Nom en arabe"),
    exam_type: str = Form("bac", description="Type d'examen"),
    db: Session = Depends(get_db),
    # current_user: AdminUser = Depends(get_current_user)
):
    """Créer une nouvelle série"""
    
    # Vérifier si existe déjà
    existing = db.query(RefSerie).filter(RefSerie.code == code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Série avec ce code existe déjà")
    
    serie = RefSerie(code=code, name_fr=name_fr, name_ar=name_ar, exam_type=exam_type)
    db.add(serie)
    db.commit()
    db.refresh(serie)
    
    return SerieResponse.from_orm(serie)

@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    year: int = Form(..., description="Année de l'examen"),
    exam_type: str = Form("bac", description="Type d'examen"),
    session_name: str = Form(..., description="Nom de la session"),
    db: Session = Depends(get_db),
    # current_user: AdminUser = Depends(get_current_user)
):
    """Créer une nouvelle session d'examen"""
    
    # Vérifier si existe déjà
    existing = db.query(ExamSession).filter(
        ExamSession.year == year, 
        ExamSession.exam_type == exam_type
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Session pour cette année existe déjà")
    
    session = ExamSession(
        year=year,
        exam_type=exam_type,
        session_name=session_name,
        is_published=True
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return SessionResponse.from_orm(session)

@router.get("/sessions", response_model=List[SessionResponse])
async def list_sessions(
    db: Session = Depends(get_db),
    # current_user: AdminUser = Depends(get_current_user)
):
    """Lister toutes les sessions d'examen"""
    sessions = db.query(ExamSession).all()
    return [SessionResponse.from_orm(session) for session in sessions]