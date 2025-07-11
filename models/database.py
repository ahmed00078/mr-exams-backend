from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, DECIMAL, Date, ForeignKey, JSON, Index
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from database import Base

class RefWilaya(Base):
    __tablename__ = "ref_wilayas"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, nullable=False)
    name_fr = Column(String(100), nullable=False)
    name_ar = Column(String(100), nullable=False)
    name_en = Column(String(100))
    # coordinates = Column(String, nullable=True)
    population_estimate = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class RefMoughata(Base):
    __tablename__ = "ref_moughatas"
    
    id = Column(Integer, primary_key=True, index=True)
    wilaya_id = Column(Integer, ForeignKey("ref_wilayas.id"))
    code = Column(String(10), nullable=False)
    name_fr = Column(String(100), nullable=False)
    name_ar = Column(String(100), nullable=False)
    name_en = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    wilaya = relationship("RefWilaya", back_populates="moughatas")

RefWilaya.moughatas = relationship("RefMoughata", back_populates="wilaya")

class RefEtablissement(Base):
    __tablename__ = "ref_etablissements"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False)
    name_fr = Column(String(200), nullable=False)
    name_ar = Column(String(200), nullable=False)
    name_en = Column(String(200))
    type_etablissement = Column(String(50), nullable=False)
    wilaya_id = Column(Integer, ForeignKey("ref_wilayas.id"))
    moughata_id = Column(Integer, ForeignKey("ref_moughatas.id"))
    address_fr = Column(Text)
    address_ar = Column(Text)
    # coordinates = Column(String, nullable=True)
    phone = Column(String(20))
    email = Column(String(100))
    director_name = Column(String(100))
    status = Column(String(20), default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    wilaya = relationship("RefWilaya")
    moughata = relationship("RefMoughata")

class RefSerie(Base):
    __tablename__ = "ref_series"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, nullable=False)
    name_fr = Column(String(100), nullable=False)
    name_ar = Column(String(100), nullable=False)
    name_en = Column(String(100))
    exam_type = Column(String(20), nullable=False)
    description_fr = Column(Text)
    description_ar = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ExamSession(Base):
    __tablename__ = "exam_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False)
    exam_type = Column(String(20), nullable=False)
    session_name = Column(String(50))
    start_date = Column(Date)
    end_date = Column(Date)
    publication_date = Column(DateTime(timezone=True))
    is_published = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    total_candidates = Column(Integer, default=0)
    total_passed = Column(Integer, default=0)
    pass_rate = Column(DECIMAL(5, 2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ExamResult(Base):
    __tablename__ = "exam_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(Integer, ForeignKey("exam_sessions.id"))
    etablissement_id = Column(Integer, ForeignKey("ref_etablissements.id"))
    serie_id = Column(Integer, ForeignKey("ref_series.id"))
    wilaya_id = Column(Integer, ForeignKey("ref_wilayas.id"))
    moughata_id = Column(Integer, ForeignKey("ref_moughatas.id"))
    
    # Identifiants candidat
    nni = Column(String(20), nullable=False, index=True)
    numero_dossier = Column(String(20), index=True)
    numero_inscription = Column(String(20))
    numero_regional = Column(String(10))
    
    # Informations personnelles
    nom_complet_fr = Column(String(200), nullable=False)
    nom_complet_ar = Column(String(200))
    nom_pere = Column(String(150))
    lieu_naissance = Column(String(100))
    date_naissance = Column(Date)
    sexe = Column(String(1))
    
    # Informations examen
    type_candidat = Column(String(20), default="officiel")
    centre_examen = Column(String(200))
    centre_correction = Column(String(200))
    
    # Résultats
    moyenne_generale = Column(DECIMAL(5, 2))
    total_points = Column(DECIMAL(8, 2))
    decision = Column(String(30), nullable=False)
    mention = Column(String(30))
    rang_etablissement = Column(Integer)
    rang_wilaya = Column(Integer)
    rang_national = Column(Integer)
    
    # Métadonnées
    is_published = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=True)
    published_at = Column(DateTime(timezone=True))
    social_share_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    session = relationship("ExamSession")
    etablissement = relationship("RefEtablissement")
    serie = relationship("RefSerie")
    wilaya = relationship("RefWilaya")
    moughata = relationship("RefMoughata")

class SocialShare(Base):
    __tablename__ = "social_shares"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    result_id = Column(UUID(as_uuid=True), ForeignKey("exam_results.id"))
    share_token = Column(String(100), unique=True, nullable=False)
    candidate_name = Column(String(200), nullable=False)
    exam_type = Column(String(20), nullable=False)
    decision = Column(String(30), nullable=False)
    moyenne = Column(DECIMAL(5, 2))
    etablissement = Column(String(200))
    wilaya = Column(String(100))
    year = Column(Integer, nullable=False)
    platform = Column(String(20))
    is_anonymous = Column(Boolean, default=False)
    expiry_date = Column(DateTime(timezone=True))
    click_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    result = relationship("ExamResult")

class AdminUser(Base):
    __tablename__ = "admin_users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False, default="operator")
    can_publish_results = Column(Boolean, default=False)
    can_manage_users = Column(Boolean, default=False)
    can_view_analytics = Column(Boolean, default=True)
    allowed_wilayas = Column(JSON)
    last_login = Column(DateTime(timezone=True))
    login_attempts = Column(Integer, default=0)
    is_locked = Column(Boolean, default=False)
    must_change_password = Column(Boolean, default=True)
    two_factor_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# Index pour performance
Index('idx_exam_results_nni', ExamResult.nni)
Index('idx_exam_results_numero_dossier', ExamResult.numero_dossier)
Index('idx_exam_results_session_published', ExamResult.session_id, ExamResult.is_published)