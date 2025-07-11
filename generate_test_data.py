#!/usr/bin/env python3
"""
Générateur de données de test pour le système d'examens mauritaniens
Remplacez votre fichier existant par cette version corrigée
"""

import random
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.orm import Session
from database import SessionLocal
from models.database import (
    ExamSession, ExamResult, RefWilaya, RefSerie, RefEtablissement, 
    AdminUser
)
from core.security import get_password_hash

# Données réalistes mauritaniennes
NOMS_MAURITANIENS = {
    'masculin': [
        "Mohamed", "Ahmed", "Abdallahi", "Mahmoud", "Sidi", "El Moctar", "Vall",
        "Cheikh", "Mohamed Lemine", "Mohamed Salem", "Mohamed Yahya", "Brahim",
        "Moustapha", "Isselmou", "Mohamed Fadel", "Sid Ahmed", "Mohamedhen",
        "El Kori", "Bah", "Mamadou", "Alpha", "Ousmane", "Amadou", "Ibrahima"
    ],
    'feminin': [
        "Fatimetou", "Mariem", "Vatimetou", "Khadijetou", "Aminetou", "Zeina",
        "Aicha", "Coumba", "Mariam", "Fatima", "Khadija", "Safiya", "Selma",
        "Fatouma", "Mounira", "Radhia", "Habiba", "Salma", "Zeinab", "Halima"
    ]
}

NOMS_FAMILLE = [
    "Abdallahi", "Mohamed", "Ahmed", "Vall", "Salem", "Mahmoud", "Cheikh", 
    "Brahim", "El Moctar", "Sidi", "Mohamedhen", "Boubacar", "Alpha", "Mamadou", 
    "Ba", "Diallo", "Sy", "Kane", "Sow", "Barry", "El Kori", "Lemjeidri"
]

PRENOMS_PERE = [
    "Abdel Ghavour", "Mohamed Emed", "Salem", "Abdallahi", "Mohamed Sidina",
    "Mohamed Ahmed", "Mohamed Abdellahi", "Mohamed Salem", "El Moctar"
]

LIEUX_NAISSANCE = [
    "Nouakchott", "Nouadhibou", "Rosso", "Kaédi", "Zouerate", "Kiffa", "Atar",
    "Selibaby", "Boutilimit", "Aleg", "Akjoujt", "Tidjikja", "Nema", "Aioun"
]

NOMS_ARABES = [
    "محمد", "أحمد", "عبدالله", "محمود", "سيدي", "المختار", "فال",
    "فاطمة", "مريم", "فاطمتو", "خديجتو", "آمنتو", "زينة", "عائشة"
]

def generer_nni():
    """Génère un NNI mauritanien de 10 chiffres"""
    return ''.join([str(random.randint(0, 9)) for _ in range(10)])

def generer_nom_complet(sexe):
    """Génère un nom complet mauritanien selon le sexe"""
    if sexe == 'M':
        prenom = random.choice(NOMS_MAURITANIENS['masculin'])
    else:
        prenom = random.choice(NOMS_MAURITANIENS['feminin'])
    
    nom_famille = random.choice(NOMS_FAMILLE)
    
    if random.random() < 0.7:
        nom_pere = random.choice(PRENOMS_PERE)
        return f"{prenom} {nom_pere} {nom_famille}"
    else:
        return f"{prenom} {nom_famille}"

def generer_date_naissance(annee_examen, type_examen):
    """Génère une date de naissance réaliste"""
    if type_examen == "bac":
        annee = random.randint(annee_examen - 20, annee_examen - 17)
    elif type_examen == "bepc":
        annee = random.randint(annee_examen - 16, annee_examen - 14)
    else:  # concours
        annee = random.randint(annee_examen - 14, annee_examen - 12)
    
    mois = random.randint(1, 12)
    jour = random.randint(1, 28)
    return date(annee, mois, jour)

def calculer_decision_et_moyenne(exam_type):
    """Calcule la décision et moyenne selon des statistiques réalistes"""
    if exam_type == "bac":
        if random.random() < 0.40:
            decision = "Admis"
            moyenne = round(random.uniform(10.0, 18.5), 2)
            
            if moyenne >= 16:
                mention = "Très Bien"
            elif moyenne >= 14:
                mention = "Bien"  
            elif moyenne >= 12:
                mention = "Assez Bien"
            else:
                mention = "Passable"
        else:
            decision = "Ajourné"
            moyenne = round(random.uniform(2.5, 9.99), 2)
            mention = None
            
    elif exam_type == "bepc":
        if random.random() < 0.65:
            decision = "Admis"
            moyenne = round(random.uniform(10.0, 19.5), 2)
            mention = None
        else:
            decision = "Ajourné"
            moyenne = round(random.uniform(3.0, 9.99), 2)
            mention = None
            
    else:  # concours
        total_points = round(random.uniform(25.0, 145.0), 2)
        if total_points >= 80:
            decision = "Admis"
        else:
            decision = "Refusé"
        moyenne = None
        mention = None
        
    return decision, moyenne, mention, total_points if exam_type == "concours" else None

def setup_data_if_needed(db):
    """Configure les données de base si elles n'existent pas"""
    
    # 1. Créer admin si nécessaire
    admin = db.query(AdminUser).filter(AdminUser.username == "admin").first()
    if not admin:
        print("👤 Création de l'utilisateur admin...")
        admin = AdminUser(
            username="admin",
            email="admin@examens.mr",
            password_hash=get_password_hash("admin123"),
            full_name="Administrateur Test",
            role="super_admin",
            can_publish_results=True,
            can_manage_users=True,
            must_change_password=False
        )
        db.add(admin)
        db.commit()
        print("✅ Utilisateur admin créé: admin / admin123")
    
    # 2. Créer séries si nécessaire
    series_count = db.query(RefSerie).count()
    if series_count == 0:
        print("📚 Création des séries...")
        
        series_data = [
            # BAC
            ("SN", "Sciences naturelles", "العلوم الطبيعية", "bac"),
            ("M", "Mathématiques", "الرياضيات", "bac"),
            ("LM", "Lettres modernes", "الآداب العصرية", "bac"),
            ("LO", "Lettres Originales", "الآداب الأصلية", "bac"),
            # BEPC
            ("BIL", "Bilingue", "ثنائي اللغة", "bepc"),
            ("AR", "Arabe", "عربي", "bepc"),
            ("FR", "Français", "فرنسي", "bepc"),
            # Concours
            ("CONC", "Concours d'entrée", "مسابقة الدخول", "concours")
        ]
        
        for code, name_fr, name_ar, exam_type in series_data:
            serie = RefSerie(
                code=code,
                name_fr=name_fr,
                name_ar=name_ar,
                exam_type=exam_type
            )
            db.add(serie)
        
        db.commit()
        print(f"✅ {len(series_data)} séries créées")
    
    # 3. Créer sessions si nécessaire
    sessions_count = db.query(ExamSession).count()
    if sessions_count == 0:
        print("📅 Création des sessions d'examens...")
        
        sessions_data = [
            (2020, "bac", "Session normale", date(2020, 6, 1), date(2020, 6, 15)),
            (2021, "bac", "Session normale", date(2021, 6, 1), date(2021, 6, 15)),
            (2022, "bac", "Session normale", date(2022, 6, 1), date(2022, 6, 15)),
            (2023, "bepc", "Session normale", date(2023, 5, 15), date(2023, 5, 25)),
            (2024, "bepc", "Session normale", date(2024, 5, 15), date(2024, 5, 25)),
            (2023, "concours", "Concours d'entrée", date(2023, 4, 10), date(2023, 4, 12)),
            (2024, "concours", "Concours d'entrée", date(2024, 4, 10), date(2024, 4, 12)),
        ]
        
        for year, exam_type, name, start_date, end_date in sessions_data:
            session = ExamSession(
                year=year,
                exam_type=exam_type,
                session_name=name,
                start_date=start_date,
                end_date=end_date,
                publication_date=datetime.now(),
                is_published=True,
                total_candidates=0,
                total_passed=0,
                pass_rate=Decimal('0')
            )
            db.add(session)
        
        db.commit()
        print(f"✅ {len(sessions_data)} sessions créées")

def generate_results_for_session(db, session, nb_candidats):
    """Génère les résultats pour une session"""
    
    # Vérifier s'il y a déjà des résultats
    existing_count = db.query(ExamResult).filter(ExamResult.session_id == session.id).count()
    if existing_count > 0:
        print(f"✅ Session {session.exam_type.upper()} {session.year} contient déjà {existing_count} résultats")
        return
    
    print(f"📝 Génération de {nb_candidats} résultats pour {session.exam_type.upper()} {session.year}...")
    
    # Récupérer les données de référence
    series = db.query(RefSerie).filter(RefSerie.exam_type == session.exam_type).all()
    etablissements = db.query(RefEtablissement).all()
    wilayas = db.query(RefWilaya).all()
    
    if not series:
        print(f"❌ Aucune série trouvée pour {session.exam_type}")
        return
    
    if not etablissements:
        print("❌ Aucun établissement trouvé")
        return
        
    if not wilayas:
        print("❌ Aucune wilaya trouvée")
        return
    
    admis_count = 0
    
    for i in range(nb_candidats):
        # Données personnelles
        sexe = random.choice(['M', 'F'])
        nni = generer_nni()
        nom_complet_fr = generer_nom_complet(sexe)
        nom_complet_ar = random.choice(NOMS_ARABES)
        date_naissance = generer_date_naissance(session.year, session.exam_type)
        lieu_naissance = random.choice(LIEUX_NAISSANCE)
        
        # Références
        serie = random.choice(series)
        etablissement = random.choice(etablissements)
        wilaya = random.choice(wilayas)
        
        # Résultats
        decision, moyenne, mention, total_points = calculer_decision_et_moyenne(session.exam_type)
        
        if decision == "Admis":
            admis_count += 1
            rang_etab = random.randint(1, 50)
            rang_wilaya = random.randint(1, 300)
            rang_national = random.randint(1, 2000)
        else:
            rang_etab = rang_wilaya = rang_national = None
        
        # Créer le résultat
        resultat = ExamResult(
            session_id=session.id,
            nni=nni,
            numero_dossier=f"{session.exam_type.upper()}{session.year}{str(i+1).zfill(5)}",
            nom_complet_fr=nom_complet_fr,
            nom_complet_ar=nom_complet_ar,
            lieu_naissance=lieu_naissance,
            date_naissance=date_naissance,
            sexe=sexe,
            moyenne_generale=moyenne,
            total_points=total_points,
            decision=decision,
            mention=mention,
            rang_etablissement=rang_etab,
            rang_wilaya=rang_wilaya,
            rang_national=rang_national,
            etablissement_id=etablissement.id,
            serie_id=serie.id,
            wilaya_id=wilaya.id,
            is_published=True,
            is_verified=True,
            published_at=datetime.now(),
            view_count=random.randint(0, 100),
            social_share_count=random.randint(0, 10)
        )
        
        db.add(resultat)
        
        # Commit par batches
        if (i + 1) % 100 == 0:
            db.commit()
            print(f"  📊 {i + 1}/{nb_candidats} résultats générés...")
    
    # Commit final
    db.commit()
    
    # Mettre à jour les statistiques de la session
    session.total_candidates = nb_candidats
    session.total_passed = admis_count
    if nb_candidats > 0:
        session.pass_rate = Decimal(str(round((admis_count / nb_candidats) * 100, 2)))
    
    db.commit()
    
    print(f"  ✅ {nb_candidats} candidats, {admis_count} admis ({session.pass_rate}%)")

def main():
    """Fonction principale"""
    print("🇲🇷 Générateur de données de test - Examens Mauritaniens")
    print("=" * 65)
    
    db = SessionLocal()
    
    try:
        # 1. Récupérer les wilayas existantes
        print("🗺️  Récupération des wilayas...")
        wilayas = db.query(RefWilaya).all()
        if not wilayas:
            print("❌ Aucune wilaya trouvée. Assurez-vous que les wilayas sont initialisées.")
            return
        print(f"✅ {len(wilayas)} wilayas trouvées")
        
        # 2. Configurer les données de base
        setup_data_if_needed(db)
        
        # 3. Récupérer toutes les sessions
        sessions = db.query(ExamSession).all()
        print(f"📋 {len(sessions)} sessions trouvées")
        
        # 4. Générer les résultats
        print("\n📋 Génération des résultats...")
        
        candidats_config = {
            "bac": 800,       # 800 candidats par session BAC
            "bepc": 400,      # 400 candidats par session BEPC
            "concours": 200   # 200 candidats par session concours
        }
        
        for session in sessions:
            nb_candidats = candidats_config.get(session.exam_type, 300)
            generate_results_for_session(db, session, nb_candidats)
        
        # 5. Afficher le résumé
        print("\n🎉 Génération terminée avec succès!")
        print("=" * 65)
        print("📊 Résumé des sessions:")
        
        for session in sessions:
            db.refresh(session)
            results_count = db.query(ExamResult).filter(ExamResult.session_id == session.id).count()
            print(f"  • {session.exam_type.upper()} {session.year}: {results_count} candidats, {session.total_passed} admis ({session.pass_rate}%)")
        
        print(f"\n👤 Connexion admin: admin / admin123")
        print(f"🌐 Backend: http://localhost:8000")
        print(f"🌐 Frontend: http://localhost:3000")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()