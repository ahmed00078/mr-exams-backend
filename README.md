# 🚀 Guide d'Installation - Backend FastAPI Mauritanie

## 📋 Prérequis

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Git

## 📦 Installation Rapide

### 1. Cloner et Configurer le Projet

```bash
# Créer le dossier du projet
mkdir mauritania-exams-backend
cd mauritania-exams-backend

# Créer l'environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# Installer les dépendances
pip install -r requirements.txt
```

### 2. Configuration Base de Données

```bash
# Se connecter à PostgreSQL
sudo -u postgres psql

# Créer la base de données
CREATE DATABASE mauritania_exams;
CREATE USER mauritania_user WITH PASSWORD 'password123';
GRANT ALL PRIVILEGES ON DATABASE mauritania_exams TO mauritania_user;
\q

# Exécuter le schéma SQL
psql -U mauritania_user -d mauritania_exams -f database_schema.sql
"/c/Program Files/PostgreSQL/17/bin/psql.exe" -U postgres -d mauritania_exams -f mauritania_database_schema.sql
```

### 3. Configuration Redis

```bash
# Démarrer Redis (selon votre OS)
sudo systemctl start redis    # Linux systemd
brew services start redis     # macOS avec Homebrew
# ou démarrer manuellement
redis-server
```

### 4. Variables d'Environnement

Créer le fichier `.env` :

```env
DATABASE_URL=postgresql://mauritania_user:password123@localhost:5432/mauritania_exams
DATABASE_URL_ASYNC=postgresql+asyncpg://mauritania_user:password123@localhost:5432/mauritania_exams
REDIS_URL=redis://localhost:6379
SECRET_KEY=votre-cle-secrete-super-longue-et-complexe-ici
BASE_URL=http://localhost:8000
ENVIRONMENT=development
DEBUG=true
```

### 5. Initialiser les Données

```bash
# Créer les données de base
python -m app.utils.data_generator
```

## 🔥 Démarrage Rapide

```bash
# Démarrer le serveur de développement
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Le backend sera accessible sur : **http://localhost:8000**

## 📖 Endpoints Principaux

### Documentation API
- **Swagger UI** : http://localhost:8000/docs
- **ReDoc** : http://localhost:8000/redoc

### Endpoints Publics

#### Recherche de Résultats
```bash
# Recherche par NNI
GET /results/search?nni=1234567890

# Recherche par nom
GET /results/search?nom=Ahmed&wilaya_id=6

# Recherche complexe
GET /results/search?year=2024&exam_type=bac&serie_id=1&page=1&size=50
```

#### Détails d'un Résultat
```bash
GET /results/{result_id}
```

#### Partage Social
```bash
# Générer un lien de partage
POST /results/{result_id}/share
{
  "platform": "whatsapp",
  "is_anonymous": false
}

# Page publique de partage
GET /share/{token}
```

#### Références
```bash
# Liste des wilayas
GET /references/wilayas

# Liste des établissements
GET /references/etablissements?wilaya_id=6

# Liste des séries
GET /references/series?exam_type=bac
```

#### Statistiques Publiques
```bash
# Stats par wilaya
GET /stats/wilaya/6?year=2024&exam_type=bac

# Stats par établissement
GET /stats/etablissement/1?year=2024&exam_type=bac

# Stats globales
GET /stats/global?year=2024&exam_type=bac
```

### Endpoints d'Administration

#### Authentification
```bash
# Login
POST /auth/login
{
  "username": "admin",
  "password": "admin123"
}

# Profil utilisateur
GET /auth/me
Authorization: Bearer {token}
```

#### Upload en Masse
```bash
# Upload de résultats
POST /admin/upload
Content-Type: multipart/form-data
Authorization: Bearer {token}

file: {fichier.csv ou .xlsx}
session_id: 1

# Status de l'upload
GET /admin/upload/{task_id}/status
Authorization: Bearer {token}
```

## 🐳 Déploiement Docker

### Docker Compose (Recommandé)

```bash
# Démarrer tous les services
docker-compose up -d

# Voir les logs
docker-compose logs -f

# Arrêter les services
docker-compose down
```

### Docker Manuel

```bash
# Build l'image
docker build -t mauritania-exams-api .

# Démarrer PostgreSQL
docker run -d --name postgres-mauritania \
  -e POSTGRES_DB=mauritania_exams \
  -e POSTGRES_USER=mauritania_user \
  -e POSTGRES_PASSWORD=password123 \
  -p 5432:5432 postgres:15

# Démarrer Redis
docker run -d --name redis-mauritania \
  -p 6379:6379 redis:7-alpine

# Démarrer l'API
docker run -d --name api-mauritania \
  -p 8000:8000 \
  --link postgres-mauritania:db \
  --link redis-mauritania:redis \
  -e DATABASE_URL=postgresql://mauritania_user:password123@db:5432/mauritania_exams \
  -e REDIS_URL=redis://redis:6379 \
  mauritania-exams-api
```

## 🧪 Tests et Validation

### Tests des Endpoints

```bash
# Test de santé
curl http://localhost:8000/health

# Test de recherche
curl "http://localhost:8000/results/search?nni=1234567890"

# Test d'authentification
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

### Test de Performance

```bash
# Installer Apache Bench
sudo apt-get install apache2-utils

# Test de charge simple
ab -n 1000 -c 10 http://localhost:8000/results/search?nni=1234567890

# Test avec authentification
ab -n 100 -c 5 -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/auth/me
```

## 📊 Monitoring et Logs

### Logs de l'Application

```bash
# Voir les logs en temps réel
tail -f app.log

# Filtrer les erreurs
grep "ERROR" app.log

# Analyser les performances
grep "Process-Time" app.log | sort -k5 -n
```

### Monitoring Redis

```bash
# Se connecter à Redis CLI
redis-cli

# Voir les statistiques
INFO stats

# Lister les clés de cache
KEYS "search:*"
KEYS "stats:*"
```

### Monitoring PostgreSQL

```bash
# Se connecter à la base
psql -U mauritania_user -d mauritania_exams

-- Voir les requêtes actives
SELECT * FROM pg_stat_activity WHERE state = 'active';

-- Statistiques des tables
SELECT schemaname,tablename,n_tup_ins,n_tup_upd,n_tup_del,n_live_tup,n_dead_tup 
FROM pg_stat_user_tables;

-- Performance des index
SELECT schemaname,tablename,indexname,idx_scan,idx_tup_read,idx_tup_fetch 
FROM pg_stat_user_indexes;
```

## 🔧 Configuration Avancée

### Variables d'Environnement Complètes

```env
# Database
DATABASE_URL=postgresql://user:pass@host:5432/db
DATABASE_URL_ASYNC=postgresql+asyncpg://user:pass@host:5432/db

# Redis
REDIS_URL=redis://host:6379/0

# Security
SECRET_KEY=your-256-bit-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480

# CORS (pour production)
CORS_ORIGINS=["https://examens.mauritanie.mr","https://www.examens.mauritanie.mr"]

# Application
BASE_URL=https://examens.mauritanie.mr
ENVIRONMENT=production
DEBUG=false

# File Upload
UPLOAD_MAX_SIZE=52428800  # 50MB
UPLOAD_PATH=/app/uploads

# Cache (secondes)
CACHE_TTL_RESULTS=3600    # 1 heure
CACHE_TTL_STATS=7200      # 2 heures

# Social Media
SOCIAL_SHARE_EXPIRE_DAYS=30

# Pagination
DEFAULT_PAGE_SIZE=50
MAX_PAGE_SIZE=1000
```

### Configuration Nginx (Production)

```nginx
server {
    listen 80;
    server_name examens.mauritanie.mr;
    
    # Redirection HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name examens.mauritanie.mr;
    
    # Certificats SSL
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/private.key;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    
    location / {
        limit_req zone=api burst=20 nodelay;
        
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
    
    # Page de partage social
    location /share/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Fichiers statiques (si nécessaire)
    location /static/ {
        alias /app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### Systemd Service (Production)

```ini
# /etc/systemd/system/mauritania-exams.service
[Unit]
Description=Mauritania Exams API
After=network.target postgresql.service redis.service

[Service]
Type=exec
User=mauritania
Group=mauritania
WorkingDirectory=/opt/mauritania-exams
Environment=PATH=/opt/mauritania-exams/venv/bin
ExecStart=/opt/mauritania-exams/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
# Activer et démarrer le service
sudo systemctl enable mauritania-exams
sudo systemctl start mauritania-exams
sudo systemctl status mauritania-exams
```

## 🚀 Optimisations de Performance

### Configuration PostgreSQL

```sql
-- postgresql.conf (ajustements recommandés)
shared_buffers = 256MB                # 25% de la RAM
effective_cache_size = 1GB            # 75% de la RAM disponible
work_mem = 4MB                        # Par connexion
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1               # SSD
effective_io_concurrency = 200       # SSD

-- Index additionnels pour performance
CREATE INDEX CONCURRENTLY idx_exam_results_search_combined 
ON exam_results(session_id, wilaya_id, is_published) 
WHERE is_published = true;

CREATE INDEX CONCURRENTLY idx_exam_results_stats 
ON exam_results(session_id, etablissement_id, decision) 
WHERE is_published = true;
```

### Configuration Redis

```conf
# redis.conf
maxmemory 512mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

### Configuration Uvicorn Production

```bash
# Démarrage optimisé
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --access-log \
  --log-level info \
  --limit-concurrency 1000 \
  --limit-max-requests 10000 \
  --timeout-keep-alive 5
```

## 🔒 Sécurité

### Checklist de Sécurité

- [ ] Changer le `SECRET_KEY` par défaut
- [ ] Utiliser HTTPS en production
- [ ] Configurer les CORS correctement
- [ ] Activer le rate limiting
- [ ] Mettre à jour PostgreSQL et Redis
- [ ] Configurer les backups automatiques
- [ ] Monitoring des logs de sécurité
- [ ] Validation stricte des uploads
- [ ] Chiffrement des données sensibles

### Backup et Restore

```bash
# Backup automatique (crontab)
0 2 * * * pg_dump -U mauritania_user mauritania_exams > /backups/mauritania_$(date +\%Y\%m\%d).sql

# Restore
psql -U mauritania_user -d mauritania_exams < backup.sql

# Backup Redis
redis-cli BGSAVE
```

## 🆘 Dépannage

### Problèmes Fréquents

#### 1. Erreur de Connexion Database
```bash
# Vérifier PostgreSQL
sudo systemctl status postgresql
sudo -u postgres psql -c "SELECT version();"

# Tester la connexion
psql -U mauritania_user -d mauritania_exams -c "SELECT 1;"
```

#### 2. Redis Non Accessible
```bash
# Vérifier Redis
redis-cli ping
# Réponse attendue: PONG

# Redémarrer si nécessaire
sudo systemctl restart redis
```

#### 3. Performance Lente
```bash
# Vérifier les logs
grep "Process-Time" app.log | tail -20

# Analyser les requêtes PostgreSQL lentes
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY mean_time DESC LIMIT 10;
```

#### 4. Upload Files Échoue
```bash
# Vérifier les permissions
ls -la uploads/
chmod 755 uploads/

# Vérifier l'espace disque
df -h
```

## 📞 Support

Pour toute question ou problème :

1. **Logs** : Vérifiez `app.log` pour les erreurs
2. **Documentation** : http://localhost:8000/docs
3. **Health Check** : http://localhost:8000/health
4. **Database** : Vérifiez les connexions et performances

Le backend est maintenant prêt pour la production ! 🚀