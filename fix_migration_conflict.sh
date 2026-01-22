#!/bin/bash
# Script para resolver conflictos de migración
# Este script marca la migración como aplicada sin ejecutarla

echo "🔧 Resolviendo conflicto de migración..."

# Conectar a la base de datos y marcar la migración como aplicada
docker exec -i secureapprove-db psql -U secureapprove -d secureapprove << EOF
-- Verificar si la migración ya está registrada
SELECT * FROM django_migrations WHERE app = 'authentication' AND name = '0007_terms_approval_session_and_audit';

-- Si no está registrada, insertarla manualmente
INSERT INTO django_migrations (app, name, applied)
SELECT 'authentication', '0007_terms_approval_session_and_audit', NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM django_migrations 
    WHERE app = 'authentication' 
    AND name = '0007_terms_approval_session_and_audit'
);

-- Verificar que se insertó correctamente
SELECT * FROM django_migrations WHERE app = 'authentication' ORDER BY applied DESC LIMIT 5;
EOF

echo "✅ Conflicto resuelto. Ahora puedes ejecutar el deploy nuevamente."
echo "Ejecuta: ./deploy.sh"
