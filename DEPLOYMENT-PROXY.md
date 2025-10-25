# SecureApprove - Despliegue con Proxy Externo

## Configuración para Red Proxy Externa

Esta aplicación está configurada para funcionar con un proxy/load balancer externo (como Traefik) que maneja el enrutamiento y SSL.

### Prerequisitos

1. **Red Proxy Externa**: Debe existir una red Docker llamada `proxy`
2. **Proxy/Load Balancer**: Traefik u otro proxy configurado en la red `proxy`

### Configuración de Red

```bash
# Crear la red proxy si no existe
docker network create proxy
```

### Variables de Entorno

La aplicación está configurada con estas variables principales:

- **Host**: `secureapprove.local` o `localhost`
- **Puerto Interno**: `8000` (expuesto solo al proxy)
- **Base de Datos**: PostgreSQL interno en red `secureapprove_internal`
- **Cache**: Redis interno en red `secureapprove_internal`

### Labels de Traefik

El servicio web incluye labels para descubrimiento automático:

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.secureapprove.rule=Host(`secureapprove.local`) || Host(`localhost`)"
  - "traefik.http.routers.secureapprove.entrypoints=web"
  - "traefik.http.services.secureapprove.loadbalancer.server.port=8000"
  - "traefik.docker.network=proxy"
```

### Despliegue

```bash
# Levantar los servicios
docker-compose -f docker-compose.simple.yml up -d

# Verificar estado
docker-compose -f docker-compose.simple.yml ps

# Ver logs
docker-compose -f docker-compose.simple.yml logs -f web
```

### Acceso

Una vez desplegado:

- **URL**: http://secureapprove.local (a través del proxy)
- **Admin**: admin@secureapprove.com / admin123
- **API Docs**: http://secureapprove.local/api/docs/

### Redes

La aplicación utiliza dos redes:

1. **default (secureapprove_internal)**: Para comunicación entre servicios internos
2. **proxy (externa)**: Para comunicación con el proxy/load balancer

### Monitoreo

```bash
# Estado de servicios
docker-compose -f docker-compose.simple.yml ps

# Logs en tiempo real
docker-compose -f docker-compose.simple.yml logs -f

# Health checks
curl http://secureapprove.local/health/
```

### Producción

Para producción, asegúrate de:

1. Cambiar `SECRET_KEY` en variables de entorno
2. Configurar credenciales de base de datos seguras
3. Configurar email SMTP
4. Configurar Mercado Pago (opcional)
5. Usar HTTPS en el proxy
6. Configurar backups automáticos

### Backup

```bash
# Backup manual de base de datos
docker-compose -f docker-compose.simple.yml exec db pg_dump -U postgres secureapprove > backup.sql

# Restaurar backup
docker-compose -f docker-compose.simple.yml exec -T db psql -U postgres secureapprove < backup.sql
```