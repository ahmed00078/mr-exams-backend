from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal
import uuid

# Schémas de base
class WilayaBase(BaseModel):
    code: str
    name_fr: str
    name_ar: str
    name_en: Optional[str] = None

class WilayaResponse(WilayaBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class EtablissementBase(BaseModel):
    code: str
    name_fr: str
    name_ar: str
    type_etablissement: str
    wilaya_id: int

class EtablissementResponse(EtablissementBase):
    id: int
    phone: Optional[str]
    email: Optional[str]
    status: str
    wilaya: Optional[WilayaResponse]
    
    class Config:
        from_attributes = True

class SerieResponse(BaseModel):
    id: int
    code: str
    name_fr: str
    name_ar: str
    exam_type: str
    
    class Config:
        from_attributes = True

# Schémas pour résultats d'examen
class ExamResultBase(BaseModel):
    nni: str = Field(..., min_length=10, max_length=20)
    numero_dossier: Optional[str] = None
    nom_complet_fr: str = Field(..., min_length=2, max_length=200)
    nom_complet_ar: Optional[str] = None
    lieu_naissance: Optional[str] = None
    date_naissance: Optional[date] = None
    sexe: Optional[str] = Field(None, pattern="^[MF]$")
    moyenne_generale: Optional[Decimal] = Field(None, ge=0, le=20)
    decision: str
    mention: Optional[str] = None

class ExamResultCreate(ExamResultBase):
    session_id: int
    etablissement_id: Optional[int] = None
    serie_id: Optional[int] = None
    wilaya_id: Optional[int] = None

class ExamResultResponse(ExamResultBase):
    id: uuid.UUID
    session_id: int
    rang_etablissement: Optional[int] = None
    rang_wilaya: Optional[int] = None
    rang_national: Optional[int] = None
    is_published: bool
    view_count: int
    created_at: datetime
    
    # Relations
    etablissement: Optional[EtablissementResponse] = None
    serie: Optional[SerieResponse] = None
    wilaya: Optional[WilayaResponse] = None
    
    class Config:
        from_attributes = True

class ExamResultDetailResponse(ExamResultResponse):
    # Informations complètes pour affichage individuel
    nom_pere: Optional[str] = None
    type_candidat: str
    centre_examen: Optional[str] = None
    total_points: Optional[Decimal] = None
    published_at: Optional[datetime] = None

# Schémas de recherche
class SearchParams(BaseModel):
    nni: Optional[str] = None
    numero_dossier: Optional[str] = None
    nom: Optional[str] = None
    wilaya_id: Optional[int] = None
    etablissement_id: Optional[int] = None
    serie_id: Optional[int] = None
    serie_code: Optional[str] = None
    decision: Optional[str] = None
    year: Optional[int] = None
    exam_type: Optional[str] = None
    page: int = Field(1, ge=1)
    size: int = Field(50, ge=1, le=1000)

class SearchResponse(BaseModel):
    results: List[ExamResultResponse]
    total: int
    page: int
    size: int
    total_pages: int
    has_next: bool
    has_prev: bool

# Schémas pour partage social
class SocialShareCreate(BaseModel):
    result_id: uuid.UUID
    platform: str = Field(..., pattern="^(facebook|twitter|whatsapp|telegram|linkedin)$")
    is_anonymous: bool = False

class SocialShareResponse(BaseModel):
    share_token: str
    share_url: str
    expires_at: datetime

class SocialSharePublic(BaseModel):
    candidate_name: str
    exam_type: str
    decision: str
    moyenne: Optional[Decimal]
    etablissement: Optional[str]
    wilaya: Optional[str]
    year: int
    is_anonymous: bool

# Schémas pour statistiques
class StatsEtablissement(BaseModel):
    etablissement_id: int
    etablissement_name: str
    total_candidats: int
    total_admis: int
    taux_reussite: Decimal
    moyenne_etablissement: Optional[Decimal]
    rang_wilaya: Optional[int]

class StatsWilaya(BaseModel):
    wilaya_id: int
    wilaya_name: str
    total_candidats: int
    total_admis: int
    taux_reussite: Decimal
    moyenne_wilaya: Optional[Decimal]
    rang_national: Optional[int]
    stats_par_serie: Dict[str, Any]

# Schémas d'authentification
class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    role: str
    can_publish_results: bool
    can_manage_users: bool
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: UserResponse

# Schémas pour upload en masse
class BulkUploadResponse(BaseModel):
    task_id: str
    message: str
    total_rows: int
    
class BulkUploadStatus(BaseModel):
    task_id: str
    status: str  # 'pending', 'processing', 'completed', 'failed'
    progress: int  # 0-100
    total_rows: int
    processed_rows: int
    success_count: int
    error_count: int
    errors: List[str] = []

class SessionResponse(BaseModel):
    id: int
    year: int
    exam_type: str
    session_name: str
    start_date: Optional[date]
    end_date: Optional[date]
    publication_date: Optional[datetime]
    is_published: bool
    total_candidates: int
    total_passed: int
    pass_rate: Optional[Decimal]
    
    class Config:
        from_attributes = True

class SessionListResponse(BaseModel):
    sessions: List[SessionResponse]
    total: int