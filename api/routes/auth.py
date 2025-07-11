from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from database import get_db
from models.database import AdminUser
from models.schemas import Token, UserLogin, UserResponse
from core.security import verify_password, create_access_token, get_current_user
from config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Authentification des utilisateurs administrateurs"""
    
    # Récupérer l'utilisateur
    user = db.query(AdminUser).filter(AdminUser.username == form_data.username).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nom d'utilisateur ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Vérifier si le compte est verrouillé
    if user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Compte verrouillé. Contactez l'administrateur.",
        )
    
    # Vérifier le mot de passe
    if not verify_password(form_data.password, user.password_hash):
        # Incrémenter les tentatives de connexion
        user.login_attempts += 1
        if user.login_attempts >= 5:
            user.is_locked = True
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nom d'utilisateur ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Réinitialiser les tentatives de connexion
    user.login_attempts = 0
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Créer le token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, 
        expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserResponse.from_orm(user)
    )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: AdminUser = Depends(get_current_user)):
    """Récupère les informations de l'utilisateur connecté"""
    return UserResponse.from_orm(current_user)

@router.post("/logout")
async def logout(current_user: AdminUser = Depends(get_current_user)):
    """Déconnexion (côté client principalement)"""
    return {"message": "Déconnexion réussie"}