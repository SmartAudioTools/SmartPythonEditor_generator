#!/usr/bin/env python3
"""Banc A/B du demarrage complet : runs ENTRELACES, medianes par arbre.

usage : BANC=<dossier de travail> ab.py <etiquette> <N> <arbre> [<arbre> ...]
  Chaque <arbre> est un sous-dossier de $BANC (copie de spyder/ + smartos_startup_trace.py).
  Un tour complet est jete (cache froid), N sont gardes. Les runs sont entrelaces
  (A, B, A, B...) pour que la charge de la machine pese autant sur chaque arbre : deux series
  successives ne sont PAS comparables (mesure du 05/10/2026 : la charge est passee de 3 a 16
  entre deux series, +60 % sur tous les reperes).
Les traces sont dans $BANC/traces/<etiquette>-<arbre>-<i>.json, le resume sur la sortie.
"""
import json
import os
import statistics as st
import subprocess
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
BANC = os.environ["BANC"]
NOMS = ["main_entree", "import_mainwindow_fin", "setup_debut",
        "decouverte_greffons_internes_fin", "setup_fin", "fenetre_visible",
        "editeur_utilisable", "lsp_pret", "noyau_pret"]


def main(argv):
    etiquette, n, arbres = argv[1], int(argv[2]), argv[3:]
    resultats = {a: [] for a in arbres}
    os.makedirs(f"{BANC}/traces", exist_ok=True)
    for i in range(n + 1):
        for a in arbres:
            trace = f"{BANC}/traces/{etiquette}-{a}-{i}.json"
            subprocess.run(["bash", f"{ICI}/run.sh", f"{BANC}/{a}", trace],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
            if i and os.path.exists(trace):
                resultats[a].append(json.load(open(trace)))
    for a in arbres:
        runs = resultats[a]
        print(a, "runs", len(runs),
              "charge", [round(j["contexte"]["charge_debut"], 1) for j in runs],
              "modules", st.median(j["contexte"].get("modules_apres_setup", 0) for j in runs))
    for nom in NOMS:
        ligne = f"  {nom:34}"
        for a in arbres:
            v = [j["reperes"][nom] for j in resultats[a] if nom in j["reperes"]]
            ligne += (f" | {a}: {st.median(v):6.0f} [{min(v):.0f}-{max(v):.0f}]" if v
                      else f" | {a}: -")
        print(ligne)


if __name__ == "__main__":
    main(sys.argv)
