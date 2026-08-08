#!/usr/bin/env python3
"""Patch codeeditor/lsp_mixin.py : les marques de pylint ne sont plus effacees, donc plus decalees.

Demande de l'utilisateur du 26/07/2026 : « j'aimerai que lors du decalage de ligne les remarques
restent ancrees sur la bonne ligne de code. »

CE QUE J'AI VERIFIE AVANT D'ECRIRE UNE LIGNE, et qui a rendu ce patch minuscule. Tout l'affichage des
remarques d'analyse lit `data.code_analysis`, c'est-a-dire la liste portee par le BLOC DE TEXTE :
    la marge ................ linenumber.py, paintEvent -> data.code_analysis
    la barre de defilement .. scrollflag.py -> data.code_analysis
    l'infobulle au survol ... codeeditor.py, show_code_analysis_results(ligne, block_data)
    la navigation ........... codeeditor.py, go_to_next_warning -> data.code_analysis
AUCUNE de ces quatre ne consulte un numero de ligne. La liste `self._diagnostics` ne sert QU'UNE fois,
en entree, pour remplir les blocs.

⇒ L'ANCRAGE N'EST DONC PAS A CONSTRUIRE : IL EXISTE DEJA. Qt deplace le bloc avec sa ligne, et ce qui
est accroche au bloc suit - c'est exactement ainsi que les points d'arret et les signets restent en
place quand on insere des lignes au-dessus. Le decalage a une seule cause : `cleanup_code_analysis()`
VIDE tous les blocs a chaque publication du serveur, et `_process_code_analysis()` les reremplit a
partir de numeros de ligne devenus faux.

CE QUE FAIT LE PATCH. Une expression, dans ce vidage : ne retirer que les marques que le serveur va
republier, et laisser les notres - celles de source « pylint », posees par le greffon
spyder_code_analysis (ex-spyder_code_analysis, scinde le 08/08/2026) depuis les resultats du panneau « Analyse de code ». N'etant plus jamais
repositionnees, elles ne peuvent plus etre decalees.

Deux itineraires ont ete essayes puis abandonnes, et il vaut la peine de dire pourquoi :
  - un champ separe sur BlockUserData plus une boucle de reinjection apres le vidage : inutile, le
    champ existant fait deja l'affaire, et la boucle etait du travail en double ;
  - reajuster les numeros de ligne de nos diagnostics a chaque modification du document, comme le
    font les clients LSP : beaucoup plus de code, et faux des qu'une modification est complexe.
La lecon, payee trois fois dans la journee : chercher le mecanisme que Spyder emploie DEJA avant
d'en inventer un.

⚠ INVARIANT DONT CE PATCH DEPEND : le serveur de langage ne doit PAS emettre de diagnostics de source
« pylint ». Sinon ses marques, preservees elles aussi, s'accumuleraient - et surtout elles seraient
mal ancrees, puisqu'elles portent des numeros de ligne figes. C'est pourquoi le greffon pylint de
pylsp reste ETEINT (l'activation posee plus tot le 26/07/2026 par
patch_spyder_pylint_dans_la_marge.py a ete retiree des installation_SmartPythonEditor.sh pour cette raison
precise). Filet de securite : le greffon SmartOS efface toutes les marques de source « pylint » avant
d'en poser de nouvelles, donc une accumulation eventuelle serait bornee a une analyse.

⚠ POURQUOI LA SOURCE EST EXACTEMENT « pylint » ET PAS UN NOM A NOUS : Spyder traite ce nom
specialement a l'affichage - `show_code_analysis_results()` retire le prefixe « [nom-du-symbole] »
des messages de pylint. Un autre nom donnerait des infobulles plus verbeuses.

Usage : patch_spyder_marques_pylint_ancrees.py <chemin vers codeeditor/lsp_mixin.py installe>

IDEMPOTENCE : bloc saute si son marqueur est deja present. Ancrage sur un motif UNIQUE, ast.parse
avant ecriture, echec BRUYANT (code 1) si l'ancre manque ou n'est pas unique.
"""
import ast
import sys

MARQUEUR = "[SmartOS marques-pylint-ancrees]"

ANCIEN = """        for data in self.blockuserdata_list():
            data.code_analysis = []"""

NOUVEAU = """        for data in self.blockuserdata_list():
            # PATCH SmartOS %s (26/07/2026) : on ne retire que
            # les marques que le serveur de langage va republier, et on LAISSE celles de pylint,
            # posees par le greffon spyder_code_analysis depuis les resultats du panneau
            # « Analyse de code ».
            #
            # POURQUOI CELA SUFFIT A LES ANCRER : tout l'affichage (marge, barre de defilement,
            # infobulle au survol, navigation d'un avertissement au suivant) lit `data.code_analysis`,
            # c'est-a-dire la liste portee par le BLOC DE TEXTE - jamais un numero de ligne. Qt
            # deplace le bloc avec sa ligne, comme il le fait pour les points d'arret. Le decalage
            # venait uniquement de ce vidage suivi d'un remplissage a partir de numeros de ligne
            # devenus faux ; ce qui n'est plus repositionne ne peut plus etre decale.
            #
            # ⚠ Depend d'un invariant : le serveur ne doit pas emettre de diagnostics de source
            # « pylint » (le greffon pylint de pylsp reste eteint). Cf.
            # Commun/scripts/patch_spyder_marques_pylint_ancrees.py.
            data.code_analysis = [
                marque for marque in data.code_analysis if marque[0] == "pylint"
            ]""" % MARQUEUR


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers codeeditor/lsp_mixin.py>", file=sys.stderr)
        return 1

    chemin = sys.argv[1]
    try:
        with open(chemin, encoding="utf-8") as f:
            source = f.read()
    except OSError as erreur:
        print(f"lsp_mixin.py illisible ({erreur}) - patch marques ancrees non applique.",
              file=sys.stderr)
        return 1

    if MARQUEUR in source:
        print("Patch marques pylint ancrees : deja en place.")
        return 0

    n = source.count(ANCIEN)
    if n != 1:
        print(f"Ancre introuvable ou non unique (occurrences={n}) dans {chemin} - "
              f"cleanup_code_analysis() a peut-etre change, patch marques ancrees non applique.",
              file=sys.stderr)
        return 1

    patchee = source.replace(ANCIEN, NOUVEAU, 1)
    try:
        ast.parse(patchee)
    except SyntaxError as erreur:
        print(f"Le lsp_mixin.py patche n'est pas du Python valide ({erreur}) - aucune modification "
              "ecrite.", file=sys.stderr)
        return 1

    with open(chemin, "w", encoding="utf-8") as f:
        f.write(patchee)
    print(f"Patch marques pylint ancrees applique : les remarques de pylint survivent aux "
          f"publications du serveur, donc suivent leur ligne ({chemin})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
