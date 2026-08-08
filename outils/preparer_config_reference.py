#!/usr/bin/env python3
"""Prepare les spyder.ini / transient.ini de REFERENCE embarques dans le fork SmartPythonEditor.

Part des fichiers de Commun/config_files/spyder_<version>/ (la configuration SmartOS) et en
derive une version DISTRIBUABLE :
  - purge des chemins propres a la machine SmartOS (project_dir, interpreteurs ClearLinux,
    fichiers recents, css_path - autant de valeurs qui n'ont aucun sens ailleurs) ;
  - ajout des barres d'outils des greffons dans last_visible_toolbars (sur SmartOS, quatre
    scripts d'installation les ajoutent apres coup par spyder_config_set.py ; ici on controle
    le fichier livre, autant les y mettre directement) et retrait de main_toolbar (meme
    reglage que le "-=main_toolbar" d'installation_SmartPythonEditor.sh).

Ce que ce script NE fait PAS : estampiller main/version (CONF_VERSION depend du Spyder
reellement installe - fait par install.sh), remplir [main_interpreter] (depend du venv cible -
fait par install.sh), substituer __HOME__ (depend de la machine cible - fait par install.sh).

Transformation LIGNE A LIGNE, jamais configparser : meme raison que spyder_config_set.py
(reordonnancement des sections et reformatage des valeurs de plusieurs milliers de caracteres).

Usage : preparer_config_reference.py <dossier_source> <dossier_destination>
"""

import os
import re
import sys

# Sans main_toolbar (masquee sur SmartOS comme en distribution), avec les barres des greffons.
TOOLBARS = ("['file_toolbar', 'profile_toolbar', 'debug_toolbar', 'run_toolbar', "
            "'working_directory_toolbar', 'interpreter_toolbar', 'python_tutor_toolbar', "
            "'smartos_stop_toolbar', 'smartos_code_analysis_toolbar', "
            "'window_controls_toolbar']")

# cle -> nouvelle valeur, appliquee seulement dans la section indiquee (None = partout).
# Chaque entree DOIT etre consommee : une cle absente signifie que le format amont a change,
# et on echoue bruyamment plutot que de livrer une reference a moitie purgee.
REGLES_SPYDER_INI = {
    (None, "last_visible_toolbars"): TOOLBARS,
    (None, "project_dir"): "''",
    (None, "css_path"): "",
}
REGLES_TRANSIENT_INI = {
    ("main_interpreter", "custom_interpreters_list"): "[]",
    ("main_interpreter", "custom_interpreter"): "",
    ("main_interpreter", "last_envs"): "{}",
    ("main_interpreter", "executable"): "",
    ("editor", "recent_files"): "[]",
    ("editor", "filenames"): "[]",
    ("editor", "file_uuids"): "{}",
}


def transformer(chemin_source, chemin_dest, regles):
    restantes = dict(regles)
    section = None
    sortie = []
    with open(chemin_source, encoding="utf-8") as flux:
        for ligne in flux:
            m = re.match(r"\[(.+)\]\s*$", ligne)
            if m:
                section = m.group(1)
            else:
                m = re.match(r"([^=\s][^=]*?)\s*=", ligne)
                if m:
                    cle = m.group(1)
                    for (sec, nom) in list(restantes):
                        if nom == cle and sec in (None, section):
                            ligne = f"{cle} = {restantes.pop((sec, nom))}\n"
                            break
            sortie.append(ligne)
    if restantes:
        for (sec, nom) in restantes:
            print(f"ERREUR : cle '{nom}' (section {sec or 'quelconque'}) introuvable dans "
                  f"{chemin_source} - le format a-t-il change ?", file=sys.stderr)
        raise SystemExit(1)
    with open(chemin_dest, "w", encoding="utf-8") as flux:
        flux.writelines(sortie)


def main():
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        raise SystemExit(2)
    source, dest = sys.argv[1], sys.argv[2]
    os.makedirs(dest, exist_ok=True)
    transformer(os.path.join(source, "spyder.ini"),
                os.path.join(dest, "spyder.ini"), REGLES_SPYDER_INI)
    transformer(os.path.join(source, "transient.ini"),
                os.path.join(dest, "transient.ini"), REGLES_TRANSIENT_INI)
    print(f"Config de reference ecrite dans {dest} (purgee + barres de greffons).")


if __name__ == "__main__":
    main()
