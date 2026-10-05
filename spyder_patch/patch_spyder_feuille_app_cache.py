#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Garde sur disque la feuille de style de l'application (spyder/utils/stylesheet.py).

Contexte (TODO - Spyder - accélération démarage.txt, etape 5, 05/10/2026) : a chaque lancement,
AppStylesheet.to_string() relit la feuille de QDarkStyle (55 000 caracteres), la fait ANALYSER
par qstylizer (un analyseur CSS en python pur), lui applique une trentaine de retouches, puis la
reconvertit en texte. Mesure hors profileur, banc hors ecran : 78 ms (11 ms avec le cache), pour un resultat qui ne
change que si le theme, la police de l'interface ou le code changent.

Le texte final est donc garde dans le dossier de configuration (smartos_feuille_app.json), avec
une CLE qui reprend tout ce dont il depend :
  - la feuille brute rendue par qdarkstyle.load_stylesheet(palette=SpyderPalette) - elle porte
    le theme et la version de QDarkStyle ;
  - toutes les valeurs textuelles de SpyderPalette (les retouches en utilisent qui ne figurent
    pas dans la feuille brute) ;
  - la police de l'interface (famille, taille) et la hauteur des listes deroulantes qui en
    decoule ;
  - le fond du theme de coloration de l'editeur (smartos_editor_background, correctif SmartOS
    des couleurs : il entre dans la barre d'etat et les separateurs - oubli trouve a la
    relecture du 05/10/2026, un changement de theme de l'editeur gardait l'ancienne couleur) ;
  - la plateforme ;
  - la date et la taille de stylesheet.py lui-meme et de qstylizer/style.py : un correctif
    rejoue ou une mise a jour invalident le cache.
Cle differente, fichier absent ou illisible : la feuille est construite comme en amont, puis
gardee. Une erreur d'ecriture est ignoree.

qdarkstyle.load_stylesheet() reste appele dans tous les cas : c'est lui qui enregistre les
ressources Qt (images) que la feuille reference.

L'objet qstylizer n'est plus construit quand le cache sert ; get_stylesheet() le construit alors
a la demande (aucun appelant dans Spyder 6.1.5 pour l'instance de l'application, verifie par
recherche ; garde pour un greffon tiers).

Usage : patch_spyder_feuille_app_cache.py <spyder/utils/stylesheet.py>
Idempotent (marqueur _smartos_feuille_app_cache), echoue bruyamment si la forme amont a change.
"""

import ast
import sys

MARQUEUR = "_smartos_feuille_app_cache"

BLOC = '''

# ---- SmartOS (_smartos_feuille_app_cache) : feuille de style de l'application gardee sur disque --
# La construire demandait 78 ms a chaque lancement (analyse de la feuille de QDarkStyle en python
# pur). Voir spyder_patch/patch_spyder_feuille_app_cache.py du generator.
def _smartos_feuille_app_cache():
    import hashlib
    import json

    construire = AppStylesheet.to_string
    objet_amont = AppStylesheet.get_stylesheet

    def cle_de(self, brute):
        ingredients = [
            brute,
            sorted((nom, valeur) for nom in dir(SpyderPalette)
                   if not nom.startswith("_")
                   for valeur in [getattr(SpyderPalette, nom)] if isinstance(valeur, str)),
            self.get_conf('app_font/family', section='appearance'),
            self.get_conf('app_font/size', section='appearance'),
            AppStyle._fs, AppStyle.ComboBoxMinHeight, sys.platform,
        ]
        # Fond du theme de coloration de l'editeur : le correctif SmartOS des couleurs le pose
        # sur la barre d'etat et les separateurs (absent si ce correctif n'est pas applique).
        fond_editeur = globals().get("smartos_editor_background")
        if fond_editeur is not None:
            ingredients.append(fond_editeur())
        for fichier in (__file__, qstylizer.style.__file__):
            etat = os.stat(fichier)
            ingredients.append((etat.st_mtime_ns, etat.st_size))
        return hashlib.sha1(repr(ingredients).encode("utf-8")).hexdigest()

    def to_string(self):
        if self._stylesheet_as_string is not None:
            return self._stylesheet_as_string
        chemin = cle = None
        try:
            from spyder.config.base import get_conf_path

            chemin = get_conf_path("smartos_feuille_app.json")
            # Toujours appele : enregistre les ressources Qt que la feuille reference.
            cle = cle_de(self, qdarkstyle.load_stylesheet(palette=SpyderPalette))
            with open(chemin, encoding="utf-8") as fichier:
                garde = json.load(fichier)
            if garde["cle"] == cle and garde["feuille"]:
                self._smartos_objet_a_construire = True
                self._stylesheet_as_string = garde["feuille"]
                return self._stylesheet_as_string
        except Exception:
            pass
        feuille = construire(self)
        if cle is not None:
            try:
                provisoire = "%s.%d" % (chemin, os.getpid())
                with open(provisoire, "w", encoding="utf-8") as fichier:
                    json.dump({"cle": cle, "feuille": feuille}, fichier)
                os.replace(provisoire, chemin)
            except Exception:
                pass
        return feuille

    def get_stylesheet(self):
        if getattr(self, "_smartos_objet_a_construire", False):
            self._smartos_objet_a_construire = False
            self.set_stylesheet()
        return objet_amont(self)

    AppStylesheet.to_string = to_string
    AppStylesheet.get_stylesheet = get_stylesheet


_smartos_feuille_app_cache()
'''


def patcher(chemin):
    source = open(chemin, encoding="utf-8").read()
    if MARQUEUR in source:
        print(f"Deja patche : {chemin}")
        return True
    arbre = ast.parse(source)
    classes = {n.name: n for n in arbre.body if isinstance(n, ast.ClassDef)}
    app = classes.get("AppStylesheet")
    methodes = {n.name for n in app.body if isinstance(n, ast.FunctionDef)} if app else set()
    base = classes.get("SpyderStyleSheet")
    methodes_base = ({n.name for n in base.body if isinstance(n, ast.FunctionDef)}
                     if base else set())
    noms = {alias.asname or alias.name for n in arbre.body
            if isinstance(n, (ast.Import, ast.ImportFrom)) for alias in n.names}
    if (not {"to_string", "set_stylesheet"} <= methodes
            or "get_stylesheet" in methodes or "get_stylesheet" not in methodes_base
            or "_stylesheet_as_string" not in source
            or "qdarkstyle.load_stylesheet(palette=SpyderPalette)" not in source
            or not {"os", "sys", "qdarkstyle", "qstylizer.style", "SpyderPalette"} <= noms
            or "AppStyle" not in classes):
        print(f"ERREUR : AppStylesheet (to_string, set_stylesheet, _stylesheet_as_string), "
              f"AppStyle ou les imports attendus sont introuvables dans {chemin} - la forme "
              f"amont a change.", file=sys.stderr)
        return False
    resultat = source.rstrip("\n") + "\n" + BLOC
    try:
        ast.parse(resultat)
    except SyntaxError as erreur:
        print(f"ERREUR : patch invalide pour {chemin} ({erreur})", file=sys.stderr)
        return False
    open(chemin, "w", encoding="utf-8").write(resultat)
    print(f"Patche : {chemin}")
    return True


def main(argv):
    if len(argv) != 2:
        print(f"Usage : {argv[0]} <spyder/utils/stylesheet.py>", file=sys.stderr)
        return 1
    return 0 if patcher(argv[1]) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
