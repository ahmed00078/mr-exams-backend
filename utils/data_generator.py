"""
Script utilitaire pour générer des données de test
Usage: python -m app.utils.data_generator
"""

import random
from datetime import datetime, date
from sqlalchemy.orm import Session
from database import SessionLocal
from models.database import *
from core.security import get_password_hash

def generate_sample_data():
    """Génère des données d'exemple pour les tests"""
    
    db = SessionLocal()
    
    try:
        # Créer un utilisateur admin par défaut
        admin_user = AdminUser(
            username="admin",
            email="admin@examens.mr",
            password_hash=get_password_hash("admin123"),
            full_name="Administrateur Principal",
            role="super_admin",
            can_publish_results=True,
            can_manage_users=True,
            must_change_password=False
        )
        db.add(admin_user)
        
        # Créer une session d'examen
        session = ExamSession(
            year=2024,
            exam_type="bac",
            session_name="normale",
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 15),
            publication_date=datetime(2024, 7, 15, 14, 0, 0),
            is_published=True,
            total_candidates=1000,
            total_passed=750,
            pass_rate=75.0
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        
        # Récupérer les références
        wilayas = db.query(RefWilaya).all()
        series = db.query(RefSerie).filter(RefSerie.exam_type == "bac").all()
        etablissements = db.query(RefEtablissement).all()
        
        # Générer des résultats d'exemple
        decisions = ["Admis", "Ajourné", "Passable"]
        mentions = ["Très Bien", "Bien", "Assez Bien", "Passable", None]
        
        for i in range(100):  # 100 résultats d'exemple
            result = ExamResult(
                session_id=session.id,
                nni=f"123456789{i:02d}",
                numero_dossier=f"BAC2024{i:04d}",
                nom_complet_fr=f"Candidat Test {i:02d}",
                nom_complet_ar=f"مرشح تجريبي {i:02d}",
                lieu_naissance="Nouakchott",
                date_naissance=date(2005, random.randint(1, 12), random.randint(1, 28)),
                sexe=random.choice(["M", "F"]),
                moyenne_generale=round(random.uniform(8, 18), 2),
                decision=random.choice(decisions),
                mention=random.choice(mentions),
                rang_etablissement=random.randint(1, 50),
                rang_wilaya=random.randint(1, 200),
                rang_national=random.randint(1, 1000),
                is_published=True,
                is_verified=True,
                published_at=datetime.now(),
                wilaya_id=random.choice(wilayas).id if wilayas else None,
                serie_id=random.choice(series).id if series else None,
                etablissement_id=random.choice(etablissements).id if etablissements else None
            )
            db.add(result)
        
        db.commit()
        print("Données d'exemple générées avec succès!")
        print("Utilisateur admin créé: admin / admin123")
        
    except Exception as e:
        print(f"Erreur lors de la génération des données: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    generate_sample_data()