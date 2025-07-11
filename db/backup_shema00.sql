--
-- PostgreSQL database dump
--

-- Dumped from database version 17.5
-- Dumped by pg_dump version 17.5

-- Started on 2025-07-10 21:52:56

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- TOC entry 3 (class 3079 OID 16401)
-- Name: pg_trgm; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;


--
-- TOC entry 5201 (class 0 OID 0)
-- Dependencies: 3
-- Name: EXTENSION pg_trgm; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pg_trgm IS 'text similarity measurement and index searching based on trigrams';


--
-- TOC entry 2 (class 3079 OID 16390)
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- TOC entry 5202 (class 0 OID 0)
-- Dependencies: 2
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- TOC entry 300 (class 1255 OID 16795)
-- Name: calculate_etablissement_stats(integer, integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.calculate_etablissement_stats(p_session_id integer, p_etablissement_id integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
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
$$;


ALTER FUNCTION public.calculate_etablissement_stats(p_session_id integer, p_etablissement_id integer) OWNER TO postgres;

--
-- TOC entry 301 (class 1255 OID 16796)
-- Name: generate_social_share_token(uuid, character varying); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.generate_social_share_token(p_result_id uuid, p_platform character varying) RETURNS character varying
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_token VARCHAR(100);
    v_result RECORD;
BEGIN
    -- RÃ©cupÃ©rer les infos du rÃ©sultat
    SELECT er.nom_complet_fr, er.decision, er.moyenne_generale, et.name_fr, rw.name_fr, es.year, es.exam_type
    INTO v_result
    FROM exam_results er
    JOIN exam_sessions es ON er.session_id = es.id
    LEFT JOIN ref_etablissements et ON er.etablissement_id = et.id
    LEFT JOIN ref_wilayas rw ON er.wilaya_id = rw.id
    WHERE er.id = p_result_id;
    
    -- GÃ©nÃ©rer token unique
    v_token := encode(digest(p_result_id::text || p_platform || extract(epoch from now())::text, 'sha256'), 'hex');
    v_token := substring(v_token, 1, 32);
    
    -- InsÃ©rer dans la table de partage
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
$$;


ALTER FUNCTION public.generate_social_share_token(p_result_id uuid, p_platform character varying) OWNER TO postgres;

--
-- TOC entry 299 (class 1255 OID 16797)
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION public.update_updated_at_column() OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 240 (class 1259 OID 16720)
-- Name: admin_users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.admin_users (
    id integer NOT NULL,
    username character varying(50) NOT NULL,
    email character varying(100) NOT NULL,
    password_hash character varying(255) NOT NULL,
    full_name character varying(100) NOT NULL,
    role character varying(20) DEFAULT 'operator'::character varying NOT NULL,
    can_publish_results boolean DEFAULT false,
    can_manage_users boolean DEFAULT false,
    can_view_analytics boolean DEFAULT true,
    allowed_wilayas integer[],
    last_login timestamp without time zone,
    login_attempts integer DEFAULT 0,
    is_locked boolean DEFAULT false,
    must_change_password boolean DEFAULT true,
    two_factor_enabled boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.admin_users OWNER TO postgres;

--
-- TOC entry 239 (class 1259 OID 16719)
-- Name: admin_users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.admin_users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.admin_users_id_seq OWNER TO postgres;

--
-- TOC entry 5203 (class 0 OID 0)
-- Dependencies: 239
-- Name: admin_users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.admin_users_id_seq OWNED BY public.admin_users.id;


--
-- TOC entry 242 (class 1259 OID 16743)
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.audit_logs (
    id integer NOT NULL,
    user_id integer,
    action character varying(50) NOT NULL,
    entity_type character varying(50) NOT NULL,
    entity_id character varying(100),
    old_values jsonb,
    new_values jsonb,
    ip_address inet,
    user_agent text,
    session_id character varying(100),
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.audit_logs OWNER TO postgres;

--
-- TOC entry 241 (class 1259 OID 16742)
-- Name: audit_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.audit_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.audit_logs_id_seq OWNER TO postgres;

--
-- TOC entry 5204 (class 0 OID 0)
-- Dependencies: 241
-- Name: audit_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.audit_logs_id_seq OWNED BY public.audit_logs.id;


--
-- TOC entry 231 (class 1259 OID 16571)
-- Name: exam_results; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.exam_results (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    session_id integer,
    etablissement_id integer,
    serie_id integer,
    wilaya_id integer,
    moughata_id integer,
    nni character varying(20) NOT NULL,
    numero_dossier character varying(20),
    numero_inscription character varying(20),
    numero_regional character varying(10),
    nom_complet_fr character varying(200) NOT NULL,
    nom_complet_ar character varying(200),
    nom_pere character varying(150),
    lieu_naissance character varying(100),
    date_naissance date,
    sexe character(1),
    type_candidat character varying(20) DEFAULT 'officiel'::character varying,
    centre_examen character varying(200),
    centre_correction character varying(200),
    moyenne_generale numeric(5,2),
    total_points numeric(8,2),
    decision character varying(30) NOT NULL,
    mention character varying(30),
    rang_etablissement integer,
    rang_wilaya integer,
    rang_national integer,
    is_published boolean DEFAULT false,
    is_verified boolean DEFAULT true,
    published_at timestamp without time zone,
    social_share_count integer DEFAULT 0,
    view_count integer DEFAULT 0,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now(),
    CONSTRAINT check_moyenne CHECK (((moyenne_generale >= (0)::numeric) AND (moyenne_generale <= (20)::numeric))),
    CONSTRAINT exam_results_sexe_check CHECK ((sexe = ANY (ARRAY['M'::bpchar, 'F'::bpchar])))
);


ALTER TABLE public.exam_results OWNER TO postgres;

--
-- TOC entry 230 (class 1259 OID 16557)
-- Name: exam_sessions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.exam_sessions (
    id integer NOT NULL,
    year integer NOT NULL,
    exam_type character varying(20) NOT NULL,
    session_name character varying(50),
    start_date date,
    end_date date,
    publication_date timestamp without time zone,
    is_published boolean DEFAULT false,
    is_archived boolean DEFAULT false,
    total_candidates integer DEFAULT 0,
    total_passed integer DEFAULT 0,
    pass_rate numeric(5,2),
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.exam_sessions OWNER TO postgres;

--
-- TOC entry 229 (class 1259 OID 16556)
-- Name: exam_sessions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.exam_sessions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.exam_sessions_id_seq OWNER TO postgres;

--
-- TOC entry 5205 (class 0 OID 0)
-- Dependencies: 229
-- Name: exam_sessions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.exam_sessions_id_seq OWNED BY public.exam_sessions.id;


--
-- TOC entry 233 (class 1259 OID 16613)
-- Name: exam_subject_scores; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.exam_subject_scores (
    id integer NOT NULL,
    result_id uuid,
    subject_id integer,
    note_controle numeric(5,2),
    note_examen numeric(5,2),
    note_finale numeric(5,2) NOT NULL,
    coefficient numeric(3,1) DEFAULT 1.0,
    is_optional boolean DEFAULT false,
    is_rattrapage boolean DEFAULT false,
    appreciation character varying(50),
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.exam_subject_scores OWNER TO postgres;

--
-- TOC entry 232 (class 1259 OID 16612)
-- Name: exam_subject_scores_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.exam_subject_scores_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.exam_subject_scores_id_seq OWNER TO postgres;

--
-- TOC entry 5206 (class 0 OID 0)
-- Dependencies: 232
-- Name: exam_subject_scores_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.exam_subject_scores_id_seq OWNED BY public.exam_subject_scores.id;


--
-- TOC entry 224 (class 1259 OID 16509)
-- Name: ref_etablissements; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ref_etablissements (
    id integer NOT NULL,
    code character varying(20) NOT NULL,
    name_fr character varying(200) NOT NULL,
    name_ar character varying(200) NOT NULL,
    name_en character varying(200),
    type_etablissement character varying(50) NOT NULL,
    wilaya_id integer,
    moughata_id integer,
    address_fr text,
    address_ar text,
    coordinates point,
    phone character varying(20),
    email character varying(100),
    director_name character varying(100),
    status character varying(20) DEFAULT 'active'::character varying,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.ref_etablissements OWNER TO postgres;

--
-- TOC entry 223 (class 1259 OID 16508)
-- Name: ref_etablissements_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ref_etablissements_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ref_etablissements_id_seq OWNER TO postgres;

--
-- TOC entry 5207 (class 0 OID 0)
-- Dependencies: 223
-- Name: ref_etablissements_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ref_etablissements_id_seq OWNED BY public.ref_etablissements.id;


--
-- TOC entry 222 (class 1259 OID 16494)
-- Name: ref_moughatas; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ref_moughatas (
    id integer NOT NULL,
    wilaya_id integer,
    code character varying(10) NOT NULL,
    name_fr character varying(100) NOT NULL,
    name_ar character varying(100) NOT NULL,
    name_en character varying(100),
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.ref_moughatas OWNER TO postgres;

--
-- TOC entry 221 (class 1259 OID 16493)
-- Name: ref_moughatas_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ref_moughatas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ref_moughatas_id_seq OWNER TO postgres;

--
-- TOC entry 5208 (class 0 OID 0)
-- Dependencies: 221
-- Name: ref_moughatas_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ref_moughatas_id_seq OWNED BY public.ref_moughatas.id;


--
-- TOC entry 226 (class 1259 OID 16533)
-- Name: ref_series; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ref_series (
    id integer NOT NULL,
    code character varying(10) NOT NULL,
    name_fr character varying(100) NOT NULL,
    name_ar character varying(100) NOT NULL,
    name_en character varying(100),
    exam_type character varying(20) NOT NULL,
    description_fr text,
    description_ar text,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.ref_series OWNER TO postgres;

--
-- TOC entry 225 (class 1259 OID 16532)
-- Name: ref_series_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ref_series_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ref_series_id_seq OWNER TO postgres;

--
-- TOC entry 5209 (class 0 OID 0)
-- Dependencies: 225
-- Name: ref_series_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ref_series_id_seq OWNED BY public.ref_series.id;


--
-- TOC entry 228 (class 1259 OID 16545)
-- Name: ref_subjects; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ref_subjects (
    id integer NOT NULL,
    code character varying(10) NOT NULL,
    name_fr character varying(100) NOT NULL,
    name_ar character varying(100) NOT NULL,
    name_en character varying(100),
    coefficient numeric(3,1) DEFAULT 1.0,
    is_optional boolean DEFAULT false,
    exam_type character varying(20) NOT NULL,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.ref_subjects OWNER TO postgres;

--
-- TOC entry 227 (class 1259 OID 16544)
-- Name: ref_subjects_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ref_subjects_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ref_subjects_id_seq OWNER TO postgres;

--
-- TOC entry 5210 (class 0 OID 0)
-- Dependencies: 227
-- Name: ref_subjects_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ref_subjects_id_seq OWNED BY public.ref_subjects.id;


--
-- TOC entry 220 (class 1259 OID 16483)
-- Name: ref_wilayas; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ref_wilayas (
    id integer NOT NULL,
    code character varying(10) NOT NULL,
    name_fr character varying(100) NOT NULL,
    name_ar character varying(100) NOT NULL,
    name_en character varying(100),
    coordinates point,
    population_estimate integer,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.ref_wilayas OWNER TO postgres;

--
-- TOC entry 219 (class 1259 OID 16482)
-- Name: ref_wilayas_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ref_wilayas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.ref_wilayas_id_seq OWNER TO postgres;

--
-- TOC entry 5211 (class 0 OID 0)
-- Dependencies: 219
-- Name: ref_wilayas_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ref_wilayas_id_seq OWNED BY public.ref_wilayas.id;


--
-- TOC entry 238 (class 1259 OID 16701)
-- Name: social_shares; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.social_shares (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    result_id uuid,
    share_token character varying(100) NOT NULL,
    candidate_name character varying(200) NOT NULL,
    exam_type character varying(20) NOT NULL,
    decision character varying(30) NOT NULL,
    moyenne numeric(5,2),
    etablissement character varying(200),
    wilaya character varying(100),
    year integer NOT NULL,
    platform character varying(20),
    is_anonymous boolean DEFAULT false,
    expiry_date timestamp without time zone,
    click_count integer DEFAULT 0,
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.social_shares OWNER TO postgres;

--
-- TOC entry 235 (class 1259 OID 16634)
-- Name: stats_etablissements; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.stats_etablissements (
    id integer NOT NULL,
    session_id integer,
    etablissement_id integer,
    serie_id integer,
    total_candidats integer DEFAULT 0,
    total_admis integer DEFAULT 0,
    total_ajournes integer DEFAULT 0,
    taux_reussite numeric(5,2) DEFAULT 0,
    moyenne_etablissement numeric(5,2),
    mention_tres_bien integer DEFAULT 0,
    mention_bien integer DEFAULT 0,
    mention_assez_bien integer DEFAULT 0,
    mention_passable integer DEFAULT 0,
    candidats_masculins integer DEFAULT 0,
    candidats_feminins integer DEFAULT 0,
    admis_masculins integer DEFAULT 0,
    admis_feminins integer DEFAULT 0,
    last_calculated timestamp without time zone DEFAULT now(),
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.stats_etablissements OWNER TO postgres;

--
-- TOC entry 234 (class 1259 OID 16633)
-- Name: stats_etablissements_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.stats_etablissements_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.stats_etablissements_id_seq OWNER TO postgres;

--
-- TOC entry 5212 (class 0 OID 0)
-- Dependencies: 234
-- Name: stats_etablissements_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.stats_etablissements_id_seq OWNED BY public.stats_etablissements.id;


--
-- TOC entry 237 (class 1259 OID 16672)
-- Name: stats_wilayas; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.stats_wilayas (
    id integer NOT NULL,
    session_id integer,
    wilaya_id integer,
    exam_type character varying(20) NOT NULL,
    total_candidats integer DEFAULT 0,
    total_admis integer DEFAULT 0,
    taux_reussite numeric(5,2) DEFAULT 0,
    moyenne_wilaya numeric(5,2),
    rang_national integer,
    stats_par_serie jsonb,
    candidats_masculins integer DEFAULT 0,
    candidats_feminins integer DEFAULT 0,
    admis_masculins integer DEFAULT 0,
    admis_feminins integer DEFAULT 0,
    evolution_vs_annee_precedente numeric(5,2),
    last_calculated timestamp without time zone DEFAULT now(),
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.stats_wilayas OWNER TO postgres;

--
-- TOC entry 236 (class 1259 OID 16671)
-- Name: stats_wilayas_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.stats_wilayas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.stats_wilayas_id_seq OWNER TO postgres;

--
-- TOC entry 5213 (class 0 OID 0)
-- Dependencies: 236
-- Name: stats_wilayas_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.stats_wilayas_id_seq OWNED BY public.stats_wilayas.id;


--
-- TOC entry 244 (class 1259 OID 16758)
-- Name: system_config; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.system_config (
    id integer NOT NULL,
    config_key character varying(100) NOT NULL,
    config_value text,
    description text,
    is_public boolean DEFAULT false,
    updated_by integer,
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.system_config OWNER TO postgres;

--
-- TOC entry 243 (class 1259 OID 16757)
-- Name: system_config_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.system_config_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.system_config_id_seq OWNER TO postgres;

--
-- TOC entry 5214 (class 0 OID 0)
-- Dependencies: 243
-- Name: system_config_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.system_config_id_seq OWNED BY public.system_config.id;


--
-- TOC entry 245 (class 1259 OID 16790)
-- Name: v_exam_results_complete; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_exam_results_complete AS
 SELECT er.id,
    er.nni,
    er.numero_dossier,
    er.nom_complet_fr,
    er.nom_complet_ar,
    er.lieu_naissance,
    er.date_naissance,
    er.sexe,
    er.moyenne_generale,
    er.decision,
    er.mention,
    er.rang_etablissement,
    er.rang_wilaya,
    er.rang_national,
    es.year,
    es.exam_type,
    es.session_name,
    et.name_fr AS etablissement_fr,
    et.name_ar AS etablissement_ar,
    et.code AS etablissement_code,
    rs.name_fr AS serie_fr,
    rs.name_ar AS serie_ar,
    rs.code AS serie_code,
    rw.name_fr AS wilaya_fr,
    rw.name_ar AS wilaya_ar,
    rw.code AS wilaya_code,
    rm.name_fr AS moughata_fr,
    rm.name_ar AS moughata_ar,
    er.created_at,
    er.published_at
   FROM (((((public.exam_results er
     LEFT JOIN public.exam_sessions es ON ((er.session_id = es.id)))
     LEFT JOIN public.ref_etablissements et ON ((er.etablissement_id = et.id)))
     LEFT JOIN public.ref_series rs ON ((er.serie_id = rs.id)))
     LEFT JOIN public.ref_wilayas rw ON ((er.wilaya_id = rw.id)))
     LEFT JOIN public.ref_moughatas rm ON ((er.moughata_id = rm.id)));


ALTER VIEW public.v_exam_results_complete OWNER TO postgres;

--
-- TOC entry 246 (class 1259 OID 16815)
-- Name: v_stats_wilayas_public; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.v_stats_wilayas_public AS
 SELECT sw.id,
    sw.session_id,
    sw.wilaya_id,
    sw.total_candidats,
    sw.total_admis,
    sw.taux_reussite,
    sw.moyenne_wilaya,
    sw.rang_national,
    sw.stats_par_serie,
    sw.candidats_masculins,
    sw.candidats_feminins,
    sw.admis_masculins,
    sw.admis_feminins,
    sw.evolution_vs_annee_precedente,
    sw.last_calculated,
    sw.created_at,
    rw.name_fr AS wilaya_name_fr,
    rw.name_ar AS wilaya_name_ar,
    es.year,
    es.exam_type
   FROM ((public.stats_wilayas sw
     JOIN public.ref_wilayas rw ON ((sw.wilaya_id = rw.id)))
     JOIN public.exam_sessions es ON ((sw.session_id = es.id)))
  WHERE (es.is_published = true);


ALTER VIEW public.v_stats_wilayas_public OWNER TO postgres;

--
-- TOC entry 4939 (class 2604 OID 16723)
-- Name: admin_users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.admin_users ALTER COLUMN id SET DEFAULT nextval('public.admin_users_id_seq'::regclass);


--
-- TOC entry 4950 (class 2604 OID 16746)
-- Name: audit_logs id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_logs ALTER COLUMN id SET DEFAULT nextval('public.audit_logs_id_seq'::regclass);


--
-- TOC entry 4890 (class 2604 OID 16560)
-- Name: exam_sessions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exam_sessions ALTER COLUMN id SET DEFAULT nextval('public.exam_sessions_id_seq'::regclass);


--
-- TOC entry 4905 (class 2604 OID 16616)
-- Name: exam_subject_scores id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exam_subject_scores ALTER COLUMN id SET DEFAULT nextval('public.exam_subject_scores_id_seq'::regclass);


--
-- TOC entry 4880 (class 2604 OID 16512)
-- Name: ref_etablissements id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ref_etablissements ALTER COLUMN id SET DEFAULT nextval('public.ref_etablissements_id_seq'::regclass);


--
-- TOC entry 4878 (class 2604 OID 16497)
-- Name: ref_moughatas id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ref_moughatas ALTER COLUMN id SET DEFAULT nextval('public.ref_moughatas_id_seq'::regclass);


--
-- TOC entry 4884 (class 2604 OID 16536)
-- Name: ref_series id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ref_series ALTER COLUMN id SET DEFAULT nextval('public.ref_series_id_seq'::regclass);


--
-- TOC entry 4886 (class 2604 OID 16548)
-- Name: ref_subjects id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ref_subjects ALTER COLUMN id SET DEFAULT nextval('public.ref_subjects_id_seq'::regclass);


--
-- TOC entry 4875 (class 2604 OID 16486)
-- Name: ref_wilayas id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ref_wilayas ALTER COLUMN id SET DEFAULT nextval('public.ref_wilayas_id_seq'::regclass);


--
-- TOC entry 4910 (class 2604 OID 16637)
-- Name: stats_etablissements id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stats_etablissements ALTER COLUMN id SET DEFAULT nextval('public.stats_etablissements_id_seq'::regclass);


--
-- TOC entry 4925 (class 2604 OID 16675)
-- Name: stats_wilayas id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stats_wilayas ALTER COLUMN id SET DEFAULT nextval('public.stats_wilayas_id_seq'::regclass);


--
-- TOC entry 4952 (class 2604 OID 16761)
-- Name: system_config id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.system_config ALTER COLUMN id SET DEFAULT nextval('public.system_config_id_seq'::regclass);


--
-- TOC entry 5016 (class 2606 OID 16741)
-- Name: admin_users admin_users_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.admin_users
    ADD CONSTRAINT admin_users_email_key UNIQUE (email);


--
-- TOC entry 5018 (class 2606 OID 16737)
-- Name: admin_users admin_users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.admin_users
    ADD CONSTRAINT admin_users_pkey PRIMARY KEY (id);


--
-- TOC entry 5020 (class 2606 OID 16739)
-- Name: admin_users admin_users_username_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.admin_users
    ADD CONSTRAINT admin_users_username_key UNIQUE (username);


--
-- TOC entry 5022 (class 2606 OID 16751)
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);


--
-- TOC entry 4982 (class 2606 OID 16586)
-- Name: exam_results exam_results_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exam_results
    ADD CONSTRAINT exam_results_pkey PRIMARY KEY (id);


--
-- TOC entry 4978 (class 2606 OID 16568)
-- Name: exam_sessions exam_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exam_sessions
    ADD CONSTRAINT exam_sessions_pkey PRIMARY KEY (id);


--
-- TOC entry 4980 (class 2606 OID 16570)
-- Name: exam_sessions exam_sessions_year_exam_type_session_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exam_sessions
    ADD CONSTRAINT exam_sessions_year_exam_type_session_name_key UNIQUE (year, exam_type, session_name);


--
-- TOC entry 4998 (class 2606 OID 16622)
-- Name: exam_subject_scores exam_subject_scores_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exam_subject_scores
    ADD CONSTRAINT exam_subject_scores_pkey PRIMARY KEY (id);


--
-- TOC entry 4966 (class 2606 OID 16521)
-- Name: ref_etablissements ref_etablissements_code_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ref_etablissements
    ADD CONSTRAINT ref_etablissements_code_key UNIQUE (code);


--
-- TOC entry 4968 (class 2606 OID 16519)
-- Name: ref_etablissements ref_etablissements_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ref_etablissements
    ADD CONSTRAINT ref_etablissements_pkey PRIMARY KEY (id);


--
-- TOC entry 4962 (class 2606 OID 16500)
-- Name: ref_moughatas ref_moughatas_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ref_moughatas
    ADD CONSTRAINT ref_moughatas_pkey PRIMARY KEY (id);


--
-- TOC entry 4964 (class 2606 OID 16502)
-- Name: ref_moughatas ref_moughatas_wilaya_id_code_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ref_moughatas
    ADD CONSTRAINT ref_moughatas_wilaya_id_code_key UNIQUE (wilaya_id, code);


--
-- TOC entry 4970 (class 2606 OID 16543)
-- Name: ref_series ref_series_code_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ref_series
    ADD CONSTRAINT ref_series_code_key UNIQUE (code);


--
-- TOC entry 4972 (class 2606 OID 16541)
-- Name: ref_series ref_series_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ref_series
    ADD CONSTRAINT ref_series_pkey PRIMARY KEY (id);


--
-- TOC entry 4974 (class 2606 OID 16555)
-- Name: ref_subjects ref_subjects_code_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ref_subjects
    ADD CONSTRAINT ref_subjects_code_key UNIQUE (code);


--
-- TOC entry 4976 (class 2606 OID 16553)
-- Name: ref_subjects ref_subjects_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ref_subjects
    ADD CONSTRAINT ref_subjects_pkey PRIMARY KEY (id);


--
-- TOC entry 4958 (class 2606 OID 16492)
-- Name: ref_wilayas ref_wilayas_code_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ref_wilayas
    ADD CONSTRAINT ref_wilayas_code_key UNIQUE (code);


--
-- TOC entry 4960 (class 2606 OID 16490)
-- Name: ref_wilayas ref_wilayas_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ref_wilayas
    ADD CONSTRAINT ref_wilayas_pkey PRIMARY KEY (id);


--
-- TOC entry 5012 (class 2606 OID 16711)
-- Name: social_shares social_shares_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.social_shares
    ADD CONSTRAINT social_shares_pkey PRIMARY KEY (id);


--
-- TOC entry 5014 (class 2606 OID 16713)
-- Name: social_shares social_shares_share_token_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.social_shares
    ADD CONSTRAINT social_shares_share_token_key UNIQUE (share_token);


--
-- TOC entry 5001 (class 2606 OID 16653)
-- Name: stats_etablissements stats_etablissements_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stats_etablissements
    ADD CONSTRAINT stats_etablissements_pkey PRIMARY KEY (id);


--
-- TOC entry 5003 (class 2606 OID 16655)
-- Name: stats_etablissements stats_etablissements_session_id_etablissement_id_serie_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stats_etablissements
    ADD CONSTRAINT stats_etablissements_session_id_etablissement_id_serie_id_key UNIQUE (session_id, etablissement_id, serie_id);


--
-- TOC entry 5006 (class 2606 OID 16688)
-- Name: stats_wilayas stats_wilayas_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stats_wilayas
    ADD CONSTRAINT stats_wilayas_pkey PRIMARY KEY (id);


--
-- TOC entry 5008 (class 2606 OID 16690)
-- Name: stats_wilayas stats_wilayas_session_id_wilaya_id_exam_type_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stats_wilayas
    ADD CONSTRAINT stats_wilayas_session_id_wilaya_id_exam_type_key UNIQUE (session_id, wilaya_id, exam_type);


--
-- TOC entry 5024 (class 2606 OID 16769)
-- Name: system_config system_config_config_key_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.system_config
    ADD CONSTRAINT system_config_config_key_key UNIQUE (config_key);


--
-- TOC entry 5026 (class 2606 OID 16767)
-- Name: system_config system_config_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.system_config
    ADD CONSTRAINT system_config_pkey PRIMARY KEY (id);


--
-- TOC entry 4996 (class 2606 OID 16834)
-- Name: exam_results unique_nni_session; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exam_results
    ADD CONSTRAINT unique_nni_session UNIQUE (nni, session_id);


--
-- TOC entry 4983 (class 1259 OID 16781)
-- Name: idx_exam_results_decision; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_exam_results_decision ON public.exam_results USING btree (decision);


--
-- TOC entry 4984 (class 1259 OID 16778)
-- Name: idx_exam_results_etablissement; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_exam_results_etablissement ON public.exam_results USING btree (etablissement_id);


--
-- TOC entry 4985 (class 1259 OID 16775)
-- Name: idx_exam_results_nni; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_exam_results_nni ON public.exam_results USING btree (nni);


--
-- TOC entry 4986 (class 1259 OID 16783)
-- Name: idx_exam_results_nom_ar_trgm; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_exam_results_nom_ar_trgm ON public.exam_results USING gin (nom_complet_ar public.gin_trgm_ops);


--
-- TOC entry 4987 (class 1259 OID 16782)
-- Name: idx_exam_results_nom_trgm; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_exam_results_nom_trgm ON public.exam_results USING gin (nom_complet_fr public.gin_trgm_ops);


--
-- TOC entry 4988 (class 1259 OID 16776)
-- Name: idx_exam_results_numero_dossier; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_exam_results_numero_dossier ON public.exam_results USING btree (numero_dossier);


--
-- TOC entry 4989 (class 1259 OID 16785)
-- Name: idx_exam_results_published_session; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_exam_results_published_session ON public.exam_results USING btree (is_published, session_id) WHERE (is_published = true);


--
-- TOC entry 4990 (class 1259 OID 16780)
-- Name: idx_exam_results_serie; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_exam_results_serie ON public.exam_results USING btree (serie_id);


--
-- TOC entry 4991 (class 1259 OID 16777)
-- Name: idx_exam_results_session_published; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_exam_results_session_published ON public.exam_results USING btree (session_id, is_published);


--
-- TOC entry 4992 (class 1259 OID 16784)
-- Name: idx_exam_results_session_wilaya_serie; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_exam_results_session_wilaya_serie ON public.exam_results USING btree (session_id, wilaya_id, serie_id);


--
-- TOC entry 4993 (class 1259 OID 16779)
-- Name: idx_exam_results_wilaya; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_exam_results_wilaya ON public.exam_results USING btree (wilaya_id);


--
-- TOC entry 5009 (class 1259 OID 16789)
-- Name: idx_social_shares_result; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_social_shares_result ON public.social_shares USING btree (result_id);


--
-- TOC entry 5010 (class 1259 OID 16788)
-- Name: idx_social_shares_token; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_social_shares_token ON public.social_shares USING btree (share_token);


--
-- TOC entry 4999 (class 1259 OID 16786)
-- Name: idx_stats_etablissements_session; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_stats_etablissements_session ON public.stats_etablissements USING btree (session_id);


--
-- TOC entry 5004 (class 1259 OID 16787)
-- Name: idx_stats_wilayas_session; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_stats_wilayas_session ON public.stats_wilayas USING btree (session_id);


--
-- TOC entry 4994 (class 1259 OID 16847)
-- Name: unique_dossier_session; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX unique_dossier_session ON public.exam_results USING btree (numero_dossier, session_id) WHERE (numero_dossier IS NOT NULL);


--
-- TOC entry 5048 (class 2620 OID 16801)
-- Name: admin_users update_admin_users_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER update_admin_users_updated_at BEFORE UPDATE ON public.admin_users FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- TOC entry 5045 (class 2620 OID 16800)
-- Name: ref_etablissements update_etablissements_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER update_etablissements_updated_at BEFORE UPDATE ON public.ref_etablissements FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- TOC entry 5047 (class 2620 OID 16798)
-- Name: exam_results update_exam_results_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER update_exam_results_updated_at BEFORE UPDATE ON public.exam_results FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- TOC entry 5046 (class 2620 OID 16799)
-- Name: exam_sessions update_exam_sessions_updated_at; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER update_exam_sessions_updated_at BEFORE UPDATE ON public.exam_sessions FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- TOC entry 5043 (class 2606 OID 16752)
-- Name: audit_logs audit_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.admin_users(id);


--
-- TOC entry 5030 (class 2606 OID 16592)
-- Name: exam_results exam_results_etablissement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exam_results
    ADD CONSTRAINT exam_results_etablissement_id_fkey FOREIGN KEY (etablissement_id) REFERENCES public.ref_etablissements(id);


--
-- TOC entry 5031 (class 2606 OID 16607)
-- Name: exam_results exam_results_moughata_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exam_results
    ADD CONSTRAINT exam_results_moughata_id_fkey FOREIGN KEY (moughata_id) REFERENCES public.ref_moughatas(id);


--
-- TOC entry 5032 (class 2606 OID 16597)
-- Name: exam_results exam_results_serie_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exam_results
    ADD CONSTRAINT exam_results_serie_id_fkey FOREIGN KEY (serie_id) REFERENCES public.ref_series(id);


--
-- TOC entry 5033 (class 2606 OID 16587)
-- Name: exam_results exam_results_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exam_results
    ADD CONSTRAINT exam_results_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.exam_sessions(id);


--
-- TOC entry 5034 (class 2606 OID 16602)
-- Name: exam_results exam_results_wilaya_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exam_results
    ADD CONSTRAINT exam_results_wilaya_id_fkey FOREIGN KEY (wilaya_id) REFERENCES public.ref_wilayas(id);


--
-- TOC entry 5035 (class 2606 OID 16623)
-- Name: exam_subject_scores exam_subject_scores_result_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exam_subject_scores
    ADD CONSTRAINT exam_subject_scores_result_id_fkey FOREIGN KEY (result_id) REFERENCES public.exam_results(id) ON DELETE CASCADE;


--
-- TOC entry 5036 (class 2606 OID 16628)
-- Name: exam_subject_scores exam_subject_scores_subject_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exam_subject_scores
    ADD CONSTRAINT exam_subject_scores_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.ref_subjects(id);


--
-- TOC entry 5028 (class 2606 OID 16527)
-- Name: ref_etablissements ref_etablissements_moughata_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ref_etablissements
    ADD CONSTRAINT ref_etablissements_moughata_id_fkey FOREIGN KEY (moughata_id) REFERENCES public.ref_moughatas(id);


--
-- TOC entry 5029 (class 2606 OID 16522)
-- Name: ref_etablissements ref_etablissements_wilaya_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ref_etablissements
    ADD CONSTRAINT ref_etablissements_wilaya_id_fkey FOREIGN KEY (wilaya_id) REFERENCES public.ref_wilayas(id);


--
-- TOC entry 5027 (class 2606 OID 16503)
-- Name: ref_moughatas ref_moughatas_wilaya_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ref_moughatas
    ADD CONSTRAINT ref_moughatas_wilaya_id_fkey FOREIGN KEY (wilaya_id) REFERENCES public.ref_wilayas(id);


--
-- TOC entry 5042 (class 2606 OID 16714)
-- Name: social_shares social_shares_result_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.social_shares
    ADD CONSTRAINT social_shares_result_id_fkey FOREIGN KEY (result_id) REFERENCES public.exam_results(id);


--
-- TOC entry 5037 (class 2606 OID 16661)
-- Name: stats_etablissements stats_etablissements_etablissement_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stats_etablissements
    ADD CONSTRAINT stats_etablissements_etablissement_id_fkey FOREIGN KEY (etablissement_id) REFERENCES public.ref_etablissements(id);


--
-- TOC entry 5038 (class 2606 OID 16666)
-- Name: stats_etablissements stats_etablissements_serie_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stats_etablissements
    ADD CONSTRAINT stats_etablissements_serie_id_fkey FOREIGN KEY (serie_id) REFERENCES public.ref_series(id);


--
-- TOC entry 5039 (class 2606 OID 16656)
-- Name: stats_etablissements stats_etablissements_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stats_etablissements
    ADD CONSTRAINT stats_etablissements_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.exam_sessions(id);


--
-- TOC entry 5040 (class 2606 OID 16691)
-- Name: stats_wilayas stats_wilayas_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stats_wilayas
    ADD CONSTRAINT stats_wilayas_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.exam_sessions(id);


--
-- TOC entry 5041 (class 2606 OID 16696)
-- Name: stats_wilayas stats_wilayas_wilaya_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stats_wilayas
    ADD CONSTRAINT stats_wilayas_wilaya_id_fkey FOREIGN KEY (wilaya_id) REFERENCES public.ref_wilayas(id);


--
-- TOC entry 5044 (class 2606 OID 16770)
-- Name: system_config system_config_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.system_config
    ADD CONSTRAINT system_config_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public.admin_users(id);


-- Completed on 2025-07-10 21:52:56

--
-- PostgreSQL database dump complete
--

