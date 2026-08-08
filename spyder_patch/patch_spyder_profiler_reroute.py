#!/usr/bin/env python3
"""Aiguille le profilage "fichier" de Spyder (F10 / bouton "Profiler le fichier").

Demande de l'utilisateur (TODO - Spyder - line profiler.txt) : F10 et le bouton "Profiler le
fichier" doivent lancer LES DEUX profilages (cProfile normal + line profiler) SI le fichier porte
des marqueurs de line profiler, et seulement le cProfile normal sinon.

CE QUE CE PATCH FAIT
--------------------
Modifie spyder/plugins/profiler/plugin.py (le profileur INTEGRE, cProfile) :

1. Ajoute 'spyder_line_profiler' a son OPTIONAL, pour pouvoir l'atteindre par get_plugin().

2. Reroute Profiler.profile_file (contexte Fichier, declenche par F10 ET par le bouton) : en tete
   de la methode, si le fichier a des marqueurs de line profiler (profile_targets.load_targets),
   on delegue au run du Line Profiler - qui, depuis le profilage COMBINE (cf.
   le fork du greffon spyder-line-profiler (depot SmartPythonEditorPlugins/spyder_line_profiler)), execute cProfile ET kernprof en une seule fois et
   remplit les DEUX panneaux. Sinon, on laisse le cProfile in-noyau d'origine s'executer (le
   corps de la methode, inchange). Les contextes Cellule/Selection ne passent pas par profile_file
   et gardent donc le cProfile in-noyau.

POURQUOI CETTE FORME
--------------------
cProfile n'a aucun besoin d'un noyau ; c'est Spyder 6 qui l'execute in-noyau par choix. Le run
COMBINE, lui, tourne en sous-processus externe (cProfile enveloppe kernprof) - le seul montage
qui donne les deux mesures en UNE execution. On ne reroute que le cas "fichier avec marqueurs" :
le cas "cellule/selection" a besoin de l'etat vivant du noyau et resterait faux en sous-processus.

Localisation par le module ast (structure du code), echec BRUYANT si un point d'ancrage manque,
idempotent (marqueur _smartos_lp).

Usage : patch_spyder_profiler_reroute.py <profiler/plugin.py>
"""

import ast
import os.path as osp
import sys

MARKER = "_smartos_lp"

# --- Def-heatmap cProfile meme SANS marqueur -----------------------------------------------
# Le chemin cProfile-seul du bouton "Profiler le fichier" (Profiler.profile_file -> exec_files, quand
# aucune fonction n'est marquee) ne passe PAS par le line profiler, donc n'appelait jamais publish() :
# la marge de droite de l'editeur restait vide. On se greffe sur l'arrivee du resultat cProfile
# (ProfilerSubWidget.show_profile_buffer) pour publier la couche def-heatmap (un cumtime par fonction,
# a sa ligne de `def`). Cf. profile_results.publish_cprofile.
DATA_TREE_MARKER = "_smartos_publish_cprofile"
DATA_TREE_PATCH = (
    "        # SmartOS : alimenter la marge de droite de l'editeur (def-heatmap cProfile) meme sans\n"
    "        # fonction marquee. Le chemin cProfile-seul du bouton \"Profiler le fichier\" ne passe pas\n"
    "        # par le line profiler, donc n'appelait jamais publish(). Cf.\n"
    "        # profile_results.publish_cprofile et patch_spyder_profiler_reroute.py.\n"
    "        try:\n"
    "            from spyder_line_profiler.spyder.profile_results import (\n"
    "                publish_cprofile as _smartos_publish_cprofile)\n"
    "            _smartos_publish_cprofile(prof_buffer)\n"
    "        except Exception:\n"
    "            pass\n"
)


def patch_data_tree(plugin_path):
    """Branche publish_cprofile sur ProfilerSubWidget.show_profile_buffer (widgets/profiler_data_tree.py).

    Non fatal si le fichier ou la methode est introuvable : la def-heatmap sans marqueur est un plus,
    elle ne doit pas empecher le reste du patch.
    """
    dt = osp.join(osp.dirname(plugin_path), "widgets", "profiler_data_tree.py")
    if not osp.isfile(dt):
        print(f"AVERTISSEMENT : {dt} introuvable - def-heatmap cProfile sans marqueur non branchee.",
              file=sys.stderr)
        return
    with open(dt, encoding="utf-8") as stream:
        source = stream.read()
    if DATA_TREE_MARKER in source:
        return  # deja branche
    method = find_method(ast.parse(source), "ProfilerSubWidget", "show_profile_buffer")
    if method is None:
        print(f"AVERTISSEMENT : show_profile_buffer introuvable dans {dt} - def-heatmap non branchee.",
              file=sys.stderr)
        return
    # Inserer juste apres le docstring (body[0]) : publish_cprofile ignore un buffer vide, donc pas
    # besoin de se placer apres la garde `if not prof_buffer`.
    insert_line = method.body[1].lineno - 1
    lines = source.splitlines(keepends=True)
    lines.insert(insert_line, DATA_TREE_PATCH)
    patched = "".join(lines)
    try:
        ast.parse(patched)
    except SyntaxError as error:
        print(f"AVERTISSEMENT : patch data_tree invalide ({error}) - non applique.", file=sys.stderr)
        return
    with open(dt, "w", encoding="utf-8") as stream:
        stream.write(patched)
    print(f"Patche : {dt} (def-heatmap cProfile sur show_profile_buffer)")

OPTIONAL_ANCHOR = "    OPTIONAL = [Plugins.Editor]\n"
OPTIONAL_PATCH = "    OPTIONAL = [Plugins.Editor, 'spyder_line_profiler']  # SmartOS : profilage combine\n"

REROUTE_PATCH = '''        # Ajout SmartOS (_smartos_lp) : aiguillage du profilage "fichier" (F10 / bouton
        # "Profiler le fichier"). Si le fichier lance a QUELQUE CHOSE a line-profiler (des marqueurs
        # n'importe ou, OU l'option "profiler tout le code utilisateur"), on lance le profilage
        # COMBINE (cProfile + lignes en une execution) qui remplit les deux panneaux ; sinon on
        # laisse le cProfile in-noyau d'origine (le corps ci-dessous) s'executer. Cf.
        # Commun/scripts/patch_spyder_profiler_reroute.py
        #
        # DECISION et LANCEMENT sont SEPARES a dessein (durcissement du 23/07/2026) :
        #   - la DECISION est sous try/except : si elle echoue, on se replie sur le cProfile
        #     integre, mais JAMAIS en silence. L'ancien `traceback.print_exc()` partait sur un
        #     stderr que personne ne lit (le processus graphique de Spyder l'envoie la ou il a ete
        #     lance, donc nulle part depuis le menu) ; il a fallu une soiree pour diagnostiquer un
        #     "le line profiler ne se lance plus" alors que toute la chaine etait intacte ;
        #   - le LANCEMENT est HORS du try : analyze() peut avoir DEJA demarre le sous-processus
        #     kernprof, donc enchainer sur le cProfile in-noyau REJOUERAIT le script - effets de
        #     bord en double (fichiers ecrits, requetes reseau). Une exception remonte alors a
        #     Spyder, qui l'affiche : bruyant, mais sans seconde execution.
        _smartos_cibles = None
        try:
            _smartos_lp = self.get_plugin('spyder_line_profiler', error=False)
            if _smartos_lp is not None:
                import os.path as _smartos_osp
                from spyder_line_profiler.spyder.profile_targets import (
                    config_lanceur as _smartos_config_lanceur)
                # config_lanceur honore les DEUX modes : des marqueurs (targets non vides,
                # n'importe ou) OU l'option "tout le code utilisateur" (all_user) => combine.
                _smartos_file = _smartos_osp.normpath(
                    _smartos_osp.abspath(input['run_input']['path']))
                _smartos_config = _smartos_config_lanceur(_smartos_file)
                _smartos_cibles = (bool(_smartos_config['targets'])
                                   or _smartos_config['all_user'])
        except Exception:
            import logging as _smartos_logging
            _smartos_logging.getLogger(__name__).exception(
                "SmartOS : la decision de reroutage vers le line profiler a echoue ; repli sur "
                "le cProfile integre. Des fonctions marquees seront ignorees.")
            _smartos_cibles = None
        if _smartos_cibles:
            _smartos_p = conf['params']
            _smartos_lp.get_widget().analyze(
                _smartos_file,
                wdir=_smartos_p['working_dir']['path'],
                args=_smartos_p['executor_params'].get('args'))
            return []
'''

# Migration d'une install deja patchee avec l'ANCIEN reroutage (predicat base sur les seuls
# marqueurs) vers le nouveau (run_prof_mod_args, qui honore aussi l'option "tout le code
# utilisateur"). Deux remplacements ciblant UNIQUEMENT le code (pas les commentaires, dont le
# texte a pu deriver entre versions installees) : (1) l'import, (2) le predicat, qui passe de
# "if _smartos_prof_mod():" (sans argument, _smartos_file calcule dans le if) a
# "if _smartos_prof_mod(_smartos_file):" (_smartos_file calcule avant, passe en argument).
MIGRATIONS = [
    ("                    build_prof_mod_args as _smartos_prof_mod)",
     "                    run_prof_mod_args as _smartos_prof_mod)"),
    ("                if _smartos_prof_mod():\n"
     "                    _smartos_file = _smartos_osp.normpath(\n"
     "                        _smartos_osp.abspath(input['run_input']['path']))\n",
     "                _smartos_file = _smartos_osp.normpath(\n"
     "                    _smartos_osp.abspath(input['run_input']['path']))\n"
     "                if _smartos_prof_mod(_smartos_file):\n"),
]

# Migration du DURCISSEMENT (23/07/2026) : une install patchee avec l'ancien bloc "tout sous
# try/except + traceback.print_exc()" passe au bloc "decision sous try (journalisee), lancement
# hors try". Deux fragments de CODE seulement (les commentaires ont pu deriver d'une version
# installee a l'autre - regle du depot : ancrer sur du code, jamais sur du commentaire), chacun
# unique dans le fichier. Declenchee par la presence de `_smartos_tb.print_exc()`.
# Migration vers la refonte du lanceur (24/07/2026) : le predicat passe de
# run_prof_mod_args (liste de cibles kernprof, supprimee de profile_targets) a config_lanceur
# (configuration du lanceur lp_launcher : targets non vides OU all_user). Declenchee par la
# presence de l'ancien import. Fragments de CODE uniquement, uniques dans le fichier.
MIGRATIONS_LANCEUR = [
    ("                from spyder_line_profiler.spyder.profile_targets import (\n"
     "                    run_prof_mod_args as _smartos_prof_mod)\n",
     "                from spyder_line_profiler.spyder.profile_targets import (\n"
     "                    config_lanceur as _smartos_config_lanceur)\n"),
    ("                _smartos_cibles = _smartos_prof_mod(_smartos_file)\n",
     "                _smartos_config = _smartos_config_lanceur(_smartos_file)\n"
     "                _smartos_cibles = (bool(_smartos_config['targets'])\n"
     "                                   or _smartos_config['all_user'])\n"),
]

MIGRATIONS_DURCISSEMENT = [
    # 1) Initialiser _smartos_cibles AVANT le try : sans plugin line profiler, la variable ne
    #    serait jamais affectee et le `if _smartos_cibles` leverait NameError.
    ("        try:\n"
     "            _smartos_lp = self.get_plugin('spyder_line_profiler', error=False)\n",
     "        _smartos_cibles = None\n"
     "        try:\n"
     "            _smartos_lp = self.get_plugin('spyder_line_profiler', error=False)\n"),
    # 2) Sortir le lancement du try, et journaliser le repli au lieu de le taire.
    ("                if _smartos_prof_mod(_smartos_file):\n"
     "                    _smartos_p = conf['params']\n"
     "                    _smartos_lp.get_widget().analyze(\n"
     "                        _smartos_file,\n"
     "                        wdir=_smartos_p['working_dir']['path'],\n"
     "                        args=_smartos_p['executor_params'].get('args'))\n"
     "                    return []\n"
     "        except Exception:\n"
     "            import traceback as _smartos_tb\n"
     "            _smartos_tb.print_exc()\n",
     "                _smartos_cibles = _smartos_prof_mod(_smartos_file)\n"
     "        except Exception:\n"
     "            import logging as _smartos_logging\n"
     "            _smartos_logging.getLogger(__name__).exception(\n"
     "                \"SmartOS : la decision de reroutage vers le line profiler a echoue ; \"\n"
     "                \"repli sur le cProfile integre. Des fonctions marquees seront ignorees.\")\n"
     "            _smartos_cibles = None\n"
     "        if _smartos_cibles:\n"
     "            _smartos_p = conf['params']\n"
     "            _smartos_lp.get_widget().analyze(\n"
     "                _smartos_file,\n"
     "                wdir=_smartos_p['working_dir']['path'],\n"
     "                args=_smartos_p['executor_params'].get('args'))\n"
     "            return []\n"),
]


# --- Correctif F10 : rendre le raccourci du bouton "Profile file" APPLICATIF.
# Par defaut create_run_in_executor_button enregistre le raccourci en Qt.WidgetShortcut : il ne se
# declenche que si le panneau Profileur a le focus, jamais depuis l'editeur - d'ou "F10 ne fait
# rien" alors que le bouton et Shift+F10 marchent. Le Line Profiler, lui, passe explicitement
# Qt.ApplicationShortcut (fire depuis n'importe ou). On aligne le profileur integre pour son bouton
# Fichier (F10). Independant du reroutage, idempotent (presence de shortcut_widget_context).
QT_IMPORT_ANCHOR = "from packaging.version import parse\n"
QT_IMPORT_LINE = ("from packaging.version import parse\n"
                  "from qtpy.QtCore import Qt  # SmartOS : F10 applicatif (cf. patch reroute)\n")

F10_OLD = ('            text=_("Profile file"),\n'
           '            tip=_("Profile file"),\n'
           "            icon=self.create_icon('profiler'),\n"
           "            shortcut_context=self.NAME,\n"
           "            register_shortcut=True,\n")
F10_NEW = ('            text=_("Profile file"),\n'
           '            tip=_("Profile file"),\n'
           "            icon=self.create_icon('profiler'),\n"
           "            shortcut_context=self.NAME,\n"
           "            register_shortcut=True,\n"
           "            # SmartOS : F10 doit partir depuis l'editeur, pas seulement quand le panneau\n"
           "            # Profileur a le focus (defaut Qt.WidgetShortcut). Comme Shift+F10 du Line\n"
           "            # Profiler, on rend le raccourci applicatif.\n"
           "            shortcut_widget_context=Qt.ApplicationShortcut,\n")


def appliquer_f10_applicatif(source, path):
    """(source modifiee, a_change) ; (None, False) si l'ancre manque. Idempotent."""
    if "shortcut_widget_context=Qt.ApplicationShortcut" in source:
        return source, False
    if F10_OLD not in source:
        print(f"ERREUR : bouton 'Profile file' introuvable pour le correctif F10 dans {path} "
              f"(structure changee ?)", file=sys.stderr)
        return None, False
    patched = source.replace(F10_OLD, F10_NEW)
    if "from qtpy.QtCore import Qt" not in patched:
        if QT_IMPORT_ANCHOR not in patched:
            print(f"ERREUR : ancre d'import Qt introuvable dans {path}", file=sys.stderr)
            return None, False
        patched = patched.replace(QT_IMPORT_ANCHOR, QT_IMPORT_LINE)
    return patched, True


def find_method(tree, class_name, method_name):
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for sub in node.body:
                if (isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and sub.name == method_name):
                    return sub
    return None


def patch(path):
    with open(path, encoding="utf-8") as stream:
        source = stream.read()

    patched = source
    faits = []

    # 1) Reroutage de profile_file (OPTIONAL + insertion) : pose si absent, migration si ancien.
    if MARKER in patched:
        # Deja reroute. Migrer un ancien predicat (marqueurs seuls) vers run_prof_mod_args
        # (marqueurs OU option "tout le code utilisateur").
        if "build_prof_mod_args as _smartos_prof_mod" in patched:
            for vieux, neuf in MIGRATIONS:
                if vieux not in patched:
                    print(f"ERREUR : fragment de migration introuvable dans {path} "
                          f"(reroutage d'une version inattendue ?)", file=sys.stderr)
                    return False
                patched = patched.replace(vieux, neuf)
            faits.append("reroutage migre (option 'tout le code utilisateur')")
        # Durcissement : APRES la migration ci-dessus, qui produit justement l'ancrage attendu
        # ("if _smartos_prof_mod(_smartos_file):"). Un ancien bloc se reconnait a son print_exc().
        if "_smartos_tb.print_exc()" in patched:
            for vieux, neuf in MIGRATIONS_DURCISSEMENT:
                if vieux not in patched:
                    print(f"ERREUR : fragment de durcissement introuvable dans {path} "
                          f"(reroutage d'une version inattendue ?)", file=sys.stderr)
                    return False
                patched = patched.replace(vieux, neuf)
            faits.append("reroutage durci (repli journalise, lancement hors try)")
        # Refonte du lanceur : APRES les deux migrations ci-dessus, qui produisent justement
        # l'ancrage attendu ("_smartos_cibles = _smartos_prof_mod(_smartos_file)").
        if "run_prof_mod_args as _smartos_prof_mod" in patched:
            for vieux, neuf in MIGRATIONS_LANCEUR:
                if vieux not in patched:
                    print(f"ERREUR : fragment de migration vers config_lanceur introuvable "
                          f"dans {path} (reroutage d'une version inattendue ?)",
                          file=sys.stderr)
                    return False
                patched = patched.replace(vieux, neuf)
            faits.append("predicat migre vers config_lanceur (refonte du lanceur)")
    else:
        # OPTIONAL : rend le Line Profiler atteignable.
        if OPTIONAL_ANCHOR not in patched:
            print(f"ERREUR : ancre OPTIONAL introuvable dans {path} (structure changee ?)",
                  file=sys.stderr)
            return False
        patched = patched.replace(OPTIONAL_ANCHOR, OPTIONAL_PATCH)
        # Insertion en tete du corps de profile_file.
        method = find_method(ast.parse(patched), "Profiler", "profile_file")
        if method is None:
            print(f"ERREUR : Profiler.profile_file introuvable dans {path}", file=sys.stderr)
            return False
        insert_line = method.body[0].lineno - 1   # 0-indexe : juste avant la 1re instruction
        lines = patched.splitlines(keepends=True)
        lines.insert(insert_line, REROUTE_PATCH)
        patched = "".join(lines)
        faits.append("OPTIONAL + profile_file reroute")

    # 2) F10 applicatif (independant du reroutage).
    patched, change_f10 = appliquer_f10_applicatif(patched, path)
    if patched is None:
        return False
    if change_f10:
        faits.append("F10 applicatif")

    # 3) Def-heatmap cProfile sans marqueur (fichier separe profiler_data_tree.py, idempotent).
    patch_data_tree(path)

    if not faits:
        print(f"Deja patche (a jour) : {path}")
        return True

    try:
        ast.parse(patched)
    except SyntaxError as error:
        print(f"ERREUR : patch invalide pour {path} ({error})", file=sys.stderr)
        return False
    with open(path, "w", encoding="utf-8") as stream:
        stream.write(patched)
    print(f"Patche : {path} ({', '.join(faits)})")
    return True


def main(argv):
    if len(argv) != 2:
        print(f"Usage : {argv[0]} <profiler/plugin.py>", file=sys.stderr)
        return 1
    return 0 if patch(argv[1]) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
