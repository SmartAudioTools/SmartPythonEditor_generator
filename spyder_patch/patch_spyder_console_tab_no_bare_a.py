#!/usr/bin/env python3
"""Patch spyder/plugins/ipythonconsole/widgets/client.py : ClientWidget.get_name() n'affiche
plus "/A" sur la console MASTER d'un fichier (celle creee par create_client_for_file, cf.
patch_spyder_fresh_kernel_per_run.py) - seule une console SLAVE (Ctrl+T sur cette meme
console, partageant son noyau) affichera encore son suffixe ("/B", "/C", ...).

CONTEXTE (TODO - Spyder - Debug.txt, 09/08/2026)
-------------------------------------------------
Question de l'utilisateur en decouvrant l'onglet "temp.py/A" : a quoi sert le "/A" ? Reponse :
"A" est la lettre native de Spyder pour la PREMIERE console attachee a un noyau (id_['str_id']),
distinguant une eventuelle console SECONDAIRE ("/B", partageant le meme noyau) - cf.
main_widget.py, create_new_client(). Avec un noyau neuf a chaque execution
(patch_spyder_fresh_kernel_per_run.py), une console de fichier est PRESQUE TOUJOURS seule sur
son noyau : le "/A" est alors du bruit systematique, jamais une information utile. Decision de
l'utilisateur, 09/08/2026 : le retirer pour "A", le garder pour "B" et suivantes si une console
secondaire venait a exister.

CE QUE CE PATCH FAIT
---------------------
Dans ClientWidget.get_name(), seule la branche "else" (given_name pose et ordinaire - donc PAS
une console Pylab/SymPy/Cython/interprete force, qui garde son "int_id/str_id" complet, ni une
console anonyme "Console N/A") : n'accole "/" + str_id que si str_id != 'A'.

Usage : patch_spyder_console_tab_no_bare_a.py <chemin vers ipythonconsole/widgets/client.py>

IDEMPOTENT : re-application sans effet si deja pose (verifie sur le texte exact). Re-parse avant
ecriture ; echec BRUYANT (code 1) si l'ancre est introuvable ou non unique.
"""
import ast
import sys

MARKER = "_smartos_no_bare_a"

ANCIEN = (
    "        else:\n"
    "            name = self.given_name + u'/' + self.id_['str_id']\n"
    "        return name\n"
)

NOUVEAU = (
    "        else:\n"
    "            # SmartOS ({marker}) : \"/A\" est du bruit pour la console MASTER d'un\n"
    "            # fichier - avec noyau neuf a chaque execution, elle est presque toujours\n"
    "            # seule sur son noyau. Une eventuelle console SLAVE (\"/B\", ...) garde son\n"
    "            # suffixe, seul cas ou il distingue vraiment deux onglets. Decision de\n"
    "            # l'utilisateur du 09/08/2026.\n"
    "            if self.id_['str_id'] == 'A':\n"
    "                name = self.given_name\n"
    "            else:\n"
    "                name = self.given_name + u'/' + self.id_['str_id']\n"
    "        return name\n"
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
              f"dans {path} (get_name() a change ?)", file=sys.stderr)
        return False

    patched = source.replace(ANCIEN, NOUVEAU)

    try:
        ast.parse(patched)
    except SyntaxError as error:
        print(f"ERREUR : patch invalide pour {path} ({error})", file=sys.stderr)
        return False

    with open(path, "w", encoding="utf-8") as stream:
        stream.write(patched)
    print(f"Patche : {path} (console master sans suffixe /A, console slave inchangee)")
    return True


def main(argv):
    if len(argv) != 2:
        print(f"Usage : {argv[0]} <chemin vers ipythonconsole/widgets/client.py>",
              file=sys.stderr)
        return 1
    return 0 if patch(argv[1]) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
