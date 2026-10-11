#!/usr/bin/env python3
"""Patch spyder/utils/icon_manager.py : croix de fermeture plus fines.

Contexte (demande de l'utilisateur, 11/10/2026) : « les croix pour fermer des fenetre / onglets
doivent etre plus fines ».

CE QUI EST PATCHE : les cles d'icone qui portent une croix de fermeture, et seulement leur glyphe
(couleur et taille inchangees) :
  - 'fileclose' (croix de chaque onglet - CloseTabButton de spyder/widgets/tabs.py -, bouton de
    coin des onglets, editeur de raccourcis), 'DialogCloseButton' (barre de recherche, filtres des
    tableaux), 'close_pane' (entree « Fermer » du menu de chaque volet) et 'tour.close' (visite
    guidee) : 'mdi.close' / 'mdi.window-close' (Material Design, traits d'environ 2 px a 16 px)
    -> 'ph.x-light' (Phosphor, livre par qtawesome, trait d'environ 1 px) ;
  - 'close_panel' (bouton « fermer ce volet » d'un editeur scinde, pose par
    patch_spyder_editor_split_buttons.py) : 'mdi.close-box-outline' -> 'ph.x-square-light', le
    meme carre barre en trait fin.
'tour.close' est change par coherence : la visite guidee est rarement ouverte, mais une croix
epaisse y detonnerait.

ECARTES, rendus compares a 16 px (taille de CloseTabButton) avant de choisir :
  - 'ph.x-thin' : plus fin encore, mais pale et baveux a 16 px, il se lit mal sur le fond sombre ;
  - 'msc.close' (codicons de VS Code) : a peine plus fin que l'original ;
  - un SVG maison dans spyder/images/ : un fichier de plus a deployer, pour un glyphe qui existe.
Hors perimetre : la barre de titre d'un volet n'a pas de croix (son bouton porte un cadenas,
'lock_open'), et la croix d'une fenetre flottante est dessinee par la decoration KWin. Aucun autre
correctif ne reecrit ces lignes d'icon_manager.py (verifie par grep le 11/10/2026).

Usage : patch_spyder_croix_fines.py <chemin vers icon_manager.py installe>
Ancrage par texte sur la ligne de chaque cle (entrees d'un dictionnaire litteral, pas de classe ni
de methode a viser par ast), idempotent par cle (ligne portant deja le glyphe fin), echec BRUYANT si une
cle manque, est en double, ou si sa ligne ne porte plus le glyphe d'origine.
"""
import sys

# Cle d'icone -> (glyphe d'origine, glyphe fin).
REMPLACEMENTS = {
    "'fileclose':": ("('mdi.close',)", "('ph.x-light',)"),
    "'DialogCloseButton':": ("('mdi.close',)", "('ph.x-light',)"),
    "'close_pane':": ("('mdi.window-close',)", "('ph.x-light',)"),
    "'tour.close':": ("('mdi.close',)", "('ph.x-light',)"),
    "'close_panel':": ("('mdi.close-box-outline',)", "('ph.x-square-light',)"),
}


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers icon_manager.py>", file=sys.stderr)
        return 1
    path = sys.argv[1]
    with open(path, encoding="utf-8") as flux:
        lignes = flux.read().splitlines(keepends=True)
    modifiees = 0
    for cle, (ancien, nouveau) in REMPLACEMENTS.items():
        indices = [i for i, ligne in enumerate(lignes) if cle in ligne]
        if len(indices) != 1:
            print(f"icon_manager.py : cle {cle} trouvee {len(indices)} fois - patch croix fines "
                  "abandonne. Structure du fichier changee ?", file=sys.stderr)
            return 1
        i = indices[0]
        if nouveau in lignes[i]:
            continue
        if ancien not in lignes[i]:
            print(f"icon_manager.py : la ligne de {cle} ne porte plus {ancien} - patch croix fines "
                  "abandonne.", file=sys.stderr)
            return 1
        lignes[i] = lignes[i].replace(ancien, nouveau)
        modifiees += 1
    if modifiees:
        with open(path, "w", encoding="utf-8") as flux:
            flux.write("".join(lignes))
        print("icon_manager.py : croix fines appliquees.")
    else:
        print("icon_manager.py : croix fines deja appliquees.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
