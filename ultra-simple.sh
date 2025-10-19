#!/bin/bash

echo "💀 ULTRA SIMPLE - Solo API en Node"
echo "=================================="

# Cambiar al backend
cd backend

# Instalar dependencias
npm install --legacy-peer-deps

# Construir
npm run build

# Iniciar en background  
nohup npm run start:prod > ../api.log 2>&1 &

echo "✅ API corriendo en background"
echo "Logs: tail -f api.log"
echo "Puerto: 3000"

cd ..