#!/usr/bin/env python3
"""Console DEDIEE : ferme la console precedente du fichier avant de le relancer.

CONTEXTE
--------
patch_spyder_dedicated_console_default.py (01/08/2026) rend "console dediee" par defaut,
dans le but explicite d'un noyau NEUF a CHAQUE execution (variables/threads residuels
impossibles d'un lancement a l'autre). Mais "console dediee" chez Spyder veut dire "une
console PAR FICHIER" - IPythonConsoleWidget.run_script() (widgets/main_widget.py) appelle
get_client_for_file(filename), et REUTILISE la console deja ouverte pour ce fichier si elle
existe, sans jamais redemarrer son noyau.

PREMIERE VERSION (02/08/2026), ET POURQUOI ELLE ETAIT FAUSSE
------------------------------------------------------------
Elle appelait self.restart_kernel(client, ask_before_restart=False) dans la branche
"console deja ouverte". Or **restart_kernel est decore @qdebounced(timeout=200)**
(superqt) : l'appel ne redemarre RIEN sur le moment, il PROGRAMME le redemarrage 200 ms
plus tard. run_script(), lui, continue immediatement, trouve l'ANCIEN noyau toujours
"pret", et lui envoie le %runfile / %debugfile. Le noyau est tue 200 ms apres, en pleine
execution.

Symptomes signales par l'utilisateur (TODO - Spyder - Debug.txt, 09/08/2026), tous deux
reproduits puis corriges sur banc `spyder --actions` :
  - deuxieme "Executer" : le script demarre puis meurt, aucun print n'apparait, la console
    n'affiche que "Redemarrage du noyau..." et une invite vide ;
  - deuxieme "Deboguer" : la ligne %debugfile s'affiche et rien ne suit, le point d'arret
    n'est jamais atteint.
Contournement que l'utilisateur avait trouve seul - fermer l'onglet de la console - c'est
exactement le correctif ci-dessous.

Pourquoi la verification du 02/08/2026 avait laisse passer ca : son script de test ecrivait
un compteur dans un fichier et se terminait INSTANTANEMENT, donc avant le redemarrage
differe. Le fichier contenait bien "1" puis "1". Un test qui dure plus de 200 ms - celui de
l'utilisateur en dure 1000 - echoue.

CE QUE CE PATCH FAIT
--------------------
Dans run_script(), quand get_client_for_file(filename) trouve une console DEJA OUVERTE pour
ce fichier, la FERME (close_client(..., ask_recursive=False), donc sans boite de dialogue)
et laisse la branche existante en creer une neuve. L'etat obtenu est alors EXACTEMENT celui
du tout premier lancement, seul chemin qui fonctionne : un client neuf, un noyau neuf, et
l'attente de sig_prompt_ready deja ecrite par Spyder. Aucun debounce dans le circuit, donc
plus aucune course.

Toujours un seul onglet par fichier (l'ancien est ferme, le nouveau reprend sa place), et
toujours un noyau vierge - les deux garanties visees en 2026-08-02.

Localisation par texte exact (le bloc de selection du client dans run_script), echec
BRUYANT si absent, idempotent (marqueur _smartos_fresh_kernel).

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
    "            if client is not None:\n"
    "                # Ajout SmartOS ({marker}) : noyau NEUF a CHAQUE execution.\n"
    "                # On FERME la console dediee precedente au lieu de redemarrer son\n"
    "                # noyau : restart_kernel est @qdebounced(200 ms), le redemarrage\n"
    "                # arriverait APRES l'envoi du %runfile et tuerait le script en cours\n"
    "                # d'execution (aucune sortie, point d'arret jamais atteint).\n"
    "                # Fermer puis recreer redonne l'etat exact du premier lancement, seul\n"
    "                # chemin qui fonctionne. Decision utilisateur du 01/08/2026, correctif\n"
    "                # du 09/08/2026. Cf. patch_spyder_fresh_kernel_per_run.py et\n"
    "                # patch_spyder_dedicated_console_default.py.\n"
    "                self.close_client(client=client, ask_recursive=False)\n"
    "                client = None\n"
    "            if client is None:\n"
    "                # Create new client before running script\n"
    "                client = self.create_client_for_file(\n"
    "                    filename, is_cython=is_cython\n"
    "                )\n"
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
    print(f"Patche : {path} (console dediee fermee et recreee a chaque execution)")
    return True


def main(argv):
    if len(argv) != 2:
        print(f"Usage : {argv[0]} <chemin vers ipythonconsole/widgets/main_widget.py>",
              file=sys.stderr)
        return 1
    return 0 if patch(argv[1]) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
