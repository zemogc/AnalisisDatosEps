#!/bin/sh
set -e

# Carga datos de demostración la primera vez; si la base ya tiene datos, seed termina con
# código 1 y se continúa sin tocarla.
eps-analytics seed --pacientes "${EPS_PACIENTES:-2000}" || echo "La base ya tiene datos; se conservan."

exec "$@"
