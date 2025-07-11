from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from models.database import (
    ExamResult, ExamSession, RefEtablissement, RefWilaya, RefSerie
)
from models.schemas import StatsEtablissement, StatsWilaya
from core.cache import cache_manager

class StatsService:
    
    def __init__(self, db: Session):
        self.db = db
    
    async def get_wilaya_stats(self, wilaya_id: int, year: int, exam_type: str) -> Optional[StatsWilaya]:
        """Récupère les statistiques d'une wilaya avec cache"""
        
        # Vérifier le cache
        cached_stats = await cache_manager.get_cached_stats("wilaya", wilaya_id, year)
        if cached_stats and cached_stats.get("exam_type") == exam_type:
            return StatsWilaya(**cached_stats)
        
        # Récupérer la session
        session = self.db.query(ExamSession).filter(
            and_(ExamSession.year == year, ExamSession.exam_type == exam_type)
        ).first()
        
        if not session:
            return None
        
        # Récupérer la wilaya
        wilaya = self.db.query(RefWilaya).filter(RefWilaya.id == wilaya_id).first()
        if not wilaya:
            return None
        
        # Calculer les statistiques
        results = self.db.query(ExamResult).filter(
            and_(
                ExamResult.session_id == session.id,
                ExamResult.wilaya_id == wilaya_id,
                ExamResult.is_published == True
            )
        ).all()
        
        if not results:
            return None
        
        total_candidats = len(results)
        admis = [r for r in results if r.decision in ['Admis', 'Passable']]
        total_admis = len(admis)
        taux_reussite = round((total_admis / total_candidats * 100), 2) if total_candidats > 0 else 0
        
        # Moyenne de la wilaya
        moyennes = [r.moyenne_generale for r in results if r.moyenne_generale is not None]
        moyenne_wilaya = round(sum(moyennes) / len(moyennes), 2) if moyennes else None
        
        # Statistiques par série
        stats_par_serie = {}
        series = self.db.query(RefSerie).filter(RefSerie.exam_type == exam_type).all()
        
        for serie in series:
            serie_results = [r for r in results if r.serie_id == serie.id]
            if serie_results:
                serie_admis = [r for r in serie_results if r.decision in ['Admis', 'Passable']]
                stats_par_serie[serie.code] = {
                    "name_fr": serie.name_fr,
                    "name_ar": serie.name_ar,
                    "candidats": len(serie_results),
                    "admis": len(serie_admis),
                    "taux_reussite": round((len(serie_admis) / len(serie_results) * 100), 2)
                }
        
        # Calculer le rang national (simplifié)
        all_wilayas_stats = self.db.query(
            ExamResult.wilaya_id,
            func.count(ExamResult.id).label('total'),
            func.count().filter(ExamResult.decision.in_(['Admis', 'Passable'])).label('admis')
        ).filter(
            and_(ExamResult.session_id == session.id, ExamResult.is_published == True)
        ).group_by(ExamResult.wilaya_id).all()
        
        wilaya_rates = []
        for w_stat in all_wilayas_stats:
            if w_stat.total > 0:
                rate = (w_stat.admis / w_stat.total) * 100
                wilaya_rates.append((w_stat.wilaya_id, rate))
        
        wilaya_rates.sort(key=lambda x: x[1], reverse=True)
        rang_national = next((i+1 for i, (w_id, _) in enumerate(wilaya_rates) if w_id == wilaya_id), None)
        
        stats_data = {
            "wilaya_id": wilaya_id,
            "wilaya_name": wilaya.name_fr,
            "total_candidats": total_candidats,
            "total_admis": total_admis,
            "taux_reussite": taux_reussite,
            "moyenne_wilaya": moyenne_wilaya,
            "rang_national": rang_national,
            "stats_par_serie": stats_par_serie,
            "exam_type": exam_type
        }
        
        # Mettre en cache
        await cache_manager.cache_stats("wilaya", wilaya_id, year, stats_data)
        
        return StatsWilaya(**stats_data)
    
    async def get_etablissement_stats(self, etablissement_id: int, year: int, exam_type: str) -> Optional[StatsEtablissement]:
        """Récupère les statistiques d'un établissement"""
        
        # Vérifier le cache
        cached_stats = await cache_manager.get_cached_stats("etablissement", etablissement_id, year)
        if cached_stats and cached_stats.get("exam_type") == exam_type:
            return StatsEtablissement(**cached_stats)
        
        # Récupérer la session
        session = self.db.query(ExamSession).filter(
            and_(ExamSession.year == year, ExamSession.exam_type == exam_type)
        ).first()
        
        if not session:
            return None
        
        # Récupérer l'établissement
        etablissement = self.db.query(RefEtablissement).filter(RefEtablissement.id == etablissement_id).first()
        if not etablissement:
            return None
        
        # Calculer les statistiques
        results = self.db.query(ExamResult).filter(
            and_(
                ExamResult.session_id == session.id,
                ExamResult.etablissement_id == etablissement_id,
                ExamResult.is_published == True
            )
        ).all()
        
        if not results:
            return None
        
        total_candidats = len(results)
        admis = [r for r in results if r.decision in ['Admis', 'Passable']]
        total_admis = len(admis)
        taux_reussite = round((total_admis / total_candidats * 100), 2) if total_candidats > 0 else 0
        
        # Moyenne de l'établissement
        moyennes = [r.moyenne_generale for r in results if r.moyenne_generale is not None]
        moyenne_etablissement = round(sum(moyennes) / len(moyennes), 2) if moyennes else None
        
        # Rang dans la wilaya
        wilaya_etablissements = self.db.query(
            ExamResult.etablissement_id,
            func.count(ExamResult.id).label('total'),
            func.count().filter(ExamResult.decision.in_(['Admis', 'Passable'])).label('admis')
        ).filter(
            and_(
                ExamResult.session_id == session.id,
                ExamResult.wilaya_id == etablissement.wilaya_id,
                ExamResult.is_published == True
            )
        ).group_by(ExamResult.etablissement_id).all()
        
        etab_rates = []
        for e_stat in wilaya_etablissements:
            if e_stat.total > 0:
                rate = (e_stat.admis / e_stat.total) * 100
                etab_rates.append((e_stat.etablissement_id, rate))
        
        etab_rates.sort(key=lambda x: x[1], reverse=True)
        rang_wilaya = next((i+1 for i, (e_id, _) in enumerate(etab_rates) if e_id == etablissement_id), None)
        
        stats_data = {
            "etablissement_id": etablissement_id,
            "etablissement_name": etablissement.name_fr,
            "total_candidats": total_candidats,
            "total_admis": total_admis,
            "taux_reussite": taux_reussite,
            "moyenne_etablissement": moyenne_etablissement,
            "rang_wilaya": rang_wilaya,
            "exam_type": exam_type
        }
        
        # Mettre en cache
        await cache_manager.cache_stats("etablissement", etablissement_id, year, stats_data)
        
        return StatsEtablissement(**stats_data)
    
    def get_global_stats(self, year: int, exam_type: str) -> Dict[str, Any]:
        """Récupère les statistiques globales"""
        
        session = self.db.query(ExamSession).filter(
            and_(ExamSession.year == year, ExamSession.exam_type == exam_type)
        ).first()
        
        if not session:
            return {}
        
        # Statistiques par wilaya
        wilaya_stats = self.db.query(
            RefWilaya.id,
            RefWilaya.name_fr,
            RefWilaya.name_ar,
            func.count(ExamResult.id).label('total_candidats'),
            func.count().filter(ExamResult.decision.in_(['Admis', 'Passable'])).label('total_admis'),
            func.avg(ExamResult.moyenne_generale).label('moyenne')
        ).join(
            ExamResult, RefWilaya.id == ExamResult.wilaya_id
        ).filter(
            and_(ExamResult.session_id == session.id, ExamResult.is_published == True)
        ).group_by(RefWilaya.id, RefWilaya.name_fr, RefWilaya.name_ar).all()
        
        # Statistiques par série
        serie_stats = self.db.query(
            RefSerie.id,
            RefSerie.code,
            RefSerie.name_fr,
            RefSerie.name_ar,
            func.count(ExamResult.id).label('total_candidats'),
            func.count().filter(ExamResult.decision.in_(['Admis', 'Passable'])).label('total_admis')
        ).join(
            ExamResult, RefSerie.id == ExamResult.serie_id
        ).filter(
            and_(ExamResult.session_id == session.id, ExamResult.is_published == True)
        ).group_by(RefSerie.id, RefSerie.code, RefSerie.name_fr, RefSerie.name_ar).all()
        
        # Trier les wilayas par taux de réussite décroissant
        wilayas_sorted = []
        for w in wilaya_stats:
            if w.total_candidats > 0:
                taux_reussite = round((w.total_admis / w.total_candidats * 100), 2)
                wilayas_sorted.append({
                    "id": w.id,
                    "name_fr": w.name_fr,
                    "name_ar": w.name_ar,
                    "candidats": w.total_candidats,
                    "admis": w.total_admis,
                    "taux_reussite": taux_reussite,
                    "moyenne": round(float(w.moyenne), 2) if w.moyenne else None
                })
        
        # Trier par taux de réussite décroissant
        wilayas_sorted.sort(key=lambda x: x["taux_reussite"], reverse=True)
        
        # Trier les séries par taux de réussite décroissant
        series_sorted = []
        for s in serie_stats:
            if s.total_candidats > 0:
                taux_reussite = round((s.total_admis / s.total_candidats * 100), 2)
                series_sorted.append({
                    "id": s.id,
                    "code": s.code,
                    "name_fr": s.name_fr,
                    "name_ar": s.name_ar,
                    "candidats": s.total_candidats,
                    "admis": s.total_admis,
                    "taux_reussite": taux_reussite
                })
        
        # Trier par taux de réussite décroissant
        series_sorted.sort(key=lambda x: x["taux_reussite"], reverse=True)

        # Calculer le nombre d'établissements ayant des candidats
        total_etablissements = self.db.query(
            func.count(func.distinct(ExamResult.etablissement_id))
        ).filter(
            and_(ExamResult.session_id == session.id, ExamResult.is_published == True)
        ).scalar()

        return {
            "year": year,
            "exam_type": exam_type,
            "total_candidats": session.total_candidates,
            "total_admis": session.total_passed,
            "taux_reussite_global": float(session.pass_rate) if session.pass_rate else 0,
            "total_etablissements": total_etablissements or 0,
            "wilayas": wilayas_sorted,
            "series": series_sorted
        }
    
    def get_top_students(self, year: int, exam_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Récupère le top des élèves pour une année donnée"""
        
        session = self.db.query(ExamSession).filter(
            and_(ExamSession.year == year, ExamSession.exam_type == exam_type)
        ).first()
        
        if not session:
            return []
        
        # Récupérer les meilleurs élèves
        top_students = self.db.query(
            ExamResult.id,
            ExamResult.nom_complet_fr,
            ExamResult.moyenne_generale,
            ExamResult.decision,
            RefWilaya.name_fr.label('wilaya_name'),
            RefSerie.code.label('serie_code'),
            RefEtablissement.name_fr.label('etablissement_name')
        ).join(
            RefWilaya, ExamResult.wilaya_id == RefWilaya.id
        ).join(
            RefSerie, ExamResult.serie_id == RefSerie.id
        ).join(
            RefEtablissement, ExamResult.etablissement_id == RefEtablissement.id
        ).filter(
            and_(
                ExamResult.session_id == session.id,
                ExamResult.is_published == True,
                ExamResult.decision.in_(['Admis', 'Passable']),
                ExamResult.moyenne_generale.isnot(None)
            )
        ).order_by(desc(ExamResult.moyenne_generale)).limit(limit).all()
        
        return [
            {
                "id": str(student.id),
                "nom_complet": student.nom_complet_fr,
                "moyenne": float(student.moyenne_generale),
                "decision": student.decision,
                "wilaya": student.wilaya_name,
                "serie": student.serie_code,
                "etablissement": student.etablissement_name
            }
            for student in top_students
        ]
    
    def get_top_schools(self, year: int, exam_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Récupère le top des écoles pour une année donnée"""
        
        session = self.db.query(ExamSession).filter(
            and_(ExamSession.year == year, ExamSession.exam_type == exam_type)
        ).first()
        
        if not session:
            return []
        
        # Calculer les statistiques par établissement
        etablissement_stats = self.db.query(
            RefEtablissement.id,
            RefEtablissement.name_fr,
            RefEtablissement.name_ar,
            RefWilaya.name_fr.label('wilaya_name'),
            func.count(ExamResult.id).label('total_candidats'),
            func.count().filter(ExamResult.decision.in_(['Admis', 'Passable'])).label('total_admis'),
            func.avg(ExamResult.moyenne_generale).label('moyenne_etablissement')
        ).join(
            ExamResult, RefEtablissement.id == ExamResult.etablissement_id
        ).join(
            RefWilaya, RefEtablissement.wilaya_id == RefWilaya.id
        ).filter(
            and_(
                ExamResult.session_id == session.id,
                ExamResult.is_published == True
            )
        ).group_by(
            RefEtablissement.id,
            RefEtablissement.name_fr,
            RefEtablissement.name_ar,
            RefWilaya.name_fr
        ).having(
            func.count(ExamResult.id) >= 5  # Au moins 5 candidats pour être considéré
        ).all()
        
        # Calculer le taux de réussite et trier
        schools_with_rates = []
        for etab in etablissement_stats:
            if etab.total_candidats > 0:
                taux_reussite = round((etab.total_admis / etab.total_candidats * 100), 2)
                schools_with_rates.append({
                    "id": etab.id,
                    "nom": etab.name_fr,
                    "wilaya": etab.wilaya_name,
                    "candidats": etab.total_candidats,
                    "admis": etab.total_admis,
                    "taux_reussite": taux_reussite,
                    "moyenne": round(float(etab.moyenne_etablissement), 2) if etab.moyenne_etablissement else None
                })
        
        # Trier par taux de réussite puis par moyenne
        schools_with_rates.sort(key=lambda x: (x["taux_reussite"], x["moyenne"] or 0), reverse=True)
        
        return schools_with_rates[:limit]