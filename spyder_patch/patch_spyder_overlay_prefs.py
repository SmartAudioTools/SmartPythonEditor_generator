#!/usr/bin/env python3
"""Ajoute deux options + deux cases a cocher (Preferences > Editeur > Affichage) pour l'overlay
d'infos de fichier (Commun/scripts/patch_spyder_editor_file_status.py) :

  - smartos_overlay_verbose (defaut True)             : libelles VERBEUX ("Ligne 11, Colonne 1,
    encodage UTF-8, fin de ligne Unix") ou ABREGES ("L 11, C 1  UTF-8  LF").
  - smartos_overlay_only_non_standard (defaut False)  : n'afficher encodage et fin de ligne QUE
    s'ils ne sont pas standard (autre chose qu'UTF-8 / Unix).

Ces options sont dans la section "editor" (lues par l'overlay via CONF.get("editor", ...)). Deux
fichiers patches :
  1. spyder/config/main.py            : declaration des deux options (defauts) dans la section editor
  2. spyder/plugins/editor/confpage.py: un groupe "Infos du fichier" (2 cases) ajoute a l'onglet
     "Affichage/Display".

Usage : patch_spyder_overlay_prefs.py <config/main.py> <plugins/editor/confpage.py>

Ancrage TEXTE sur des motifs uniques. Idempotent (marqueur par fichier). Re-parse avant ecriture ;
echoue BRUYAMMENT (code 1) si un ancrage manque - jamais deviner.
"""
import ast
import sys

# ---- config/main.py : declaration des options dans la section editor ----
MAIN_MARKER = "smartos_overlay_verbose"
MAIN_ANCHOR = (
    "              'wrap': False,\n"
    "              'wrapflag': True,\n"
)
MAIN_ADD = (
    "              'wrap': False,\n"
    "              'wrapflag': True,\n"
    "              # Overlay d'infos de fichier (SmartOS, cf.\n"
    "              # Commun/scripts/patch_spyder_editor_file_status.py + patch_spyder_overlay_prefs.py).\n"
    "              'smartos_overlay_verbose': True,\n"
    "              'smartos_overlay_only_non_standard': False,\n"
)

# ---- confpage.py : groupe + cases, ajoute a l'onglet Affichage ----
CONF_MARKER = "smartos_overlay_group"
CONF_ANCHOR_GROUP = "        # --- Tabs ---\n"
CONF_ADD_GROUP = (
    "        # -- Infos du fichier : options de l'overlay bas de l'editeur (SmartOS, cf.\n"
    "        # Commun/scripts/patch_spyder_editor_file_status.py). Libelles ecrits directement en\n"
    "        # francais (version destinee a des etudiants).\n"
    "        smartos_overlay_group = QGroupBox(\"Infos du fichier (bas de l'editeur)\")\n"
    "        smartos_overlay_verbose_box = newcb(\n"
    "            \"Libelles detailles (ex. \\u00ab Ligne 11, Colonne 1, encodage UTF-8, fin de ligne \"\n"
    "            \"Unix \\u00bb) plutot qu'abreges (\\u00ab L 11, C 1  UTF-8  LF \\u00bb)\",\n"
    "            'smartos_overlay_verbose')\n"
    "        smartos_overlay_only_ns_box = newcb(\n"
    "            \"N'afficher l'encodage et la fin de ligne que s'ils ne sont pas standard \"\n"
    "            \"(autre chose qu'UTF-8 / Unix)\",\n"
    "            'smartos_overlay_only_non_standard')\n"
    "        smartos_overlay_layout = QVBoxLayout()\n"
    "        smartos_overlay_layout.addWidget(smartos_overlay_verbose_box)\n"
    "        smartos_overlay_layout.addWidget(smartos_overlay_only_ns_box)\n"
    "        smartos_overlay_group.setLayout(smartos_overlay_layout)\n"
    "\n"
    "        # --- Tabs ---\n"
)
CONF_ANCHOR_TAB = (
    "                interface_group,\n"
    "                helpers_group,\n"
    "                highlight_group,\n"
    "            ],\n"
)
CONF_ADD_TAB = (
    "                interface_group,\n"
    "                helpers_group,\n"
    "                highlight_group,\n"
    "                smartos_overlay_group,\n"
    "            ],\n"
)


def patch_file(path, marker, anchor, replacement, label):
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as error:
        print(f"{path} illisible ({error}) - patch {label} non applique.", file=sys.stderr)
        sys.exit(1)
    if marker in source:
        print(f"Patch {label} deja applique.")
        return
    if source.count(anchor) != 1:
        print(f"Patch {label} : ancre introuvable ou ambigue dans {path} "
              f"(occurrences : {source.count(anchor)}) - non applique.", file=sys.stderr)
        sys.exit(1)
    patched = source.replace(anchor, replacement, 1)
    try:
        ast.parse(patched)
    except SyntaxError as error:
        print(f"{path} patche non valide ({error}) - aucune modification ecrite.", file=sys.stderr)
        sys.exit(1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(patched)
    print(f"Patch {label} applique ({path}).")


def main():
    if len(sys.argv) != 3:
        print(f"Usage : {sys.argv[0]} <config/main.py> <plugins/editor/confpage.py>",
              file=sys.stderr)
        return 1
    main_py, confpage_py = sys.argv[1], sys.argv[2]

    # 1. Options dans config/main.py.
    patch_file(main_py, MAIN_MARKER, MAIN_ANCHOR, MAIN_ADD, "options overlay (config)")

    # 2. Groupe + cases dans confpage.py (deux insertions independantes, chacune verifiee ci-dessus
    #    par patch_file : marqueur commun mais la 2e insertion (onglet) n'a pas le marqueur ->
    #    on la fait sur le meme fichier, en verifiant l'ancre.
    #    On applique d'abord le groupe (qui pose le marqueur smartos_overlay_group), puis l'ajout a
    #    l'onglet (qui utilise smartos_overlay_group). Comme patch_file saute si le marqueur est deja
    #    la, on gere les deux insertions ici manuellement.
    try:
        with open(confpage_py, encoding="utf-8") as f:
            source = f.read()
    except OSError as error:
        print(f"{confpage_py} illisible ({error}) - patch confpage non applique.", file=sys.stderr)
        return 1

    if CONF_MARKER in source:
        print("Patch confpage overlay deja applique.")
    else:
        for anchor, replacement, what in (
            (CONF_ANCHOR_GROUP, CONF_ADD_GROUP, "groupe"),
            (CONF_ANCHOR_TAB, CONF_ADD_TAB, "onglet Affichage"),
        ):
            if source.count(anchor) != 1:
                print(f"Patch confpage overlay ({what}) : ancre introuvable ou ambigue "
                      f"(occurrences : {source.count(anchor)}) - non applique.", file=sys.stderr)
                return 1
            source = source.replace(anchor, replacement, 1)
        try:
            ast.parse(source)
        except SyntaxError as error:
            print(f"confpage.py patche non valide ({error}) - aucune modification ecrite.",
                  file=sys.stderr)
            return 1
        with open(confpage_py, "w", encoding="utf-8") as f:
            f.write(source)
        print(f"Patch confpage overlay applique ({confpage_py}).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
