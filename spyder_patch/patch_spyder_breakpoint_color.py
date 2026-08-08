#!/usr/bin/env python3
"""Patch spyder/utils/icon_manager.py pour colorer les points d'arret du debogueur en BLEU, du
meme bleu que les icones de la barre d'outils de debogage.

Contexte (TODO CachyOS "TODO - Spyder - cosmetique.txt", section "Editeur de fichier", demande
explicite de l'utilisateur) : Spyder dessine les points d'arret dans la marge de l'editeur avec
l'icone QtAwesome 'breakpoint_big' (cercle plein) et 'breakpoint_cond_big' (point d'arret
conditionnel), toutes deux colorees en SpyderPalette.ICON_4 (rouge, Red.B70 = #E74C3C). Les icones
de debogage de la barre d'outils (pas-a-pas, continuer, arreter...) sont, elles, colorees en
SpyderPalette.ICON_2 (bleu, Blue.B80 = #37AEFE en theme sombre, Blue.B50 en theme clair). Ce patch
aligne la couleur des deux icones de point d'arret sur ICON_2 : le point d'arret apparait alors du
meme bleu que les icones de debogage, et suit automatiquement le theme clair/sombre actif
(contrairement a une couleur codee en dur).

2e PASSE (26/07/2026) : 'breakpoint_transparent' AUSSI, contrairement a ce que decidait la 1re.
    L'apercu au survol de la marge - le rond qui dit « cliquez ici pour en poser un » - restait sur
    COLOR_ERROR_1, donc ROUGE, alors que le point d'arret pose etait passe au bleu. La 1re passe
    l'avait laisse volontairement, au motif que ce n'est pas un point d'arret pose ; l'utilisateur a
    tranche autrement le 26/07/2026 : « le survol passe par une couleur transitoire rouge foncee, il
    faudrait plutot du bleu foncé ». Le raisonnement de la 1re passe est donc caduc, et c'est ecrit
    ici plutot que supprime : la decision a change, pas les faits.

    L'OPACITE PASSE DE 0,75 A 0,55, et ce n'est pas un detail de gout. Ce qui fait lire l'apercu comme
    « pas encore pose », c'est qu'il est nettement plus SOMBRE que le point d'arret. Le rouge a 0,75
    donnait une luminance de 55 contre 154 pour le point pose : l'ecart etait considerable. Le meme
    bleu a 0,75 remonte a 125, trop proche des 154 du point pose - on confondrait les deux. A 0,55 il
    vaut 101, ce qui conserve la hierarchie tout en restant franchement bleu.
    ⚠ Ces valeurs sont MESUREES, pas choisies : luminance perceptuelle du centre du rond, rendu par Qt
    puis composite sur le fond reel de la marge (#232627). Trois candidats ont ete rendus a la taille
    reelle et soumis a l'utilisateur, qui a choisi celui-ci. Re-mesurer si Spyder change ICON_2 ou la
    couleur de fond de la marge - le bon ecart depend d'ELLES, pas d'un gout.

Usage : patch_spyder_breakpoint_color.py <chemin vers icon_manager.py installe>

Localisation par ancrage de texte EXACT sur les deux lignes de definition d'icone (reperees par
leur cle 'breakpoint_big' / 'breakpoint_cond_big'), et non par le module ast : ces icones sont des
entrees d'un dictionnaire litteral, pas des methodes/classes. On ne remplace que la constante de
couleur ICON_4 -> ICON_2 sur ces deux lignes precises. Idempotent (si deja ICON_2, ne fait rien).
Echoue BRUYAMMENT (code de sortie 1) si une cle attendue est absente ou si sa ligne ne contient ni
ICON_4 ni ICON_2 (structure changee dans une nouvelle version de Spyder), plutot que de deviner.
"""
import sys

# Cle d'icone -> substitutions a appliquer sur SA ligne, et temoin disant que c'est deja fait.
# Le temoin est indispensable et doit etre PROPRE A LA CLE : chercher simplement ICON_2 dans la ligne
# de 'breakpoint_transparent' suffirait a la croire traitee alors que son opacite serait encore a
# 0,75 - et la 2e passe ne s'appliquerait jamais sur une machine ou la 1re est deja passee.
SUBSTITUTIONS = {
    # 1re passe : le point d'arret pose, et sa variante conditionnelle, du rouge au bleu.
    "'breakpoint_big':": {
        "temoin": "SpyderPalette.ICON_2",
        "remplacements": (("SpyderPalette.ICON_4", "SpyderPalette.ICON_2"),),
    },
    "'breakpoint_cond_big':": {
        "temoin": "SpyderPalette.ICON_2",
        "remplacements": (("SpyderPalette.ICON_4", "SpyderPalette.ICON_2"),),
    },
    # 2e passe : l'apercu au survol, du rouge sombre au bleu sombre. Les DEUX remplacements comptent -
    # la couleur ET l'opacite, cf. l'en-tete pour les luminances mesurees.
    "'breakpoint_transparent':": {
        "temoin": "'opacity': 0.55",
        "remplacements": (("SpyderPalette.COLOR_ERROR_1", "SpyderPalette.ICON_2"),
                          ("'opacity': 0.75", "'opacity': 0.55")),
    },
}


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers icon_manager.py>", file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines(keepends=True)
    except OSError as error:
        print(f"icon_manager.py illisible ({error}) - patch points d'arret non applique.",
              file=sys.stderr)
        return 1

    modifiees = []
    for cle, consigne in SUBSTITUTIONS.items():
        trouvee = False
        for i, ligne in enumerate(lines):
            if cle not in ligne:
                continue
            trouvee = True
            if consigne["temoin"] in ligne:
                break  # deja traitee
            manquants = [ancien for ancien, _ in consigne["remplacements"] if ancien not in ligne]
            if manquants:
                print(f"Patch points d'arret : la ligne de {cle} ne contient pas "
                      f"{', '.join(manquants)} dans {path} - structure changee dans une nouvelle "
                      "version de Spyder, patch non applique.", file=sys.stderr)
                return 1
            for ancien, nouveau in consigne["remplacements"]:
                ligne = ligne.replace(ancien, nouveau)
            lines[i] = ligne
            modifiees.append(cle.strip(":'"))
            break
        if not trouvee:
            print(f"Patch points d'arret : cle {cle} introuvable dans {path} - Spyder a "
                  "peut-etre renomme cette icone, patch non applique.", file=sys.stderr)
            return 1

    if modifiees:
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        print(f"Patch points d'arret applique ({', '.join(modifiees)}) : points d'arret et apercu "
              f"au survol en bleu dans {path}")
    else:
        print("Patch points d'arret Spyder deja applique (tout est deja en bleu).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
