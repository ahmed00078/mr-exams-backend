import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from models.database import SocialShare, ExamResult
from models.schemas import SocialShareCreate, SocialShareResponse, SocialSharePublic
from config import settings

class SocialService:
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_share_token(self, share_data: SocialShareCreate) -> SocialShareResponse:
        """Génère un token de partage social unique"""
        
        # Récupérer le résultat
        result = self.db.query(ExamResult).filter(ExamResult.id == share_data.result_id).first()
        if not result:
            raise ValueError("Result not found")
        
        # Générer un token unique
        token_data = f"{share_data.result_id}{share_data.platform}{secrets.token_hex(8)}"
        share_token = hashlib.sha256(token_data.encode()).hexdigest()[:32]
        
        # Date d'expiration
        expiry_date = datetime.utcnow() + timedelta(days=settings.social_share_expire_days)
        
        # Créer l'enregistrement de partage
        social_share = SocialShare(
            result_id=share_data.result_id,
            share_token=share_token,
            candidate_name=result.nom_complet_fr if not share_data.is_anonymous else "Candidat anonyme",
            exam_type=result.session.exam_type,
            decision=result.decision,
            moyenne=result.moyenne_generale,
            etablissement=result.etablissement.name_fr if result.etablissement else None,
            wilaya=result.wilaya.name_fr if result.wilaya else None,
            year=result.session.year,
            platform=share_data.platform,
            is_anonymous=share_data.is_anonymous,
            expiry_date=expiry_date
        )
        
        self.db.add(social_share)
        self.db.commit()
        self.db.refresh(social_share)
        
        # Incrémenter le compteur de partage
        self.db.query(ExamResult).filter(ExamResult.id == share_data.result_id).update(
            {ExamResult.social_share_count: ExamResult.social_share_count + 1}
        )
        self.db.commit()
        
        # Retourner la réponse
        share_url = f"{settings.base_url}/share/{share_token}"
        
        return SocialShareResponse(
            share_token=share_token,
            share_url=share_url,
            expires_at=expiry_date
        )
    
    def get_share_data(self, share_token: str) -> Optional[SocialSharePublic]:
        """Récupère les données de partage par token"""
        
        share = self.db.query(SocialShare).filter(
            and_(
                SocialShare.share_token == share_token,
                SocialShare.expiry_date > datetime.utcnow()
            )
        ).first()
        
        if not share:
            return None
        
        # Incrémenter le compteur de clics
        share.click_count += 1
        self.db.commit()
        
        return SocialSharePublic(
            candidate_name=share.candidate_name,
            exam_type=share.exam_type,
            decision=share.decision,
            moyenne=share.moyenne,
            etablissement=share.etablissement,
            wilaya=share.wilaya,
            year=share.year,
            is_anonymous=share.is_anonymous
        )