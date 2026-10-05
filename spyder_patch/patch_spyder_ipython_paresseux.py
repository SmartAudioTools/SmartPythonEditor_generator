#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Le terminal interactif d'IPython n'est charge qu'a son premier usage reel (mainwindow.py).

Contexte (TODO - Spyder - accélération démarage.txt, etape 8, 05/10/2026). Dans le processus de
l'interface, Spyder et qtconsole n'utilisent d'IPython que des sous-modules de IPython.core et
IPython.lib (history, inputtransformer2, release, latextools, et interactiveshell pour le type
d'un trait de l'historique du debogueur). Mais importer un sous-module execute d'abord
IPython/__init__.py, qui charge en plus tout le terminal interactif (IPython.terminal.embed,
prompt_toolkit, jedi...) : 539 modules et ~185 ms mesures seuls, contre 213 modules et ~70 ms
pour ce que l'interface utilise.

Le correctif pose dans sys.modules, avant le premier import, un module « IPython » qui a son
vrai __spec__ et son vrai __path__ (les sous-modules s'importent donc normalement) et dont
l'initialisation reelle (l'execution de IPython/__init__.py, dans ce meme module) est repoussee
au premier acces a un attribut qu'il n'a pas encore : IPython.InteractiveShell, IPython.embed,
IPython.start_ipython... A partir de la, c'est le paquet complet.

Quatre attributs sont servis SANS initialisation, exactement comme IPython/__init__.py les
definit : get_ipython (IPython.core.getipython), release, __version__ et version_info
(IPython.core.release). get_ipython est indispensable : les modules de IPython.core font
`from IPython import get_ipython` PENDANT leur propre import, et lancer l'initialisation a ce
moment-la cree un import circulaire (constate : « cannot import name 'Magics' from partially
initialized module »). Les noms en __x__ que le paquet ne definit pas (__wrapped__, sonde par
inspect) rendent AttributeError sans rien charger.

Garde de version : le mecanisme suppose que les modules de IPython.core ne demandent au paquet
que get_ipython pendant leur import. C'est verifie pour les versions de VERSIONS_VERIFIEES ;
pour toute autre, le bloc ne fait rien (IPython s'importe normalement, le gain est perdu). A
chaque montee de version d'IPython : `grep -rn "^from IPython import" IPython/core IPython/utils
IPython/lib` ne doit lister que get_ipython, puis ajouter la version ici.

Le noyau n'est pas concerne (autre processus, qui n'importe pas spyder.app.mainwindow). Rien
n'est ecrit dans le venv. Si IPython est deja importe, ou introuvable, le bloc ne fait rien.

Usage : patch_spyder_ipython_paresseux.py <spyder/app/mainwindow.py>
Idempotent (marqueur _smartos_ipython_paresseux), echoue bruyamment si la forme amont a change.
"""

import ast
import sys

MARQUEUR = "_smartos_ipython_paresseux"
ANCRE = "requirements.check_qt()"

BLOC = '''

# ---- SmartOS (_smartos_ipython_paresseux) : IPython/__init__.py execute au premier usage -------
# L'interface n'utilise que des sous-modules de IPython.core ; l'__init__ du paquet charge en plus
# tout le terminal interactif (prompt_toolkit, jedi : ~115 ms). Voir
# spyder_patch/patch_spyder_ipython_paresseux.py du generator.
def _smartos_ipython_paresseux():
    if "IPython" in sys.modules:
        return
    import importlib
    import importlib.util
    import threading
    import types

    # (majeure, mineure) pour lesquelles il est verifie que les modules de IPython.core ne
    # demandent au paquet que get_ipython pendant leur import.
    VERSIONS_VERIFIEES = {(9, 15)}
    # Servis sans initialiser le paquet, comme IPython/__init__.py les definit.
    LEGERS = {
        "get_ipython": ("IPython.core.getipython", "get_ipython"),
        "release": ("IPython.core.release", None),
        "__version__": ("IPython.core.release", "version"),
        "version_info": ("IPython.core.release", "version_info"),
    }
    DU_PAQUET = {"__all__", "__author__", "__license__", "__patched_cves__"}

    try:
        spec = importlib.util.find_spec("IPython")
    except (ImportError, ValueError):
        return
    if spec is None or spec.loader is None or not spec.submodule_search_locations:
        return

    verrou = threading.RLock()

    class _IPythonParesseux(types.ModuleType):
        def __getattr__(self, nom):
            # Appele seulement pour un attribut absent du module.
            if nom in LEGERS:
                origine, attribut = LEGERS[nom]
                valeur = importlib.import_module(origine)
                if attribut is not None:
                    valeur = getattr(valeur, attribut)
                self.__dict__[nom] = valeur
                return valeur
            if nom.startswith("__") and nom not in DU_PAQUET:
                raise AttributeError(f"module 'IPython' has no attribute '{nom}'")
            # Premier usage reel du paquet : son __init__ s'execute dans ce meme module.
            with verrou:
                etat = self.__dict__
                if etat.get("_smartos_etat") is None:
                    etat["_smartos_etat"] = "en cours"
                    try:
                        self.__spec__.loader.exec_module(self)
                    except BaseException:
                        etat["_smartos_etat"] = None
                        raise
                    etat["_smartos_etat"] = "fait"
                    self.__class__ = types.ModuleType
            try:
                return self.__dict__[nom]
            except KeyError:
                raise AttributeError(
                    f"module 'IPython' has no attribute '{nom}'"
                ) from None

    module = importlib.util.module_from_spec(spec)
    module._smartos_etat = None
    module.__class__ = _IPythonParesseux
    sys.modules["IPython"] = module
    try:
        version = module.version_info[:2]
    except Exception:
        version = None
    if version not in VERSIONS_VERIFIEES:
        # Version non verifiee : on rend la main a l'import normal du paquet.
        for nom in [n for n in sys.modules if n == "IPython" or n.startswith("IPython.")]:
            del sys.modules[nom]


_smartos_ipython_paresseux()
'''


def patcher(chemin):
    source = open(chemin, encoding="utf-8").read()
    if MARQUEUR in source:
        print(f"Deja patche : {chemin}")
        return True
    arbre = ast.parse(source)
    lignes = source.splitlines(keepends=True)
    ancres = [n for n in arbre.body if isinstance(n, ast.Expr)
              and lignes[n.lineno - 1].strip() == ANCRE and n.lineno == n.end_lineno]
    noms = {alias.asname or alias.name for n in arbre.body
            if isinstance(n, ast.Import) and n.lineno < (ancres[0].lineno if ancres else 0)
            for alias in n.names}
    if len(ancres) != 1 or "sys" not in noms:
        print(f"ERREUR : l'appel `{ANCRE}` (unique, au niveau du module, apres `import sys`) "
              f"est introuvable dans {chemin} - la forme amont a change.", file=sys.stderr)
        return False
    fin = ancres[0].end_lineno
    resultat = "".join(lignes[:fin]) + BLOC + "".join(lignes[fin:])
    try:
        ast.parse(resultat)
    except SyntaxError as erreur:
        print(f"ERREUR : patch invalide pour {chemin} ({erreur})", file=sys.stderr)
        return False
    open(chemin, "w", encoding="utf-8").write(resultat)
    print(f"Patche : {chemin}")
    return True


def main(argv):
    if len(argv) != 2:
        print(f"Usage : {argv[0]} <spyder/app/mainwindow.py>", file=sys.stderr)
        return 1
    return 0 if patcher(argv[1]) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
