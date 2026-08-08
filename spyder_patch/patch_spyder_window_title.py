#!/usr/bin/env python3
"""Patch spyder/app/mainwindow.py pour afficher le chemin du fichier actif dans le titre de la
fenetre, sous la forme "Spyder - /chemin/du/fichier.py".

Contexte (demande explicite de l'utilisateur, 20/07/2026) : Spyder affiche le chemin du fichier
courant dans une barre dediee juste au-dessus des onglets de l'editeur, ce qui coute une ligne
entiere de hauteur pour une information qui a sa place dans la barre de titre. La barre en question
se masque sans patch, par l'option Spyder "editor/show_filename_toolbar" (reglee a False dans
Commun/config_files/spyder_<version>/spyder.ini) - ce script ne s'occupe donc QUE du titre.

Le titre par defaut de Spyder ("Spyder (Python 3.12)", eventuellement prefixe du projet actif) est
conserve tant qu'aucun fichier n'est ouvert ; des qu'il y en a un, il est remplace par
"Spyder - <chemin>", strictement la forme demandee.

⚠ Consequence a ne pas perdre de vue : la regle KWin qui impose le schema de couleurs de la barre
de titre (cf. Commun/scripts/spyder_titlebar_colorscheme.py) filtrait sur le titre de la fenetre
("Spyder (Python X.Y)"). Ce titre disparaissant des qu'un fichier est ouvert, installation_SmartPythonEditor.sh ne
genere plus de condition "title=" : la regle ne s'appuie plus que sur la classe de fenetre
(wmclass=Spyder), qui, elle, ne depend pas du contenu de l'editeur.

Mise a jour du titre : la premiere execution de set_window_title() (appelee par le main window une
fois tous les plugins enregistres) branche le signal "sig_editor_focus_changed" du plugin Editor
sur set_window_title elle-meme. Ce signal est emis a chaque changement de focus d'editeur, donc a
chaque changement d'onglet et a chaque ouverture de fichier - inutile d'aller brancher quoi que ce
soit dans l'editeur lui-meme. Le branchement est garde par un attribut pour ne pas s'empiler a
chaque appel, et il n'y a pas de risque de recursion (on ne reemet aucun signal).

Usage : patch_spyder_window_title.py <chemin vers mainwindow.py installe>

Localisation du point d'insertion via le module "ast" (structure du code, pas texte brut) : retrouve
set_window_title() par son nom dans la classe MainWindow, quels que soient les commentaires, blancs
ou l'ordre des methodes autour. Le patch AJOUTE des instructions a la fin de la methode au lieu de
la remplacer : toute la logique de Spyder (mode DEV, mode debug, option --window-title, prefixe du
projet actif) est conservee et reste visible tant qu'aucun fichier n'est ouvert. Echoue BRUYAMMENT
(code de sortie 1) si la methode n'est pas trouvee comme attendu, plutot que de deviner.

Idempotent : si le marqueur du patch ("_smartos_title_connected") est deja present, ne fait rien.
"""
import ast
import sys

MARKER = '_smartos_title_connected'

TITLE_PATCH = '''
        # Chemin du fichier actif dans le titre de la fenetre (ajout SmartOS, cf.
        # Commun/scripts/patch_spyder_window_title.py) - remplace la barre de chemin au-dessus des
        # onglets, masquee par l'option "editor/show_filename_toolbar".
        editor = self.get_plugin(Plugins.Editor, error=False)
        if editor is not None:
            if not getattr(self, '_smartos_title_connected', False):
                # Reappelle set_window_title a chaque changement d'onglet / ouverture de fichier.
                editor.sig_editor_focus_changed.connect(self.set_window_title)
                self._smartos_title_connected = True

            filename = editor.get_current_filename()
            if filename:
                self.base_title = u'Spyder - {}'.format(filename)
                self.setWindowTitle(self.base_title)
'''


def find_method(tree, class_name, method_name):
    """Retourne le noeud AST de <class_name>.<method_name>, ou None."""
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for sub in node.body:
                if isinstance(sub, ast.FunctionDef) and sub.name == method_name:
                    return sub
    return None


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers mainwindow.py>", file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        with open(path, encoding='utf-8') as f:
            source = f.read()
    except OSError as error:
        print(f"mainwindow.py illisible ({error}) - patch du titre non applique.", file=sys.stderr)
        return 1

    if MARKER in source:
        print("Patch du titre de fenetre Spyder deja applique.")
        return 0

    tree = ast.parse(source)
    method = find_method(tree, 'MainWindow', 'set_window_title')
    if method is None:
        print("MainWindow.set_window_title introuvable dans mainwindow.py - patch du titre "
              "abandonne.", file=sys.stderr)
        return 1

    lines = source.splitlines(keepends=True)
    lines.insert(method.body[-1].end_lineno, TITLE_PATCH)
    patched = ''.join(lines)

    # Filet de securite : ne jamais ecrire un fichier que Python ne sait plus lire.
    try:
        ast.parse(patched)
    except SyntaxError as error:
        print(f"Le mainwindow.py patche n'est pas du Python valide ({error}) - aucune "
              "modification ecrite.", file=sys.stderr)
        return 1

    with open(path, 'w', encoding='utf-8') as f:
        f.write(patched)

    print("Patch du titre de fenetre Spyder applique (chemin du fichier actif dans le titre).")
    return 0


if __name__ == '__main__':
    sys.exit(main())
