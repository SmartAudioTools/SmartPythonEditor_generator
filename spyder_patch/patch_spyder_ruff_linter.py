#!/usr/bin/env python3
"""Patch languageserver/provider.py : rend a ruff son drapeau de LINT, que Spyder ecrase.

BUG AMONT DE SPYDER 6.1.5, pas de nous. Consequence visible : la marge gauche de l'editeur n'affiche
AUCUN avertissement ni erreur, alors que tout semble en place.

CAUSE RACINE. ruff est A LA FOIS un linter et un formateur, et pylsp-ruff a deux cles DISTINCTES
pour cela (pylsp_ruff/settings.py) :
    enabled        -> le LINT
    formatEnabled  -> le FORMATAGE
Spyder ecrit les deux sur la meme cle. Dans generate_python_config() :

    ruff = {"enabled": self.get_conf("ruff"), ...}     # le choix du LINTER
    ...
    plugins['ruff'].update(ruff)                       # correct
    for fmt in ['autopep8', 'yapf', 'black', 'ruff']:
        plugins[fmt].update({'enabled': fmt == formatter})   # <- ECRASE le drapeau du LINT

Des lors que le formateur choisi n'est pas ruff - ici black -, la seconde ecriture remet
`enabled` a False. Et pylsp ne fait pas dans la nuance : _update_disabled_plugins() DESENREGISTRE
tout greffon dont `enabled` est faux (pylsp/config/config.py). ruff ne lint donc plus du tout. Si
pyflakes est coupe par ailleurs - ce que fait naturellement quiconque a choisi ruff comme linter -,
il ne reste PLUS AUCUN linter, et le serveur publie une liste de diagnostics VIDE.

Detail qui montre que l'intention amont etait bien d'avoir deux cles : le dictionnaire par defaut de
Spyder (spyder/config/lsp.py) declare `'formatedEnabled': False` pour ruff... orthographie de travers,
donc jamais lu par pylsp-ruff, qui attend `formatEnabled`. La cle existait, elle ne servait a rien.

CE QUE FAIT LE PATCH. Retirer ruff de la boucle des formateurs et lui donner son propre dictionnaire,
portant le choix du formateur sur `formatEnabled`. `enabled` reste donc celui du linter. Une seule
expression change ; ni le choix du formateur ni la longueur de ligne ne bougent.

POURQUOI PAS AUTREMENT
  - remettre pyflakes en marche masquerait le defaut sans le corriger, et donnerait a l'utilisateur
    un linter qu'il n'a pas choisi ;
  - corriger la faute de frappe de config/lsp.py ne suffirait PAS : c'est la boucle qui ecrase, pas
    la valeur par defaut ;
  - forcer `enabled` a True en dur ignorerait le reglage de l'utilisateur.

PREUVE, faite le 26/07/2026 avant d'ecrire une ligne de correctif. La configuration EXACTE generee
par Spyder a ete capturee dans l'application en marche, puis rejouee contre un vrai pylsp en
JSON-RPC : zero diagnostic. La meme, en changeant LE SEUL booleen plugins.ruff.enabled : deux
diagnostics (F401 et F821). Le test echoue donc bien sans le correctif.

COMMENT SAVOIR, UN JOUR, QUE CE CONTOURNEMENT EST INUTILE. Relire la boucle des formateurs dans
generate_python_config() : si elle n'ecrit plus `enabled` pour ruff (ou si ruff n'y figure plus), le
bug est corrige en amont et ce patch peut disparaitre. Test de bout en bout : choisir ruff comme
linter et black comme formateur, ouvrir un fichier contenant un import inutilise, et regarder si la
marge affiche le triangle.

Usage : patch_spyder_ruff_linter.py <chemin vers languageserver/provider.py installe>

IDEMPOTENCE : le bloc est saute si son marqueur est deja dans le fichier. Ancrage sur un motif
UNIQUE, ast.parse avant ecriture, echec BRUYANT (code 1) si l'ancre est introuvable ou non unique -
un patch qui devine est un patch qui casse en silence a la prochaine version.
"""
import ast
import sys

MARQUEUR = "[SmartOS ruff-linter-vs-formateur]"

ANCIEN = '''        # Setting max line length for formatters.'''

NOUVEAU = '''        # PATCH SmartOS %s (26/07/2026) : ruff est A LA FOIS un
        # linter et un formateur, et pylsp-ruff a deux cles DISTINCTES - `enabled` pour le lint,
        # `formatEnabled` pour le formatage. La boucle ci-dessus ecrit le choix du FORMATEUR sur
        # `enabled`, donc elle ECRASE plus bas (plugins['ruff'].update) le drapeau du LINTER : des
        # que le formateur choisi n'est pas ruff, ruff cesse de linter. Et pylsp desenregistre tout
        # greffon dont `enabled` est faux, si bien qu'avec pyflakes coupe - le reglage naturel quand
        # on a choisi ruff - il ne reste AUCUN linter et le serveur publie une liste vide : la marge
        # de l'editeur n'affiche plus rien.
        # On rend donc a ruff son drapeau de lint, en portant le choix du formateur sur la cle que
        # pylsp-ruff lit vraiment. (La cle `formatedEnabled` du dictionnaire par defaut de Spyder est
        # une faute de frappe : elle n'est lue par personne.)
        formatter_options['ruff'] = {
            'formatEnabled': formatter == 'ruff',
        }

        # Setting max line length for formatters.''' % MARQUEUR


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers languageserver/provider.py>", file=sys.stderr)
        return 1

    chemin = sys.argv[1]
    try:
        with open(chemin, encoding="utf-8") as f:
            source = f.read()
    except OSError as erreur:
        print(f"provider.py illisible ({erreur}) - patch linter ruff non applique.", file=sys.stderr)
        return 1

    if MARQUEUR in source:
        print("Patch linter ruff : deja en place.")
        return 0

    n = source.count(ANCIEN)
    if n != 1:
        print(f"Ancre introuvable ou non unique (occurrences={n}) dans {chemin} - "
              f"generate_python_config() a peut-etre ete restructure, patch linter ruff non "
              f"applique.", file=sys.stderr)
        return 1

    patchee = source.replace(ANCIEN, NOUVEAU, 1)
    try:
        ast.parse(patchee)
    except SyntaxError as erreur:
        print(f"Le provider.py patche n'est pas du Python valide ({erreur}) - aucune modification "
              "ecrite.", file=sys.stderr)
        return 1

    with open(chemin, "w", encoding="utf-8") as f:
        f.write(patchee)
    print(f"Patch linter ruff applique : le choix du formateur n'eteint plus le linter ({chemin})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
