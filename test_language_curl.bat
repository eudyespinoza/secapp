@echo off
REM Test de cambio de idioma con curl

echo ================================
echo TEST DE CAMBIO DE IDIOMA
echo ================================

echo.
echo 1. Obteniendo pagina inicial (debe estar en español):
curl -s -c cookies.txt http://localhost:8000/es/ | findstr /C:"Panel de Control" /C:"Dashboard"

echo.
echo 2. Cambiando a inglés:
curl -s -b cookies.txt -c cookies.txt -X POST http://localhost:8000/i18n/setlang/ -d "language=en&next=/en/" -L | findstr /C:"Dashboard" /C:"Panel"

echo.
echo 3. Verificando cookie:
type cookies.txt | findstr django_language

echo.
echo 4. Accediendo a /en/ con la cookie:
curl -s -b cookies.txt http://localhost:8000/en/ | findstr /C:"Dashboard" /C:"Panel de Control"

echo.
echo 5. Cambiando a portugués:
curl -s -b cookies.txt -c cookies.txt -X POST http://localhost:8000/i18n/setlang/ -d "language=pt-br&next=/pt-br/" -L | findstr /C:"Painel" /C:"Dashboard"

echo.
echo ================================
echo FIN DEL TEST
echo ================================
