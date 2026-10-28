#!/bin/bash
# Crea la base ProyectoEPS con los scripts de sql/ solo si todavía no existe,
# para no borrar los datos cuando el servicio se vuelve a ejecutar.
set -euo pipefail

SQLCMD=(/opt/mssql-tools18/bin/sqlcmd -S sqlserver -U sa -P "$MSSQL_SA_PASSWORD" -C -b)

existe=$("${SQLCMD[@]}" -h -1 -W -Q "SET NOCOUNT ON; SELECT CASE WHEN OBJECT_ID('ProyectoEPS.dbo.Pacientes') IS NULL THEN 0 ELSE 1 END")
if [ "$existe" = "1" ]; then
    echo "ProyectoEPS ya existe; no se recrea el esquema."
    exit 0
fi

for f in /sql/01_schema.sql /sql/02_vistas.sql; do
    echo "Ejecutando $f"
    "${SQLCMD[@]}" -i "$f"
done
