#!/usr/bin/env python3
"""Patch spyder/plugins/profiler/plugin.py : le dock "Profiler" (natif, F10 SANS marqueur) ne
revient plus tout seul au premier plan a chaque profilage.

CONSTAT (question utilisateur, 02/08/2026). `patch_spyder_hide_docks.py` masque ce dock par defaut
au premier lancement (2e passe, item 6) et promet explicitement de respecter ensuite le choix de
l'utilisateur - s'il le redecoche d'Affichage > Panneaux, il doit rester cache. Mais Spyder possede
deja, cote amont, une preference SEPAREE qui gouverne le meme effet : `profiler/switch_to_plugin`
(case a cocher "Open profiler when profiling finishes" dans Preferences > Profileur), par defaut
`True` (spyder/config/main.py). Tant que l'utilisateur ne va pas decocher CETTE case precise -
distincte de celle qu'il a effectivement decochee, Affichage > Panneaux -, `_display_request()`
(widgets/main_widget.py) rappelle `switch_to_plugin()` a la fin de CHAQUE profilage et re-affiche
le dock, contredisant la promesse de patch_spyder_hide_docks.py.

⚠ CHANGER LE DEFAUT DANS config/main.py NE SUFFIT PAS. `UserConfig.get()` (spyder/config/user.py)
ecrit la valeur par defaut dans le fichier .ini AU PREMIER APPEL puis lit ensuite CE QUI Y EST
ECRIT, jamais le defaut du code : sur un profil deja initialise (le cas de l'utilisateur, qui a
deja profile et vu le probleme), `switch_to_plugin` vaut deja True dans son spyder.ini et un
nouveau defaut resterait sans effet - meme piege documente pour la CONF_VERSION dans
CLAUDE_spyder.md. Le correctif doit donc ECRIRE la valeur, pas seulement changer son defaut.

CHANGEMENT. Meme mecanisme et meme genre de garde que celui deja ecrit par Spyder trois lignes plus
haut dans la meme methode (`on_mainwindow_visible`, drapeau conf `make_visible`) : au premier
demarrage APRES ce correctif, on met `switch_to_plugin` a False UNE fois, puis on ne touche plus
jamais a ce reglage - l'utilisateur reste libre de le recocher depuis Preferences > Profileur, et
ce choix est respecte aux lancements suivants (le drapeau ne repasse jamais a False).

Usage : patch_spyder_profiler_no_forced_switch.py <chemin vers spyder/plugins/profiler/plugin.py>

IDEMPOTENCE PAR BLOC, meme structure que les autres patchs de ce depot : marqueur teste avant
application, re-parse AST avant ecriture, echec BRUYANT (code 1) si l'ancrage est introuvable ou
non unique - jamais deviner.
"""
import ast
import sys

MARQUEUR = "patch_spyder_profiler_no_forced_switch.py"

ANCIEN = (
    "    def on_mainwindow_visible(self):\n"
    "        # Make plugin visible in case it's not but only once. For most users\n"
    "        # this will display it in the UI when moving from 6.0 to 6.1\n"
    "        if not self.get_conf(\"make_visible\", default=False):\n"
    "            if not self.get_widget().is_visible:\n"
    "                self.get_widget().toggle_view(True)\n"
    "            self.set_conf(\"make_visible\", True)\n"
)

BLOC_AJOUTE = f'''
        # SmartOS (patch_spyder_profiler_no_forced_switch.py) : meme garde que ci-dessus,
        # pour DESACTIVER switch_to_plugin UNE fois - son defaut amont (True) ramene ce dock
        # au premier plan a la fin de CHAQUE profilage, meme decoche d'Affichage > Panneaux,
        # contraire a la promesse de patch_spyder_hide_docks.py ("on respecte le choix de
        # l'utilisateur"). Ecrit le reglage UNE seule fois ; s'il le recoche ensuite depuis
        # Preferences > Profileur, ce choix est respecte aux lancements suivants.
        if not self.get_conf("smartos_switch_to_plugin_disabled_once", default=False):
            self.set_conf("switch_to_plugin", False)
            self.set_conf("smartos_switch_to_plugin_disabled_once", True)
'''

NOUVEAU = ANCIEN + BLOC_AJOUTE


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers spyder/plugins/profiler/plugin.py>",
              file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as error:
        print(f"plugin.py illisible ({error}) - patch affichage force Profiler non applique.",
              file=sys.stderr)
        return 1

    if MARQUEUR in source:
        print("Patch affichage force Profiler : deja en place.")
        return 0

    n = source.count(ANCIEN)
    if n != 1:
        print(f"Ancrage attendu introuvable ou non unique (occurrences={n}) dans {path} - "
              f"spyder a peut-etre change de version, patch non applique. Ancrage:\n{ANCIEN}",
              file=sys.stderr)
        return 1

    source = source.replace(ANCIEN, NOUVEAU)

    # 2e bloc (08/08/2026) : neutraliser le "make_visible" AMONT du meme on_mainwindow_visible
    # (migration 6.0->6.1 : il force le dock visible une fois). Sur une configuration neuve il
    # se declenche APRES notre patch_spyder_hide_docks et REAFFICHE le panneau que celui-ci
    # vient de cacher - constate le 08/08/2026 sur l'installation complete fraiche. Le neutraliser
    # ici (et non poser make_visible=True dans la config de reference) couvre aussi les
    # configurations existantes qui n'ont pas la cle.
    ANCIEN2 = 'if not self.get_conf("make_visible", default=False):'
    NOUVEAU2 = ('if False:  # [SmartOS no-forced-switch] make_visible amont neutralise : il '
                'reaffichait le dock apres notre masquage par defaut')
    if NOUVEAU2.split("  #")[0] not in source:
        n2 = source.count(ANCIEN2)
        if n2 != 1:
            print(f"AVERTISSEMENT : ancrage make_visible trouve {n2} fois - bloc 2 non applique.",
                  file=sys.stderr)
        else:
            source = source.replace(ANCIEN2, NOUVEAU2)

    try:
        ast.parse(source)
    except SyntaxError as error:
        print(f"Le plugin.py patche n'est pas du Python valide ({error}) - aucune modification "
              "ecrite.", file=sys.stderr)
        return 1

    with open(path, "w", encoding="utf-8") as f:
        f.write(source)
    print(f"Patch affichage force Profiler applique : le dock ne revient plus au premier plan "
          f"tout seul ({path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
