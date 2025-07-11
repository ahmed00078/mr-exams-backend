from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from typing import Optional, List
import uuid

from database import get_db
from models.schemas import (
    SearchParams, SearchResponse, ExamResultDetailResponse,
    SocialShareCreate, SocialShareResponse
)
from services.results_service import ResultsService
from services.social_service import SocialService

router = APIRouter(prefix="/results", tags=["Results"])

@router.get("/search", response_model=SearchResponse)
async def search_results(
    nni: Optional[str] = Query(None, description="Numéro National d'Identification"),
    numero_dossier: Optional[str] = Query(None, description="Numéro de dossier"),
    nom: Optional[str] = Query(None, description="Nom du candidat (recherche floue)"),
    wilaya_id: Optional[int] = Query(None, description="ID de la wilaya"),
    etablissement_id: Optional[int] = Query(None, description="ID de l'établissement"),
    serie_id: Optional[int] = Query(None, description="ID de la série"),
    serie_code: Optional[str] = Query(None, description="Code de la série"),
    decision: Optional[str] = Query(None, description="Décision (Admis, Ajourné, etc.)"),
    year: Optional[int] = Query(None, description="Année de l'examen"),
    exam_type: Optional[str] = Query(None, description="Type d'examen (bac, bepc, concours)"),
    page: int = Query(1, ge=1, description="Numéro de page"),
    size: int = Query(50, ge=1, le=1000, description="Nombre de résultats par page"),
    db: Session = Depends(get_db)
):
    """Recherche des résultats d'examens avec filtres multiples"""
    
    search_params = SearchParams(
        nni=nni,
        numero_dossier=numero_dossier,
        nom=nom,
        wilaya_id=wilaya_id,
        etablissement_id=etablissement_id,
        serie_id=serie_id,
        serie_code=serie_code,
        decision=decision,
        year=year,
        exam_type=exam_type,
        page=page,
        size=size
    )
    
    service = ResultsService(db)
    return await service.search_results(search_params)

@router.get("/{result_id}", response_model=ExamResultDetailResponse)
async def get_result_detail(
    result_id: uuid.UUID = Path(..., description="ID du résultat"),
    db: Session = Depends(get_db)
):
    """Récupère les détails complets d'un résultat"""
    
    service = ResultsService(db)
    result = service.get_result_by_id(result_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    
    # Incrémenter le compteur de vues
    service.increment_view_count(result_id)
    
    return ExamResultDetailResponse.from_orm(result)

@router.post("/{result_id}/share", response_model=SocialShareResponse)
async def create_social_share(
    share_data: SocialShareCreate,
    result_id: uuid.UUID = Path(..., description="ID du résultat"),
    db: Session = Depends(get_db)
):
    """Génère un lien de partage social pour un résultat"""
    
    share_data.result_id = result_id
    
    service = SocialService(db)
    try:
        return service.generate_share_token(share_data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))