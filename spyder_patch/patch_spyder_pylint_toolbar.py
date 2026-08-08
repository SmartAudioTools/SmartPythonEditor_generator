#!/usr/bin/env python3
"""Patch spyder/plugins/pylint/main_widget.py : deplace le bouton "Sortie" (sortie complete de
pylint) de la barre secondaire du dock "Analyse de code" vers son menu burger (options).

Contexte : chapitre "Dock2" de CachyOS/Documentation/TODO - Spyder - cosmetique.txt ("voir dock par
dock quels boutons on peut deplacer dans le menu burger du dock"), inventaire + approbation de
l'utilisateur le 25/07/2026.

CONSTAT. Le dock a DEUX barres : la principale (choix du fichier + Demarrer l'analyse) et une barre
secondaire d'etat qui affiche la note et la date de la derniere analyse - et, tout a droite, un
bouton "Sortie" qui ouvre la sortie brute de pylint dans une fenetre. C'est une action de mise au
point, consultee rarement, dans une barre par ailleurs purement informative.

CHANGEMENT (1re passe, 25/07/2026). "Sortie" passe dans le menu burger, en TETE
(before_section=Global, donc avant les replier/deplier). Les deux etirements de la barre secondaire
sont conserves : la date reste centree, comme avant.

CHANGEMENT (2e passe, 26/07/2026). "Selectionner un fichier Python" (le bouton "parcourir") quitte
la barre principale pour le meme endroit du burger : on analyse presque toujours le fichier courant,
et le combo qui reste dans la barre garde de toute facon l'historique des fichiers analyses. La
barre principale se reduit donc au COMBO et a "Demarrer l'analyse de code".

CHANGEMENT (3e passe, 26/07/2026). La barre principale est VIDEE : le combo de choix du fichier et
"Demarrer l'analyse de code" s'en vont. Le fichier analyse est celui ouvert dans l'editeur - le
greffon Pylint le suit deja par sig_editor_focus_changed -> set_filename() - et le lancement se fait
par le bouton "Docteur" de la barre d'outils du haut (greffon spyder_code_analysis), qui rend le
bouton local redondant.
⚠ Le COMBO est MASQUE, pas supprime : il PORTE L'ETAT du panneau (get_filename() lit son texte
courant, set_filename() l'y ecrit, l'historique des fichiers analyses y vit, et sa validite pilote
l'activation de l'action). Et le hide() est indispensable, pas decoratif : un widget retire d'une
barre d'outils RESTE AFFICHE chez son parent, a l'origine du panneau - le piege des boutons orphelins,
paye le matin meme sur trois panneaux. Le filet de patch_spyder_dock_actions.py ne couvre que les
QToolButton, pas un combo.

Les actions restent CREEES et enregistrees a l'identique (self.log_action, self.browse_action) : on
ne change QUE leur emplacement.

Usage : patch_spyder_pylint_toolbar.py <chemin vers pylint/main_widget.py installe>

IDEMPOTENCE PAR BLOC. Chaque bloc porte SON marqueur et est saute si ce marqueur est deja dans le
fichier - c'est ce qui permet a la 2e passe de s'appliquer sur une installation ou la 1re est deja
en place, sans rien defaire (un marqueur global unique l'aurait rendue inoperante, piege deja paye
sur ce depot). Les blocs sont appliques DANS L'ORDRE, un bloc pouvant s'ancrer sur le resultat d'un
precedent ; chaque marqueur doit etre une chaine STABLE de son propre remplacement. Re-parse avant
ecriture, echec BRUYANT (code 1) si un bloc est introuvable ou non unique - jamais deviner.
"""
import ast
import sys

# Texte pose par le bloc 2, reutilise comme ancre par le bloc 3.
MENU_V1 = '''        self.add_item_to_menu(
            self.log_action,
            menu=options_menu,
            section=PylintWidgetOptionsMenuSections.Output,
            before_section=PylintWidgetOptionsMenuSections.Global,
        )'''

# (marqueur, ancien, nouveau), appliques DANS CET ORDRE.
PAIRS = [
    # ---- 1re passe (25/07/2026) ---------------------------------------------------------------
    # 1. Declaration de la nouvelle section du menu burger.
    (
        'Output = "output_section"',
        '''class PylintWidgetOptionsMenuSections:
    Global = "global_section"
    Section = "section_section"
    History = "history_section"''',
        '''class PylintWidgetOptionsMenuSections:
    # SmartOS (patch_spyder_pylint_toolbar.py) : section du bouton "Sortie", deplace de la barre
    # secondaire vers le menu burger.
    Output = "output_section"
    Global = "global_section"
    Section = "section_section"
    History = "history_section"''',
    ),
    # 2. Barre secondaire : retirer "Sortie", et l'ajouter en tete du menu burger.
    (
        '"Sortie" (sortie brute de pylint) quitte la',
        '''        secondary_toolbar = self.create_toolbar("secondary")
        for item in [self.ratelabel,
                     self.create_stretcher(
                         id_=PylintWidgetToolbarItems.Stretcher1),
                     self.datelabel,
                     self.create_stretcher(
                         id_=PylintWidgetToolbarItems.Stretcher2),
                     self.log_action]:''',
        '''        # SmartOS (patch_spyder_pylint_toolbar.py) : "Sortie" (sortie brute de pylint) quitte la
        # barre secondaire - purement informative : note et date de la derniere analyse - pour le
        # menu burger, en tete (before_section, donc avant les replier/deplier). Les deux
        # etirements restent : la date demeure centree comme avant.
        self.add_item_to_menu(
            self.log_action,
            menu=options_menu,
            section=PylintWidgetOptionsMenuSections.Output,
            before_section=PylintWidgetOptionsMenuSections.Global,
        )

        secondary_toolbar = self.create_toolbar("secondary")
        for item in [self.ratelabel,
                     self.create_stretcher(
                         id_=PylintWidgetToolbarItems.Stretcher1),
                     self.datelabel,
                     self.create_stretcher(
                         id_=PylintWidgetToolbarItems.Stretcher2)]:''',
    ),

    # ---- 2e passe (26/07/2026) -----------------------------------------------------------------
    # 3. Barre principale : retirer le bouton "parcourir".
    # ⚠ DEUX marqueurs : la 3e passe (bloc 5) REECRIT le commentaire pose ici, donc efface le premier.
    # Sans le second, ce bloc serait considere comme non applique a chaque relance, son ancre serait
    # introuvable, et le script echouerait alors que tout est en place.
    (
        ('"Selectionner un fichier Python" (parcourir) quitte la',
         "3e passe, 26/07/2026) : la barre principale est videe"),
        '''        toolbar = self.get_main_toolbar()
        for item in [self.filecombo, self.browse_action,
                     self.code_analysis_action]:''',
        '''        # SmartOS (2e passe, 26/07/2026) : "Selectionner un fichier Python" (parcourir) quitte la
        # barre pour le menu burger (cf. plus haut). Le combo qui reste garde l'historique des
        # fichiers analyses, et l'analyse porte presque toujours sur le fichier courant.
        toolbar = self.get_main_toolbar()
        for item in [self.filecombo,
                     self.code_analysis_action]:''',
    ),
    # 4. Menu burger : y accueillir le bouton "parcourir", sous "Sortie".
    (
        'le bouton "parcourir" retire de la barre principale',
        MENU_V1,
        MENU_V1 + '''

        # SmartOS (2e passe, 26/07/2026) : le bouton "parcourir" retire de la barre principale.
        self.add_item_to_menu(
            self.browse_action,
            menu=options_menu,
            section=PylintWidgetOptionsMenuSections.Output,
        )''',
    ),

    # ---- 3e passe (26/07/2026) -----------------------------------------------------------------
    # 5. La barre principale est VIDEE : ni le combo de choix du fichier, ni "Demarrer l'analyse".
    (
        "3e passe, 26/07/2026) : la barre principale est videe",
        '''        # SmartOS (2e passe, 26/07/2026) : "Selectionner un fichier Python" (parcourir) quitte la
        # barre pour le menu burger (cf. plus haut). Le combo qui reste garde l'historique des
        # fichiers analyses, et l'analyse porte presque toujours sur le fichier courant.
        toolbar = self.get_main_toolbar()
        for item in [self.filecombo,
                     self.code_analysis_action]:
            self.add_item_to_toolbar(
                item,
                toolbar,
                section=PylintWidgetMainToolbarSections.Main,
            )''',
        '''        # SmartOS (3e passe, 26/07/2026) : la barre principale est videe (demande de
        # l'utilisateur). Le COMBO de choix du fichier n'a plus de raison d'etre - le fichier analyse
        # est celui ouvert dans l'editeur, que le greffon Pylint suit deja par
        # sig_editor_focus_changed -> set_filename(). Et "Demarrer l'analyse de code" fait doublon
        # avec le bouton "Docteur" de la barre d'outils du haut (greffon spyder_code_analysis).
        #
        # ⚠ LE COMBO EST MASQUE, PAS SUPPRIME, et les deux raisons comptent :
        #   - il PORTE L'ETAT : get_filename() lit son texte courant, set_filename() l'y ecrit,
        #     _update_combobox_history() y tient l'historique des fichiers analyses, et sa validite
        #     pilote l'activation de l'action (filecombo.valid -> setEnabled). Le retirer casserait
        #     tout le panneau ;
        #   - un widget retire d'une barre d'outils RESTE AFFICHE chez son parent, a l'origine du
        #     panneau et a sa taille par defaut - le piege des boutons orphelins, paye le matin meme
        #     sur trois panneaux. D'ou le hide() explicite : il ne suffit pas de ne plus l'ajouter.
        #     Le filet de patch_spyder_dock_actions.py ne couvre que les QToolButton, pas un combo.
        toolbar = self.get_main_toolbar()
        self.filecombo.hide()''',
    ),

    # ---- 4e passe (26/07/2026) -----------------------------------------------------------------
    # 6. Le panneau tient sur UNE ligne : la barre de COIN (qui porte le burger) et la barre
    #    SECONDAIRE (note et date) partagent desormais une meme ligne.
    (
        "4e passe, 26/07/2026) : la barre de coin rejoint la ligne de la note",
        '''            self.add_item_to_toolbar(
                item,
                secondary_toolbar,
                section=PylintWidgetMainToolbarSections.Main,
            )''',
        '''            self.add_item_to_toolbar(
                item,
                secondary_toolbar,
                section=PylintWidgetMainToolbarSections.Main,
            )

        # SmartOS (4e passe, 26/07/2026) : la barre de coin rejoint la ligne de la note. Demande de
        # l'utilisateur : « je veux le menu burger du panneau sur la meme ligne que Evaluation
        # globale et la date ». Le panneau occupait DEUX lignes pour rien depuis que la 3e passe a
        # vide la barre principale : la premiere ne portait plus que le burger.
        #
        # ⚠ ON DEPLACE DES BARRES, PAS LEUR CONTENU, et c'est tout le point. Deux voies ont ete
        # essayees et ECHOUENT, a ne pas refaire :
        #   - deplacer le WIDGET DE COIN dans la barre secondaire par addWidget() : le widget change
        #     bien de parent, mais reste INVISIBLE meme avec un setVisible(True) explicite.
        #     addWidget() cree une QWidgetAction qui POSSEDE le widget ; l'ajouter a une seconde
        #     barre fait relacher le widget par la premiere, ce qui le masque ;
        #   - mettre la note et la date dans la barre PRINCIPALE et ne plus creer la secondaire :
        #     SPYDER NE DEMARRE PLUS (TypeError dans pixelMetric au rendu des barres d'APPLICATION).
        # Ici on ne touche ni aux QWidgetAction ni aux items : on prend les deux BARRES, objets
        # ordinaires, et on les met cote a cote dans un layout horizontal. Ajouter un widget a un
        # layout le retire automatiquement du precedent.
        #
        # ⚠ ET ON N'EN CREE MEME PAS : la ligne horizontale existe DEJA. `_main_toolbar_layout`
        # (api/widgets/main_widget.py) porte la barre principale, avec un etirement de 10000, puis la
        # barre de coin avec 1 - c'est-a-dire exactement la disposition voulue, burger colle a droite.
        # Il suffit donc d'y INSERER la barre secondaire en tete et de masquer la barre principale,
        # vide depuis la 3e passe. Deux lignes, aucun layout a construire, aucun import a ajouter.
        # (Une premiere version creait son propre QHBoxLayout et importait QHBoxLayout dans ce fichier
        # amont : meme resultat mesure, mais six lignes et un import de plus.)
        #
        # Les deux etirements de la barre secondaire sont intacts : la date reste centree.
        self._main_toolbar_layout.insertWidget(0, secondary_toolbar, stretch=10000)
        self.get_main_toolbar().setVisible(False)''',
    ),
]


def appliquer(source, path, nom, pairs):
    """Applique les blocs dans l'ordre. Renvoie (source_patchee, nb_appliques) ou (None, 0).

    Un marqueur peut etre une CHAINE ou un TUPLE de chaines ; le bloc est saute si l'une d'elles est
    presente.

    ⚠ POURQUOI UN TUPLE EST PARFOIS NECESSAIRE, defaut trouve le 26/07/2026 en relancant ce script :
    la 3e passe REECRIT le commentaire pose par la 2e, donc DETRUIT le marqueur de celle-ci. A la
    relance, le bloc de la 2e passe n'etait plus reconnu comme applique, son ancre avait disparu, et
    le script echouait en bloc - alors que tout etait en place. La regle du depot dit qu'un marqueur
    doit etre une chaine STABLE de son propre remplacement ; quand une passe ulterieure l'efface, il
    faut donc lui adjoindre le marqueur de cette passe-la.
    """
    applied = 0
    for marqueur, old, new in pairs:
        marqueurs = (marqueur,) if isinstance(marqueur, str) else marqueur
        if any(m in source for m in marqueurs):
            continue  # bloc deja en place
        n = source.count(old)
        if n != 1:
            print(f"Bloc attendu introuvable ou non unique (occurrences={n}) dans {path} - le code "
                  f"amont a peut-etre ete restructure, patch {nom} non applique. "
                  f"Bloc:\n{old[:80]}...", file=sys.stderr)
            return None, 0
        source = source.replace(old, new)
        applied += 1
    return source, applied


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers pylint/main_widget.py>", file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as error:
        print(f"main_widget.py illisible ({error}) - patch barre Analyse de code non applique.",
              file=sys.stderr)
        return 1

    patched, applied = appliquer(source, path, "barre Analyse de code", PAIRS)
    if patched is None:
        return 1
    if applied == 0:
        print("Patch barre Analyse de code : tous les blocs sont deja en place.")
        return 0

    try:
        ast.parse(patched)
    except SyntaxError as error:
        print(f"Le main_widget.py patche n'est pas du Python valide ({error}) - aucune modification "
              "ecrite.", file=sys.stderr)
        return 1

    with open(path, "w", encoding="utf-8") as f:
        f.write(patched)
    print(f"Patch barre Analyse de code applique ({applied} bloc(s)) : \"Sortie\" et le bouton "
          f"\"parcourir\" deplaces dans le menu burger ({path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
