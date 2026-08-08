#!/usr/bin/env python3
"""Repare le demarrage de Spyder sous PySide6 >= 6.9 (mesure sur 6.11.1, le 26/07/2026).

SYMPTOME. Spyder ne demarre plus du tout, des l'enregistrement du premier greffon :

    File ".../spyder/utils/qthelpers.py", line 375, in create_action
        action.triggered.connect(triggered)
    RuntimeError: Target signal has been deleted

puis, si l'on contourne cet appel-la, quatre lignes plus loin :

    File ".../spyder/api/plugins/new_api.py", line 561, in __init__
        container.sig_free_memory_requested.connect(...)
    RuntimeError: Signal source has been deleted

CE QUE CE N'EST PAS. Ce n'est PAS la plage de versions codee en dur dans
`spyder/requirements.py:check_qt()` (PySide6 >=6.8.0,<6.9.0). Cette borne-la est deja
relevee par Commun/scripts/Spyder.sh : Spyder la franchit, demarre, et plante APRES,
a l'execution. Ce n'est pas non plus la configuration de l'utilisateur (reproduit en
--safe-mode), ni un greffon externe (reproduit avec les dix greffons SmartOS ecartes des
points d'entree), ni le binding QTermWidget.

CAUSE RACINE, isolee par bisection jusqu'a un cas de quinze lignes SANS Spyder :

    class Toucheur:
        def __init__(self):
            super().__init__()
            for n in dir(self):          # <-- lire ses propres attributs PENDANT la
                getattr(self, n, None)   #     construction de l'objet

    class W(QWidget, Toucheur):
        sig = Signal()

    W().sig                              # -> RuntimeError: signal has been deleted

Sous PySide6 6.11.1, tout `Signal` LU pendant la construction de l'objet est
definitivement mort ensuite. Sous 6.8.3 la meme lecture etait inoffensive. Le meme
programme sans le parcours de `dir(self)` fonctionne : c'est bien la LECTURE PRECOCE qui
empoisonne le signal, pas l'heritage multiple ni la presence d'un `__del__`.

Or `SpyderConfigurationObserver._gather_observers()` fait exactement cela — parcourir
`dir(self)` et appeler `getattr(self, ...)` sur chaque nom — et il est appele depuis le
constructeur de PRESQUE TOUT dans Spyder (tout conteneur, tout widget de greffon). Tous
leurs signaux naissent donc morts. Spyder connaissait deja le probleme de loin : deux
noms ("painters", "restart_kernel") y sont sautes explicitement sous PySide6 avec le
commentaire « Avoid a crash at startup due to MRO ». C'est la meme cause, vue par le
petit bout.

CORRECTIF. Chercher les methodes decorees par `@on_conf_change` dans les CLASSES
(`type(self).__mro__`, dictionnaires de classe) au lieu de les chercher sur l'INSTANCE.
L'information est strictement la meme — le decorateur pose `_conf_listen` sur la fonction,
et le code n'a besoin que du NOM de la methode, qu'il range tel quel dans
`_configuration_listeners`. Mais plus aucun attribut d'instance n'est lu pendant la
construction : les signaux restent vivants.

Une nuance a connaitre : l'ordre d'enregistrement des ecouteurs passe de l'ordre
alphabetique de `dir()` a l'ordre de definition dans les classes, du plus derive au plus
general. Cela ne change l'ordre d'APPEL que si deux methodes observent la meme option de
la meme section, cas ou Spyder ne garantit deja rien.

PORTEE. C'est un contournement d'un defaut AMONT (interaction PySide6 6.9+ / Spyder
6.1.5), a inscrire dans Contournement_bugs_a_supprimer_quand_corrigés.txt. Test de
peremption : retirer le patch, lancer Spyder sous la version de PySide6 du jour ; s'il
demarre, le contournement ne sert plus.

Usage : patch_spyder_pyside611_signaux.py <chemin spyder/api/config/mixins.py>
"""

import ast
import shutil
import sys

MARQUEUR = "[SmartOS pyside611-signaux]"

ANCRE = '''    def _gather_observers(self):
        """Gather all the methods decorated with :func:`on_conf_change`."""
        for method_name in dir(self):
'''

REMPLACEMENT = '''    def _gather_observers(self):
        """Gather all the methods decorated with :func:`on_conf_change`."""
        # PATCH SmartOS ''' + MARQUEUR + ''' (26/07/2026) : parcourir les CLASSES, jamais
        # l'INSTANCE. Sous PySide6 >= 6.9, tout Signal lu pendant la construction de
        # l'objet est definitivement mort ensuite ("Target signal has been deleted"), et
        # cette methode est appelee depuis le constructeur de presque tout Spyder.
        # `_conf_listen` est pose par @on_conf_change sur la FONCTION : on le lit donc
        # dans le dictionnaire de classe, sans jamais toucher a self.
        _vus = set()
        for _classe in type(self).__mro__:
            for _nom, _attribut in list(_classe.__dict__.items()):
                if _nom in _vus:
                    continue
                _fonction = getattr(_attribut, "__func__", _attribut)
                _info = getattr(_fonction, "_conf_listen", None)
                if _info is None:
                    continue
                # Le plus derive gagne, comme le faisait getattr(self, nom).
                _vus.add(_nom)
                if len(_info) > 1:
                    self._multi_option_listeners |= {_nom}
                for _section, _option in _info:
                    self._add_listener(_nom, _option, _section)
        return

        # ⚠ NE PAS SUPPRIMER CE QUI SUIT. Ce n'est pas du code mort decoratif : l'ancre
        # remplacee INCLUT la ligne `for method_name in dir(self):`, et le corps de la
        # boucle d'origine reste dans le fichier apres elle. Sans ce `return` suivi de la
        # meme ligne `for`, ce corps se rattache silencieusement a la boucle precedente :
        # le fichier compile toujours, et leve une NameError a l'execution (essaye le
        # 26/07/2026, en croyant simplifier). Le `return` garantit qu'il n'est jamais
        # atteint ; la ligne `for` garantit qu'il reste syntaxiquement a sa place.
        for method_name in dir(self):
'''


# --------------------------------------------------------------------------------------
# Second site, MEME cause : spyder/plugins/completion/api.py redefinit _gather_observers
# pour les fournisseurs de completion, avec le meme parcours de dir(self). Sans ce
# bloc-la, Spyder passe l'enregistrement des greffons puis meurt en instanciant le premier
# fournisseur ("sig_provider_ready ... Signal source has been deleted"). Marqueur propre,
# pour que chacun des deux blocs puisse etre pose ou retire independamment.

MARQUEUR_COMPLETION = "[SmartOS pyside611-signaux-completion]"

ANCRE_COMPLETION = '''    def _gather_observers(self):
        """Gather all the methods decorated with `on_conf_change`."""
        for method_name in dir(self):
'''

REMPLACEMENT_COMPLETION = '''    def _gather_observers(self):
        """Gather all the methods decorated with `on_conf_change`."""
        # PATCH SmartOS ''' + MARQUEUR_COMPLETION + ''' (26/07/2026) : meme cause et meme
        # correctif que dans spyder/api/config/mixins.py — on cherche les methodes
        # decorees dans les CLASSES, sans jamais lire un attribut de l'instance, sous
        # peine de tuer tous ses signaux sous PySide6 >= 6.9.
        _vus = set()
        for _classe in type(self).__mro__:
            for method_name, _attribut in list(_classe.__dict__.items()):
                if method_name in _vus:
                    continue
                _fonction = getattr(_attribut, "__func__", _attribut)
                info = getattr(_fonction, "_conf_listen", None)
                if info is None:
                    continue
                _vus.add(method_name)
                if len(info) > 1:
                    self._multi_option_listeners |= {method_name}
                for section, option in info:
                    if section is None:
                        section = 'completions'
                        if option == '__section':
                            option = (
                                'provider_configuration',
                                self.COMPLETION_PROVIDER_NAME,
                                'values'
                            )
                        else:
                            option = self._wrap_provider_option(option)
                    section_listeners = self._configuration_listeners.get(section, {})
                    option_listeners = section_listeners.get(option, [])
                    option_listeners.append(method_name)
                    section_listeners[option] = option_listeners
                    self._configuration_listeners[section] = section_listeners
        return

        # ⚠ NE PAS SUPPRIMER CE QUI SUIT. Ce n'est pas du code mort decoratif : l'ancre
        # remplacee INCLUT la ligne `for method_name in dir(self):`, et le corps de la
        # boucle d'origine reste dans le fichier apres elle. Sans ce `return` suivi de la
        # meme ligne `for`, ce corps se rattache silencieusement a la boucle precedente :
        # le fichier compile toujours, et leve une NameError a l'execution (essaye le
        # 26/07/2026, en croyant simplifier). Le `return` garantit qu'il n'est jamais
        # atteint ; la ligne `for` garantit qu'il reste syntaxiquement a sa place.
        for method_name in dir(self):
'''

#: (marqueur, ancre, remplacement, fragment identifiant le fichier attendu)
BLOCS = (
    (MARQUEUR, ANCRE, REMPLACEMENT, "class SpyderConfigurationObserver"),
    (MARQUEUR_COMPLETION, ANCRE_COMPLETION, REMPLACEMENT_COMPLETION,
     "class CompletionConfigurationObserver"),
)


def principal(chemin):
    source = open(chemin, encoding="utf-8").read()

    for marqueur, ancre, remplacement, signature in BLOCS:
        if signature in source:
            break
    else:
        print("ECHEC : %s ne contient aucun des deux observateurs attendus." % chemin,
              file=sys.stderr)
        return 1

    if marqueur in source:
        print("Deja applique (%s) : rien a faire." % marqueur)
        return 0

    if source.count(ancre) != 1:
        print("ECHEC : ancre introuvable ou ambigue (%d occurrences) dans %s"
              % (source.count(ancre), chemin), file=sys.stderr)
        print("        _gather_observers a change en amont : relire la methode avant "
              "de rejouer ce patch.", file=sys.stderr)
        return 1

    nouveau = source.replace(ancre, remplacement, 1)

    # Refuser d'ecrire un fichier qui ne compile pas : un mixin casse rend Spyder
    # totalement muet (il avale les exceptions d'import de greffons).
    try:
        ast.parse(nouveau)
    except SyntaxError as erreur:
        print("ECHEC : le resultat n'est pas du Python valide : %s" % erreur,
              file=sys.stderr)
        return 1

    shutil.copyfile(chemin, chemin + ".smartos.bak")
    open(chemin, "w", encoding="utf-8").write(nouveau)
    print("Applique %s a %s (sauvegarde : %s.smartos.bak)" % (marqueur, chemin, chemin))
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    sys.exit(principal(sys.argv[1]))
