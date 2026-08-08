#!/usr/bin/env python3
"""Patch spyder/app/mainwindow.py pour ramener la fenetre Spyder deja ouverte au premier plan.

Contexte (TODO CachyOS du 18/07/2026, "Pb spyder qui ne se remet pas au 1er plan si deja ouvert") :
quand Spyder tourne deja et qu'une deuxieme invocation "spyder <fichier>" est lancee, start.py
detecte le verrou (spyder.lock) et transmet l'argument a l'instance existante via un socket local
(send_args_to_spyder -> open_files_server -> signal sig_open_external_file -> slot
MainWindow.open_external_file, cf. app/mainwindow.py et app/start.py). Avant ce patch,
open_external_file() se contentait d'ouvrir le fichier dans l'editeur SANS jamais tenter de rendre
la fenetre visible - elle restait minimisee ou cachee derriere une autre fenetre (bug confirme en
direct : le fichier s'ouvrait bien dans l'editeur, mais la fenetre ne revenait jamais au premier
plan).

self.raise_()/activateWindow() seuls (essayes en premier, cf. historique de ce fichier) se sont
reveles insuffisants meme avec une regle KWin fsplevel=0/Force dediee a Spyder (verifie en direct :
toujours aucun effet visible). Cause probable : sous Wayland, la reactivation TARDIVE d'une fenetre
deja mappee passe par le protocole xdg-activation-v1, qui exige un jeton d'activation issu d'un
evenement d'entree recent - absent ici puisque l'appel vient d'un thread reveille par un signal
reseau, pas d'une interaction utilisateur. La prevention de vol de focus (fsplevel) est un mecanisme
different (mapping initial d'une fenetre), qui ne couvre pas ce cas.

Solution retenue, verifiee en direct : "kdotool" (AUR, https://github.com/jinliu/kdotool -
equivalent de xdotool pour KDE Wayland). Il passe par l'interface de scripting privilegiee de KWin
(le compositeur agit lui-meme, pas un client soumis aux restrictions xdg-activation) - confirme
fonctionnel en test manuel ("kdotool search --class spyder windowactivate" ramene bien la fenetre au
premier plan la ou raise_()/activateWindow() echouaient). Necessite le paquet AUR "kdotool" (installe
par installation_SmartPythonEditor.sh, qui applique aussi ce patch). Les appels Qt (raise_/activateWindow/alert) sont
conserves en repli pour les plateformes/environnements ou kdotool serait absent (UbuntuStudio par
exemple, qui n'utilise pas KWin).

Important : la mise au premier plan est cablee sur le SIGNAL sig_open_external_file (emis
uniquement par le serveur socket, donc uniquement quand une DEUXIEME invocation de Spyder transmet
son argument a l'instance deja lancee), PAS directement dans open_external_file() lui-meme - cette
methode est aussi appelee directement, sans signal, pour ouvrir les fichiers passes en argument au
tout PREMIER lancement (spyder/app/utils.py, create_window() : "for a in args: main.open_external_file(a)").
Un premier essai de ce patch modifiait open_external_file() directement, ce qui faisait revenir la
fenetre au premier plan une deuxieme fois, juste apres main.show(), meme au tout premier lancement -
constate en direct. D'ou l'ajout d'un slot dedie (_raise_and_open_external_file), branche a la place
de open_external_file sur ce signal precis, qui laisse open_external_file() totalement inchangee.

Localisation des points d'insertion via le module "ast" (comme patch_spyder_status_menu.py) plutot
qu'une recherche exacte de bloc de texte : retrouve la methode open_external_file() par son nom dans
la classe MainWindow (pour inserer le nouveau slot juste avant), quels que soient les
commentaires/docstring/corps exact autour - resiste donc aux changements de pure forme d'une version
de Spyder a l'autre. La ligne de connexion du signal reste elle localisee par recherche exacte de
texte (une seule occurrence attendue) : plus simple qu'un parcours ast pour un unique appel de
methode, et echoue tout aussi bruyamment si introuvable.

Idempotent : si le marqueur du patch (nom du nouveau slot) est deja present, ne fait rien.

Usage : patch_spyder_raise_window.py <chemin vers mainwindow.py installe>
"""
import ast
import sys

RAISE_WINDOW_MARKER = "_raise_and_open_external_file"

OLD_CONNECT_LINE = (
    "            self.sig_open_external_file.connect(self.open_external_file)\n"
)
NEW_CONNECT_LINE = (
    "            self.sig_open_external_file.connect(\n"
    "                self._raise_and_open_external_file)\n"
)

NEW_METHODS = '''    def _raise_and_open_external_file(self, fname):
        """
        Ramene la fenetre au premier plan puis ouvre fname (TODO CachyOS du 18/07/2026, "Pb spyder
        qui ne se remet pas au 1er plan si deja ouvert"). Cf. docstring de
        patch_spyder_raise_window.py pour le contexte complet - branchee uniquement sur le signal
        emis par le serveur socket (deuxieme invocation de Spyder), pas sur le premier lancement.
        """
        if shutil.which('kdotool'):
            try:
                subprocess.run(
                    ['kdotool', 'search', '--class', 'spyder', 'windowactivate'],
                    timeout=2, check=False,
                )
            except OSError:
                pass
        else:
            self.setWindowState(
                (self.windowState() & ~Qt.WindowMinimized) | Qt.WindowActive
            )
            self.show()
            self.raise_()
            self.activateWindow()
            QApplication.alert(self)
        self.open_external_file(fname)

'''

NEW_STDLIB_IMPORT = "import subprocess\n"


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


def _insert_before_method(content, class_name, method_name, new_text):
    method_range = _find_method_line_range(content, class_name, method_name)
    if method_range is None:
        return None
    start, _end = method_range
    lines = content.split("\n")
    lines[start - 1:start - 1] = new_text.rstrip("\n").split("\n") + [""]
    return "\n".join(lines)


def _insert_import(content, new_import_text, predicate):
    """Insere new_import_text juste apres le dernier import de haut niveau verifiant predicate."""
    last_line = _find_last_import_line(content, predicate)
    if last_line is None:
        return None
    lines = content.split("\n")
    lines[last_line:last_line] = new_import_text.rstrip("\n").split("\n")
    return "\n".join(lines)


def main():
    if len(sys.argv) != 2:
        print("Usage : patch_spyder_raise_window.py <chemin vers mainwindow.py>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    with open(path) as f:
        content = f.read()

    if RAISE_WINDOW_MARKER in content:
        return  # deja applique

    if content.count(OLD_CONNECT_LINE) != 1:
        print(
            f"Patch raise_window : ligne de connexion du signal sig_open_external_file introuvable "
            f"(ou presente plusieurs fois) dans {path} - Spyder a peut-etre restructure son code, "
            f"patch non applique.",
            file=sys.stderr,
        )
        sys.exit(1)
    content = content.replace(OLD_CONNECT_LINE, NEW_CONNECT_LINE)

    new_content = _insert_before_method(
        content, "MainWindow", "open_external_file", NEW_METHODS
    )
    if new_content is None:
        print(
            f"Patch raise_window : methode MainWindow.open_external_file introuvable dans "
            f"{path} - Spyder a peut-etre restructure son code, patch non applique.",
            file=sys.stderr,
        )
        sys.exit(1)
    content = new_content

    # "import subprocess" apres le dernier "import X" de haut niveau (section stdlib) - "shutil" est
    # deja importe par Spyder lui-meme, inutile de le rajouter.
    new_content = _insert_import(
        content, NEW_STDLIB_IMPORT, lambda node: isinstance(node, ast.Import)
    )
    if new_content is None:
        print(
            f"Patch raise_window : aucun import 'import X' de haut niveau trouve dans {path} - "
            "situation inattendue, patch non applique.",
            file=sys.stderr,
        )
        sys.exit(1)
    content = new_content

    with open(path, "w") as f:
        f.write(content)
    print(f"Patch raise_window applique : {path}")


if __name__ == "__main__":
    main()
