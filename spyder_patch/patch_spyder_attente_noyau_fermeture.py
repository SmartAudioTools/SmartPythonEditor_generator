#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Spyder ferme pendant que le noyau demarre se termine proprement (ipythonconsole).

Contexte (DONE - Spyder - reste.txt, 05/10/2026). Deux defauts de l'AMONT (code identique dans
spyder-ide/spyder 6.1.5), exposes par un demarrage devenu court : on peut fermer la fenetre
avant que le premier noyau soit pret. Deux blocs, chacun avec son marqueur :

  - _smartos_attente_noyau_fermeture (comms/kernelcomm.py). KernelComm._wait attend la reponse
    du noyau en relancant un QEventLoop tant que la condition n'est pas remplie et que son
    minuteur de delai est actif. Si QApplication.quit() a deja ete demande - le noyau s'annonce
    pret PENDANT la fermeture, et handle_kernel_is_ready demande aussitot get_pythonenv_info en
    bloquant -, QEventLoop.exec() rend -1 immediatement, plus aucun evenement n'est traite, le
    minuteur ne tombe jamais : la boucle tourne a vide et le processus ne se termine pas (un
    coeur a 100 %, fenetre deja fermee ; 2 lancements sur ~35 a fermeture rapide). Le correctif
    lit le retour de exec() et rend alors la meme erreur que pour un noyau mort (RuntimeError),
    que les appelants savent deja recevoir. Les connexions posees par _wait ne sont pas
    defaites : l'application quitte.

  - _smartos_console_fermee (widgets/client.py, widgets/main_widget.py). create_new_client
    demande l'environnement de l'utilisateur de facon asynchrone, et ne lance le noyau qu'a la
    reponse (_connect_new_client_to_kernel). Si la console est fermee entre-temps, la reponse
    lance quand meme deux noyaux (celui de la console et celui mis en cache), que plus personne
    n'arrete : a la fermeture de Spyder leurs fils de lecture tournent encore quand QApplication
    est detruite, et Qt abandonne (« QThread: Destroyed while thread is still running »,
    SIGABRT : 4 fermetures rapides sur 134). Trace relevee : get_cached_kernel appele 12 ms
    APRES la fin de close_all_clients. Le correctif marque la console a sa fermeture
    (ClientWidget.close_client) et ne lui lance plus de noyau.

Inscrit dans Contournement_bugs_a_supprimer_quand_corrigés.txt (entree 51). Tests :
outils/banc_demarrage/test_attente_noyau_fermeture.py pour le premier bloc (BOUCLE sans, OK
avec) ; pour le second, des series de fermetures rapides au banc (pas de test unitaire).

Usage : patch_spyder_attente_noyau_fermeture.py <racine de spyder/plugins/ipythonconsole>
Idempotent (un marqueur par bloc), echoue bruyamment si la forme amont a change.
"""

import ast
import sys

MARQUEUR_ATTENTE = "_smartos_attente_noyau_fermeture"
ANCRE_ATTENTE = "wait_loop.exec_()"
BLOC_ATTENTE = '''            # Ajout SmartOS (_smartos_attente_noyau_fermeture) : exec() rend -1 sans tourner
            # quand l'application quitte ; sans cette sortie, la boucle ne finit jamais.
            if wait_loop.exec_() == -1:
                raise RuntimeError("Application is quitting")
'''

MARQUEUR_CONSOLE = "_smartos_console_fermee"
BLOC_CONSOLE_POSE = '''        # Ajout SmartOS (_smartos_console_fermee) : lu par
        # IPythonConsoleWidget._connect_new_client_to_kernel, qui peut arriver apres.
        self._smartos_console_fermee = True
'''
BLOC_CONSOLE_LUE = '''        # Ajout SmartOS (_smartos_console_fermee) : console fermee avant la reponse
        # asynchrone qui mene ici ; un noyau lance maintenant ne serait jamais arrete.
        if getattr(client, "_smartos_console_fermee", False):
            return
'''


def _echec(message, chemin):
    print(f"ERREUR : {message} dans {chemin} - la forme amont a change.", file=sys.stderr)
    return False


def _ecrire(chemin, resultat):
    try:
        ast.parse(resultat)
    except SyntaxError as erreur:
        print(f"ERREUR : patch invalide pour {chemin} ({erreur})", file=sys.stderr)
        return False
    open(chemin, "w", encoding="utf-8").write(resultat)
    print(f"Patche : {chemin}")
    return True


def _methodes(source, classe, nom):
    return [m for c in ast.parse(source).body if isinstance(c, ast.ClassDef) and c.name == classe
            for m in c.body if isinstance(m, ast.FunctionDef) and m.name == nom]


def patcher_kernelcomm(chemin):
    source = open(chemin, encoding="utf-8").read()
    if MARQUEUR_ATTENTE in source:
        print(f"Deja patche : {chemin}")
        return True
    lignes = source.splitlines(keepends=True)
    ancres = [n for m in _methodes(source, "KernelComm", "_wait")
              for b in m.body if isinstance(b, ast.While)
              for n in b.body if isinstance(n, ast.Expr)
              and lignes[n.lineno - 1].strip() == ANCRE_ATTENTE]
    if len(ancres) != 1:
        return _echec(f"`{ANCRE_ATTENTE}` (unique, dans la boucle while de KernelComm._wait) "
                      "est introuvable", chemin)
    ligne = ancres[0].lineno
    return _ecrire(chemin, "".join(lignes[:ligne - 1]) + BLOC_ATTENTE + "".join(lignes[ligne:]))


def _patcher_debut(chemin, classe, nom, bloc):
    """Insere `bloc` en tete du corps de classe.nom, apres sa docstring."""
    source = open(chemin, encoding="utf-8").read()
    if MARQUEUR_CONSOLE in source:
        print(f"Deja patche : {chemin}")
        return True
    lignes = source.splitlines(keepends=True)
    methodes = _methodes(source, classe, nom)
    if len(methodes) != 1 or ast.get_docstring(methodes[0]) is None:
        return _echec(f"{classe}.{nom} (unique, avec docstring) est introuvable", chemin)
    fin = methodes[0].body[0].end_lineno
    return _ecrire(chemin, "".join(lignes[:fin]) + bloc + "".join(lignes[fin:]))


def main(argv):
    if len(argv) != 2:
        print(f"Usage : {argv[0]} <racine de spyder/plugins/ipythonconsole>", file=sys.stderr)
        return 1
    racine = argv[1].rstrip("/")
    # Tous tentes, meme apres un echec : chaque message d'erreur nomme sa forme amont.
    resultats = [
        patcher_kernelcomm(f"{racine}/comms/kernelcomm.py"),
        _patcher_debut(f"{racine}/widgets/client.py", "ClientWidget", "close_client",
                       BLOC_CONSOLE_POSE),
        _patcher_debut(f"{racine}/widgets/main_widget.py", "IPythonConsoleWidget",
                       "_connect_new_client_to_kernel", BLOC_CONSOLE_LUE),
    ]
    return 0 if all(resultats) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
