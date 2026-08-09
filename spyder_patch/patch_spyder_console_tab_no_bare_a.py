#!/usr/bin/env python3
"""Patch spyder/plugins/ipythonconsole/widgets/client.py : ClientWidget.get_name() n'affiche
plus "/A" sur la console MASTER d'un noyau - fichier ("temp.py/A" -> "temp.py") ou console
anonyme ("Console 1/A" -> "Console 1"). Seule une console SLAVE (Ctrl+T sur cette meme
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
secondaire venait a exister - et etendue le meme jour a la console anonyme ("Console 1/A"),
meme raison, meme demande pour le "+"  qui ouvre une console sans fichier associe.

CE QUE CE PATCH FAIT
---------------------
Dans ClientWidget.get_name(), DEUX branches sur les TROIS n'accolent plus "/" + str_id que si
str_id != 'A' :
  - la branche "given_name is None" (console anonyme, "Console N") ;
  - la branche "else" (given_name ordinaire - console de fichier).
La branche restante (Pylab/SymPy/Cython/interprete force) garde son "int_id/str_id" complet :
ces consoles speciales sont rarement seules sur leur noyau (SymPy en cree souvent plusieurs), et
l'utilisateur n'a demande le changement que pour les deux premieres.

Usage : patch_spyder_console_tab_no_bare_a.py <chemin vers ipythonconsole/widgets/client.py>

IDEMPOTENT : re-application sans effet si deja pose (verifie sur le texte exact des DEUX
ancres). Re-parse avant ecriture ; echec BRUYANT (code 1) si une ancre est introuvable ou non
unique - aucune des deux n'est ecrite si l'une des deux echoue.
"""
import ast
import sys

MARKER = "_smartos_no_bare_a"

REMPLACEMENTS = [
    (
        "        if self.given_name is None:\n"
        "            # Name according to host\n"
        "            if self.hostname is None:\n"
        "                name = _(\"Console\")\n"
        "            else:\n"
        "                name = self.hostname\n"
        "            # Adding id to name\n"
        "            client_id = self.id_['int_id'] + u'/' + self.id_['str_id']\n"
        "            name = name + u' ' + client_id\n",

        "        if self.given_name is None:\n"
        "            # Name according to host\n"
        "            if self.hostname is None:\n"
        "                name = _(\"Console\")\n"
        "            else:\n"
        "                name = self.hostname\n"
        "            # Adding id to name\n"
        "            # SmartOS ({marker}) : meme raison que pour la console de fichier plus\n"
        "            # bas - \"/A\" ne distingue rien tant qu'aucune seconde console ne\n"
        "            # partage ce noyau. Decision de l'utilisateur du 09/08/2026.\n"
        "            client_id = self.id_['int_id']\n"
        "            if self.id_['str_id'] != 'A':\n"
        "                client_id = client_id + u'/' + self.id_['str_id']\n"
        "            name = name + u' ' + client_id\n"
    ),
    (
        "        else:\n"
        "            name = self.given_name + u'/' + self.id_['str_id']\n"
        "        return name\n",

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
    ),
]
REMPLACEMENTS = [(anc, nouv.format(marker=MARKER)) for anc, nouv in REMPLACEMENTS]


def patch(path):
    with open(path, encoding="utf-8") as stream:
        source = stream.read()

    if MARKER in source:
        print(f"Deja patche : {path}")
        return True

    patched = source
    for ancien, nouveau in REMPLACEMENTS:
        count = patched.count(ancien)
        if count != 1:
            print(f"ERREUR : point d'ancrage introuvable ou non unique ({count} occurrence(s)) "
                  f"dans {path} (get_name() a change ?)", file=sys.stderr)
            return False
        patched = patched.replace(ancien, nouveau)

    try:
        ast.parse(patched)
    except SyntaxError as error:
        print(f"ERREUR : patch invalide pour {path} ({error})", file=sys.stderr)
        return False

    with open(path, "w", encoding="utf-8") as stream:
        stream.write(patched)
    print(f"Patche : {path} (console master sans suffixe /A - fichier et anonyme -, "
          f"console slave inchangee)")
    return True


def main(argv):
    if len(argv) != 2:
        print(f"Usage : {argv[0]} <chemin vers ipythonconsole/widgets/client.py>",
              file=sys.stderr)
        return 1
    return 0 if patch(argv[1]) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
