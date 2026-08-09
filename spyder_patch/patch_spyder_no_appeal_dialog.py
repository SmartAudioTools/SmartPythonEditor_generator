#!/usr/bin/env python3
"""La fenetre d'appel aux dons ("Help keep Spyder strong") ne s'ouvre plus toute seule.

DEMANDE (TODO - Spyder - Debug.txt, 09/08/2026)
    « J'ai une fenetre "Help keep Spyder strong" qui s'ouvre tout seul, je voudrais qu'elle
    ne s'ouvre jamais. »

CE QUI LA DECLENCHE
    spyder/plugins/application/plugin.py, on_mainwindow_visible() : Spyder compte ses
    demarrages dans l'option "spyder_runs_for_appeal" et ouvre la fenetre au 5e puis au 25e.

POURQUOI UN CORRECTIF PLUTOT QUE L'OPTION
    Mettre le compteur a 26 dans la configuration suffirait a la faire taire... jusqu'a la
    prochaine migration de CONF_VERSION, qui remet a leur defaut les options apparues depuis
    (piege deja documente dans CLAUDE_spyder.md) : le compteur repartirait a 1 et la fenetre
    reviendrait au 5e demarrage. Le bloc est donc retire, ce qui rend l'option elle-meme
    inutile - elle n'est lue et ecrite qu'ici.

CE QUI RESTE
    Le coeur dans la barre d'etat et l'entree de menu qui ouvrent la meme page restent en
    place : on supprime la sollicitation NON DEMANDEE, pas la possibilite de donner.

Usage : patch_spyder_no_appeal_dialog.py <chemin vers plugins/application/plugin.py>

IDEMPOTENT (marqueur _smartos_no_appeal). Echec BRUYANT si l'ancre est absente ou non
unique. QTimer reste importe et utilise ailleurs dans le fichier (show_changelog).
"""

import ast
import sys

MARKER = "_smartos_no_appeal"

ANCIEN = (
    "        # Show appeal the fifth and 25th time Spyder starts\n"
    "        spyder_runs = self.get_conf(\"spyder_runs_for_appeal\", default=1)\n"
    "        if spyder_runs in [5, 25]:\n"
    "            QTimer.singleShot(1500, container.show_appeal)\n"
    "\n"
    "            # Increase counting in one to not get stuck at this point.\n"
    "            # Fixes spyder-ide/spyder#22457\n"
    "            self.set_conf(\"spyder_runs_for_appeal\", spyder_runs + 1)\n"
    "        else:\n"
    "            if spyder_runs < 25:\n"
    "                self.set_conf(\"spyder_runs_for_appeal\", spyder_runs + 1)\n"
)

NOUVEAU = (
    "        # Retrait SmartOS ({marker}) : Spyder ouvrait ici la fenetre d'appel aux dons\n"
    "        # (\"Help keep Spyder strong\") au 5e puis au 25e demarrage, en comptant dans\n"
    "        # l'option \"spyder_runs_for_appeal\". Demande de l'utilisateur du 09/08/2026 :\n"
    "        # qu'elle ne s'ouvre jamais toute seule. Le coeur de la barre d'etat et l'entree\n"
    "        # de menu, qui ouvrent la meme page a la demande, sont conserves.\n"
    "        # Cf. spyder_patch/patch_spyder_no_appeal_dialog.py.\n"
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
              f"dans {path} (bloc d'appel aux dons change ?)", file=sys.stderr)
        return False

    patched = source.replace(ANCIEN, NOUVEAU)

    try:
        ast.parse(patched)
    except SyntaxError as error:
        print(f"ERREUR : patch invalide pour {path} ({error})", file=sys.stderr)
        return False

    with open(path, "w", encoding="utf-8") as stream:
        stream.write(patched)
    print(f"Patche : {path} (fenetre d'appel aux dons desactivee)")
    return True


def main(argv):
    if len(argv) != 2:
        print(f"Usage : {argv[0]} <chemin vers plugins/application/plugin.py>",
              file=sys.stderr)
        return 1
    return 0 if patch(argv[1]) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
