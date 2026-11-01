#!/usr/bin/env python3
"""Patch spyder/plugins/editor/panels/scrollflag.py : la CARTE DES ERREURS (bande des marques
d'erreur, d'avertissement, de todo, de point d'arret, d'occurrence) est dessinee DANS la barre de
defilement verticale, au lieu d'occuper une bande de 12 px a sa gauche.

DEMANDE : "la carte des erreurs et la barre de defillement ne peuvent pas etre fusionnees ?"
(l'utilisateur, 31/10/2026), apres avoir pris la carte pour une seconde barre de defilement.
Approche validee par le Superviseur le meme jour ; feu vert de l'utilisateur : "oui, vas-y pour la
fusion".

CE QUE FAIT LE PATCH :
  1. sizeHint() du panneau rend une largeur NULLE : le gestionnaire de panneaux (manager.py) prend
     la largeur dans sizeHint() ; le panneau reste "visible" et "enabled", si bien que tout ce qui
     le cherche (l'option de Spyder, set_todo_enabled, l'overlay d'etat du fichier de
     patch_spyder_editor_file_status.py qui se cale sur son bord gauche) continue de marcher - ce
     bord gauche est desormais celui de la barre.
  2. Une couche _SmartosMarquesSurBarre, ENFANT de la barre verticale, transparente aux clics
     (WA_TransparentForMouseEvents : la barre garde tout son comportement), recalee par un filtre
     d'evenements sur Resize/Show, dessine les marques avec le code de dessin d'origine de Spyder
     (paintEvent decoupe : la partie "marques" devient _smartos_dessiner_marques). Le rectangle
     gris de survol de l'ancienne bande disparait : la poignee de la barre en tient lieu.
  3. La barre verticale est TOUJOURS affichee (ScrollBarAlwaysOn) : avec la politique par defaut
     (AsNeeded), un fichier court n'a pas de barre, donc plus aucune marque. Alternative ecartee :
     rendre au panneau sa largeur quand la barre se cache - changer les marges de la vue peut
     faire reapparaitre la barre, qui les rechange : risque d'oscillation.
  4. Masquer la carte (option de Spyder -> set_enabled) masque aussi la couche.

Usage : patch_spyder_carte_dans_barre.py <chemin vers plugins/editor/panels/scrollflag.py>

Methodes REMPLACEES EN ENTIER, localisees par le module "ast" (classe ScrollFlagArea + nom de
methode) ; la classe de la couche est ajoutee en fin de module. Idempotent (marqueur). Re-parse
avant ecriture ; echec BRUYANT (code 1) si une methode est introuvable - jamais deviner.
"""
import ast
import sys

MARKER = "Carte des erreurs DANS la barre de defilement"

IMPORT_ANCHOR = "from qtpy.QtCore import QSize, Qt, QThread\n"
IMPORT_NEW = "from qtpy.QtCore import QEvent, QSize, Qt, QThread\n"
IMPORT_W_ANCHOR = "from qtpy.QtWidgets import QApplication, QStyle, QStyleOptionSlider\n"
IMPORT_W_NEW = ("from qtpy.QtWidgets import (\n"
                "    QApplication, QStyle, QStyleOptionSlider, QWidget)\n")

NEW_METHODS = {
    "on_install": '''    def on_install(self, editor):
        """Manages install setup of the pane."""
        super().on_install(editor)
        # Define permanent Qt colors that are needed for painting the flags
        # and the slider range.
        self._facecolors = {
            'warning': QColor(editor.warning_color),
            'error': QColor(editor.error_color),
            'todo': QColor(editor.todo_color),
            'breakpoint': QColor(editor.breakpoint_color),
            'occurrence': QColor(editor.occurrence_color),
            'found_results': QColor(editor.found_results_color)
            }
        self._edgecolors = {key: color.darker(120) for
                            key, color in self._facecolors.items()}

        # Signals
        editor.sig_focus_changed.connect(self.update)
        editor.sig_key_pressed.connect(self.keyPressEvent)
        editor.sig_key_released.connect(self.keyReleaseEvent)
        editor.sig_scrollflag_shortcut_click.connect(self.mousePressEvent)
        editor.sig_scrollflag_shortcut_move.connect(self.mouseMoveEvent)
        editor.sig_leave_out.connect(self.update)
        editor.sig_flags_changed.connect(self.update_flags)
        editor.sig_theme_colors_changed.connect(self.update_flag_colors)

        # This prevents that flags are updated while the user is moving the
        # cursor, e.g. when typing.
        editor.sig_cursor_position_changed.connect(self.update_flags)

        # Carte des erreurs DANS la barre de defilement (SmartOS, 31/10/2026, cf.
        # patch_spyder_carte_dans_barre.py) : les marques sont dessinees par une couche posee sur
        # la barre verticale, toujours affichee pour qu'un fichier court garde ses marques.
        editor.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        barre = editor.verticalScrollBar()
        self._smartos_couche = _SmartosMarquesSurBarre(self, barre)
        barre.valueChanged.connect(lambda *_ignore: self._smartos_couche.update())
        barre.rangeChanged.connect(lambda *_ignore: self._smartos_couche.update())
        self._smartos_couche.setVisible(self.enabled)
''',
    "sizeHint": '''    def sizeHint(self):
        """Override Qt method"""
        # Largeur NULLE (SmartOS) : les marques sont dessinees dans la barre de defilement.
        return QSize(0, 0)
''',
    "update": None,  # ajoutee apres sizeHint, cf. NEW_UPDATE
    "paintEvent": '''    def paintEvent(self, event):
        """
        Override Qt method.

        Le panneau a une largeur nulle (SmartOS) : les marques sont dessinees
        par _SmartosMarquesSurBarre, dans la barre de defilement.
        """
        painter = QPainter(self)
        painter.fillRect(event.rect(), self.editor.sideareas_color)

    def _smartos_dessiner_marques(self, painter, largeur):
        """Dessine les marques sur `painter`, sur une bande de `largeur` px.

        Code de dessin d'origine de paintEvent, la bande prenant la largeur
        de la barre de defilement au lieu de WIDTH.
        """
        # The area in which the slider handle of the scrollbar may move.
        groove_rect = self.get_scrollbar_groove_rect()

        # This is necessary to catch a possible error when the scrollbar
        # has zero height.
        # Fixes spyder-ide/spyder#21600
        try:
            # The scrollbar's scale factor ratio between pixel span height and
            # value span height
            scale_factor = (
                groove_rect.height() / self.get_scrollbar_value_height()
            )
        except ZeroDivisionError:
            scale_factor = 1

        # The vertical offset of the scroll flag area relative to the
        # top of the text editor.
        offset = groove_rect.y()

        rect_x = ceil(self.FLAGS_DX / 2)
        rect_w = max(1, largeur - self.FLAGS_DX)
        rect_h = self.FLAGS_DY

        editor = self.editor

        # Paint flags for the entire document
        last_line = editor.document().lastBlock().firstLineNumber()
        # The 0.5 offset is used to align the flags with the center of
        # their corresponding text edit block before scaling.
        first_y_pos = self.value_to_position(
            0.5, scale_factor, offset) - self.FLAGS_DY / 2
        last_y_pos = self.value_to_position(
            last_line + 0.5, scale_factor, offset) - self.FLAGS_DY / 2

        # Compute the height of a line and of a flag in lines.
        line_height = last_y_pos - first_y_pos
        if line_height > 0:
            flag_height_lines = rect_h * last_line / line_height
        else:
            flag_height_lines = 0

        # All the lists of block numbers for flags
        dict_flag_lists = {
            "occurrence": editor.occurrences,
            "found_results": editor.found_results
        }
        dict_flag_lists.update(self._dict_flag_list)

        # This is necessary to paint find matches above errors and warnings.
        # See spyder-ide/spyder#20970
        dict_flag_lists_iter = reversed(dict_flag_lists)

        for flag_type in dict_flag_lists_iter:
            # Don't paint todo's if they are not enabled.
            # Fixes spyder-ide/spyder#24940.
            if flag_type == 'todo' and not self.todo_enabled:
                continue

            painter.setBrush(self._facecolors[flag_type])
            painter.setPen(self._edgecolors[flag_type])
            if editor.verticalScrollBar().maximum() == 0:
                # No scroll
                for block in dict_flag_lists[flag_type]:
                    if not is_block_safe(block):
                        continue
                    geometry = editor.blockBoundingGeometry(block)
                    rect_y = ceil(
                        geometry.y() +
                        geometry.height() / 2 +
                        rect_h / 2
                    )
                    painter.drawRect(rect_x, rect_y, rect_w, rect_h)
            elif last_line == 0:
                # Only one line
                for block in dict_flag_lists[flag_type]:
                    if not is_block_safe(block):
                        continue
                    rect_y = ceil(first_y_pos)
                    painter.drawRect(rect_x, rect_y, rect_w, rect_h)
            else:
                # Many lines
                if len(dict_flag_lists[flag_type]) < MAX_FLAGS:
                    # If the file is too long, do not freeze the editor
                    next_line = 0
                    for block in dict_flag_lists[flag_type]:
                        if not is_block_safe(block):
                            continue
                        block_line = block.firstLineNumber()
                        # block_line = -1 if invalid
                        if block_line < next_line:
                            # Don't print flags on top of flags
                            continue
                        next_line = block_line + flag_height_lines / 2
                        frac = block_line / last_line
                        rect_y = ceil(first_y_pos + frac * line_height)
                        painter.drawRect(rect_x, rect_y, rect_w, rect_h)
''',
    "get_scrollbar_groove_rect": '''    def get_scrollbar_groove_rect(self):
        """Return the area in which the slider handle may move."""
        vsb = self.editor.verticalScrollBar()
        style = QApplication.instance().style()
        opt = QStyleOptionSlider()
        vsb.initStyleOption(opt)

        # Get the area in which the slider handle may move. Rectangle dans
        # le repere de la barre (SmartOS) : c'est la que les marques sont
        # dessinees.
        groove_rect = style.subControlRect(
            QStyle.CC_ScrollBar, opt, QStyle.SC_ScrollBarGroove, vsb)

        return groove_rect
''',
    "set_enabled": '''    def set_enabled(self, state):
        """Toggle scroll flag area visibility"""
        self.enabled = state
        self.setVisible(state)
        couche = getattr(self, '_smartos_couche', None)
        if couche is not None:
            couche.setVisible(state)
''',
}

NEW_UPDATE = '''
    def update(self, *args):
        """Override Qt method : repeint aussi la couche de la barre (SmartOS)."""
        super().update(*args)
        couche = getattr(self, '_smartos_couche', None)
        if couche is not None:
            couche.update()
'''

NEW_CLASS = '''

class _SmartosMarquesSurBarre(QWidget):
    """Couche transparente posee sur la barre de defilement verticale, qui y
    dessine les marques de la carte des erreurs (SmartOS, 31/10/2026, cf.
    patch_spyder_carte_dans_barre.py). Transparente aux clics : la barre
    garde tout son comportement."""

    def __init__(self, area, barre):
        super().__init__(barre)
        self._area = area
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        barre.installEventFilter(self)
        self._recaler(barre)

    def _recaler(self, barre):
        self.setGeometry(barre.rect())
        self.raise_()

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
            self._recaler(obj)
        return False

    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            self._area._smartos_dessiner_marques(painter, self.width())
        finally:
            painter.end()
'''


def fail(msg):
    print("patch_spyder_carte_dans_barre: ECHEC - " + msg)
    sys.exit(1)


def main():
    if len(sys.argv) != 2:
        fail("usage : patch_spyder_carte_dans_barre.py <scrollflag.py>")
    path = sys.argv[1]
    with open(path, encoding="utf-8") as f:
        src = f.read()
    if MARKER in src:
        print("patch_spyder_carte_dans_barre: deja applique")
        return

    for anchor, new in ((IMPORT_ANCHOR, IMPORT_NEW), (IMPORT_W_ANCHOR, IMPORT_W_NEW)):
        if src.count(anchor) != 1:
            fail("import introuvable ou multiple : " + anchor.strip())
        src = src.replace(anchor, new)

    tree = ast.parse(src)
    classe = next((n for n in tree.body
                   if isinstance(n, ast.ClassDef) and n.name == "ScrollFlagArea"), None)
    if classe is None:
        fail("classe ScrollFlagArea introuvable")
    methodes = {n.name: n for n in classe.body if isinstance(n, ast.FunctionDef)}

    lignes = src.splitlines(keepends=True)
    remplacements = []
    for nom, code in NEW_METHODS.items():
        if code is None:
            continue
        noeud = methodes.get(nom)
        if noeud is None:
            fail("methode ScrollFlagArea.%s introuvable" % nom)
        debut = (noeud.decorator_list[0].lineno if noeud.decorator_list else noeud.lineno) - 1
        if nom == "sizeHint":
            code = code + NEW_UPDATE
        remplacements.append((debut, noeud.end_lineno, code))
    for debut, fin, code in sorted(remplacements, reverse=True):
        lignes[debut:fin] = [code]
    src = "".join(lignes).rstrip("\n") + "\n" + NEW_CLASS

    if MARKER not in src:
        fail("marqueur absent apres remplacement")
    try:
        ast.parse(src)
    except SyntaxError as e:
        fail("resultat non analysable : %s" % e)
    with open(path, "w", encoding="utf-8") as f:
        f.write(src)
    print("patch_spyder_carte_dans_barre: applique")


if __name__ == "__main__":
    main()
