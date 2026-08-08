#!/usr/bin/env python3
"""Patch spyder/api/widgets/menus.py pour ne calculer qu'UNE FOIS la feuille de style des menus.

Contexte (TODO - Spyder.txt, section "vitesse de lancement", 20/07/2026) : le profilage du
lancement de Spyder montre que SpyderMenu._generate_stylesheet() est appele 129 fois au demarrage
- une fois par menu cree - pour un cout mesure de 420 ms, soit ~10 % des 4,4 s de lancement. Le
detail (cProfile) pointe qstylizer : 7 415 instanciations de qstylizer.style.Style et 103 818
appels a get_attributes(), a reconstruire encore et encore exactement la meme feuille.

"Exactement la meme" est bien le mot : _generate_stylesheet est un classmethod qui ne lit AUCUN
etat d'instance, uniquement des donnees globales - la police d'interface (SpyderFontType.Interface),
la palette (SpyderPalette), les marges (AppStyle) et les constantes de plateforme MAC/WIN. Deux
appels consecutifs produisent donc des feuilles identiques. Ce patch memorise le resultat dans un
cache dont la cle englobe precisement ces entrees : un changement de theme ou de police produit une
cle differente, donc une feuille recalculee, sans invalidation manuelle.

Gain mesure (mediane de 4 lancements, meme configuration, hors ecran) : 4381 ms -> 4087 ms, le
temps passe dans _generate_stylesheet tombant de 420 ms a 14 ms (3 calculs reels au lieu de 129).
Mesure au passage et NON traite car negligeable : StyleSheet.toString(), 948 appels pour 42 ms.

⚠ Le cache renvoie un objet StyleSheet PARTAGE entre tous les menus. C'est sans risque tant que
personne ne le modifie apres coup : dans Spyder 6.1.5, l'attribut self.css d'un menu n'apparait
qu'aux deux lignes qui le creent et le serialisent (self.css = self._generate_stylesheet() puis
self.setStyleSheet(self.css.toString())), et aucune sous-classe ne surcharge _generate_stylesheet.
Le patch VERIFIE ces deux points et refuse de s'appliquer s'ils ne tiennent plus - une future
version de Spyder qui personnaliserait la feuille par menu rendrait le partage faux, et le bug
serait purement visuel, donc difficile a relier a ce patch.

Usage : patch_spyder_menu_stylesheet_cache.py <chemin vers menus.py installe>

Idempotent : si le marqueur du patch (_SMARTOS_MENU_CSS_CACHE) est deja present, ne fait rien.
Echoue bruyamment (code de sortie 1) plutot que de deviner, des qu'une des hypotheses ci-dessus
n'est pas verifiee.
"""
import ast
import sys

MARQUEUR = "_SMARTOS_MENU_CSS_CACHE"

PATCH = '''

# ---- SmartOS : mise en cache de la feuille de style des menus ----------------------------------
# _generate_stylesheet() ne lit aucun etat d'instance : seulement la police d'interface, la palette,
# les marges et les constantes de plateforme. Spyder la recalculait pourtant pour chacun des 129
# menus crees au demarrage (420 ms mesures, ~10 % du lancement, l'essentiel passe dans qstylizer).
# La cle du cache reprend exactement ces entrees : changer de theme ou de police donne une cle
# differente, donc une feuille recalculee, sans invalidation a gerer.
# ⚠ L'objet StyleSheet renvoye est PARTAGE entre tous les menus : valable tant qu'aucun menu ne le
# modifie apres coup (verifie par Installation/tools/patch_spyder_menu_stylesheet_cache.py, qui refuse
# de s'appliquer si self.css apparait ailleurs que dans sa creation et sa serialisation).
_SMARTOS_MENU_CSS_CACHE = {}
_smartos_generate_stylesheet = SpyderMenu._generate_stylesheet.__func__


def _smartos_generate_stylesheet_cached(cls) -> qstylizer.style.StyleSheet:
    """Version memorisee de SpyderMenu._generate_stylesheet (cf. commentaire ci-dessus)."""
    font = cls.get_font(SpyderFontType.Interface)
    cle = (
        cls,
        font.family(),
        font.pointSize(),
        SpyderPalette.COLOR_BACKGROUND_3,
        SpyderPalette.COLOR_BACKGROUND_6,
        AppStyle.MarginSize,
        cls.HORIZONTAL_MARGIN_FOR_ITEMS,
        cls.HORIZONTAL_PADDING_FOR_ITEMS,
        MAC,
        WIN,
    )
    css = _SMARTOS_MENU_CSS_CACHE.get(cle)
    if css is None:
        css = _SMARTOS_MENU_CSS_CACHE[cle] = _smartos_generate_stylesheet(cls)
    return css


SpyderMenu._generate_stylesheet = classmethod(_smartos_generate_stylesheet_cached)
'''


def echec(message, *details):
    print(f"\033[1;31mECHEC du patch du cache de feuille de style des menus\033[0m", file=sys.stderr)
    print(f"\033[1;31m  {message}\033[0m", file=sys.stderr)
    for ligne in details:
        print(f"\033[1;31m  {ligne}\033[0m", file=sys.stderr)
    print("\033[1;31m  Spyder reste fonctionnel, seulement plus lent au demarrage. Verifier si le"
          "\033[0m", file=sys.stderr)
    print("\033[1;31m  code vise a change dans cette version de Spyder, puis adapter ce patch."
          "\033[0m", file=sys.stderr)
    sys.exit(1)


def main():
    if len(sys.argv) != 2:
        echec("Usage : patch_spyder_menu_stylesheet_cache.py <chemin vers menus.py>")
    chemin = sys.argv[1]

    try:
        with open(chemin, encoding="utf-8") as f:
            source = f.read()
    except OSError as e:
        echec(f"Fichier illisible : {chemin}", str(e))

    if MARQUEUR in source:
        print("   - cache des feuilles de style des menus : deja applique")
        return

    arbre = ast.parse(source, filename=chemin)

    # 1. La classe SpyderMenu et sa methode _generate_stylesheet existent-elles toujours ?
    classe = next(
        (n for n in arbre.body if isinstance(n, ast.ClassDef) and n.name == "SpyderMenu"), None
    )
    if classe is None:
        echec("La classe SpyderMenu est introuvable dans " + chemin)
    if not any(isinstance(n, ast.FunctionDef) and n.name == "_generate_stylesheet"
               for n in classe.body):
        echec("SpyderMenu ne definit plus de methode _generate_stylesheet.")

    # 2. Aucune sous-classe du module ne doit surcharger _generate_stylesheet : elle heriterait
    #    sinon de la version mise en cache tout en attendant sa propre feuille.
    for noeud in arbre.body:
        if isinstance(noeud, ast.ClassDef) and noeud.name != "SpyderMenu":
            herite = any(isinstance(b, ast.Name) and b.id == "SpyderMenu" for b in noeud.bases)
            surcharge = any(isinstance(n, ast.FunctionDef) and n.name == "_generate_stylesheet"
                            for n in noeud.body)
            if herite and surcharge:
                echec(f"La sous-classe {noeud.name} surcharge _generate_stylesheet.",
                      "Le cache renverrait la feuille de la classe de base.")

    # 3. self.css ne doit apparaitre que deux fois : sa creation et sa serialisation. Toute autre
    #    occurrence signalerait une personnalisation par menu, incompatible avec un objet partage.
    occurrences = source.count("self.css")
    if occurrences != 2:
        echec(f"self.css apparait {occurrences} fois dans {chemin} (2 attendues).",
              "Un menu personnalise peut-etre sa feuille de style : le partage de l'objet mis en",
              "cache serait alors faux, et le bug purement visuel.")

    with open(chemin, "w", encoding="utf-8") as f:
        f.write(source.rstrip("\n") + "\n" + PATCH)
    print("   - cache des feuilles de style des menus : applique")


if __name__ == "__main__":
    main()
