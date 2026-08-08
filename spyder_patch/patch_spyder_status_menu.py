#!/usr/bin/env python3
"""Patch spyder/plugins/ipythonconsole/widgets/status.py pour ajouter un vrai menu de selection
d'interpreteur directement dans le widget de barre d'etat, sans passer par les Preferences.

Contexte (TODO du 18/07/2026, demande explicite de l'utilisateur) : PythonEnvironmentStatus.show_menu()
n'affiche par defaut qu'une seule action, "Change default environment in Preferences...", simple
raccourci vers les Preferences - pas un vrai selecteur (cf. CachyOS/Documentation/CachyOS - DONE.txt
"SPYDER : Interpreteurs python..."). Ce patch ajoute une entree de menu cliquable par interpreteur
present dans custom_interpreters_list (deja peuplee/maintenue par nos propres scripts d'installation,
cf. Commun/scripts/update_spyder_interpreters.py), qui bascule directement l'interpreteur par defaut
sans ouvrir aucun dialogue - en s'appuyant sur le mecanisme reactif deja existant de Spyder
(MainInterpreterContainer.on_interpreter_changed, qui ecoute les options 'default'/'custom_interpreter'/
'custom' et calcule lui-meme 'executable' - on ne fait que positionner ces 3 options, sans dupliquer
sa logique).

Usage : patch_spyder_status_menu.py <chemin vers status.py installe>

Localisation des points d'insertion via le module "ast" (analyse de la structure du code, pas du
texte brut) plutot qu'une recherche exacte de bloc de texte : retrouve la methode show_menu() par son
nom dans la classe PythonEnvironmentStatus, et le dernier import de haut niveau, quels que soient les
commentaires/docstrings/blancs autour ou l'ordre des autres methodes/imports - resiste donc aux
changements de pure forme d'une version de Spyder a l'autre. Ceci ne resout PAS le risque inverse :
si le CONTENU de show_menu() change reellement dans une future version de Spyder (nouvelle
fonctionnalite ajoutee par l'equipe Spyder a l'interieur de cette methode), ce patch la remplace quand
meme integralement - remplacer "intelligemment" reviendrait a fusionner deux logiques arbitraires,
bien plus risque qu'un remplacement complet suivi d'une verification manuelle. D'ou le choix
d'echouer BRUYAMMENT (code de sortie 1) des que la methode ou les imports ne sont pas trouves comme
attendu, plutot que de deviner.

Idempotent : si le marqueur du patch (methode "select_interpreter") est deja present, ne fait rien.
"""
import ast
import sys

NEW_SHOW_MENU = '''    def show_menu(self):
        """Display a menu when clicking on the widget."""
        self.menu.clear_actions()

        # Liste des interpreteurs directement selectionnables ici, sans passer par les Preferences
        # (TODO du 18/07/2026, demande explicite de l'utilisateur). Reprend custom_interpreters_list,
        # deja peuplee/maintenue a jour par nos propres scripts d'installation (cf.
        # Commun/scripts/update_spyder_interpreters.py) plutot que par la detection pyenv de Spyder
        # (buggy avec l'architecture SmartPythons, cf. CachyOS - DONE.txt).
        current_path = (
            self._current_env_info["path"] if self._current_env_info else None
        )
        interpreters = self.get_conf(
            'custom_interpreters_list', default=[], section='main_interpreter'
        )

        def _interpreter_label(interpreter_path):
            # Affiche juste le nom de l'environnement pyenv (ex. "SmartKonsole") plutot que le
            # chemin complet ("/DATA/Python/SmartPython/CachyOS/versions/SmartKonsole/bin/python") -
            # convention pyenv-virtualenv : le chemin est toujours de la forme
            # ".../versions/<nom>/bin/python", donc le nom est le dossier 2 niveaux au-dessus de
            # l'executable. Si la structure ne correspond pas a cette convention (interpreteur
            # ajoute manuellement ailleurs), retourne le chemin complet tel quel plutot que de planter.
            try:
                label = osp.basename(osp.dirname(osp.dirname(interpreter_path)))
            except Exception:
                label = interpreter_path
            return label or interpreter_path

        # Tri alphabetique (insensible a la casse) sur le nom affiche, pas sur le chemin complet -
        # demande explicite de l'utilisateur.
        labeled_interpreters = sorted(
            ((_interpreter_label(p), p) for p in interpreters),
            key=lambda item: item[0].lower(),
        )
        for label, interpreter_path in labeled_interpreters:
            # icone coche verte (deja utilisee par Spyder pour indiquer un etat "valide/ok", cf.
            # icon_manager.py "dependency_ok") plutot qu'un prefixe texte - couleur issue de la
            # palette Spyder (SpyderPalette.COLOR_SUCCESS_2), donc coherente avec le theme
            # clair/sombre actif, contrairement a une couleur codee en dur.
            select_action = self.create_action(
                f"select_environment_{interpreter_path}",
                text=label,
                icon=ima.icon('dependency_ok') if interpreter_path == current_path else None,
                triggered=functools.partial(
                    self.select_interpreter, interpreter_path
                ),
                register_action=False,
            )
            self.add_item_to_menu(select_action, self.menu)

        text = _("Change default environment in Preferences...")
        change_action = self.create_action(
            "change_environment",
            text=text,
            triggered=self.open_interpreter_preferences,
            register_action=False,
        )
        self.add_item_to_menu(change_action, self.menu)

        x_offset = (
            # Margin of menu items to left and right
            2 * SpyderMenu.HORIZONTAL_MARGIN_FOR_ITEMS
            # Padding of menu items to left and right
            + 2 * SpyderMenu.HORIZONTAL_PADDING_FOR_ITEMS
        )
        y_offset = 4 if MAC else (3 if WIN else 2)

        metrics = QFontMetrics(self.font())
        rect = self.contentsRect()
        pos = self.mapToGlobal(
            rect.topLeft()
            + QPoint(
                -metrics.width(text) // 2 + x_offset,
                -2 * self.parent().height() + y_offset,
            )
        )

        self.menu.popup(pos)

    def select_interpreter(self, path):
        """Set the given interpreter as Spyder's default, without opening any dialog."""
        # Ne positionne pas 'executable' nous-memes : MainInterpreterContainer.on_interpreter_changed
        # (deja cablee, cf. spyder/plugins/maininterpreter/container.py) le calcule et l'ecrit
        # elle-meme a partir de ces 3 options - on reste sur le meme chemin que celui emprunte par
        # les Preferences, sans dupliquer sa logique.
        self.set_conf('custom_interpreter', path, section='main_interpreter')
        self.set_conf('default', False, section='main_interpreter')
        self.set_conf('custom', True, section='main_interpreter')
'''

NEW_STDLIB_IMPORT = "import os.path as osp\n"
NEW_SPYDER_IMPORT = "from spyder.utils.icon_manager import ima\n"


def _find_method_line_range(content, class_name, method_name):
    """Renvoie (lineno, end_lineno) 1-indexes (inclus) de la methode, ou None si introuvable."""
    tree = ast.parse(content)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if (
                    isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and item.name == method_name
                ):
                    return item.lineno, item.end_lineno
    return None


def _find_last_import_line(content, predicate):
    """Renvoie le end_lineno (1-indexe) du dernier import de haut niveau verifiant predicate(node),
    ou None si aucun ne correspond."""
    tree = ast.parse(content)
    last_line = None
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)) and predicate(node):
            if last_line is None or node.end_lineno > last_line:
                last_line = node.end_lineno
    return last_line


def _replace_method(content, class_name, method_name, new_method_text):
    method_range = _find_method_line_range(content, class_name, method_name)
    if method_range is None:
        return None
    start, end = method_range
    lines = content.split("\n")
    lines[start - 1:end] = new_method_text.rstrip("\n").split("\n")
    return "\n".join(lines)


def _insert_import(content, new_import_text, predicate):
    """Insere new_import_text juste apres le dernier import de haut niveau verifiant predicate -
    classe donc le nouvel import dans la bonne section (stdlib/spyder/...) plutot que de tout
    entasser en fin de bloc."""
    last_line = _find_last_import_line(content, predicate)
    if last_line is None:
        return None
    lines = content.split("\n")
    lines[last_line:last_line] = new_import_text.rstrip("\n").split("\n")
    return "\n".join(lines)


def main():
    if len(sys.argv) != 2:
        print("Usage : patch_spyder_status_menu.py <chemin vers status.py>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    with open(path) as f:
        content = f.read()

    if "def select_interpreter(self, path):" in content:
        return  # deja applique

    new_content = _replace_method(
        content, "PythonEnvironmentStatus", "show_menu", NEW_SHOW_MENU
    )
    if new_content is None:
        print(
            f"Patch status_menu : methode PythonEnvironmentStatus.show_menu introuvable dans "
            f"{path} - Spyder a peut-etre restructure son code, patch non applique.",
            file=sys.stderr,
        )
        sys.exit(1)
    content = new_content

    # Classe chaque nouvel import dans la bonne section plutot que de les entasser en fin de bloc :
    # "import os.path as osp" apres le dernier "import X" (section stdlib), "from spyder.utils...
    # import ima" apres le dernier "from spyder.xxx import ..." (section imports locaux Spyder -
    # le "." final exclut spyder_kernels, qui a sa propre section separee dans ce fichier).
    new_content = _insert_import(
        content, NEW_STDLIB_IMPORT, lambda node: isinstance(node, ast.Import)
    )
    if new_content is None:
        print(
            f"Patch status_menu : aucun import 'import X' de haut niveau trouve dans {path} - "
            "situation inattendue, patch non applique.",
            file=sys.stderr,
        )
        sys.exit(1)
    content = new_content

    new_content = _insert_import(
        content,
        NEW_SPYDER_IMPORT,
        lambda node: (
            isinstance(node, ast.ImportFrom)
            and node.module is not None
            and node.module.startswith("spyder.")
        ),
    )
    if new_content is None:
        print(
            f"Patch status_menu : aucun import 'from spyder.xxx import ...' de haut niveau trouve "
            f"dans {path} - situation inattendue, patch non applique.",
            file=sys.stderr,
        )
        sys.exit(1)
    content = new_content

    with open(path, "w") as f:
        f.write(content)
    print(f"Patch status_menu applique : {path}")


if __name__ == "__main__":
    main()
