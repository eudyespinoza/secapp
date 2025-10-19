# Solución de Problemas de Docker - SecureApprove

## Problema 1: Variables de entorno no definidas

**Error**: `The "vL9xR4wQ" variable is not set. Defaulting to a blank string.`

**Solución**:
```bash
# 1. Generar secretos seguros
node scripts/generate-production-secrets.js

# 2. Copiar el contenido del archivo .env.secrets generado a tu archivo .env
cp .env.secrets .env

# 3. Verificar que las variables estén cargadas
set -a  # Exportar todas las variables
source .env
set +a
```

## Problema 2: Frontend - package-lock.json faltante

**Error**: `npm ci command can only install with an existing package-lock.json`

**Solución**:
```bash
# Generar package-lock.json para frontend
cd frontend
npm install --package-lock-only
cd ..

# O usar el script automatizado
chmod +x fix-and-deploy.sh
./fix-and-deploy.sh
```

## Problema 3: Backend - Conflicto de dependencias

**Error**: `ERESOLVE could not resolve` con cache-manager

**Solución**: Ya está corregido en Dockerfile.prod del backend con `--legacy-peer-deps`

## Solución RÁPIDA - Script Automatizado

```bash
# Script que arregla todos los problemas automáticamente:
chmod +x fix-and-deploy.sh
./fix-and-deploy.sh

# Este script:
# 1. Genera .env si no existe
# 2. Crea package-lock.json del frontend
# 3. Limpia builds anteriores
# 4. Construye imágenes una por una
# 5. Despliega todos los servicios
```

## Problema 2: Permisos de Docker

**Error**: `permission denied while trying to connect to the Docker daemon socket`

**Solución**:
```bash
# Opción 1: Agregar usuario al grupo docker
sudo usermod -aG docker $USER

# Aplicar los cambios sin cerrar sesión
newgrp docker

# Opción 2: Si lo anterior no funciona, reiniciar sesión
# logout y volver a entrar

# Verificar permisos
docker ps
```

## Problema 3: Versión obsoleta en docker-compose.yml

**Error**: `the attribute 'version' is obsolete`

**Solución**: Ya está corregido en los archivos, pero si persiste:
```bash
# Verificar que estés usando el docker-compose.yml correcto
grep -n "version:" docker-compose.yml
# Si aparece, eliminar esa línea manualmente
```

## Solución RÁPIDA - Script Automatizado

```bash
# Si tienes problemas, usa el script de setup rápido:
chmod +x quick-start.sh
./quick-start.sh

# Este script hace todo automáticamente:
# 1. Genera .env con secretos seguros
# 2. Ejecuta el deployment completo
```

## Comandos de diagnóstico

```bash
# Verificar Docker
docker --version
docker compose version

# Verificar permisos
docker ps

# Verificar red de Traefik
docker network ls | grep traefik
docker network inspect traefik_proxy

# Verificar variables de entorno
env | grep MONGODB
env | grep JWT
env | grep REDIS

# Ver logs detallados
docker compose logs -f --tail=50

# Limpiar todo si es necesario
docker compose down --volumes --remove-orphans
docker system prune -f
```

## Deployment paso a paso (manual)

Si el script automatizado falla, ejecutar manualmente:

```bash
# 1. Verificar archivo .env
ls -la .env
head -5 .env

# 2. Cargar variables de entorno
set -a && source .env && set +a

# 3. Crear directorios
mkdir -p ./data/{mongodb,redis,prometheus,grafana}/{data,logs}
mkdir -p ./backups ./logs

# 4. Verificar red de Traefik
docker network inspect traefik_proxy

# 5. Detener contenedores existentes
docker compose down --remove-orphans

# 6. Construir imágenes
docker compose build --no-cache --progress=plain

# 7. Iniciar servicios uno por uno
docker compose up -d mongodb-primary
sleep 30
docker compose up -d redis-master
sleep 10
docker compose up -d api
sleep 20
docker compose up -d frontend
sleep 10
docker compose up -d prometheus grafana

# 8. Verificar estado
docker compose ps
docker compose logs --tail=20
```

## Verificación final

```bash
# Verificar servicios
curl -f http://localhost:3000/api/health
curl -f http://localhost:3001

# Ver logs específicos
docker compose logs api
docker compose logs frontend
docker compose logs mongodb-primary
```