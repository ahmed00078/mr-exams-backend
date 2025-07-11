from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from database import get_db
from models.schemas import SocialSharePublic
from services.social_service import SocialService

router = APIRouter(prefix="/share", tags=["Social Sharing"])

@router.get("/{share_token}", response_class=HTMLResponse)
async def get_social_share_page(
    share_token: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Page publique de partage social avec Open Graph meta tags"""
    
    service = SocialService(db)
    share_data = service.get_share_data(share_token)
    
    if not share_data:
        raise HTTPException(status_code=404, detail="Lien de partage expiré ou invalide")
    
    # Générer la page HTML avec les meta tags Open Graph
    html_content = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Résultat d'Examen - {share_data.candidate_name}</title>
        
        <!-- Open Graph Meta Tags -->
        <meta property="og:title" content="Résultat {share_data.exam_type.upper()} {share_data.year} - {share_data.candidate_name}" />
        <meta property="og:description" content="Décision: {share_data.decision} | Établissement: {share_data.etablissement or 'N/A'} | Wilaya: {share_data.wilaya or 'N/A'}" />
        <meta property="og:type" content="article" />
        <meta property="og:url" content="{request.url}" />
        <meta property="og:site_name" content="Portail des Résultats d'Examens - Mauritanie" />
        
        <!-- Twitter Card Meta Tags -->
        <meta name="twitter:card" content="summary" />
        <meta name="twitter:title" content="Résultat {share_data.exam_type.upper()} {share_data.year} - {share_data.candidate_name}" />
        <meta name="twitter:description" content="Décision: {share_data.decision} | Établissement: {share_data.etablissement or 'N/A'}" />
        
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }}
            .card {{
                background: white;
                border-radius: 15px;
                padding: 30px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                text-align: center;
            }}
            .header {{
                color: #2c3e50;
                margin-bottom: 30px;
            }}
            .result-info {{
                background: #f8f9fa;
                border-radius: 10px;
                padding: 20px;
                margin: 20px 0;
            }}
            .decision {{
                font-size: 2em;
                font-weight: bold;
                margin: 20px 0;
            }}
            .decision.admis {{
                color: #27ae60;
            }}
            .decision.ajourne {{
                color: #e74c3c;
            }}
            .moyenne {{
                font-size: 1.5em;
                color: #3498db;
                font-weight: bold;
            }}
            .details {{
                margin: 15px 0;
                color: #7f8c8d;
            }}
            .flag {{
                display: inline-block;
                width: 30px;
                height: 20px;
                background: linear-gradient(to bottom, #28a745 33%, #ffc107 33%, #ffc107 66%, #dc3545 66%);
                margin-right: 10px;
                border-radius: 3px;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="header">
                <span class="flag"></span>
                <h1>La plateforme d’examens de référence en Mauritanie</h1>
                <h2>Résultat d'Examen {share_data.exam_type.upper()} {share_data.year}</h2>
            </div>
            
            <div class="result-info">
                <h3>{share_data.candidate_name}</h3>
                
                <div class="decision {'admis' if 'admis' in share_data.decision.lower() else 'ajourne'}">
                    {share_data.decision}
                </div>
                
                {'<div class="moyenne">Moyenne: ' + str(share_data.moyenne) + '/20</div>' if share_data.moyenne else ''}
                
                {'<div class="details">Établissement: ' + share_data.etablissement + '</div>' if share_data.etablissement else ''}
                {'<div class="details">Wilaya: ' + share_data.wilaya + '</div>' if share_data.wilaya else ''}
                
                <div class="details">
                    <small>La plateforme d’examens de référence en Mauritanie</small>
                </div>
            </div>
            
            <div style="margin-top: 30px;">
                <a href="/" style="background: #3498db; color: white; padding: 12px 24px; text-decoration: none; border-radius: 25px; display: inline-block;">
                    Rechercher d'autres résultats
                </a>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_content

@router.get("/{share_token}/data", response_model=SocialSharePublic)
async def get_social_share_data(
    share_token: str,
    db: Session = Depends(get_db)
):
    """API pour récupérer les données de partage (format JSON)"""
    
    service = SocialService(db)
    share_data = service.get_share_data(share_token)
    
    if not share_data:
        raise HTTPException(status_code=404, detail="Lien de partage expiré ou invalide")
    
    return share_data