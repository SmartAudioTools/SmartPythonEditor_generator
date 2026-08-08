#!/usr/bin/env python3
"""Patch spyder/plugins/layout/plugin.py : MASQUE PAR DEFAUT, au premier lancement, des docks juges
redondants ou peu utilises.

Contexte (CachyOS/Documentation/TODO - Spyder - cosmetique.txt) :
  1re passe, chapitre "Dock2", decision utilisateur :
  - Line Profiler : son panneau affiche un tableau par ligne (hits/temps/%/code), redondant avec les
    timings que le greffon SmartOS peint deja DANS l'editeur. On masque le DOCK, sans desactiver le
    greffon (la machinerie de profilage - F10 - et le peinturage editeur restent).
  - Debogueur : son panneau montre la pile d'appels pendant le debogage pas-a-pas ; peu utilise ici.
  2e passe, item 6 du 26/07/2026 ("initialise comme cache lors du premier lancement de spyder les
  panneaux : VizTracer, Profiler, Historique, Terminal") :
  - VizTracer et Profileur : deux panneaux de profilage lances a la demande depuis leur barre
    d'outils ; leur dock n'a d'interet qu'apres un profilage.
  - Historique : un onglet par console IPython (client.history_filename) plus l'historique global -
    une seule console ouverte n'en remplit qu'un, et la commande qu'on cherche est de toute facon
    dans la console elle-meme (fleche haut, Ctrl+R).
  - Terminal : une konsole est a un clic dans la barre des taches.

MASQUAGE "UNE SEULE FOIS" (pas a chaque demarrage) : la visibilite des docks est persistee dans la
disposition (blob binaire, non editable a la main). On cache donc ces docks au PREMIER lancement
apres le correctif, via un drapeau de configuration, puis on RESPECTE le choix de l'utilisateur :
s'il les reaffiche (Affichage > Panneaux), ils restent affiches aux lancements suivants. Insere en
FIN de Layout.on_mainwindow_visible, apres restore_visible_plugins (les docks sont alors en place)
et toggle_lock.

⚠ UN DRAPEAU PAR PASSE (layout/smartos_docks_hidden_once puis ...._v2), et donc DEUX blocs distincts
plutot qu'un seul elargi : le drapeau de la 1re passe est deja a True sur cette machine. Elargir sa
liste aurait ete sans effet ; changer sa valeur aurait re-masque Line Profiler et Debogueur, alors
que l'utilisateur a peut-etre choisi de les reafficher depuis. Chaque passe ne decide donc que du
sort des docks qu'elle introduit.

Usage : patch_spyder_hide_docks.py <chemin vers plugins/layout/plugin.py installe>

IDEMPOTENCE PAR BLOC : chaque bloc porte SON marqueur et est saute s'il est deja present, ce qui
permet a la 2e passe de s'appliquer sur une installation ou la 1re est deja en place, sans rien
defaire (un marqueur global unique l'aurait rendue inoperante - piege deja paye sur ce depot). Les
blocs sont appliques DANS L'ORDRE : le bloc 2 s'ancre sur le texte pose par le bloc 1. Re-parse avant
ecriture ; echec BRUYANT (code 1) si un ancrage est introuvable ou non unique - jamais deviner.
"""
import ast
import sys

ANCHOR = (
    "        # Update panes and toolbars lock status\n"
    "        self.toggle_lock(self._interface_locked)\n"
)

BLOCK_V1 = (
    "\n"
    "        # SmartOS (patch_spyder_hide_docks.py) : masquer PAR DEFAUT les docks Line Profiler et\n"
    "        # Debogueur, juges redondants / peu utilises (chapitre Dock2, demande utilisateur). On\n"
    "        # les cache UNE seule fois - au premier lancement apres ce correctif - puis on respecte le\n"
    "        # choix de l'utilisateur (s'il les reaffiche, ils restent affiches). Les greffons ne sont\n"
    "        # PAS desactives (profilage F10 et timings dans l'editeur intacts).\n"
    "        if not self.get_conf(\"smartos_docks_hidden_once\", False):\n"
    "            for _smartos_dock in (\"spyder_line_profiler\", \"debugger\"):\n"
    "                _smartos_plugin = self.get_plugin(_smartos_dock, error=False)\n"
    "                if _smartos_plugin is not None:\n"
    "                    _smartos_plugin.get_widget().toggle_view(False)\n"
    "            self.set_conf(\"smartos_docks_hidden_once\", True)\n"
)

# Derniere ligne du bloc 1, servant d'ancre au bloc 2.
BLOCK_V1_TAIL = "            self.set_conf(\"smartos_docks_hidden_once\", True)\n"

BLOCK_V2 = (
    "\n"
    "        # SmartOS (2e passe, 26/07/2026, item 6 du TODO cosmetique) : meme mecanisme pour\n"
    "        # VizTracer, Profileur, Historique et Terminal. DRAPEAU DISTINCT du precedent, qui est\n"
    "        # deja a True : le reutiliser n'aurait rien masque, et le remettre a False aurait\n"
    "        # re-masque Line Profiler et Debogueur que l'utilisateur a peut-etre reaffiches depuis.\n"
    "        if not self.get_conf(\"smartos_docks_hidden_v2\", False):\n"
    "            for _smartos_dock in (\n"
    "                \"viztracer_profiler\", \"profiler\", \"historylog\", \"terminal\"\n"
    "            ):\n"
    "                _smartos_plugin = self.get_plugin(_smartos_dock, error=False)\n"
    "                if _smartos_plugin is not None:\n"
    "                    _smartos_plugin.get_widget().toggle_view(False)\n"
    "            self.set_conf(\"smartos_docks_hidden_v2\", True)\n"
)

# (marqueur, ancien, nouveau), appliques DANS CET ORDRE.
PAIRS = [
    ("smartos_docks_hidden_once", ANCHOR, ANCHOR + BLOCK_V1),
    ("smartos_docks_hidden_v2", BLOCK_V1_TAIL, BLOCK_V1_TAIL + BLOCK_V2),
]


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers plugins/layout/plugin.py>", file=sys.stderr)
        return 1

    path = sys.argv[1]
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
    except OSError as error:
        print(f"layout/plugin.py illisible ({error}) - patch masquage docks non applique.",
              file=sys.stderr)
        return 1

    applied = 0
    for marqueur, old, new in PAIRS:
        if marqueur in source:
            continue  # bloc deja en place
        n = source.count(old)
        if n != 1:
            print(f"Ancrage attendu introuvable ou non unique (occurrences={n}) dans {path} - Spyder "
                  f"a peut-etre restructure on_mainwindow_visible, patch masquage docks non "
                  f"applique. Ancrage:\n{old[:80]}...", file=sys.stderr)
            return 1
        source = source.replace(old, new)
        applied += 1

    if applied == 0:
        print("Patch masquage docks : tous les blocs sont deja en place.")
        return 0

    try:
        ast.parse(source)
    except SyntaxError as error:
        print(f"Le layout/plugin.py patche n'est pas du Python valide ({error}) - aucune "
              "modification ecrite.", file=sys.stderr)
        return 1

    with open(path, "w", encoding="utf-8") as f:
        f.write(source)
    print(f"Patch masquage docks applique ({applied} bloc(s)) : Line Profiler, Debogueur, VizTracer, "
          f"Profileur, Historique et Terminal caches au premier lancement ({path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
