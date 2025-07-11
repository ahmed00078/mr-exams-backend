from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

from database import get_db
from models.schemas import StatsWilaya, StatsEtablissement
from services.stats_service import StatsService

router = APIRouter(prefix="/stats", tags=["Statistics"])

@router.get("/wilaya/{wilaya_id}", response_model=StatsWilaya)
async def get_wilaya_statistics(
    wilaya_id: int = Path(..., description="ID de la wilaya"),
    year: int = Query(..., description="Année de l'examen"),
    exam_type: str = Query(..., description="Type d'examen (bac, bepc, concours)"),
    db: Session = Depends(get_db)
):
    """Récupère les statistiques d'une wilaya pour une année donnée"""
    
    service = StatsService(db)
    stats = await service.get_wilaya_stats(wilaya_id, year, exam_type)
    
    if not stats:
        raise HTTPException(status_code=404, detail="Statistiques non trouvées")
    
    return stats

@router.get("/etablissement/{etablissement_id}", response_model=StatsEtablissement)
async def get_etablissement_statistics(
    etablissement_id: int = Path(..., description="ID de l'établissement"),
    year: int = Query(..., description="Année de l'examen"),
    exam_type: str = Query(..., description="Type d'examen (bac, bepc, concours)"),
    db: Session = Depends(get_db)
):
    """Récupère les statistiques d'un établissement pour une année donnée"""
    
    service = StatsService(db)
    stats = await service.get_etablissement_stats(etablissement_id, year, exam_type)
    
    if not stats:
        raise HTTPException(status_code=404, detail="Statistiques non trouvées")
    
    return stats

@router.get("/global")
async def get_global_statistics(
    year: int = Query(..., description="Année de l'examen"),
    exam_type: str = Query(..., description="Type d'examen (bac, bepc, concours)"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Récupère les statistiques globales pour une année donnée"""
    
    service = StatsService(db)
    stats = service.get_global_stats(year, exam_type)
    
    if not stats:
        raise HTTPException(status_code=404, detail="Statistiques non trouvées")
    
    return stats

@router.get("/top-students")
async def get_top_students(
    year: int = Query(..., description="Année de l'examen"),
    exam_type: str = Query(..., description="Type d'examen (bac, bepc, concours)"),
    limit: int = Query(10, description="Nombre d'élèves à retourner"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Récupère le top des élèves pour une année donnée"""
    
    service = StatsService(db)
    top_students = service.get_top_students(year, exam_type, limit)
    
    return {"top_students": top_students}

@router.get("/top-schools")
async def get_top_schools(
    year: int = Query(..., description="Année de l'examen"),
    exam_type: str = Query(..., description="Type d'examen (bac, bepc, concours)"),
    limit: int = Query(10, description="Nombre d'écoles à retourner"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Récupère le top des écoles pour une année donnée"""
    
    service = StatsService(db)
    top_schools = service.get_top_schools(year, exam_type, limit)
    
    return {"top_schools": top_schools}