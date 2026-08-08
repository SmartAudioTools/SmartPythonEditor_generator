#!/usr/bin/env python3
"""Empeche le dialogue "Executer > Configuration" de planter sur un jeu de parametres d'une AUTRE forme.

SYMPTOME (rencontre en direct le 25/07/2026, en lancant un profilage) :

    File ".../spyder/plugins/ipythonconsole/widgets/run_conf.py", line 103, in set_configuration
        use_current_console = config['current']
    KeyError: 'current'

CAUSE. Chaque executeur (console IPython, profileur, terminal externe, pylint...) a sa propre
FORME de parametres : la console attend {current, post_mortem, python_args_enabled, python_args,
clear_namespace, console_namespace}, le profileur {args_enabled, args}, le terminal externe deux
formes selon l'extension. Ces jeux sont enregistres dans transient.ini, section [run], option
"parameters", indexes par executeur puis par (extension, contexte).

Spyder pousse ces parametres enregistres dans le widget de configuration affiche par DEUX chemins
distincts, et un seul des deux verifie que les formes concordent (spyder/plugins/run/widgets.py) :

  - `select_context` (~ligne 411), PRUDENT :
        params_set = default_params if reset else (exec_params["executor_params"] or default_params)
        if params_set.keys() == default_params.keys():
            self.current_widget.set_configuration(params_set)

  - `update_parameter_set` (~ligne 846), SANS GARDE :
        exec_params = params['executor_params']
        self.current_widget.set_configuration(exec_params)

Il suffit donc qu'un jeu enregistre ne corresponde pas au widget affiche pour que le second chemin
leve une KeyError sur la premiere cle manquante - le dialogue ne s'ouvre plus, et l'action qui
passait par lui (ici un profilage) echoue.

Ces jeux mal apparies EXISTENT en pratique : la configuration de l'utilisateur en contenait trois,
sous l'executeur "profiler", portant des parametres de console IPython - dont un marque "par
defaut". Leur nom, "Defaut (personnalise)", est precisement celui que fabrique
`RunDialog._get_auto_custom_name()` : ils ont donc ete ecrits par ce dialogue lui-meme. On ne
corrige pas ici le chemin d'ECRITURE (non identifie a ce stade) : on rend la LECTURE increvable,
ce qui suffit a ce que le dialogue s'ouvre toujours, et evite qu'un jeu incoherent - quelle qu'en
soit l'origine, y compris une future montee de version qui ajouterait une option - ne bloque
l'application.

CORRECTIF : la meme garde que celle deja ecrite par Spyder quinze lignes plus haut. Si les formes
divergent, on affiche les valeurs par DEFAUT du widget (plutot que de ne rien afficher : les
champs resteraient sur les valeurs du jeu precedent, ce qui donnerait a lire une configuration
qui n'est celle de personne).

Usage : patch_spyder_run_dialog_params_guard.py <chemin spyder/plugins/run/widgets.py>
"""

import ast
import shutil
import sys

MARQUEUR = "[SmartOS run-params-guard]"

ANCRE = (
    "        params = stored_params[\"params\"]\n"
    "        working_dir_params = params['working_dir']\n"
    "        exec_params = params['executor_params']\n"
    "        self.current_widget.set_configuration(exec_params)\n"
)

REMPLACEMENT = (
    "        params = stored_params[\"params\"]\n"
    "        working_dir_params = params['working_dir']\n"
    "        exec_params = params['executor_params']\n"
    "        # " + MARQUEUR + " : un jeu de parametres enregistre pour un AUTRE\n"
    "        # executeur n'a pas les memes cles que le widget affiche, et set_configuration lit ces\n"
    "        # cles sans defaut (KeyError: 'current' en lancant un profilage, 25/07/2026). Meme\n"
    "        # garde que dans select_context ci-dessus ; a formes divergentes, on montre les valeurs\n"
    "        # par defaut du widget plutot que de laisser a l'ecran celles du jeu precedent.\n"
    "        _smartos_defauts = self.current_widget.get_default_configuration()\n"
    "        if exec_params.keys() == _smartos_defauts.keys():\n"
    "            self.current_widget.set_configuration(exec_params)\n"
    "        else:\n"
    "            self.current_widget.set_configuration(_smartos_defauts)\n"
)


def echec(*lignes):
    for ligne in lignes:
        print(f"\033[1;31m{ligne}\033[0m", file=sys.stderr)
    sys.exit(1)


def main(argv):
    if len(argv) != 2:
        echec(f"Usage : {argv[0]} <chemin spyder/plugins/run/widgets.py>")
    chemin = argv[1]
    try:
        source = open(chemin, encoding="utf-8").read()
    except OSError as erreur:
        echec(f"[run-params-guard] illisible : {erreur}")

    if MARQUEUR in source:
        print("[run-params-guard] deja applique.")
        return 0

    if source.count(ANCRE) != 1:
        echec("[run-params-guard] ancrage introuvable ou multiple dans " + chemin,
              f"  {source.count(ANCRE)} occurrence(s) de l'appel non garde a set_configuration",
              "  (update_parameter_set). Le code amont a change : verifier si la garde n'y est pas",
              "  deja, auquel cas ce correctif n'a plus lieu d'etre.")

    nouveau = source.replace(ANCRE, REMPLACEMENT, 1)
    try:
        ast.parse(nouveau)
    except SyntaxError as erreur:
        echec(f"[run-params-guard] le fichier produit n'est pas du Python valide : {erreur}")

    shutil.copy2(chemin, chemin + ".stock")
    with open(chemin, "w", encoding="utf-8") as flux:
        flux.write(nouveau)
    print("[run-params-guard] garde de forme ajoutee a RunDialog.update_parameter_set.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
