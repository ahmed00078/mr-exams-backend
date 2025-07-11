-- =====================================================
-- SCHÉMA BASE DE DONNÉES - PORTAIL EXAMENS MAURITANIE
-- =====================================================

-- Extension pour UUID et fonctions avancées
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- Pour recherche floue

-- =====================================================
-- 1. TABLES DE RÉFÉRENCE (LOOKUPS)
-- =====================================================

-- Table des wilayas (régions)
CREATE TABLE ref_wilayas (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) UNIQUE NOT NULL,
    name_fr VARCHAR(100) NOT NULL,
    name_ar VARCHAR(100) NOT NULL,
    name_en VARCHAR(100),
    coordinates POINT, -- Pour cartes géographiques
    population_estimate INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Table des moughatas (départements)
CREATE TABLE ref_moughatas (
    id SERIAL PRIMARY KEY,
    wilaya_id INTEGER REFERENCES ref_wilayas(id),
    code VARCHAR(10) NOT NULL,
    name_fr VARCHAR(100) NOT NULL,
    name_ar VARCHAR(100) NOT NULL,
    name_en VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(wilaya_id, code)
);

-- Table des établissements
CREATE TABLE ref_etablissements (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL, -- Code officiel établissement
    name_fr VARCHAR(200) NOT NULL,
    name_ar VARCHAR(200) NOT NULL,
    name_en VARCHAR(200),
    type_etablissement VARCHAR(50) NOT NULL, -- 'lycee', 'college', 'ecole_primaire'
    wilaya_id INTEGER REFERENCES ref_wilayas(id),
    moughata_id INTEGER REFERENCES ref_moughatas(id),
    address_fr TEXT,
    address_ar TEXT,
    coordinates POINT,
    phone VARCHAR(20),
    email VARCHAR(100),
    director_name VARCHAR(100),
    status VARCHAR(20) DEFAULT 'active', -- 'active', 'inactive', 'merged'
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Table des séries/filières
CREATE TABLE ref_series (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) UNIQUE NOT NULL, -- 'SN', 'LM', 'BIL', etc.
    name_fr VARCHAR(100) NOT NULL,
    name_ar VARCHAR(100) NOT NULL,
    name_en VARCHAR(100),
    exam_type VARCHAR(20) NOT NULL, -- 'bac', 'bepc', 'concours'
    description_fr TEXT,
    description_ar TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Table des matières/subjects
CREATE TABLE ref_subjects (
    id SERIAL PRIMARY KEY,
    code VARCHAR(10) UNIQUE NOT NULL,
    name_fr VARCHAR(100) NOT NULL,
    name_ar VARCHAR(100) NOT NULL,
    name_en VARCHAR(100),
    coefficient DECIMAL(3,1) DEFAULT 1.0,
    is_optional BOOLEAN DEFAULT FALSE,
    exam_type VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- 2. TABLES PRINCIPALES
-- =====================================================

-- Table des sessions d'examens
CREATE TABLE exam_sessions (
    id SERIAL PRIMARY KEY,
    year INTEGER NOT NULL,
    exam_type VARCHAR(20) NOT NULL, -- 'bac', 'bepc', 'concours'
    session_name VARCHAR(50), -- 'normale', 'rattrapage', 'session1'
    start_date DATE,
    end_date DATE,
    publication_date TIMESTAMP,
    is_published BOOLEAN DEFAULT FALSE,
    is_archived BOOLEAN DEFAULT FALSE,
    total_candidates INTEGER DEFAULT 0,
    total_passed INTEGER DEFAULT 0,
    pass_rate DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(year, exam_type, session_name)
);

-- Table principale des candidats/résultats
CREATE TABLE exam_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Références
    session_id INTEGER REFERENCES exam_sessions(id),
    etablissement_id INTEGER REFERENCES ref_etablissements(id),
    serie_id INTEGER REFERENCES ref_series(id),
    wilaya_id INTEGER REFERENCES ref_wilayas(id),
    moughata_id INTEGER REFERENCES ref_moughatas(id),
    
    -- Identifiants candidat
    nni VARCHAR(20) NOT NULL, -- Numéro National d'Identification
    numero_dossier VARCHAR(20), -- N° de dossier
    numero_inscription VARCHAR(20), -- Pour concours
    numero_regional VARCHAR(10), -- Noreg
    
    -- Informations personnelles
    nom_complet_fr VARCHAR(200) NOT NULL,
    nom_complet_ar VARCHAR(200),
    nom_pere VARCHAR(150),
    lieu_naissance VARCHAR(100),
    date_naissance DATE,
    sexe CHAR(1) CHECK (sexe IN ('M', 'F')), -- 'M' ou 'F'
    
    -- Informations examen
    type_candidat VARCHAR(20) DEFAULT 'officiel', -- 'officiel', 'libre', 'redoublant'
    centre_examen VARCHAR(200),
    centre_correction VARCHAR(200),
    
    -- Résultats
    moyenne_generale DECIMAL(5,2),
    total_points DECIMAL(8,2), -- Pour concours
    decision VARCHAR(30) NOT NULL, -- 'Admis', 'Ajourné', 'Passable', etc.
    mention VARCHAR(30), -- 'Très Bien', 'Bien', 'Assez Bien', etc.
    rang_etablissement INTEGER, -- Classement dans l'établissement
    rang_wilaya INTEGER, -- Classement dans la wilaya
    rang_national INTEGER, -- Classement national
    
    -- Métadonnées
    is_published BOOLEAN DEFAULT FALSE,
    is_verified BOOLEAN DEFAULT TRUE,
    published_at TIMESTAMP,
    social_share_count INTEGER DEFAULT 0,
    view_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Table des notes détaillées par matière
CREATE TABLE exam_subject_scores (
    id SERIAL PRIMARY KEY,
    result_id UUID REFERENCES exam_results(id) ON DELETE CASCADE,
    subject_id INTEGER REFERENCES ref_subjects(id),
    
    -- Notes
    note_controle DECIMAL(5,2), -- Note contrôle continu
    note_examen DECIMAL(5,2), -- Note examen final
    note_finale DECIMAL(5,2) NOT NULL, -- Note finale calculée
    coefficient DECIMAL(3,1) DEFAULT 1.0,
    
    -- Détails
    is_optional BOOLEAN DEFAULT FALSE,
    is_rattrapage BOOLEAN DEFAULT FALSE,
    appreciation VARCHAR(50), -- 'Excellent', 'Bien', etc.
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- 3. TABLES D'AGRÉGATION (POUR PERFORMANCE)
-- =====================================================

-- Statistiques par établissement
CREATE TABLE stats_etablissements (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES exam_sessions(id),
    etablissement_id INTEGER REFERENCES ref_etablissements(id),
    serie_id INTEGER REFERENCES ref_series(id),
    
    -- Statistiques
    total_candidats INTEGER DEFAULT 0,
    total_admis INTEGER DEFAULT 0,
    total_ajournes INTEGER DEFAULT 0,
    taux_reussite DECIMAL(5,2) DEFAULT 0,
    moyenne_etablissement DECIMAL(5,2),
    
    -- Répartition par mention
    mention_tres_bien INTEGER DEFAULT 0,
    mention_bien INTEGER DEFAULT 0,
    mention_assez_bien INTEGER DEFAULT 0,
    mention_passable INTEGER DEFAULT 0,
    
    -- Répartition par genre
    candidats_masculins INTEGER DEFAULT 0,
    candidats_feminins INTEGER DEFAULT 0,
    admis_masculins INTEGER DEFAULT 0,
    admis_feminins INTEGER DEFAULT 0,
    
    -- Métadonnées
    last_calculated TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(session_id, etablissement_id, serie_id)
);

-- Statistiques par wilaya
CREATE TABLE stats_wilayas (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES exam_sessions(id),
    wilaya_id INTEGER REFERENCES ref_wilayas(id),
    exam_type VARCHAR(20) NOT NULL,
    
    -- Statistiques globales
    total_candidats INTEGER DEFAULT 0,
    total_admis INTEGER DEFAULT 0,
    taux_reussite DECIMAL(5,2) DEFAULT 0,
    moyenne_wilaya DECIMAL(5,2),
    rang_national INTEGER, -- Classement de la wilaya
    
    -- Par série
    stats_par_serie JSONB, -- Structure flexible pour différentes séries
    
    -- Par genre
    candidats_masculins INTEGER DEFAULT 0,
    candidats_feminins INTEGER DEFAULT 0,
    admis_masculins INTEGER DEFAULT 0,
    admis_feminins INTEGER DEFAULT 0,
    
    -- Évolution
    evolution_vs_annee_precedente DECIMAL(5,2), -- En pourcentage
    
    -- Métadonnées
    last_calculated TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(session_id, wilaya_id, exam_type)
);

-- =====================================================
-- 4. TABLES POUR PARTAGE SOCIAL
-- =====================================================

-- Table pour générer des liens de partage uniques
CREATE TABLE social_shares (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    result_id UUID REFERENCES exam_results(id),
    share_token VARCHAR(100) UNIQUE NOT NULL,
    candidate_name VARCHAR(200) NOT NULL,
    exam_type VARCHAR(20) NOT NULL,
    decision VARCHAR(30) NOT NULL,
    moyenne DECIMAL(5,2),
    etablissement VARCHAR(200),
    wilaya VARCHAR(100),
    year INTEGER NOT NULL,
    
    -- Métadonnées partage
    platform VARCHAR(20), -- 'facebook', 'twitter', 'whatsapp', 'telegram'
    is_anonymous BOOLEAN DEFAULT FALSE, -- Partage anonymisé
    expiry_date TIMESTAMP, -- Date d'expiration du lien
    click_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- 5. TABLES SYSTÈME ET AUDIT
-- =====================================================

-- Table des utilisateurs admin
CREATE TABLE admin_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'operator', -- 'super_admin', 'admin', 'operator', 'viewer'
    
    -- Permissions spécifiques
    can_publish_results BOOLEAN DEFAULT FALSE,
    can_manage_users BOOLEAN DEFAULT FALSE,
    can_view_analytics BOOLEAN DEFAULT TRUE,
    allowed_wilayas INTEGER[], -- Restriction par wilaya si nécessaire
    
    -- Sécurité
    last_login TIMESTAMP,
    login_attempts INTEGER DEFAULT 0,
    is_locked BOOLEAN DEFAULT FALSE,
    must_change_password BOOLEAN DEFAULT TRUE,
    two_factor_enabled BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Table d'audit/logs
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES admin_users(id),
    action VARCHAR(50) NOT NULL, -- 'create', 'update', 'delete', 'publish', 'search'
    entity_type VARCHAR(50) NOT NULL, -- 'exam_result', 'session', 'user'
    entity_id VARCHAR(100), -- ID de l'entité modifiée
    old_values JSONB, -- Anciennes valeurs
    new_values JSONB, -- Nouvelles valeurs
    ip_address INET,
    user_agent TEXT,
    session_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Table pour configuration système
CREATE TABLE system_config (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value TEXT,
    description TEXT,
    is_public BOOLEAN DEFAULT FALSE, -- Visible côté public
    updated_by INTEGER REFERENCES admin_users(id),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- 6. INDEX POUR PERFORMANCE
-- =====================================================

-- Index principaux pour recherche
CREATE INDEX idx_exam_results_nni ON exam_results(nni);
CREATE INDEX idx_exam_results_numero_dossier ON exam_results(numero_dossier);
CREATE INDEX idx_exam_results_session_published ON exam_results(session_id, is_published);
CREATE INDEX idx_exam_results_etablissement ON exam_results(etablissement_id);
CREATE INDEX idx_exam_results_wilaya ON exam_results(wilaya_id);
CREATE INDEX idx_exam_results_serie ON exam_results(serie_id);
CREATE INDEX idx_exam_results_decision ON exam_results(decision);

-- Index pour recherche par nom (avec trigram pour recherche floue)
CREATE INDEX idx_exam_results_nom_trgm ON exam_results USING gin (nom_complet_fr gin_trgm_ops);
CREATE INDEX idx_exam_results_nom_ar_trgm ON exam_results USING gin (nom_complet_ar gin_trgm_ops);

-- Index composites pour queries fréquentes
CREATE INDEX idx_exam_results_session_wilaya_serie ON exam_results(session_id, wilaya_id, serie_id);
CREATE INDEX idx_exam_results_published_session ON exam_results(is_published, session_id) WHERE is_published = true;

-- Index pour statistiques
CREATE INDEX idx_stats_etablissements_session ON stats_etablissements(session_id);
CREATE INDEX idx_stats_wilayas_session ON stats_wilayas(session_id);

-- Index pour partage social
CREATE INDEX idx_social_shares_token ON social_shares(share_token);
CREATE INDEX idx_social_shares_result ON social_shares(result_id);

-- =====================================================
-- 6.1. CONTRAINTES SUPPLÉMENTAIRES (AJOUT)
-- =====================================================

-- Contrainte sur la moyenne (doit être entre 0 et 20)
ALTER TABLE exam_results ADD CONSTRAINT check_moyenne 
CHECK (moyenne_generale >= 0 AND moyenne_generale <= 20);

-- Contrainte d'unicité: un candidat = un résultat par session
ALTER TABLE exam_results ADD CONSTRAINT unique_nni_session 
UNIQUE (nni, session_id);

-- Contrainte d'unicité sur numéro de dossier (si présent)
CREATE UNIQUE INDEX IF NOT EXISTS unique_dossier_session 
ON exam_results (numero_dossier, session_id) 
WHERE numero_dossier IS NOT NULL;

-- =====================================================
-- 8. FONCTIONS UTILITAIRES
-- =====================================================

-- Fonction pour calculer les statistiques d'un établissement
CREATE OR REPLACE FUNCTION calculate_etablissement_stats(p_session_id INTEGER, p_etablissement_id INTEGER)
RETURNS VOID AS $$
BEGIN
    INSERT INTO stats_etablissements (
        session_id, etablissement_id, serie_id, total_candidats, total_admis,
        taux_reussite, moyenne_etablissement, candidats_masculins, candidats_feminins,
        admis_masculins, admis_feminins
    )
    SELECT 
        p_session_id,
        p_etablissement_id,
        serie_id,
        COUNT(*) as total_candidats,
        COUNT(*) FILTER (WHERE decision IN ('Admis', 'Passable')) as total_admis,
        ROUND(
            (COUNT(*) FILTER (WHERE decision IN ('Admis', 'Passable'))::DECIMAL / COUNT(*)) * 100, 2
        ) as taux_reussite,
        ROUND(AVG(moyenne_generale), 2) as moyenne_etablissement,
        COUNT(*) FILTER (WHERE sexe = 'M') as candidats_masculins,
        COUNT(*) FILTER (WHERE sexe = 'F') as candidats_feminins,
        COUNT(*) FILTER (WHERE sexe = 'M' AND decision IN ('Admis', 'Passable')) as admis_masculins,
        COUNT(*) FILTER (WHERE sexe = 'F' AND decision IN ('Admis', 'Passable')) as admis_feminins
    FROM exam_results 
    WHERE session_id = p_session_id 
    AND etablissement_id = p_etablissement_id 
    AND is_published = true
    GROUP BY serie_id
    ON CONFLICT (session_id, etablissement_id, serie_id) 
    DO UPDATE SET
        total_candidats = EXCLUDED.total_candidats,
        total_admis = EXCLUDED.total_admis,
        taux_reussite = EXCLUDED.taux_reussite,
        moyenne_etablissement = EXCLUDED.moyenne_etablissement,
        candidats_masculins = EXCLUDED.candidats_masculins,
        candidats_feminins = EXCLUDED.candidats_feminins,
        admis_masculins = EXCLUDED.admis_masculins,
        admis_feminins = EXCLUDED.admis_feminins,
        last_calculated = NOW();
END;
$$ LANGUAGE plpgsql;

-- Fonction pour générer un token de partage social
CREATE OR REPLACE FUNCTION generate_social_share_token(p_result_id UUID, p_platform VARCHAR)
RETURNS VARCHAR AS $$
DECLARE
    v_token VARCHAR(100);
    v_result RECORD;
BEGIN
    -- Récupérer les infos du résultat
    SELECT er.nom_complet_fr, er.decision, er.moyenne_generale, et.name_fr, rw.name_fr, es.year, es.exam_type
    INTO v_result
    FROM exam_results er
    JOIN exam_sessions es ON er.session_id = es.id
    LEFT JOIN ref_etablissements et ON er.etablissement_id = et.id
    LEFT JOIN ref_wilayas rw ON er.wilaya_id = rw.id
    WHERE er.id = p_result_id;
    
    -- Générer token unique
    v_token := encode(digest(p_result_id::text || p_platform || extract(epoch from now())::text, 'sha256'), 'hex');
    v_token := substring(v_token, 1, 32);
    
    -- Insérer dans la table de partage
    INSERT INTO social_shares (
        result_id, share_token, candidate_name, exam_type, decision, 
        moyenne, etablissement, wilaya, year, platform, expiry_date
    ) VALUES (
        p_result_id, v_token, v_result.nom_complet_fr, v_result.exam_type, v_result.decision,
        v_result.moyenne_generale, v_result.name_fr, v_result.name_fr, v_result.year, 
        p_platform, NOW() + INTERVAL '30 days'
    );
    
    RETURN v_token;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 9. DONNÉES DE RÉFÉRENCE INITIALES
-- =====================================================

-- Insertion des wilayas mauritaniennes
INSERT INTO ref_wilayas (code, name_fr, name_ar) VALUES
    ('01', 'Hodh Ech Chargui', 'الحوض الشرقي'),
    ('02', 'Hodh El Gharbi', 'الحوض الغربي'),
    ('03', 'Assaba', 'العصابة'),
    ('04', 'Gorgol', 'كركول'),
    ('05', 'Brakna', 'البراكنة'),
    ('06', 'Trarza', 'اترارزه'),
    ('07', 'Adrar', 'أدرار'),
    ('08', 'Dakhlet Nouadhibou', 'داخلة نواذيبو'),
    ('09', 'Tagant', 'تكانت'),
    ('10', 'Guidimaka', 'كيديماغا'),
    ('11', 'Tiris Zemmour', 'تيرس زمور'),
    ('12', 'Inchiri', 'انشيري'),
    ('13', 'Nouakchott Nord', 'نواكشوط الشمالية'),
    ('14', 'Nouakchott Ouest', 'نواكشوط الغربية'),
    ('15', 'Nouakchott Sud', 'نواكشوط الجنوبية')
ON CONFLICT (code) DO UPDATE SET
    name_fr = EXCLUDED.name_fr,
    name_ar = EXCLUDED.name_ar;

-- Insertion des séries principales
INSERT INTO ref_series (code, name_fr, name_ar, exam_type)
VALUES
    ('SN', 'Sciences naturelles', 'العلوم الطبيعية', 'bac'),
    ('M', 'Mathématiques', 'الرياضيات', 'bac'),
    ('LM', 'Lettres modernes', 'الآداب العصرية', 'bac'),
    ('LO', 'Lettres Originales', 'الآداب الأصلية', 'bac'),
    ('TM', 'Filière technique', 'الشعبة التقنية', 'bac'),
    ('TS', 'Génie électrique', 'الهندسة الكهربائية', 'bac'),
    ('LA', 'Langues ', 'اللغات', 'bac')
ON CONFLICT (code) DO UPDATE SET
    name_fr = EXCLUDED.name_fr,
    name_ar = EXCLUDED.name_ar,
    exam_type = EXCLUDED.exam_type;


-- Configuration système initiale
INSERT INTO system_config (config_key, config_value, description, is_public)
VALUES
    ('site_title_fr', 'Portail des Résultats d''Examens - Mauritanie', 'Titre du site en français', true),
    ('site_title_ar', 'بوابة نتائج الامتحانات - موريتانيا', 'Titre du site en arabe', true),
    ('maintenance_mode', 'false', 'Mode maintenance activé', false),
    ('results_per_page', '50', 'Nombre de résultats par page', false),
    ('social_share_enabled', 'true', 'Partage social activé', true),
    ('max_search_results', '1000', 'Nombre maximum de résultats de recherche', false)
ON CONFLICT (config_key) DO NOTHING;

-- =====================================================
-- 10. TRIGGERS POUR AUDIT ET MAINTENANCE
-- =====================================================

-- Trigger pour mettre à jour updated_at automatiquement
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Appliquer le trigger aux tables principales
CREATE TRIGGER update_exam_results_updated_at BEFORE UPDATE ON exam_results FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_exam_sessions_updated_at BEFORE UPDATE ON exam_sessions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_etablissements_updated_at BEFORE UPDATE ON ref_etablissements FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_admin_users_updated_at BEFORE UPDATE ON admin_users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- FIN DU SCHÉMA
-- =====================================================