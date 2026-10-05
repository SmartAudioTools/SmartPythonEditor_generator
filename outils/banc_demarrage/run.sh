#!/bin/bash
# Un lancement COMPLET de SmartPythonEditor, hors ecran, sur une configuration JETABLE, avec la
# trace de demarrage (smartos_startup_trace.py). Ne touche jamais a la configuration reelle.
# usage : BANC=<dossier de travail> run.sh <arbre> <trace.json>
#   <arbre> : dossier contenant spyder/ et smartos_startup_trace.py ; c'est le REPERTOIRE
#   COURANT qui selectionne l'arbre charge (start.py retire PYTHONPATH de sys.path).
#   $BANC/conf et $BANC/home sont crees au besoin (HOME jetable : sans lui les greffons
#   ecrivent dans le vrai HOME, ou echouent dans le bac a sable).
V="${SMARTPYTHONEDITOR_VENV:-/DATA/Python/SmartPython/CachyOS/versions/SmartPythonEditor}"
: "${BANC:?definir BANC=<dossier de travail jetable>}"
mkdir -p "$BANC/conf" "$BANC/home" "$BANC/traces"
# Scenario minimal du moteur --actions : attendre 2 s puis fermer proprement.
printf '{"rapport": "%s/rapport.json", "depart": 2, "actions": [{"action": "fermer"}]}\n' \
    "$BANC" > "$BANC/scenario.json"
export HOME="$BANC/home" QT_API=pyside6 SPYDER_QT_MAX_VERSION=6.12.0 QT_QPA_PLATFORM=offscreen
export SMARTOS_STARTUP_TRACE="$2" SMARTOS_T0="$(date +%s.%N)"
cd "$1" && exec "$V/bin/python" -m spyder.app.start --new-instance --conf-dir "$BANC/conf" \
    --actions "$BANC/scenario.json"
