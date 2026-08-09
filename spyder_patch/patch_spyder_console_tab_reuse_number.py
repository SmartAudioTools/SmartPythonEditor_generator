#!/usr/bin/env python3
"""Patch spyder/plugins/ipythonconsole/widgets/main_widget.py et .../client.py : une console
ANONYME (bouton "+", aucun fichier associe) reutilise le plus petit numero libere par une
fermeture, au lieu de compter pour toujours vers le haut - et le tout premier emplacement ne
porte plus de numero du tout : "Console", "Console 2", "Console 3", ...

CONTEXTE (TODO - Spyder - Debug.txt, 09/08/2026)
-------------------------------------------------
Suite immediate de patch_spyder_console_tab_no_bare_a.py ("Console 1/A" -> "Console 1") :
demande de l'utilisateur, meme echange - « ou meme commencer par "Console" sans le "1" puis
"Console 2", et arreter d'incrementer sans cesse si les premiere console ont ete refermee ».

CE QUE CE PATCH FAIT
---------------------
main_widget.py, create_new_client() : quand l'appel est pour une console anonyme
(given_name et filename tous deux absents - ni fichier, ni nom donne comme "Pylab"/"SymPy"/
un environnement), le numero (int_id) n'est plus tire du compteur self.master_clients
(monotone, jamais decroissant) mais calcule comme le plus petit entier >= 1 qui n'est
utilise par AUCUNE console anonyme actuellement ouverte (self.clients, filtre sur
given_name is None). Les consoles de fichier, d'environnement, Pylab/SymPy/Cython et les
noyaux distants continuent d'utiliser self.master_clients, inchange - leur numero
n'apparait de toute facon jamais tel quel dans leur nom (cf. patch_spyder_console_tab_
no_bare_a.py) ou releve d'un tout autre compteur (create_client_for_kernel).

client.py, ClientWidget.get_name() (branche "given_name is None", deja modifiee par
patch_spyder_console_tab_no_bare_a.py pour ne plus afficher un "/A" isole) : n'affiche plus
le numero DU TOUT quand int_id == '1' - c'est desormais toujours vrai pour le premier
emplacement libre, qui peut redevenir occupe apres une fermeture.

DOIT ETRE APPLIQUE APRES patch_spyder_console_tab_no_bare_a.py (l'ancre de client.py est le
texte DEJA patche par lui).

Usage : patch_spyder_console_tab_reuse_number.py <chemin vers ipythonconsole/widgets> \
        (le dossier contenant main_widget.py ET client.py)

IDEMPOTENT : re-application sans effet si deja pose. Re-parse avant ecriture ; echec BRUYANT
(code 1) si une ancre est introuvable ou non unique - rien n'est ecrit si l'une des deux
echoue.
"""
import ast
import os
import sys

MARKER = "_smartos_reuse_numero"

ANCIEN_MAIN_WIDGET = (
    "        self.master_clients += 1\n"
    "        client_id = dict(int_id=str(self.master_clients),\n"
    "                         str_id='A')\n"
)

NOUVEAU_MAIN_WIDGET = (
    "        if given_name is None and not filename:\n"
    "            # SmartOS ({marker}) : une console ANONYME (bouton \"+\", pas de fichier\n"
    "            # associe) reutilise le plus petit numero libere par une fermeture, au\n"
    "            # lieu de ne jamais redescendre. Decision de l'utilisateur du 09/08/2026,\n"
    "            # a la suite du retrait du suffixe \"/A\" (cf. patch_spyder_console_tab_\n"
    "            # no_bare_a.py) : sans elle, la numerotation grimpait pour toujours meme\n"
    "            # apres avoir tout referme.\n"
    "            numeros_utilises = {{\n"
    "                int(cl.id_['int_id']) for cl in self.clients if cl.given_name is None\n"
    "            }}\n"
    "            numero = 1\n"
    "            while numero in numeros_utilises:\n"
    "                numero += 1\n"
    "            client_id = dict(int_id=str(numero), str_id='A')\n"
    "        else:\n"
    "            self.master_clients += 1\n"
    "            client_id = dict(int_id=str(self.master_clients),\n"
    "                             str_id='A')\n"
).format(marker=MARKER)

ANCIEN_CLIENT = (
    "            # SmartOS (_smartos_no_bare_a) : meme raison que pour la console de fichier plus\n"
    "            # bas - \"/A\" ne distingue rien tant qu'aucune seconde console ne\n"
    "            # partage ce noyau. Decision de l'utilisateur du 09/08/2026.\n"
    "            client_id = self.id_['int_id']\n"
    "            if self.id_['str_id'] != 'A':\n"
    "                client_id = client_id + u'/' + self.id_['str_id']\n"
    "            name = name + u' ' + client_id\n"
)

NOUVEAU_CLIENT = (
    "            # SmartOS (_smartos_no_bare_a, etendu par {marker}) : \"/A\" ne distingue\n"
    "            # rien tant qu'aucune seconde console ne partage ce noyau, et l'emplacement\n"
    "            # 1 (numerotation reutilisee, cf. create_new_client) ne porte pas non plus\n"
    "            # de numero.\n"
    "            if self.id_['int_id'] != '1':\n"
    "                name = name + u' ' + self.id_['int_id']\n"
    "            if self.id_['str_id'] != 'A':\n"
    "                name = name + u'/' + self.id_['str_id']\n"
).format(marker=MARKER)


def _patch_un_fichier(path, ancien, nouveau, nom_module):
    with open(path, encoding="utf-8") as stream:
        source = stream.read()

    if MARKER in source:
        return source, True

    count = source.count(ancien)
    if count != 1:
        print(f"ERREUR : point d'ancrage introuvable ou non unique ({count} occurrence(s)) "
              f"dans {path} ({nom_module} a change ?)", file=sys.stderr)
        return None, False

    return source.replace(ancien, nouveau), True


def patch(dossier):
    chemin_main_widget = os.path.join(dossier, "main_widget.py")
    chemin_client = os.path.join(dossier, "client.py")

    with open(chemin_main_widget, encoding="utf-8") as stream:
        deja = MARKER in stream.read()
    if deja:
        print(f"Deja patche : {chemin_main_widget} et {chemin_client}")
        return True

    source_main_widget, ok = _patch_un_fichier(
        chemin_main_widget, ANCIEN_MAIN_WIDGET, NOUVEAU_MAIN_WIDGET, "create_new_client()")
    if not ok:
        return False
    source_client, ok = _patch_un_fichier(
        chemin_client, ANCIEN_CLIENT, NOUVEAU_CLIENT, "get_name()")
    if not ok:
        return False

    for source, chemin in ((source_main_widget, chemin_main_widget),
                           (source_client, chemin_client)):
        try:
            ast.parse(source)
        except SyntaxError as error:
            print(f"ERREUR : patch invalide pour {chemin} ({error})", file=sys.stderr)
            return False

    with open(chemin_main_widget, "w", encoding="utf-8") as stream:
        stream.write(source_main_widget)
    with open(chemin_client, "w", encoding="utf-8") as stream:
        stream.write(source_client)
    print(f"Patche : {chemin_main_widget} et {chemin_client} "
          f"(numerotation des consoles anonymes reutilisee, emplacement 1 sans numero)")
    return True


def main(argv):
    if len(argv) != 2:
        print(f"Usage : {argv[0]} <dossier ipythonconsole/widgets>", file=sys.stderr)
        return 1
    return 0 if patch(argv[1]) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
