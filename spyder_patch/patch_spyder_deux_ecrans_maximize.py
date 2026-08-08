#!/usr/bin/env python3
"""Patch spyder/plugins/layout/plugin.py : agrandir un panneau DANS LA FENETRE QUI A LE FOCUS
(la principale ou celle du mode deux ecrans), au lieu de toujours retomber sur l'Editeur.

Contexte (TODO - Spyder - General.txt, 01/08/2026) : « l'agrandissement d'un panneau dans la 2eme
fenetre ne l'agrandit pas dans la deuxieme fenetre, mais agrandit l'editeur dans la premiere....
c'est un bug ». Rapporte tel quel par l'utilisateur, sans qu'il ait besoin de lire le code.

CAUSE RACINE, DEJA DOCUMENTEE DANS patch_spyder_deux_ecrans.py MAIS JAMAIS TRAITEE. Ce patch
modifiait deja `maximize_dockwidget()` (greffon Layout) pour EXCLURE les panneaux partis dans la
seconde fenetre de la boucle qui les cache et qui designe la cible :

    for plugin in self.get_dockable_plugins():
        if self._smartos_dock_dans_ecran2(plugin.dockwidget):
            continue          # <- jamais cache, jamais candidat
        plugin.dockwidget.hide()
        if plugin.get_widget().isAncestorOf(focus_widget):
            self._last_plugin = plugin

C'etait deliberement PRUDENT (son propre commentaire le dit : les cacher viderait leur fenetre,
les agrandir dans `self.main` les arracherait a elle) mais laissait UNE consequence non traitee :
un panneau du second ecran ne peut alors JAMAIS devenir `_last_plugin`, et la ligne suivante
retombe inconditionnellement sur l'Editeur des que rien d'autre n'a matche - l'Editeur vivant
TOUJOURS dans la fenetre principale (jamais envoye vers le second ecran). Cliquer "agrandir" sur
n'importe quel panneau du second ecran fait donc PRECISEMENT ce que l'utilisateur rapporte :
l'Editeur grossit dans la fenetre principale, la seconde ne bouge pas.

CE QUE CE PATCH FAIT : au lieu d'exclure les panneaux du second ecran de la boucle, il choisit la
fenetre CIBLE (principale ou second ecran) d'apres celle qui contient le widget focalise, puis
n'agit QUE sur les panneaux de CETTE fenetre - les cachant, les proposant comme candidats, et
appelant setCentralWidget/saveState/restoreState sur ELLE plutot que sur `self.main` en dur. Le
repli sur l'Editeur ne joue plus que si la fenetre visee EST la principale ; dans l'autre cas, le
repli est le premier panneau encore present du second ecran - jamais un panneau d'une autre
fenetre que celle qu'on regarde.

Usage : patch_spyder_deux_ecrans_maximize.py <chemin vers plugins/layout/plugin.py installe>

⚠ DOIT S'APPLIQUER APRES patch_spyder_deux_ecrans.py : il patche le texte QUE CE DERNIER a deja
ecrit (la boucle de hide), pas celui d'origine.
IDEMPOTENT ET AUTO-SUPPLANTANT, meme mecanique que les deux patches voisins sur ce fichier : quatre
remplacements ancres sur un texte UNIQUE (verifie par comptage avant ecriture), plus un bloc de
deux methodes ajoutees. Re-parse avant ecriture ; garde-fou de longueur (un patch qui n'ajoute que
ne doit jamais raccourcir le fichier - cf. l'incident du 31/07/2026 sur le patch voisin) ; echec
BRUYANT (code 1) si un ancrage est introuvable ou n'est pas unique.
"""
import ast
import sys

MARKER = "_smartos_fenetre_du_focus"

# ---- Remplacement 1 : selection de la fenetre cible et boucle de masquage/candidature ----

OLD_SELECTION = '''            # Select plugin to maximize
            self._state_before_maximizing = self.main.saveState(
                version=WINDOW_STATE_VERSION
            )
            focus_widget = QApplication.focusWidget()

            for plugin in self.get_dockable_plugins():
                # SmartOS (patch_spyder_deux_ecrans.py) : un panneau parti sur le second ecran n'est
                # ni cache (cela viderait sa fenetre) ni candidat a l'agrandissement.
                if self._smartos_dock_dans_ecran2(plugin.dockwidget):
                    continue
                plugin.dockwidget.hide()
                if plugin.get_widget().isAncestorOf(focus_widget):
                    self._last_plugin = plugin

            # This prevents a possible error when the value of _last_plugin
            # turns out to be None.
            if self._last_plugin is None:
                # Use the Editor as default plugin to maximize
                if editor is not None:
                    self._last_plugin = editor
                else:
                    return
'''

NEW_SELECTION = '''            # Select plugin to maximize
            focus_widget = QApplication.focusWidget()
            # SmartOS (patch_spyder_deux_ecrans_maximize.py) : un clic sur le bouton "Agrandir"
            # d'un panneau (patch_spyder_pane_maximize_button.py) fixe le focus PUIS bascule
            # l'action dans le MEME clic, synchrone - QApplication.focusWidget() n'a pas encore
            # eu le temps de refleter ce changement (visible seulement apres un tour de boucle
            # Qt). Le bouton a donc deja laisse ICI, explicitement, le panneau qu'il vise -
            # on lui fait confiance a la place d'un focus pas encore a jour, consomme en une fois.
            _smartos_bouton_cible = getattr(self, "_smartos_bouton_agrandir_cible", None)
            self._smartos_bouton_agrandir_cible = None
            if _smartos_bouton_cible is not None:
                focus_widget = _smartos_bouton_cible.get_widget()
            # SmartOS (patch_spyder_deux_ecrans_maximize.py) : agrandir DANS LA FENETRE QUI A LE
            # FOCUS (principale ou second ecran), et non plus toujours dans la principale - cf.
            # l'en-tete de ce patch pour le bug que corrige ce remplacement.
            self._smartos_fenetre_agrandie = self._smartos_fenetre_du_focus(focus_widget)
            _smartos_cible_ecran2 = (
                self._smartos_fenetre_agrandie is getattr(self, "_smartos_fen2", None)
            )
            self._state_before_maximizing = self._smartos_fenetre_agrandie.saveState(
                version=WINDOW_STATE_VERSION
            )

            for plugin in self.get_dockable_plugins():
                # SmartOS (patch_spyder_deux_ecrans.py / _maximize.py) : ne cacher et ne proposer
                # comme candidat que les panneaux de la fenetre VISEE - jamais ceux de l'autre.
                if self._smartos_dock_dans_ecran2(plugin.dockwidget) != _smartos_cible_ecran2:
                    continue
                plugin.dockwidget.hide()
                # ⚠ isAncestorOf(x) rend FAUX quand x EST l'objet lui-meme (Qt : un widget n'est
                # pas son propre ancetre) - sans le "is", le cas du bouton (focus_widget vaut le
                # widget du PANNEAU lui-meme, cf. plus haut) ne matchait jamais rien.
                if plugin.get_widget() is focus_widget or plugin.get_widget().isAncestorOf(focus_widget):
                    self._last_plugin = plugin

            # This prevents a possible error when the value of _last_plugin
            # turns out to be None.
            if self._last_plugin is None:
                # SmartOS (patch_spyder_deux_ecrans_maximize.py) : le repli sur l'Editeur n'a de
                # sens que si la fenetre visee est la PRINCIPALE - l'Editeur n'est jamais envoye
                # vers le second ecran. Y retomber quand meme
                # agrandirait un panneau d'une autre fenetre que celle qu'on regarde : exactement
                # le bug rapporte.
                if not _smartos_cible_ecran2 and editor is not None:
                    self._last_plugin = editor
                else:
                    self._last_plugin = self._smartos_premier_panneau_ecran2()
                if self._last_plugin is None:
                    self._state_before_maximizing = None
                    return
'''

# ---- Remplacement 2 : cible du setCentralWidget lors de l'agrandissement ----

OLD_SET_CENTRAL = (
    "self.main.setCentralWidget(self._last_plugin.get_widget())"
)
NEW_SET_CENTRAL = (
    "self._smartos_fenetre_agrandie.setCentralWidget(self._last_plugin.get_widget())"
)

# ---- Remplacement 3 : cible du setCentralWidget(None) lors de la restauration ----

OLD_UNSET_CENTRAL = "self.main.setCentralWidget(None)"
NEW_UNSET_CENTRAL = "self._smartos_fenetre_agrandie.setCentralWidget(None)"

# ---- Remplacement 4 : cible du restoreState lors de la restauration ----

OLD_RESTORE = '''            self.main.restoreState(
                self._state_before_maximizing, version=WINDOW_STATE_VERSION
            )
'''
NEW_RESTORE = '''            self._smartos_fenetre_agrandie.restoreState(
                self._state_before_maximizing, version=WINDOW_STATE_VERSION
            )
            self._smartos_fenetre_agrandie = None
'''

# ---- Bloc ajoute : deux methodes, juste apres _smartos_dock_dans_ecran2 (posee par le patch voisin) ----

ANCRE_METHODES = '''    def _smartos_dock_dans_ecran2(self, dock):
        """Vrai si ce dock vit dans la seconde fenetre."""
        fenetre = getattr(self, "_smartos_fen2", None)
        return fenetre is not None and dock is not None and fenetre.isAncestorOf(dock)
'''

DEBUT_BLOC_METHODES = "\n    # SmartOS (patch_spyder_deux_ecrans_maximize.py)"

BLOC_METHODES = '''
    # SmartOS (patch_spyder_deux_ecrans_maximize.py) : quelle fenetre agrandir dans, et le repli
    # du second ecran quand rien n'a le focus dedans. Cf. l'en-tete du patch pour le contexte.

    def _smartos_fenetre_du_focus(self, focus_widget):
        """La fenetre (principale ou second ecran) qui contient le widget focalise."""
        fenetre2 = getattr(self, "_smartos_fen2", None)
        if (fenetre2 is not None and focus_widget is not None
                and fenetre2.isAncestorOf(focus_widget)):
            return fenetre2
        return self.main

    def _smartos_premier_panneau_ecran2(self):
        """Premier panneau encore present dans le second ecran, ou None."""
        _noms = self._smartos_noms_panneaux_ecran2()
        return self.get_plugin(_noms[0], error=False) if _noms else None
'''


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers plugins/layout/plugin.py>", file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as fichier:
            source = fichier.read()
    except OSError as erreur:
        print(f"layout/plugin.py illisible ({erreur}) - patch maximize deux ecrans non applique.",
              file=sys.stderr)
        return 1

    original = source

    if MARKER in source:
        print("Patch maximize deux ecrans deja applique.")
        return 0

    if source.count(ANCRE_METHODES) != 1:
        print(f"Ancre des methodes introuvable ou non unique dans {path} - "
              f"patch_spyder_deux_ecrans.py doit etre applique AVANT. Patch non applique.",
              file=sys.stderr)
        return 1
    source = source.replace(ANCRE_METHODES, ANCRE_METHODES + BLOC_METHODES)

    for nom, ancienne, nouvelle in (
        ("selection de la fenetre cible", OLD_SELECTION, NEW_SELECTION),
        ("setCentralWidget (agrandir)", OLD_SET_CENTRAL, NEW_SET_CENTRAL),
        ("setCentralWidget(None) (restaurer)", OLD_UNSET_CENTRAL, NEW_UNSET_CENTRAL),
        ("restoreState (restaurer)", OLD_RESTORE, NEW_RESTORE),
    ):
        compte = source.count(ancienne)
        if compte != 1:
            print(f"Ancrage \"{nom}\" introuvable ou non unique ({compte} occurrence(s)) dans "
                  f"{path} - Spyder a peut-etre change son greffon Layout, ou "
                  f"patch_spyder_deux_ecrans.py n'est pas applique. Patch non applique.",
                  file=sys.stderr)
            return 1
        source = source.replace(ancienne, nouvelle)

    try:
        ast.parse(source)
    except SyntaxError as erreur:
        print(f"Le layout/plugin.py patche n'est pas du Python valide ({erreur}) - aucune "
              "modification ecrite.", file=sys.stderr)
        return 1

    if len(source.splitlines()) < len(original.splitlines()):
        print(f"Le {path} patche est PLUS COURT que l'original "
              f"({len(original.splitlines())} -> {len(source.splitlines())} lignes) : ce patch ne "
              f"fait qu'ajouter, il a donc coupe quelque chose. Aucune modification ecrite.",
              file=sys.stderr)
        return 1

    with open(path, "w", encoding="utf-8") as fichier:
        fichier.write(source)
    print(f"Patch maximize deux ecrans applique ({path}) : agrandir agit desormais dans la "
          f"fenetre qui a le focus, principale ou second ecran.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
