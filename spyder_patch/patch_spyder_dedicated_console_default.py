#!/usr/bin/env python3
"""Patch spyder/plugins/ipythonconsole/widgets/run_conf.py : "Executer dans une console dediee"
devient le defaut pour tout fichier jamais configure individuellement, a la place de "console
actuelle".

Contexte (TODO - Spyder - General.txt, 01/08/2026), deux questions liees :
  - « pourquoi les icones des actions du debuger ne disparaissent pas apres un stop, mais que
    quand on ferme que IPython ? » - reponse (cf. DONE - Spyder - reste.txt, entree du meme jour) :
    Stop met la commande pdb "exit" en FILE D'ATTENTE si le code debogue ne rend jamais la main a
    Python apres l'interruption (boucle native, bibliotheque C, appel bloquant) ; la commande n'est
    alors jamais reellement envoyee et l'etat "en debogage" persiste jusqu'a la fermeture du noyau -
    limitation de Spyder/pdb, pas un bug SmartOS, et pas contournable cote debogueur ;
  - « ne faut-il pas lancer une nouvelle console a chaque execution d'un script ? » - decision de
    l'utilisateur (AskUserQuestion, 01/08/2026) : OUI, dediee par defaut pour tous les scripts. Un
    noyau NEUF a chaque execution rend le residu ci-dessus tout simplement impossible (rien ne
    PERSISTE d'une execution a l'autre), au prix de la vitesse (redemarrage de noyau a chaque
    "Executer") et de la perte des variables entre deux lancements - compromis assume, pedagogique
    pour des eleves.

CE QUE CE PATCH FAIT : "Executer dans une console dediee" existe deja nativement dans Spyder (menu
Executer > Configuration par fichier, choix radio) ; seul son REGLAGE PAR DEFAUT pour un fichier
jamais configure (get_default_configuration(), 'current': True) est change en False. Un fichier
DEJA configure explicitement par l'utilisateur (console actuelle OU dediee) n'est pas affecte : ce
choix est mémorisé par fichier dans running_config, get_default_configuration() n'intervenant que
pour un fichier qui n'a jamais ete configure.

Usage : patch_spyder_dedicated_console_default.py <chemin vers ipythonconsole/widgets/run_conf.py>

IDEMPOTENT : re-application sans effet si deja pose (verifie sur le texte exact). Re-parse avant
ecriture ; echec BRUYANT (code 1) si l'ancre est introuvable ou non unique.
"""
import ast
import sys

ANCIEN = "            'current': True,\n"
NOUVEAU = (
    "            # SmartOS (patch_spyder_dedicated_console_default.py) : dediee par defaut - "
    "decision de l'utilisateur du 01/08/2026, cf. TODO - Spyder - General.txt.\n"
    "            'current': False,\n"
)


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers ipythonconsole/widgets/run_conf.py>",
              file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as fichier:
            source = fichier.read()
    except OSError as erreur:
        print(f"run_conf.py illisible ({erreur}) - patch console dediee par defaut non applique.",
              file=sys.stderr)
        return 1

    if NOUVEAU in source:
        print("Patch console dediee par defaut deja applique.")
        return 0

    if source.count(ANCIEN) != 1:
        print(f"Ancre introuvable ou non unique dans {path} - Spyder a peut-etre change "
              f"get_default_configuration(). Patch non applique.", file=sys.stderr)
        return 1

    patched = source.replace(ANCIEN, NOUVEAU)

    try:
        ast.parse(patched)
    except SyntaxError as erreur:
        print(f"Le run_conf.py patche n'est pas du Python valide ({erreur}) - aucune "
              "modification ecrite.", file=sys.stderr)
        return 1

    with open(path, "w", encoding="utf-8") as fichier:
        fichier.write(patched)
    print(f"Patch console dediee par defaut applique ({path}) : chaque script demarre desormais "
          f"dans un noyau neuf, sauf fichier deja configure explicitement.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
