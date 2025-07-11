import pandas as pd
import uuid
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from fastapi import UploadFile
from models.database import ExamResult, ExamSession, RefEtablissement, RefWilaya, RefSerie
from models.schemas import BulkUploadResponse, BulkUploadStatus
import asyncio
import json

class UploadService:
    
    # Stockage global des tâches (partagé entre instances)
    _upload_tasks = {}
    
    def __init__(self, db: Session):
        self.db = db
    
    async def process_bulk_upload(self, file: UploadFile, session_id: int) -> BulkUploadResponse:
        """Traite l'upload en masse de résultats"""
        
        # Générer un ID de tâche unique
        task_id = str(uuid.uuid4())
        
        # Lire le fichier
        content = await file.read()
        
        # Déterminer le type de fichier et lire les données
        if file.filename.endswith('.csv'):
            df = pd.read_csv(pd.io.common.StringIO(content.decode('utf-8')))
        elif file.filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(pd.io.common.BytesIO(content))
        else:
            raise ValueError("Format de fichier non supporté. Utilisez CSV ou Excel.")
        
        total_rows = len(df)
        
        # Initialiser le statut de la tâche
        UploadService._upload_tasks[task_id] = BulkUploadStatus(
            task_id=task_id,
            status="pending",
            progress=0,
            total_rows=total_rows,
            processed_rows=0,
            success_count=0,
            error_count=0,
            errors=[]
        )
        
        # Lancer le traitement en arrière-plan
        print(f"Lancement traitement pour tâche {task_id} avec session_id {session_id}")
        asyncio.create_task(self._process_upload_async(task_id, df, session_id))
        
        return BulkUploadResponse(
            task_id=task_id,
            message="Upload en cours de traitement",
            total_rows=total_rows
        )
    
    async def _process_upload_async(self, task_id: str, df: pd.DataFrame, session_id: int):
        """Traite l'upload de manière asynchrone"""
        
        task_status = UploadService._upload_tasks[task_id]
        task_status.status = "processing"
        
        try:
            # Vérifier que la session existe
            session = self.db.query(ExamSession).filter(ExamSession.id == session_id).first()
            if not session:
                task_status.status = "failed"
                task_status.errors.append("Session d'examen introuvable")
                return
            
            # Créer des caches pour les références
            etablissements_cache = {e.code: e.id for e in self.db.query(RefEtablissement).all()}
            wilayas_cache = {w.code: w.id for w in self.db.query(RefWilaya).all()}
            series_cache = {s.code: s.id for s in self.db.query(RefSerie).all()}
            
            success_count = 0
            error_count = 0
            
            print(f"Début traitement {len(df)} lignes pour la tâche {task_id}")
            
            for index, row in df.iterrows():
                try:
                    # Valider et créer le résultat
                    result_data = self._validate_and_map_row(row, session_id, etablissements_cache, wilayas_cache, series_cache)
                    
                    if result_data:
                        # Vérifier si le résultat existe déjà
                        existing = self.db.query(ExamResult).filter(
                            and_(
                                ExamResult.nni == result_data["nni"],
                                ExamResult.session_id == session_id
                            )
                        ).first()
                        
                        if existing:
                            # Mettre à jour
                            for key, value in result_data.items():
                                setattr(existing, key, value)
                            print(f"Ligne {index + 1}: Mise à jour NNI {result_data['nni']}")
                        else:
                            # Créer nouveau
                            result = ExamResult(**result_data)
                            self.db.add(result)
                            print(f"Ligne {index + 1}: Ajout NNI {result_data['nni']}")
                        
                        success_count += 1
                    else:
                        error_count += 1
                        error_msg = f"Ligne {index + 2}: Données invalides"
                        task_status.errors.append(error_msg)
                        print(error_msg)
                    
                except Exception as e:
                    error_count += 1
                    error_msg = f"Ligne {index + 2}: {str(e)}"
                    task_status.errors.append(error_msg)
                    print(f"Erreur: {error_msg}")
                
                # Mettre à jour le progrès
                task_status.processed_rows = index + 1
                task_status.success_count = success_count
                task_status.error_count = error_count
                task_status.progress = int((index + 1) / len(df) * 100)
                
                # Commit par batches pour la performance
                if (index + 1) % 100 == 0:
                    try:
                        self.db.commit()
                        print(f"Commit batch à la ligne {index + 1}")
                    except Exception as e:
                        print(f"Erreur commit batch: {e}")
                        self.db.rollback()
            
            # Commit final
            try:
                self.db.commit()
                print(f"Commit final - {success_count} succès, {error_count} erreurs")
            except Exception as e:
                print(f"Erreur commit final: {e}")
                self.db.rollback()
                task_status.status = "failed"
                task_status.errors.append(f"Erreur lors du commit final: {str(e)}")
                return
            
            # Finaliser le statut
            task_status.status = "completed"
            task_status.progress = 100
            print(f"Traitement terminé pour la tâche {task_id}")
            
        except Exception as e:
            print(f"Erreur globale dans _process_upload_async: {e}")
            task_status.status = "failed"
            task_status.errors.append(f"Erreur globale: {str(e)}")
            self.db.rollback()
    
    def _validate_and_map_row(self, row: pd.Series, session_id: int, etablissements_cache: Dict, wilayas_cache: Dict, series_cache: Dict) -> Dict[str, Any]:
        """Valide et mappe une ligne du fichier vers un ExamResult"""
        
        # Mapping des colonnes selon le format mauritanien
        # (basé sur les exemples fournis dans la demande)
        
        result_data = {
            "session_id": session_id,
            "nni": str(row.get("NNI", "")).strip(),
            "numero_dossier": str(row.get("NODOSS", "")).strip() if pd.notna(row.get("NODOSS")) else None,
            "nom_complet_fr": str(row.get("NOMPL", "")).strip(),
            "nom_complet_ar": str(row.get("NOMPA", "")).strip() if pd.notna(row.get("NOMPA")) else None,
            "lieu_naissance": str(row.get("LIEUN", "")).strip() if pd.notna(row.get("LIEUN")) else None,
            "decision": str(row.get("Decision", "")).strip(),
            "is_published": True,
            "is_verified": True
        }
        
        # Date de naissance
        if pd.notna(row.get("DATN")):
            try:
                # Traiter différents formats de date
                date_str = str(row.get("DATN")).strip()
                if "/" in date_str:
                    result_data["date_naissance"] = pd.to_datetime(date_str, format="%d/%m/%y").date()
                else:
                    result_data["date_naissance"] = pd.to_datetime(date_str).date()
            except:
                pass  # Ignorer les erreurs de date
        
        # Moyenne
        if pd.notna(row.get("MOYBAC")) or pd.notna(row.get("MOYG")) or pd.notna(row.get("Total")):
            moyenne = row.get("MOYBAC") or row.get("MOYG") or row.get("Total")
            try:
                result_data["moyenne_generale"] = float(str(moyenne).replace(",", "."))
            except:
                pass
        
        # Série
        serie_code = str(row.get("SERIE", "")).strip()
        if serie_code and serie_code in series_cache:
            result_data["serie_id"] = series_cache[serie_code]
        
        # Wilaya
        wilaya_fr = str(row.get("WILAYA_FR", "")).strip()
        # Mapping simplifié - en production, utiliser une table de correspondance
        wilaya_mapping = {
            "Trarza": "06",
            "Dakhlet Nouadhibou": "08",
            "Nouakchott": "13"  # Simplifié
        }
        
        if wilaya_fr in wilaya_mapping:
            wilaya_code = wilaya_mapping[wilaya_fr]
            if wilaya_code in wilayas_cache:
                result_data["wilaya_id"] = wilayas_cache[wilaya_code]
        
        # Établissement (si disponible)
        if pd.notna(row.get("Etablissement")):
            etab_name = str(row.get("Etablissement")).strip()
            # Recherche par nom partiel (à optimiser en production)
            for code, etab_id in etablissements_cache.items():
                etab = self.db.query(RefEtablissement).filter(RefEtablissement.id == etab_id).first()
                if etab and etab_name.lower() in etab.name_fr.lower():
                    result_data["etablissement_id"] = etab_id
                    break
        
        # Validation minimale
        if not result_data["nni"] or len(result_data["nni"]) < 10:
            return None
        
        if not result_data["nom_complet_fr"]:
            return None
        
        if not result_data["decision"]:
            return None
        
        return result_data
    
    def get_upload_status(self, task_id: str) -> Optional[BulkUploadStatus]:
        """Récupère le statut d'un upload"""
        print(f"Recherche tâche {task_id}, tâches disponibles: {list(UploadService._upload_tasks.keys())}")
        return UploadService._upload_tasks.get(task_id)