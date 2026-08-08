#!/usr/bin/env python3
"""Patch spyder/plugins/editor/panels/linenumber.py : la COLONNE DE MARQUEURS a gauche des numeros de
ligne est retablie, et le numero des lignes en ERREUR reste trace en rouge fonce.

HISTORIQUE, parce qu'il explique la forme du patch et qu'il s'est retourne une fois :
  - 22/07/2026, demande de l'utilisateur : "que les erreurs ne s'affichent plus sous forme d'un rond
    avec une croix a gauche du numero, mais en mettant en rouge le numero". Puis, meme jour : "la zone
    a gauche des numeros n'est plus utile, supprime-la pour reduire la marge". La colonne a donc ete
    supprimee (get_markers_margin -> 0) et paintEvent reecrit sans aucun marqueur.
  - 26/07/2026, demande inverse : "remettre la colonne a gauche des numeros de ligne qui permettait de
    voir les resultats de l'analyse de code". La raison saute aux yeux avec le recul, et le patch
    precedent la notait lui-meme sans en tirer la consequence : le numero rouge ne signale que les
    ERREURS. Supprimer la colonne faisait donc disparaitre TOUT indicateur d'avertissement,
    d'information, d'indice et de todo - c'est-a-dire l'essentiel de ce que produit l'analyse de code.

CE QUE FAIT CETTE VERSION : les deux, sans se marcher dessus.
  1. get_markers_margin() rend a nouveau font_height + 2 : la colonne existe, avec ses icones
     error / warning / info / hint / todo.
  2. paintEvent reprend le code d'origine de Spyder - donc tous les marqueurs - et y AJOUTE le trace
     en rouge fonce du numero des lignes en erreur.
  ⚠ 3. ET L'EFFACEMENT DE CELLULE DU BLOC ROUGE COMMENCE APRES LA MARGE DE MARQUEURS. La version
     precedente repeignait la cellule depuis x=0 sur toute la largeur, ce qui etait sans consequence
     quand la colonne n'existait pas. La colonne retablie, ce meme fillRect aurait recouvert l'icone
     d'erreur qu'on vient de tracer - le numero rouge aurait mange le marqueur, sur les lignes
     precisement ou il compte le plus. Defaut anticipe par lecture, pas constate a l'usage.

Usage : patch_spyder_error_margin.py <chemin vers plugins/editor/panels/linenumber.py installe>

LES DEUX METHODES SONT REMPLACEES EN ENTIER, localisees par le module "ast" (nom de classe + nom de
methode) et non par ancrage de texte. C'est ce qui rend le patch applicable depuis N'IMPORTE QUEL
etat - fichier d'origine de Spyder, ou deja patche par la version precedente - sans avoir a enumerer
les textes anterieurs. Idempotent (marqueur). L'import de SpyderPalette, absent de linenumber.py, est
ajoute par ancrage de texte. Re-parse avant ecriture ; echec BRUYANT (code 1) si une methode est
introuvable - jamais deviner.
"""
import ast
import sys

MARKER = "Colonne de marqueurs RETABLIE"

# --- Import de SpyderPalette (absent de linenumber.py), pour la couleur d'erreur du theme ---------
IMPORT_ANCHOR = "from spyder.utils.icon_manager import ima\n"
IMPORT_MARKER = "from spyder.utils.palette import SpyderPalette"
IMPORT_ADD = "from spyder.utils.palette import SpyderPalette\n"

NEW_MARKERS_MARGIN = '''    def get_markers_margin(self):
        """Get marker margins."""
        # Colonne de marqueurs RETABLIE (SmartOS, 26/07/2026) : elle avait ete supprimee le
        # 22/07/2026 - get_markers_margin renvoyait 0 - au profit du seul numero en rouge. Retour a
        # la demande de l'utilisateur : le numero rouge ne signalait que les ERREURS, et faisait donc
        # disparaitre tout indicateur d'avertissement, d'information, d'indice et de todo.
        font_height = self.editor.fontMetrics().height() + 2
        return font_height
'''

NEW_PAINTEVENT = '''    def paintEvent(self, event):
        """Override Qt method.

        Painting line number area
        """

        painter = QPainter(self)
        painter.fillRect(event.rect(), self.editor.sideareas_color)
        font_height = self.editor.fontMetrics().height()

        def draw_pixmap(xleft, ytop, pixmap):
            # Scale pixmap height to device independent pixels
            pixmap_height = pixmap.height() / pixmap.devicePixelRatio()
            painter.drawPixmap(
                xleft,
                ceil(ytop + (font_height-pixmap_height) / 2),
                pixmap
            )

        size = self.get_markers_margin() - 2
        icon_size = QSize(size, size)

        if self._margin:
            font = self.editor.font()
            fm = QFontMetricsF(font)
            if (
                fm.leading() == 0
                and self.editor.lineWrapMode() == QTextOption.NoWrap
            ):
                self.draw_linenumbers(painter)
            else:
                # The editor doesn't care about leading or the text is being
                # wrapped, so each line must be drawn independently.
                self.draw_linenumbers_slow(painter)
        self.paint_cell(painter)

        for top, line_number, block in self.editor.visible_blocks:
            data = block.userData()
            if data:
                if data.code_analysis:
                    errors = 0
                    warnings = 0
                    infos = 0
                    hints = 0
                    for _, _, sev, _ in data.code_analysis:
                        errors += sev == DiagnosticSeverity.ERROR
                        warnings += sev == DiagnosticSeverity.WARNING
                        infos += sev == DiagnosticSeverity.INFORMATION
                        hints += sev == DiagnosticSeverity.HINT

                    if errors:
                        draw_pixmap(1, top, self.error_icon.pixmap(icon_size))
                    elif warnings:
                        draw_pixmap(
                            1, top, self.warning_icon.pixmap(icon_size))
                    elif infos:
                        draw_pixmap(1, top, self.info_icon.pixmap(icon_size))
                    elif hints:
                        draw_pixmap(1, top, self.hint_icon.pixmap(icon_size))

                if self._markers_margin and data.todo:
                    draw_pixmap(1, top, self.todo_icon.pixmap(icon_size))

        # Numero de ligne en ROUGE FONCE pour les lignes en erreur (SmartOS, cf.
        # Commun/scripts/patch_spyder_error_margin.py). Complete l'icone de la marge, elle ne la
        # remplace plus : la colonne de marqueurs a ete RETABLIE le 26/07/2026 a la demande de
        # l'utilisateur, apres qu'elle avait ete supprimee le 22/07/2026 a sa demande egalement.
        # ⚠ L'EFFACEMENT DE LA CELLULE COMMENCE APRES LA MARGE DE MARQUEURS, jamais a x=0 : la
        # version precedente repeignait toute la largeur, ce qui recouvrirait desormais l'icone
        # d'erreur que l'on vient de tracer - le numero rouge aurait alors mange le marqueur, sur
        # les lignes precisement ou il compte le plus.
        marge = self.get_markers_margin()
        font = self.editor.font()
        font.setWeight(QFont.Weight.Normal)
        painter.setFont(font)
        for top, line_number, block in self.editor.visible_blocks:
            data = block.userData()
            if data and data.code_analysis and any(
                sev == DiagnosticSeverity.ERROR
                for _, _, sev, _ in data.code_analysis
            ):
                painter.fillRect(
                    marge, top, self.width() - marge, font_height,
                    self.editor.sideareas_color
                )
                painter.setPen(QColor(SpyderPalette.COLOR_ERROR_1))
                painter.drawText(
                    marge, top, self.width() - marge, font_height,
                    int(Qt.AlignRight | Qt.AlignTop), str(line_number)
                )
'''


def remplacer_methode(source, classe, methode, nouveau, path):
    """Remplace une methode entiere, localisee par ast. Renvoie la source ou None."""
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ClassDef) and node.name == classe:
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                        and item.name == methode:
                    lignes = source.splitlines(keepends=True)
                    lignes[item.lineno - 1:item.end_lineno] = [nouveau]
                    return "".join(lignes)
    print(f"{classe}.{methode} introuvable dans {path} - Spyder a peut-etre restructure son code, "
          f"patch marge d'erreurs non applique.", file=sys.stderr)
    return None


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers editor/panels/linenumber.py>", file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as error:
        print(f"linenumber.py illisible ({error}) - patch marge d'erreurs non applique.",
              file=sys.stderr)
        return 1

    if MARKER in source:
        print("Patch marge d'erreurs deja applique.")
        return 0

    if IMPORT_MARKER not in source:
        if source.count(IMPORT_ANCHOR) != 1:
            print(f"Ancre d'import introuvable ou non unique dans {path} - patch marge d'erreurs "
                  f"non applique.", file=sys.stderr)
            return 1
        source = source.replace(IMPORT_ANCHOR, IMPORT_ANCHOR + IMPORT_ADD, 1)

    for methode, nouveau in (("get_markers_margin", NEW_MARKERS_MARGIN),
                             ("paintEvent", NEW_PAINTEVENT)):
        source = remplacer_methode(source, "LineNumberArea", methode, nouveau, path)
        if source is None:
            return 1

    try:
        ast.parse(source)
    except SyntaxError as error:
        print(f"Le linenumber.py patche n'est pas du Python valide ({error}) - aucune modification "
              "ecrite.", file=sys.stderr)
        return 1

    with open(path, "w", encoding="utf-8") as f:
        f.write(source)
    print(f"Patch marge d'erreurs applique : colonne de marqueurs retablie, numero des lignes en "
          f"erreur en rouge fonce ({path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
