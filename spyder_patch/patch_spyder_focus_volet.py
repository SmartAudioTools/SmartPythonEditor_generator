#!/usr/bin/env python3
"""Volet qui a le focus : onglet actif en bleu, contenu eclairci (editeur et console).

Contexte (demandes de l'utilisateur, 11/10/2026) : « tous les fenetre ne s'eclaircissent pas
(editeur de code, explorateur de fichiers, etc...) » et « le contour des titres d' onglet de
l'editeur , du terminal et de la console ne se collorient pas en bleu quand ils ont le focus ».
Les greffons Claude et Konsole le font deja pour leurs propres volets (_appliquer_cadre) ; le
coeur de Spyder ne le faisait nulle part.

CE QUI EST PATCHE (quatre fichiers, un bloc chacun, chacun son marqueur)
    spyder/widgets/tabs.py
        Une fonction de module, branchee UNE fois sur QApplication.focusChanged depuis
        BaseTabs.__init__ : elle remonte du widget qui recoit le focus jusqu'au premier
        QTabWidget dont la barre s'appelle 'pane-tabbar' (editeur, console IPython...), pose la
        propriete dynamique smartos_focus=True sur cette barre et False sur la precedente, puis
        les repolit. La regle de feuille qui la lit (contour bleu, fond eclairci) est dans
        PanesTabBarStyleSheet, posee par patch_spyder_colors.py. Ecarte : un eventFilter par
        BaseTabs - il faudrait l'installer sur chaque descendant, y compris ceux ajoutes plus
        tard ; focusChanged voit tout, une seule connexion.
    spyder/plugins/editor/widgets/base.py
        set_palette ajoute a la feuille par ID de l'editeur une variante :focus au fond eclairci.
        Feuille du widget, donc pas d'appel a faire au changement de focus : Qt repeint seul.
    spyder/plugins/editor/widgets/codeeditor/codeeditor.py
        Les marges (numeros de ligne, repliement, drapeaux...) peignent self.editor.sideareas_color
        en sept endroits : sideareas_color devient une propriete qui rend la couleur eclaircie
        quand l'editeur a le focus, et les panneaux sont repeints a chaque changement de focus
        (signal focus_changed, emis par focusInEvent ET focusOutEvent). Ecarte : retoucher les
        sept peintres un par un.
    spyder/plugins/ipythonconsole/utils/style.py
        create_qss_style ajoute une variante :focus au fond eclairci de la console. Sa feuille est
        posee AU NIVEAU du widget : une regle de la feuille d'application ne l'emporterait pas.

    Facteur : SMARTOS_ECLAIRCISSEMENT (spyder/utils/stylesheet.py, pose par
    patch_spyder_colors.py), le meme que les greffons. Remplacements ancres sur des lignes uniques,
    idempotents par marqueur, echec bruyant si ni l'ancre ni le marqueur ne sont trouves, fichier
    reparse avant ecriture.
"""

import ast
import sys

TABS = (
    "tabs.py",
    "# Suivi du volet qui a le focus (ajout SmartOS",
    [
        (
            "class BaseTabs(QTabWidget):\n",
            "# Suivi du volet qui a le focus (ajout SmartOS, cf. patch_spyder_focus_volet.py) : la\n"
            "# barre 'pane-tabbar' du volet qui contient le widget qui a le focus porte la propriete\n"
            "# smartos_focus, que lit PanesTabBarStyleSheet (onglet actif en bleu).\n"
            "_smartos_barre_focus = None\n"
            "_smartos_suivi_branche = False\n"
            "\n"
            "\n"
            "def _smartos_suivre_focus(_ancien, nouveau):\n"
            "    global _smartos_barre_focus\n"
            "    widget = nouveau\n"
            "    while widget is not None and not (\n"
            "            isinstance(widget, QTabWidget)\n"
            "            and widget.tabBar().objectName() == 'pane-tabbar'):\n"
            "        widget = widget.parentWidget()\n"
            "    barre = widget.tabBar() if widget is not None else None\n"
            "    if barre is _smartos_barre_focus:\n"
            "        return\n"
            "    for cible, etat in ((_smartos_barre_focus, False), (barre, True)):\n"
            "        if cible is None:\n"
            "            continue\n"
            "        try:\n"
            "            cible.setProperty('smartos_focus', etat)\n"
            "            cible.style().unpolish(cible)\n"
            "            cible.style().polish(cible)\n"
            "            cible.update()\n"
            "        except RuntimeError:\n"
            "            pass  # barre deja detruite (volet ferme)\n"
            "    _smartos_barre_focus = barre\n"
            "\n"
            "\n"
            "class BaseTabs(QTabWidget):\n",
        ),
        (
            "        self.tabBar().setObjectName('pane-tabbar')\n",
            "        self.tabBar().setObjectName('pane-tabbar')\n"
            "        global _smartos_suivi_branche\n"
            "        if not _smartos_suivi_branche:\n"
            "            from qtpy.QtWidgets import QApplication\n"
            "            QApplication.instance().focusChanged.connect(_smartos_suivre_focus)\n"
            "            _smartos_suivi_branche = True\n",
        ),
    ],
)

BASE = (
    "base.py",
    "# Variante :focus eclaircie (ajout SmartOS",
    [
        (
            "        self.setStyleSheet(style)\n\n    # ---- Extra selections\n",
            "        # Variante :focus eclaircie (ajout SmartOS, cf. patch_spyder_focus_volet.py).\n"
            "        from spyder.utils.stylesheet import SMARTOS_ECLAIRCISSEMENT\n"
            "        style += \"QPlainTextEdit#%s:focus {background: %s;}\" % (\n"
            "            self.objectName(),\n"
            "            background.lighter(SMARTOS_ECLAIRCISSEMENT).name())\n"
            "        self.setStyleSheet(style)\n\n    # ---- Extra selections\n",
        ),
    ],
)

CODEEDITOR = (
    "codeeditor.py",
    "# Marges eclaircies quand l'editeur a le focus (ajout SmartOS",
    [
        (
            "    CONF_SECTION = 'editor'\n",
            "    CONF_SECTION = 'editor'\n"
            "\n"
            "    # Marges eclaircies quand l'editeur a le focus (ajout SmartOS, cf.\n"
            "    # patch_spyder_focus_volet.py) : les sept peintres des marges lisent cette propriete.\n"
            "    @property\n"
            "    def sideareas_color(self):\n"
            "        from spyder.utils.stylesheet import SMARTOS_ECLAIRCISSEMENT\n"
            "        couleur = self._smartos_sideareas_color\n"
            "        return couleur.lighter(SMARTOS_ECLAIRCISSEMENT) if self.hasFocus() else couleur\n"
            "\n"
            "    @sideareas_color.setter\n"
            "    def sideareas_color(self, couleur):\n"
            "        self._smartos_sideareas_color = couleur\n",
        ),
        (
            "        self.folding_panel = self.panels.register(FoldingPanel())\n",
            "        self.folding_panel = self.panels.register(FoldingPanel())\n"
            "        self.focus_changed.connect(\n"
            "            lambda: [panel.update() for panel in self.panels])\n",
        ),
    ],
)

STYLE = (
    "style.py",
    "# Variante :focus eclaircie (ajout SmartOS",
    [
        (
            "    return (sheet_formatted, dark_color(font_color))\n",
            "    # Variante :focus eclaircie (ajout SmartOS, cf. patch_spyder_focus_volet.py).\n"
            "    from qtpy.QtGui import QColor\n"
            "    from spyder.utils.stylesheet import SMARTOS_ECLAIRCISSEMENT\n"
            "    sheet_formatted += (\n"
            "        'QPlainTextEdit:focus, QTextEdit:focus, ControlWidget:focus '\n"
            "        '{ background-color: %s; }' % QColor(background_color).lighter(\n"
            "            SMARTOS_ECLAIRCISSEMENT).name())\n"
            "\n"
            "    return (sheet_formatted, dark_color(font_color))\n",
        ),
    ],
)


def patcher(path, cible):
    nom, marqueur, remplacements = cible
    with open(path, encoding='utf-8') as flux:
        source = flux.read()
    if marqueur in source:
        print(f"{nom} : suivi du focus deja applique.")
        return 0
    for ancre, bloc in remplacements:
        if source.count(ancre) != 1:
            print(f"{nom} : ancre introuvable ou multiple ({ancre.strip()[:60]!r}) - patch "
                  "abandonne. Structure du fichier changee ?", file=sys.stderr)
            return 1
        source = source.replace(ancre, bloc)
    ast.parse(source)
    with open(path, 'w', encoding='utf-8') as flux:
        flux.write(source)
    print(f"{nom} : suivi du focus applique.")
    return 0


def main():
    if len(sys.argv) != 5:
        print(f"Usage : {sys.argv[0]} <tabs.py> <editor/widgets/base.py> <codeeditor.py> "
              "<ipythonconsole/utils/style.py>", file=sys.stderr)
        return 1
    erreurs = 0
    for path, cible in zip(sys.argv[1:], (TABS, BASE, CODEEDITOR, STYLE)):
        erreurs += patcher(path, cible)
    return 1 if erreurs else 0


if __name__ == '__main__':
    sys.exit(main())
