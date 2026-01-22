# Script PowerShell para resolver conflictos de migración
# Este script marca la migración como aplicada sin ejecutarla

Write-Host "🔧 Resolviendo conflicto de migración..." -ForegroundColor Cyan

# SQL para marcar la migración como aplicada
$sql = @"
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
"@

# Ejecutar en el contenedor de base de datos
Write-Host "Ejecutando consulta SQL en la base de datos..." -ForegroundColor Yellow
$sql | docker exec -i secureapprove-db psql -U secureapprove -d secureapprove

Write-Host "`n✅ Conflicto resuelto. Ahora puedes ejecutar el deploy nuevamente." -ForegroundColor Green
Write-Host "Ejecuta: .\deploy.ps1" -ForegroundColor Cyan
