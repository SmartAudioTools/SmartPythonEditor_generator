#!/usr/bin/env python3
"""Patch spyder/plugins/editor/widgets/editorstack/editorstack.py : OVERLAY FLOTTANT en bas a droite
de CHAQUE panneau d'edition (EditorStack), affichant, pour le fichier ACTIF de ce panneau :
ligne/colonne du curseur, encodage, fin de ligne (EOL) - SUPERPOSE a la zone de texte (dans le cadre
du texte), donc sans rogner l'editeur d'une ligne.

Contexte (demande utilisateur du 22/07/2026). Trois exigences :
  - dans le cadre du texte, pas une ligne de layout ;
  - les trois infos RAPPROCHEES (separateurs "·"), pas eparpillees ;
  - NE PAS deborder sur la barre de defilement (verticale ni horizontale) : l'overlay est decale a
    gauche de la scrollbar verticale et au-dessus de l'horizontale (largeurs lues sur l'editeur actif).

POURQUOI UN PATCH : injecter un widget flottant dans chaque EditorStack (crees dynamiquement a chaque
scission). CABLAGE : signaux PROPRES a l'EditorStack (donc lie a SON fichier) :
sig_editor_cursor_position_changed, encoding_changed, sig_refresh_eol_chars. REPOSITIONNEMENT :
EditorStack n'a pas de resizeEvent propre -> l'overlay s'installe comme eventFilter sur son parent.
Il est WA_TransparentForMouseEvents (clics vers l'editeur) et raise_() (au-dessus du texte).

Usage : patch_spyder_editor_file_status.py <chemin vers editorstack.py installe>

UPDATE-SAFE : a chaque execution, retire ses blocs precedents (bornes par des sentinelles) puis les
reinsere a jour - on peut donc rejouer le patch apres avoir change le style, sans reinstaller Spyder.
Deux insertions via ast (classe avant `class EditorStack`, cablage a la fin de __init__), de bas en
haut. Re-parse avant ecriture ; echoue BRUYAMMENT (code 1) si un point d'insertion manque.
"""
import ast
import sys

SENTINEL = "SmartOS editor file-status overlay"

OVERLAY_CLASS = '''# >>> SmartOS editor file-status overlay (class) >>>
# Overlay flottant d'infos de fichier par panneau d'edition (SmartOS, cf.
# Commun/scripts/patch_spyder_editor_file_status.py).
from qtpy.QtCore import QEvent as _smartos_QEvent, Qt as _smartos_Qt
from qtpy.QtWidgets import (QWidget as _smartos_QWidget, QLabel as _smartos_QLabel,
                            QHBoxLayout as _smartos_QHBoxLayout)


class _SmartOSFileStatusBar(_smartos_QWidget):
    """Petit bandeau ligne/colonne + encodage + fin de ligne, SUPERPOSE au coin bas-droit de la
    zone de texte de son EditorStack parent (ne prend aucune ligne de layout)."""

    def __init__(self, parent):
        super().__init__(parent)
        # Les clics traversent l'overlay et vont a l'editeur.
        self.setAttribute(_smartos_Qt.WA_TransparentForMouseEvents)
        _lay = _smartos_QHBoxLayout(self)
        _lay.setContentsMargins(6, 1, 0, 1)   # marge droite 0 : coller au bord
        _lay.setSpacing(0)
        # PLUSIEURS QLabel (texte simple) plutot qu'un seul en RichText : le RichText reserve une
        # etiquette plus large que le texte et ne s'aligne pas a droite de facon fiable
        # (setAlignment et <div align> restent sans effet), laissant un vide jusqu'a la scrollbar.
        # Des labels simples se dimensionnent au plus juste, et le fond rouge d'alerte est pose par
        # feuille de style sur le seul label concerne (encodage ou fin de ligne).
        self._smartos_lbl_cursor = _smartos_QLabel("", self)
        self._smartos_lbl_sep1 = _smartos_QLabel("", self)
        self._smartos_lbl_encoding = _smartos_QLabel("", self)
        self._smartos_lbl_sep2 = _smartos_QLabel("", self)
        self._smartos_lbl_eol = _smartos_QLabel("", self)
        for _w in (self._smartos_lbl_cursor, self._smartos_lbl_sep1,
                   self._smartos_lbl_encoding, self._smartos_lbl_sep2,
                   self._smartos_lbl_eol):
            # QLabel applique par defaut un indent d'environ un demi-caractere sur le bord aligne :
            # cumule sur 5 labels, cela creusait un large vide autour des virgules. On l'annule.
            _w.setIndent(0)
            _w.setContentsMargins(0, 0, 0, 0)
            _lay.addWidget(_w)
        self._smartos_line = 1
        self._smartos_col = 1
        self._smartos_encoding_base = ""      # base normalisee (sert au test "non UTF-8" -> rouge)
        self._smartos_encoding_display = ""   # libelle affiche, ex. "UTF-8 (BOM)", "LATIN-1"
        self._smartos_eol_os = ""             # "nt" (Windows/CRLF), "posix" (Unix/LF), autre (Mac/CR)
        # Fond d'ALERTE (rouge) pour un encodage non-UTF-8 ou une fin de ligne Windows.
        self._smartos_warn_bg = "#E74C3C"
        # Fond opaque (sinon le texte transparait derriere) + texte discret.
        try:
            from spyder.utils.palette import SpyderPalette as _P
            self._smartos_warn_bg = _P.COLOR_ERROR_2
            self.setStyleSheet(
                "_SmartOSFileStatusBar { background-color: %s; border-top-left-radius: 6px; }"
                "QLabel { color: %s; background: transparent; }"
                % (_P.COLOR_BACKGROUND_1, _P.COLOR_TEXT_4)
            )
        except Exception:
            pass
        # Police un peu plus petite que celle de l'editeur : resserre la HAUTEUR de l'overlay (et
        # donc du fond rouge d'alerte, qui remplit la hauteur du label), pour un rendu compact qui
        # ne deborde pas du cadre de l'editeur. La hauteur suit la police via adjustSize().
        try:
            _f = self.font()
            _ps = _f.pointSizeF()
            if _ps > 0:
                _f.setPointSizeF(max(7.5, _ps - 1.0))
                self.setFont(_f)   # heritee par les QLabel enfants
        except Exception:
            pass
        parent.installEventFilter(self)
        self._smartos_reposition()

    def eventFilter(self, obj, event):
        if obj is self.parent() and event.type() in (
                _smartos_QEvent.Resize, _smartos_QEvent.Show):
            self._smartos_reposition()
        return False

    def _smartos_reposition(self):
        parent = self.parent()
        if parent is None:
            return
        self.adjustSize()
        margin = 2
        # Bord droit de l'overlay = bord GAUCHE de la "scroll flag area" (la bande grise des
        # marqueurs, classe ScrollFlagArea) -> l'overlay se place a gauche a la fois des marqueurs ET
        # de la scrollbar, sans les recouvrir. Repli sur la largeur de la scrollbar si la scroll flag
        # area est introuvable. Bas : au-dessus de la scrollbar horizontale si elle est visible.
        right_limit = parent.width()
        sb_h = 0
        try:
            editor = parent.get_current_editor()
            if editor is not None:
                _scrollflag = None
                for _p in editor.panels:
                    if type(_p).__name__ == "ScrollFlagArea":
                        _scrollflag = _p
                        break
                if _scrollflag is not None and _scrollflag.isVisible():
                    right_limit = parent.mapFromGlobal(
                        _scrollflag.mapToGlobal(_scrollflag.rect().topLeft())).x()
                else:
                    vsb = editor.verticalScrollBar()
                    if vsb is not None and vsb.isVisible():
                        right_limit = parent.width() - vsb.width()
                hsb = editor.horizontalScrollBar()
                if hsb is not None and hsb.isVisible():
                    sb_h = hsb.height()
        except Exception:
            pass
        x = right_limit - self.width() - margin
        y = parent.height() - self.height() - margin - sb_h
        self.move(max(0, x), max(0, y))
        self.raise_()
        self.show()

    def _smartos_warn_span(self, text):
        # Fond rouge d'alerte autour du texte (encodage/fin de ligne non standard).
        return ('<span style="background-color: %s; color: white;">&#160;%s&#160;</span>'
                % (self._smartos_warn_bg, text))

    @staticmethod
    def _smartos_conf(option, default):
        # Options lues dans la section "editor" (cases de Preferences > Editeur > Affichage). Lues a
        # chaque rafraichissement (peu couteux) -> un changement dans les Preferences s'applique au
        # prochain evenement de l'editeur.
        try:
            from spyder.config.manager import CONF
            return CONF.get("editor", option, default)
        except Exception:
            return default

    def _smartos_refresh(self):
        # Deux options (Preferences) :
        #  - smartos_overlay_verbose : VERBEUX ("Ligne 11, Colonne 1, encodage UTF-8, fin de ligne
        #    Unix") ou ABREGE ("L 11, C 1  UTF-8  LF") ;
        #  - smartos_overlay_only_non_standard : n'afficher encodage/fin de ligne QUE s'ils ne sont
        #    pas standard (autre chose qu'UTF-8 / Unix).
        # ALERTE pedagogique (version pour etudiants) : fond ROUGE si l'encodage n'est pas compatible
        # UTF-8, ou si la fin de ligne n'est pas Unix. Parties non encore connues : omises.
        verbose = self._smartos_conf("smartos_overlay_verbose", True)
        only_ns = self._smartos_conf("smartos_overlay_only_non_standard", False)
        sep = ", " if verbose else "  "
        red = "background-color: %s; color: white; padding: 0px 3px;" % self._smartos_warn_bg

        # Ligne/colonne (toujours affiche)
        if verbose:
            self._smartos_lbl_cursor.setText(_("Line {line}, Column {column}").format(
                line=self._smartos_line, column=self._smartos_col))
        else:
            self._smartos_lbl_cursor.setText("L {line}, C {column}".format(
                line=self._smartos_line, column=self._smartos_col))

        # Encodage : ASCII et variantes UTF-8 (BOM) sont compatibles -> pas d'alerte. Rouge pour un
        # encodage reellement different (Latin-1, Windows-1252, UTF-16...). Cache si l'option
        # "seulement si non standard" est active et que c'est de l'UTF-8.
        non_utf8 = self._smartos_encoding_base.replace("_", "-") not in (
            "UTF-8", "ASCII", "US-ASCII")
        show_enc = bool(self._smartos_encoding_base) and (non_utf8 or not only_ns)
        self._smartos_lbl_sep1.setText(sep)
        self._smartos_lbl_sep1.setVisible(show_enc)
        self._smartos_lbl_encoding.setVisible(show_enc)
        if show_enc:
            self._smartos_lbl_encoding.setText(
                _("encoding {encoding}").format(encoding=self._smartos_encoding_display)
                if verbose else self._smartos_encoding_display)
            self._smartos_lbl_encoding.setStyleSheet(red if non_utf8 else "")

        # Fin de ligne : standard = Unix (posix). Rouge si non-Unix (Windows/CRLF ; Mac/CR).
        non_unix = bool(self._smartos_eol_os) and self._smartos_eol_os != "posix"
        show_eol = bool(self._smartos_eol_os) and (non_unix or not only_ns)
        self._smartos_lbl_sep2.setText(sep)
        self._smartos_lbl_sep2.setVisible(show_eol)
        self._smartos_lbl_eol.setVisible(show_eol)
        if show_eol:
            if verbose:
                name = {"nt": "Windows", "posix": "Unix"}.get(self._smartos_eol_os, "Mac")
                self._smartos_lbl_eol.setText(_("end of line {eol}").format(eol=name))
            else:
                self._smartos_lbl_eol.setText(
                    {"nt": "CRLF", "posix": "LF"}.get(self._smartos_eol_os, "CR"))
            self._smartos_lbl_eol.setStyleSheet(red if non_unix else "")

        self._smartos_reposition()

    def update_cursor(self, line, index):
        self._smartos_line = line + 1
        self._smartos_col = index + 1
        self._smartos_refresh()

    def update_encoding(self, encoding):
        # Spyder encode le BOM et l'incertitude dans le nom de l'encodage : "utf-8-bom" (BOM
        # present), "<enc>-guessed" (encodage devine par detection). On separe la BASE (pour le test
        # "non UTF-8" -> fond rouge) du LIBELLE affiche. Le suffixe "-guessed" est simplement RETIRE
        # (la detection est generalement fiable - demande utilisateur) ; seul "(BOM)" est conserve
        # comme qualificatif car il change le contenu reel du fichier.
        raw = str(encoding).lower()
        qualifier = ""
        if raw.endswith("-bom"):
            base = raw[:-len("-bom")]
            qualifier = "BOM"
        elif raw.endswith("-guessed"):
            base = raw[:-len("-guessed")]
        else:
            base = raw
        self._smartos_encoding_base = base.upper()
        self._smartos_encoding_display = self._smartos_encoding_base
        if qualifier:
            self._smartos_encoding_display += " (%s)" % qualifier
        self._smartos_refresh()

    def update_eol(self, os_name):
        self._smartos_eol_os = str(os_name)
        self._smartos_refresh()
# <<< SmartOS editor file-status overlay (class) <<<
'''

WIRING = '''        # >>> SmartOS editor file-status overlay (wiring) >>>
        # Overlay d'infos du fichier actif, superpose au coin bas-droit de ce panneau (SmartOS, cf.
        # Commun/scripts/patch_spyder_editor_file_status.py) - alimente par les signaux PROPRES a cet
        # EditorStack, donc lie a son propre fichier ; ne prend aucune ligne de layout.
        self._smartos_status_bar = _SmartOSFileStatusBar(self)
        self.sig_editor_cursor_position_changed.connect(
            self._smartos_status_bar.update_cursor)
        self.encoding_changed.connect(self._smartos_status_bar.update_encoding)
        self.sig_refresh_eol_chars.connect(self._smartos_status_bar.update_eol)
        # <<< SmartOS editor file-status overlay (wiring) <<<
'''


def remove_sentinel_blocks(source):
    """Retire tous les blocs bornes par '# >>> ... SENTINEL ... >>>' / '# <<< ... SENTINEL ... <<<'."""
    lines = source.splitlines(keepends=True)
    out, skip = [], False
    for line in lines:
        if (">>>" in line) and (SENTINEL in line):
            skip = True
            continue
        if ("<<<" in line) and (SENTINEL in line):
            skip = False
            continue
        if not skip:
            out.append(line)
    return "".join(out)


def find_class(tree, class_name):
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    return None


def find_method(class_node, method_name):
    for sub in class_node.body:
        if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and sub.name == method_name:
            return sub
    return None


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers editorstack.py>", file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as error:
        print(f"editorstack.py illisible ({error}) - patch overlay infos editeur non applique.",
              file=sys.stderr)
        return 1

    # Update-safe : repartir d'une base propre (retire une eventuelle version anterieure).
    source = remove_sentinel_blocks(source)

    tree = ast.parse(source)
    cls = find_class(tree, "EditorStack")
    if cls is None:
        print("class EditorStack introuvable dans editorstack.py - patch overlay non applique.",
              file=sys.stderr)
        return 1
    init = find_method(cls, "__init__")
    if init is None:
        print("EditorStack.__init__ introuvable dans editorstack.py - patch overlay non applique.",
              file=sys.stderr)
        return 1

    inserts = [
        (init.body[-1].end_lineno, WIRING),   # cablage a la fin de __init__ (ligne haute)
        (cls.lineno - 1, OVERLAY_CLASS),       # classe overlay AVANT `class EditorStack` (ligne basse)
    ]
    inserts.sort(key=lambda t: t[0], reverse=True)

    lines = source.splitlines(keepends=True)
    for idx, text in inserts:
        lines.insert(idx, text)
    patched = "".join(lines)

    try:
        ast.parse(patched)
    except SyntaxError as error:
        print(f"L'editorstack.py patche n'est pas du Python valide ({error}) - aucune modification "
              "ecrite.", file=sys.stderr)
        return 1

    with open(path, "w", encoding="utf-8") as f:
        f.write(patched)
    print(f"Patch overlay infos par panneau d'edition applique/mis a jour ({path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
