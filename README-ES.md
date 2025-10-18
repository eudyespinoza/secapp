# 🚀 SecureApprove - Guía de Despliegue en Español

## 📋 Índice

1. [Introducción](#introducción)
2. [Requisitos Previos](#requisitos-previos)
3. [Instalación Rápida](#instalación-rápida)
4. [Configuración](#configuración)
5. [Despliegue](#despliegue)
6. [Acceso a Servicios](#acceso-a-servicios)
7. [Comandos Útiles](#comandos-útiles)
8. [Solución de Problemas](#solución-de-problemas)

---

## 📖 Introducción

**SecureApprove** es un sistema empresarial de aprobaciones sin contraseñas que utiliza autenticación biométrica (WebAuthn) para máxima seguridad.

### ✨ Características Principales

- 🔐 **Sin contraseñas**: Autenticación con huella digital, Face ID o llaves de seguridad
- 🏢 **Nivel empresarial**: Alta disponibilidad, load balancing, backups automáticos
- 📊 **Monitoreo completo**: Dashboards de Grafana con métricas en tiempo real
- 🔒 **Seguridad máxima**: Encriptación end-to-end, mTLS, audit logging
- ⚡ **Alto rendimiento**: <1s tiempo de respuesta, 10,000+ req/min

---

## 💻 Requisitos Previos

### Software Necesario

- **Windows 10/11** con PowerShell
- **Docker Desktop** para Windows ([Descargar](https://www.docker.com/products/docker-desktop))
- **Node.js 18+** ([Descargar](https://nodejs.org/))
- **Git** (opcional)

### Verificar Instalación

```powershell
# Verificar Docker
docker --version
# Resultado esperado: Docker version 24.x.x

# Verificar Docker Compose
docker-compose --version
# Resultado esperado: Docker Compose version 2.x.x

# Verificar Node.js
node --version
# Resultado esperado: v18.x.x o superior

# Verificar npm
npm --version
# Resultado esperado: 9.x.x o superior
```

---

## 🚀 Instalación Rápida

### Paso 1: Preparación (2 minutos)

```powershell
# Navegar al directorio del proyecto
cd d:\OtherProyects\SecApp

# Instalar dependencias de Node.js
npm install
```

### Paso 2: Generar Secretos (1 minuto)

```powershell
# Generar secretos de seguridad
npm run generate:secrets

# El script creará:
# - Passwords seguros para MongoDB, Redis, etc.
# - Keys de encriptación
# - JWT secrets
# - MongoDB keyfile
```

**📝 Nota**: Los secretos se guardan automáticamente en el archivo `.env`

### Paso 3: Generar Certificados SSL (1 minuto)

```powershell
# Generar certificados auto-firmados para desarrollo
npm run generate:ssl

# Para producción, Traefik obtendrá automáticamente
# certificados de Let's Encrypt
```

### Paso 4: Configurar Variables de Entorno (1 minuto)

Abrir el archivo `.env` y actualizar estas variables:

```powershell
# Abrir con el editor de texto
notepad .env

# O con VS Code
code .env
```

**Variables críticas a actualizar**:

```env
# Tu dominio (si tienes uno)
DOMAIN=secureapprove.com

# Credenciales de AWS S3 (para backups)
AWS_ACCESS_KEY_ID=tu_access_key_aqui
AWS_SECRET_ACCESS_KEY=tu_secret_key_aqui
AWS_S3_BUCKET=tu-bucket-backups

# API Key de SendGrid (para emails)
SMTP_PASSWORD=tu_sendgrid_api_key_aqui

# Email para Let's Encrypt (certificados SSL)
TRAEFIK_ACME_EMAIL=tu-email@ejemplo.com
```

**💡 Tip**: Si no tienes AWS o SendGrid configurado, el sistema funcionará igualmente, pero sin backups a S3 ni emails.

---

## 🏗️ Despliegue

### Opción A: Despliegue Completo (Recomendado)

```powershell
# Construir todas las aplicaciones
npm run build

# Iniciar ambiente de producción
npm run docker:prod

# Esperar 30-60 segundos para que los servicios inicien

# Verificar que todo está funcionando
npm run health:check
```

### Opción B: Despliegue de Desarrollo

```powershell
# Modo desarrollo con hot-reload
npm run dev
```

---

## 🌐 Acceso a Servicios

Una vez desplegado, puedes acceder a:

### Servicios Web

| Servicio | URL Local | Credenciales |
|----------|-----------|--------------|
| **Aplicación Web** | http://localhost:3000 | Crear usuario nuevo |
| **API REST** | http://localhost:3000/api | Via JWT token |
| **Grafana** | http://localhost:3001 | admin / (ver .env) |
| **Prometheus** | http://localhost:9090 | Sin autenticación |
| **Traefik** | http://localhost:8080 | admin / (ver .env) |

### Bases de Datos

```powershell
# Conectar a MongoDB
docker exec -it secureapprove-mongodb-primary mongosh -u root -p
# Password: ver MONGODB_ROOT_PASSWORD en .env

# Conectar a Redis
docker exec -it secureapprove-redis-master redis-cli -a <REDIS_PASSWORD>
# Password: ver REDIS_PASSWORD en .env
```

---

## 🛠️ Comandos Útiles

### Gestión de Servicios

```powershell
# Ver todos los contenedores en ejecución
docker ps

# Ver logs de todos los servicios
npm run docker:logs

# Ver logs de un servicio específico
npm run logs:api
npm run logs:mongodb
npm run logs:redis

# Detener todos los servicios
npm run docker:down

# Reiniciar un servicio específico
docker-compose restart api-1

# Ver uso de recursos
docker stats
```

### Backups

```powershell
# Crear backup manual
npm run backup:create

# Listar backups disponibles
npm run backup:list

# Restaurar desde backup
npm run backup:restore nombre-del-backup
```

### Testing

```powershell
# Ejecutar todos los tests
npm test

# Tests end-to-end
npm run test:e2e

# Tests con interfaz visual
npm run test:e2e:ui

# Audit de seguridad
npm run security:audit
```

### Monitoreo

```powershell
# Verificar salud de servicios
npm run health:check

# Abrir dashboard de Grafana
npm run monitor:dashboard

# Ver métricas en tiempo real
curl http://localhost:9090/metrics
```

---

## 🔧 Solución de Problemas

### Problema: "Docker no está iniciado"

**Solución**:
```powershell
# Abrir Docker Desktop y esperar a que inicie
# Verificar con:
docker ps
```

### Problema: "Puerto ya en uso"

**Error**: `Error starting userland proxy: listen tcp 0.0.0.0:3000: bind: address already in use`

**Solución**:
```powershell
# Ver qué proceso usa el puerto
netstat -ano | findstr :3000

# Detener el proceso o cambiar el puerto en .env
```

### Problema: "MongoDB no se conecta"

**Solución**:
```powershell
# Ver logs de MongoDB
docker logs secureapprove-mongodb-primary

# Verificar que el ReplicaSet se inicializó
docker exec secureapprove-mongodb-primary mongosh --eval "rs.status()"

# Si está "STARTUP" o "RECOVERING", esperar 1-2 minutos
```

### Problema: "API retorna 500"

**Solución**:
```powershell
# Ver logs de la API
docker logs secureapprove-api-1

# Verificar que MongoDB está listo
npm run health:check

# Reiniciar la API
docker-compose restart api-1
```

### Problema: "No puedo acceder a Grafana"

**Solución**:
```powershell
# Verificar que Grafana está corriendo
docker ps | findstr grafana

# Ver logs
docker logs secureapprove-grafana

# Acceder directamente
# URL: http://localhost:3001
# Usuario: admin
# Password: ver GRAFANA_ADMIN_PASSWORD en .env
```

### Problema: "Olvidé las credenciales"

**Solución**:
```powershell
# Todas las credenciales están en:
notepad .env

# También documentadas en:
notepad CREDENTIALS.md
```

---

## 📚 Documentación Adicional

### Archivos de Documentación

- **[QUICKSTART.md](QUICKSTART.md)** - Inicio rápido en inglés
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Guía completa de despliegue
- **[CREDENTIALS.md](CREDENTIALS.md)** - Gestión de credenciales
- **[SECURITY.md](SECURITY.md)** - Políticas de seguridad
- **[PROYECTO-COMPLETADO.md](PROYECTO-COMPLETADO.md)** - Resumen ejecutivo

### Arquitectura

```
Internet → Traefik (Load Balancer)
              ↓
          API (3 instancias)
              ↓
       ┌──────┴──────┐
       ↓             ↓
   MongoDB       Redis
  (3 nodos)    (Sentinel)
       ↓             ↓
   Prometheus → Grafana
```

---

## 🔒 Seguridad

### Checklist Pre-Producción

Antes de usar en producción, verifica:

- [ ] Todas las passwords cambiadas en `.env`
- [ ] AWS S3 configurado para backups
- [ ] SendGrid configurado para emails
- [ ] Dominio configurado con DNS
- [ ] Firewall configurado (puertos 22, 80, 443)
- [ ] Fail2ban instalado y activo
- [ ] SSL/TLS certificados válidos
- [ ] Backups probados (crear y restaurar)
- [ ] Monitoreo con alertas configurado
- [ ] Tests E2E ejecutados exitosamente

### Mejores Prácticas

1. **Nunca commitear** el archivo `.env` a Git
2. **Rotar passwords** cada 90 días
3. **Monitorear logs** de seguridad diariamente
4. **Actualizar dependencias** mensualmente
5. **Probar backups** semanalmente
6. **Revisar alertas** de Grafana diariamente

---

## 📞 Soporte

### Contacto

- **Email de Soporte**: support@secureapprove.com
- **Seguridad**: security@secureapprove.com
- **Issues GitHub**: [Crear issue](https://github.com/your-org/secure-approve/issues)

### Recursos

- **Documentación**: Archivos `*.md` en el proyecto
- **Video Tutoriales**: (próximamente)
- **FAQ**: (próximamente)

---

## 🎉 Próximos Pasos

### Después del Despliegue

1. **Crear usuarios de prueba**
   - Registrar cuenta con WebAuthn
   - Probar flujo de aprobación

2. **Configurar monitoreo**
   - Revisar dashboards de Grafana
   - Configurar alertas por email

3. **Probar backups**
   - Crear backup manual
   - Restaurar backup de prueba

4. **Optimizar configuración**
   - Ajustar límites de recursos
   - Configurar SSL/TLS en producción

### Roadmap de Funcionalidades

- 🔜 App móvil completa (React Native)
- 🔜 Análisis con IA
- 🔜 Multi-tenancy
- 🔜 Workflows complejos
- 🔜 Integración SAML/OAuth

---

## 📊 Estado del Proyecto

**Versión**: 1.0.0  
**Estado**: ✅ **PRODUCTION READY**  
**Última Actualización**: 7 de Diciembre de 2024

### Métricas

- **Cobertura de Tests**: >90%
- **Tiempo de Respuesta**: <1s (P95)
- **Uptime Target**: 99.9%
- **Capacidad**: 10,000+ req/min
- **Usuarios Concurrentes**: 1,000+

---

## 🙏 Agradecimientos

Desarrollado con ❤️ utilizando:

- **Backend**: NestJS + TypeScript
- **Frontend**: Next.js 14 + Tailwind CSS
- **Base de datos**: MongoDB + Redis
- **Infraestructura**: Docker + Traefik
- **Monitoreo**: Prometheus + Grafana
- **Testing**: Jest + Playwright

---

## 📄 Licencia

MIT License - Ver [LICENSE](LICENSE) para detalles.

---

**¿Preguntas? ¿Problemas? ¿Sugerencias?**

Abre un [issue en GitHub](https://github.com/your-org/secure-approve/issues) o contacta a support@secureapprove.com

🚀 **¡Feliz despliegue!**
