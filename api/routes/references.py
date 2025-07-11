from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from models.database import RefWilaya, RefEtablissement, RefSerie
from models.schemas import WilayaResponse, EtablissementResponse, SerieResponse

router = APIRouter(prefix="/references", tags=["References"])

@router.get("/wilayas", response_model=List[WilayaResponse])
async def get_wilayas(db: Session = Depends(get_db)):
    """Liste toutes les wilayas"""
    wilayas = db.query(RefWilaya).order_by(RefWilaya.name_fr).all()
    return [WilayaResponse.from_orm(w) for w in wilayas]

@router.get("/etablissements", response_model=List[EtablissementResponse])
async def get_etablissements(
    wilaya_id: Optional[int] = Query(None),
    type_etablissement: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Liste les établissements avec filtres optionnels"""
    query = db.query(RefEtablissement).filter(RefEtablissement.status == "active")
    
    if wilaya_id:
        query = query.filter(RefEtablissement.wilaya_id == wilaya_id)
    
    if type_etablissement:
        query = query.filter(RefEtablissement.type_etablissement == type_etablissement)
    
    etablissements = query.order_by(RefEtablissement.name_fr).all()
    return [EtablissementResponse.from_orm(e) for e in etablissements]

@router.get("/series", response_model=List[SerieResponse])
async def get_series(
    exam_type: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Liste les séries avec filtres optionnels"""
    query = db.query(RefSerie)
    
    if exam_type:
        query = query.filter(RefSerie.exam_type == exam_type)
    
    series = query.order_by(RefSerie.name_fr).all()
    return [SerieResponse.from_orm(s) for s in series]