#!/usr/bin/env python3
"""Redemarre le noyau d'une console DEDIEE deja ouverte avant chaque nouvelle execution.

CONTEXTE
--------
patch_spyder_dedicated_console_default.py (01/08/2026) rend "console dediee" par defaut,
dans le but explicite d'un noyau NEUF a CHAQUE execution (variables/threads residuels
impossibles d'un lancement a l'autre). Mais "console dediee" chez Spyder veut dire "une
console PAR FICHIER" - IPythonConsoleWidget.run_script() (widgets/main_widget.py) appelle
get_client_for_file(filename), et REUTILISE la console deja ouverte pour ce fichier si elle
existe, sans jamais redemarrer son noyau. Consequence, signalee par l'utilisateur le
02/08/2026 : relancer plusieurs fois le MEME fichier retombe sur le MEME noyau, avec les
memes residus que la reutilisation de la console courante etait censee eliminer.

CE QUE CE PATCH FAIT
--------------------
Dans run_script(), quand get_client_for_file(filename) trouve une console DEJA OUVERTE
pour ce fichier (branche qui aujourd'hui se contente de la reutiliser telle quelle),
ajoute un appel a self.restart_kernel(client, ask_before_restart=False) AVANT de
poursuivre - meme mecanisme que le bouton "Redemarrer le noyau", sans la boite de
confirmation. La suite de run_script() (attente de sig_prompt_ready si le noyau n'est pas
encore pret) gere deja normalement ce cas, puisque spyder_kernel_ready redevient False des
que replace_kernel() installe le nouveau noyau.

Ne cree PAS de nouvel onglet a chaque lancement (contrairement a un "get_client_for_file
qui ne trouve jamais rien") : une seule console par fichier, mais toujours un noyau vierge
au moment de l'executer.

Localisation par texte exact (le bloc if/else de selection du client), echec BRUYANT si
absent, idempotent (marqueur _smartos_fresh_kernel).

Usage : patch_spyder_fresh_kernel_per_run.py <chemin vers ipythonconsole/widgets/main_widget.py>
"""

import ast
import sys

MARKER = "_smartos_fresh_kernel"

ANCIEN = (
    "            client = self.get_client_for_file(filename)\n"
    "            if client is None:\n"
    "                # Create new client before running script\n"
    "                client = self.create_client_for_file(\n"
    "                    filename, is_cython=is_cython\n"
    "                )\n"
)

NOUVEAU = (
    "            client = self.get_client_for_file(filename)\n"
    "            if client is None:\n"
    "                # Create new client before running script\n"
    "                client = self.create_client_for_file(\n"
    "                    filename, is_cython=is_cython\n"
    "                )\n"
    "            else:\n"
    "                # Ajout SmartOS ({marker}) : noyau NEUF a CHAQUE execution, meme sur\n"
    "                # une console DEDIEE deja ouverte pour ce fichier - sinon les\n"
    "                # variables/threads residuels persistent d'un lancement a l'autre,\n"
    "                # exactement ce que \"console dediee\" est censee eviter. Decision\n"
    "                # utilisateur du 01/08/2026, confirmee le 02/08/2026. Cf.\n"
    "                # Commun/scripts/patch_spyder_fresh_kernel_per_run.py et\n"
    "                # patch_spyder_dedicated_console_default.py.\n"
    "                self.restart_kernel(client, ask_before_restart=False)\n"
).format(marker=MARKER)


def patch(path):
    with open(path, encoding="utf-8") as stream:
        source = stream.read()

    if MARKER in source:
        print(f"Deja patche : {path}")
        return True

    count = source.count(ANCIEN)
    if count != 1:
        print(f"ERREUR : point d'ancrage introuvable ou non unique ({count} occurrence(s)) "
              f"dans {path} (structure de run_script() changee ?)", file=sys.stderr)
        return False

    patched = source.replace(ANCIEN, NOUVEAU)

    try:
        ast.parse(patched)
    except SyntaxError as error:
        print(f"ERREUR : patch invalide pour {path} ({error})", file=sys.stderr)
        return False

    with open(path, "w", encoding="utf-8") as stream:
        stream.write(patched)
    print(f"Patche : {path} (noyau redemarre a chaque execution sur une console dediee)")
    return True


def main(argv):
    if len(argv) != 2:
        print(f"Usage : {argv[0]} <chemin vers ipythonconsole/widgets/main_widget.py>",
              file=sys.stderr)
        return 1
    return 0 if patch(argv[1]) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
