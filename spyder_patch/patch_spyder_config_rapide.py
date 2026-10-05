#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rend la configuration de Spyder moins chere a lire et a ecrire (spyder/config/user.py).

Contexte (TODO - Spyder - accélération démarage.txt, 05/10/2026) : le profil d'un lancement
complet (cProfile, banc hors ecran, configuration existante) montre deux postes que rien ne
laissait attendre dans un module de configuration :

  1. LECTURE - UserConfig.get() repasse la valeur lue par ast.literal_eval a CHAQUE appel :
     2334 analyses au demarrage, soit 2403 builtins.compile (0,20 s) et 250 000 noeuds
     convertis (0,16 s), alors que les memes chaines reviennent sans cesse.
     -> les analyses sont memorisees par chaine. Une valeur immuable est rendue telle quelle,
        un conteneur (liste, dict, tuple, ensemble) est RECOPIE a chaque lecture : l'appelant
        recoit, comme avant, un objet neuf qu'il peut modifier sans toucher au cache.

  2. ECRITURE - UserConfig.set() reecrit le fichier .ini ENTIER a chaque option posee : 447
     ecritures completes au demarrage (0,36 s).
     -> les ecritures sont regroupees : la premiere arme une minuterie de 300 ms, les suivantes
        ne font rien tant qu'elle court, et le fichier est ecrit UNE fois a l'echeance. Tout ce
        qui est en attente est ecrit a la fermeture (aboutToQuit) et, en dernier filet, a la
        sortie de l'interpreteur (atexit). Sans QApplication, ou hors du fil principal, rien
        ne change : ecriture immediate, comme en amont.
        Deux gardes, issues de la relecture du 05/10/2026 : une configuration dont le dossier
        a ete supprime avant l'echeance n'est pas ecrite (projet efface), et cleanup(), qui
        efface le .ini, retire d'abord l'ecriture en attente (elle le recreerait).
        Ce qui est accepte : un arret brutal (SIGKILL, plantage natif) peut perdre les
        reglages poses dans les 300 dernieres millisecondes.

Deux blocs, deux marqueurs, chacun idempotent et independant. Echec bruyant si la forme amont
a change.

Usage : patch_spyder_config_rapide.py <spyder/config/user.py>
"""

import ast
import sys

MARQUEUR_LECTURE = "_smartos_config_lecture_memo"
MARQUEUR_ECRITURE = "_smartos_config_ecriture_groupee"

APPEL_AMONT = "ast.literal_eval(value)"
APPEL_SMARTOS = "_smartos_literal_eval(value)"

BLOC_LECTURE = '''

# ---- SmartOS (_smartos_config_lecture_memo) : analyses de valeurs memorisees --------------------
# get() analysait la meme chaine a chaque lecture d'option. Voir
# spyder_patch/patch_spyder_config_rapide.py du generator.
_SMARTOS_LITERAL_CACHE = {}
_SMARTOS_IMMUABLES = (str, bytes, int, float, complex, bool, type(None), type(Ellipsis))


def _smartos_copie(valeur):
    """Copie d'un resultat de literal_eval (conteneurs de litteraux seulement)."""
    genre = type(valeur)
    if genre in _SMARTOS_IMMUABLES:
        return valeur
    if genre is list:
        return [_smartos_copie(element) for element in valeur]
    if genre is dict:
        return {_smartos_copie(cle): _smartos_copie(element)
                for cle, element in valeur.items()}
    if genre is tuple:
        return tuple(_smartos_copie(element) for element in valeur)
    if genre is set:
        return {_smartos_copie(element) for element in valeur}
    return copy.deepcopy(valeur)


def _smartos_literal_eval(value):
    """ast.literal_eval memorise par chaine ; les erreurs ne sont pas memorisees."""
    if type(value) is not str:
        return ast.literal_eval(value)
    try:
        resultat = _SMARTOS_LITERAL_CACHE[value]
    except KeyError:
        resultat = ast.literal_eval(value)
        if len(_SMARTOS_LITERAL_CACHE) > 4096:
            _SMARTOS_LITERAL_CACHE.clear()
        _SMARTOS_LITERAL_CACHE[value] = resultat
    return _smartos_copie(resultat)
'''

BLOC_ECRITURE = '''

# ---- SmartOS (_smartos_config_ecriture_groupee) : ecritures du .ini regroupees ------------------
# set() reecrivait le fichier entier a chaque option : 447 fois au demarrage. Voir
# spyder_patch/patch_spyder_config_rapide.py du generator.
_SMARTOS_DELAI_ECRITURE_MS = 300
_smartos_save_immediat = DefaultsConfig._save
_smartos_en_attente = {}  # id(config) -> config dont le fichier reste a ecrire
_smartos_minuterie = []   # la QTimer unique, creee a la premiere ecriture differee


def _smartos_ecrire_en_attente():
    """Ecrit tout ce qui attend (echeance de la minuterie, fermeture, sortie)."""
    while _smartos_en_attente:
        _, config = _smartos_en_attente.popitem()
        # Dossier supprime entre-temps (projet efface juste apres sa fermeture) : l'amont
        # aurait ecrit AVANT la suppression ; ecrire apres echouerait, avec une pause de 50 ms.
        if osp.isdir(osp.dirname(config.get_config_fpath())):
            _smartos_save_immediat(config)


def _smartos_save_groupe(self):
    import sys

    QtCore = sys.modules.get("qtpy.QtCore")
    application = QtCore.QCoreApplication.instance() if QtCore is not None else None
    try:
        differable = (application is not None
                      and QtCore.QThread.currentThread() is application.thread())
        if differable and not _smartos_minuterie:
            import atexit

            minuterie = QtCore.QTimer(application)
            minuterie.setSingleShot(True)
            minuterie.setInterval(_SMARTOS_DELAI_ECRITURE_MS)
            minuterie.timeout.connect(_smartos_ecrire_en_attente)
            application.aboutToQuit.connect(_smartos_ecrire_en_attente)
            atexit.register(_smartos_ecrire_en_attente)
            _smartos_minuterie.append(minuterie)
        if differable:
            _smartos_en_attente[id(self)] = self
            if not _smartos_minuterie[0].isActive():
                _smartos_minuterie[0].start()
            return
    except Exception:
        # Au moindre doute (Qt en cours de destruction...), on ecrit tout de suite.
        pass
    _smartos_en_attente.pop(id(self), None)
    _smartos_save_immediat(self)


DefaultsConfig._save = _smartos_save_groupe

# cleanup() efface le .ini : une ecriture encore en attente le recreerait avec l'ancien contenu.
_smartos_cleanup_amont = UserConfig.cleanup
_smartos_cleanup_multi_amont = MultiUserConfig.cleanup


def _smartos_cleanup(self):
    _smartos_en_attente.pop(id(self), None)
    return _smartos_cleanup_amont(self)


def _smartos_cleanup_multi(self):
    for config in self._configs_map.values():
        _smartos_en_attente.pop(id(config), None)
    return _smartos_cleanup_multi_amont(self)


UserConfig.cleanup = _smartos_cleanup
MultiUserConfig.cleanup = _smartos_cleanup_multi
'''


def patcher(chemin):
    source = open(chemin, encoding="utf-8").read()
    resultat = source

    if MARQUEUR_LECTURE in resultat:
        print(f"Deja patche (lecture) : {chemin}")
    else:
        arbre = ast.parse(resultat)
        imports = [noeud for noeud in arbre.body
                   if isinstance(noeud, (ast.Import, ast.ImportFrom))]
        noms = {alias.asname or alias.name for noeud in imports
                if isinstance(noeud, ast.Import) for alias in noeud.names}
        if not {"ast", "copy"} <= noms or APPEL_AMONT not in resultat:
            print(f"ERREUR : `import ast`, `import copy` ou `{APPEL_AMONT}` introuvable dans "
                  f"{chemin} - la forme amont a change.", file=sys.stderr)
            return False
        lignes = resultat.splitlines(keepends=True)
        fin_imports = imports[-1].end_lineno
        resultat = ("".join(lignes[:fin_imports]) + BLOC_LECTURE
                    + "".join(lignes[fin_imports:]).replace(APPEL_AMONT, APPEL_SMARTOS))
        print(f"Patche (lecture) : {chemin}")

    if MARQUEUR_ECRITURE in resultat:
        print(f"Deja patche (ecriture) : {chemin}")
    else:
        classes = {noeud.name: noeud for noeud in ast.parse(resultat).body
                   if isinstance(noeud, ast.ClassDef)}
        defaults = classes.get("DefaultsConfig")
        surcharges = [nom for nom, classe in classes.items() if nom != "DefaultsConfig"
                      and any(isinstance(n, ast.FunctionDef) and n.name == "_save"
                              for n in classe.body)]
        def a_methode(nom_classe, nom):
            return nom_classe in classes and any(
                isinstance(n, ast.FunctionDef) and n.name == nom
                for n in classes[nom_classe].body)

        if (defaults is None or surcharges or not a_methode("DefaultsConfig", "_save")
                or not a_methode("UserConfig", "cleanup")
                or not a_methode("MultiUserConfig", "cleanup")
                or "import os.path as osp" not in resultat):
            print(f"ERREUR : DefaultsConfig._save ou cleanup() introuvable, `osp` absent, "
                  f"ou _save surchargee par {surcharges} "
                  f"dans {chemin} - la forme amont a change.", file=sys.stderr)
            return False
        resultat = resultat.rstrip("\n") + "\n" + BLOC_ECRITURE
        print(f"Patche (ecriture) : {chemin}")

    if resultat != source:
        try:
            ast.parse(resultat)
        except SyntaxError as erreur:
            print(f"ERREUR : patch invalide pour {chemin} ({erreur})", file=sys.stderr)
            return False
        open(chemin, "w", encoding="utf-8").write(resultat)
    return True


def main(argv):
    if len(argv) != 2:
        print(f"Usage : {argv[0]} <spyder/config/user.py>", file=sys.stderr)
        return 1
    return 0 if patcher(argv[1]) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
