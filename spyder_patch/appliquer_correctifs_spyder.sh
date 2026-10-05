#!/bin/bash
# Applique, dans l'ordre, les correctifs SmartOS qui touchent le code de Spyder LUI-MEME (le
# paquet "spyder", pas ses paquets tiers spyder_kernels/spyder_line_profiler - ceux-la restent
# appliques directement par installation_SmartPythonEditor.sh, hors fork). Extrait le 08/08/2026 de la boucle
# qui vivait jusque-la dans installation_SmartPythonEditor.sh, pour etre appelable identiquement par :
#   - reconstruire_fork_spyder.sh, sur un clone propre de l'etiquette officielle vise ;
#   - a defaut de fork disponible/a jour, un usage manuel ponctuel sur une installation existante.
#
# Les DEUX contextes partagent la meme structure ($ROOT/spyder/...) : un venv installe
# ($ROOT = .../site-packages) comme un clone git de spyder-ide/spyder ($ROOT = racine du clone,
# qui contient directement spyder/) - verifie sur un clone reel de la v6.1.5.
#
# Usage : appliquer_correctifs_spyder.sh <ROOT> <GEN_DIR>
#   ROOT        dossier contenant spyder/ (site-packages du venv, ou racine du clone du fork)
#   GEN_DIR     racine du depot SmartPythonEditor_generator (patchs, icones, ressources)
#
# Chaque patch est idempotent et ancre par AST (cf. CLAUDE.md, "Correctifs, derives,
# conventions") : un point d'insertion disparu fait echouer BRUYAMMENT ce script (set -e),
# plutot que de continuer sur un resultat partiel.
set -eu

ROOT="${1:?Usage: appliquer_correctifs_spyder.sh <ROOT> <GEN_DIR>}"
GEN_DIR="${2:?Usage: appliquer_correctifs_spyder.sh <ROOT> <GEN_DIR>}"

  # PAS de forcage en dur de qtpy (abandonne le 25/07/2026) : qtpy 2.4.3 lit deja correctement
  # QT_API dans son code d'origine (`API = os.environ.get(QT_API, "pyqt5").lower()`) - verifie en
  # direct avec PyQt6 ET PySide6 installes simultanement, les deux valeurs de QT_API resolvent au
  # bon binding. Le "bug" qui avait motive un forcage etait en realite un faux diagnostic : l'ancien
  # sed (guillemets simples) avait cesse de correspondre apres une mise a jour de qtpy (guillemets
  # doubles), silencieusement, et la session precedente en avait conclu - a tort - que qtpy
  # ignorait QT_API. Le binding est donc uniquement pilote par `export QT_API=...` dans
  # Commun/scripts/Spyder.sh, sans toucher a qtpy.
  # aiguille F10 / le bouton "Profiler le fichier" : profilage COMBINE (cProfile + lignes en une
  # execution, les deux panneaux remplis) si des fonctions sont marquees a line-profiler, cProfile
  # normal in-noyau sinon. Cf. Commun/scripts_installation/spyder_patch/patch_spyder_profiler_reroute.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_profiler_reroute.py" "$ROOT/spyder/plugins/profiler/plugin.py"
  # le dock "Profiler" natif revenait au premier plan a la fin de CHAQUE profilage (case
  # Preferences > Profileur "Open profiler when profiling finishes", vraie a defaut), meme
  # decoche d'Affichage > Panneaux - contraire a la promesse de patch_spyder_hide_docks.py
  # plus bas ("on respecte le choix de l'utilisateur"). Cf.
  # Commun/scripts_installation/spyder_patch/patch_spyder_profiler_no_forced_switch.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_profiler_no_forced_switch.py" "$ROOT/spyder/plugins/profiler/plugin.py"
  # rend increvable le dialogue "Executer > Configuration" : Spyder y pousse les parametres
  # ENREGISTRES dans le widget de l'executeur affiche par deux chemins, et un seul verifie que
  # les formes concordent. Un jeu enregistre sous un autre executeur (la configuration en
  # contenait trois sous "profiler", portant des parametres de console) faisait donc lever
  # "KeyError: 'current'" a l'ouverture du dialogue - et l'action qui passe par lui, ici un
  # profilage, echouait. Ajoute la meme garde que celle deja ecrite par Spyder quinze lignes
  # plus haut. Cf. Commun/scripts_installation/spyder_patch/patch_spyder_run_dialog_params_guard.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_run_dialog_params_guard.py" "$ROOT/spyder/plugins/run/widgets.py"
  # "Executer dans une console dediee" devient le defaut pour tout fichier jamais configure
  # individuellement (decision de l'utilisateur du 01/08/2026, TODO - Spyder - General.txt) : un
  # noyau neuf a chaque execution evite tout residu de debogage ou de variable d'un lancement a
  # l'autre. Cf. Commun/scripts_installation/spyder_patch/patch_spyder_dedicated_console_default.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_dedicated_console_default.py" \
    "$ROOT/spyder/plugins/ipythonconsole/widgets/run_conf.py"
  # "Console dediee" chez Spyder veut dire UNE CONSOLE PAR FICHIER (get_client_for_file
  # reutilise la console deja ouverte pour ce fichier), pas un noyau neuf a chaque clic -
  # residu de variables constate par l'utilisateur le 02/08/2026 en relancant plusieurs
  # fois le meme fichier. FERME desormais la console dediee precedente avant de relancer,
  # la branche existante en recreant une neuve : un seul onglet par fichier, toujours un
  # noyau vierge. (Redemarrer le noyau, premiere version, ne marchait pas : restart_kernel
  # est @qdebounced(200 ms), le redemarrage arrivait APRES l'envoi du %runfile et tuait le
  # script en cours - detail dans l'en-tete du patch.) Cf.
  # spyder_patch/patch_spyder_fresh_kernel_per_run.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_fresh_kernel_per_run.py" \
    "$ROOT/spyder/plugins/ipythonconsole/widgets/main_widget.py"
  # Avec un noyau neuf a chaque execution, une console de fichier est presque toujours SEULE
  # sur son noyau : le suffixe "/A" que Spyder accole systematiquement (lettre de la premiere
  # console d'un noyau, cf. ClientWidget.get_name()) devient du bruit. Retire, en ne gardant
  # le suffixe QUE pour une eventuelle console secondaire ("/B", ...) qui partagerait ce meme
  # noyau. Decision de l'utilisateur du 09/08/2026. Cf.
  # spyder_patch/patch_spyder_console_tab_no_bare_a.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_console_tab_no_bare_a.py" \
    "$ROOT/spyder/plugins/ipythonconsole/widgets/client.py"
  # Une console ANONYME (bouton "+") reutilise desormais le plus petit numero libere par
  # une fermeture au lieu de compter pour toujours vers le haut, et l'emplacement 1 ne
  # porte plus de numero du tout : "Console", "Console 2", "Console 3", ... Decision de
  # l'utilisateur du 09/08/2026, suite immediate du retrait du "/A" ci-dessus. DOIT rester
  # APRES patch_spyder_console_tab_no_bare_a.py (son ancre dans client.py est le texte deja
  # patche par lui). Cf. spyder_patch/patch_spyder_console_tab_reuse_number.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_console_tab_reuse_number.py" \
    "$ROOT/spyder/plugins/ipythonconsole/widgets"
  # remplace l'icone du bouton "Profiler le fichier" par la notre. C'est l'icone nommee 'profiler'
  # du gestionnaire d'icones de Spyder (ima.icon('profiler') -> images/<theme>/profiler.svg), aussi
  # reutilisee comme marqueur par les marqueurs de profilage du fork spyder_line_profiler : la remplacer met les
  # deux d'accord. On ecrase les DEUX variantes de theme (dark et light), la version affichee
  # dependant du theme actif. Comme tout correctif de site-packages, il est efface a la prochaine
  # mise a jour du paquet spyder et donc rejoue ici. --remove-destination : ecrire le fichier neuf
  # au lieu d'ecrire A TRAVERS un eventuel lien symbolique (regle du depot). Echec BRUYANT si la
  # source ou une cible manque, jamais silencieux.
  ICONE_PROFILER="$GEN_DIR/ressources/icones/spyder/profiler.svg"
  if [ ! -f "$ICONE_PROFILER" ]; then
    echo "ATTENTION : $ICONE_PROFILER introuvable - icone du bouton Profiler non remplacee." >&2
  else
    for THEME_PROFILER in dark light; do
      CIBLE_PROFILER="$ROOT/spyder/images/${THEME_PROFILER}/profiler.svg"
      if [ -f "$CIBLE_PROFILER" ]; then
        cp -f --remove-destination "$ICONE_PROFILER" "$CIBLE_PROFILER"
      else
        echo "ATTENTION : $CIBLE_PROFILER introuvable - arborescence des icones spyder changee ?" >&2
      fi
    done
  fi
  # passe la ligne de bord (marge PEP8, "edge line") en POINTILLES, pour ne pas la confondre avec
  # la ligne PLEINE de demarcation que le greffon line-profiler ajoute entre le code et la colonne
  # des temps (TODO CachyOS "TODO - Spyder - line profiler.txt"). Cf.
  # Commun/scripts_installation/spyder_patch/patch_spyder_edgeline_dotted.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_edgeline_dotted.py" "$ROOT/spyder/plugins/editor/panels/edgeline.py"
  # permet d'éviter l'ouverture de multiples instances de spyder
  # Garde + ancrage sur la ligne entiere (05/10/2026) : rejoue, le sed doublait ses lignes, et
  # coupait en deux tout bloc ajoute contenant « import time ».
  grep -q "^import setproctitle$" "$ROOT/spyder/app/start.py" || \
    sed -i "s/^import time$/import time\nimport setproctitle\n\nsetproctitle.setproctitle('spyder')/" "$ROOT/spyder/app/start.py"
  # ajoute un vrai menu de selection d'interpreteur directement dans le widget de barre d'etat
  # (TODO du 18/07/2026, demande explicite de l'utilisateur - le menu par defaut de Spyder n'est
  # qu'un raccourci vers les Preferences, pas un vrai selecteur). Cf.
  # Commun/scripts_installation/spyder_patch/patch_spyder_status_menu.py pour le detail complet et le contenu exact du patch.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_status_menu.py" "$ROOT/spyder/plugins/ipythonconsole/widgets/status.py"
  # ramene la fenetre Spyder deja ouverte au premier plan quand une deuxieme invocation
  # "spyder <fichier>" lui transmet son argument (TODO CachyOS du 18/07/2026, "Pb spyder qui ne se
  # remet pas au 1er plan si deja ouvert"). self.raise_()/activateWindow() seuls ne suffisent pas
  # sous Wayland/KWin (verifie en direct, y compris avec une regle KWin de prevention de vol de focus
  # desactivee - sans effet) : passe par le paquet AUR "kdotool" installe ci-dessus, qui contourne
  # cette limite via l'interface de scripting de KWin. Cf. Commun/scripts_installation/spyder_patch/patch_spyder_raise_window.py
  # pour le detail complet.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_raise_window.py" "$ROOT/spyder/app/mainwindow.py"
  # remplace la barre de menus classique (File/Edit/Search/...) par un unique bouton burger a
  # gauche de la toolbar File, sur la meme ligne que les autres icones d'action (TODO CachyOS du
  # 19/07/2026, "Burger menu pour Spyder ?", demande explicite de l'utilisateur). Cf.
  # Commun/scripts_installation/spyder_patch/patch_spyder_burger_menu.py pour le detail complet.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_burger_menu.py" "$ROOT/spyder/plugins/mainmenu/plugin.py"
  # aligne le fond de la barre d'outils principale, celui des separateurs de docks et celui de la
  # barre de statut sur le fond de l'editeur de texte, au lieu du gris nettement plus clair de
  # QDarkStyle (TODO CachyOS du 20/07/2026, section "Couleurs", demande explicite de
  # l'utilisateur). Cf.
  # Commun/scripts_installation/spyder_patch/patch_spyder_colors.py pour le detail complet.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_colors.py" "$ROOT/spyder/utils/stylesheet.py"
  # affiche le chemin du fichier actif dans le titre de la fenetre ("Spyder - <chemin>") plutot que
  # dans la barre dediee au-dessus des onglets, masquee elle par l'option "editor/show_filename_toolbar"
  # de spyder.ini (demande explicite de l'utilisateur, 20/07/2026). Cf.
  # Commun/scripts_installation/spyder_patch/patch_spyder_window_title.py pour le detail complet.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_window_title.py" "$ROOT/spyder/app/mainwindow.py"
  # ajoute l'option "--run-file <script>" : Spyder ouvre le fichier ET l'execute dans sa
  # console au demarrage, sans qu'aucune frappe clavier soit necessaire. Indispensable pour
  # tester automatiquement les greffons qui affichent le resultat d'une execution (Pyxel) :
  # rien ne permet de simuler un F5 sous Wayland (kdotool ne fait que du controle de
  # fenetre). Cf. Commun/scripts_installation/spyder_patch/patch_spyder_run_file.py pour le detail complet.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_run_file.py" "$ROOT/spyder/app/cli_options.py" "$ROOT/spyder/app/mainwindow.py"
  # ajoute "spyder --profile-file FICHIER" : ouvre le fichier et lance le profilage COMBINE au
  # demarrage, sans frappe. Meme raison que --run-file (kdotool ne clique ni ne tape sous
  # Wayland) : rend testable en autonomie le profilage combine. Cf.
  # Commun/scripts_installation/spyder_patch/patch_spyder_profile_file.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_profile_file.py" "$ROOT/spyder/app/cli_options.py" "$ROOT/spyder/app/mainwindow.py"
  # ajoute "spyder --gui-exec FICHIER" : execute un script DANS le processus GUI de Spyder
  # (contrairement a --run-file, qui tourne dans le noyau IPython, processus separe sans
  # acces a PLUGIN_REGISTRY ni aux widgets de plugins - constate en direct le 25/07/2026).
  # Sert a inspecter/piloter les plugins en autonomie. Cf.
  # Commun/scripts_installation/spyder_patch/patch_spyder_gui_exec.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_gui_exec.py" "$ROOT/spyder/app/cli_options.py" "$ROOT/spyder/app/mainwindow.py"
  # ajoute "spyder --actions SCENARIO.json" : joue une SUITE d'actions au demarrage (ouvrir,
  # profiler, attendre une condition, capturer, fermer) et ecrit un rapport JSON. Ce que
  # --gui-exec ne peut pas faire : SEQUENCER. Une attente ecrite dans --gui-exec serait un
  # sleep, donc bloquerait la boucle d'evenements de Qt - donc empecherait justement l'evenement
  # attendu d'arriver. Demande utilisateur du 24/07/2026. ⚠ Le module qui porte toute la
  # logique doit etre depose A COTE de Spyder (ligne suivante) : le patch, lui, se reduit a
  # l'importer. Cf. Commun/scripts_installation/spyder_patch/patch_spyder_actions.py et smartos_spyder_actions.py ; banc
  # de test sans Spyder : Commun/scripts/test_smartos_spyder_actions.py.
  cp -f "$GEN_DIR/ressources/smartos_spyder_actions.py" "$ROOT/smartos_spyder_actions.py"
  python3 "$GEN_DIR/spyder_patch/patch_spyder_actions.py" "$ROOT/spyder/app/cli_options.py" "$ROOT/spyder/app/mainwindow.py"
  # chronometre de demarrage (05/10/2026) : SMARTOS_STARTUP_TRACE=<chemin.json> fait ecrire
  # a Spyder l'horodatage de son lancement (imports, chaque greffon, fenetre visible, editeur
  # utilisable, LSP, noyau). Meme montage que --actions : le module vit A COTE de Spyder, le
  # patch se reduit a l'importer, et seulement si la variable est definie. C'est l'outil de
  # mesure de tous les correctifs de demarrage : sans lui, un gain se juge au bruit.
  cp -f "$GEN_DIR/ressources/smartos_startup_trace.py" "$ROOT/smartos_startup_trace.py"
  python3 "$GEN_DIR/spyder_patch/patch_spyder_startup_trace.py" "$ROOT/spyder/app/start.py"
  # permet d'outrepasser la plage de version Qt figee en dur dans spyder/requirements.py via
  # les variables d'environnement SPYDER_QT_MIN_VERSION / SPYDER_QT_MAX_VERSION /
  # SPYDER_QT_SKIP_VERSION_CHECK, sans avoir a repatcher ce fichier a chaque nouvelle version
  # de binding Qt testee (demande explicite de l'utilisateur, 25/07/2026). Cf.
  # Commun/scripts_installation/spyder_patch/patch_spyder_qt_version_override.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_qt_version_override.py" "$ROOT/spyder/requirements.py"
  # ne calcule qu'UNE FOIS la feuille de style des menus, au lieu d'une fois par menu cree : le
  # profilage du lancement (TODO - Spyder.txt, section "vitesse de lancement", 20/07/2026) montre
  # 129 appels a SpyderMenu._generate_stylesheet() au demarrage pour 420 ms, ~10 % du lancement,
  # a reconstruire chaque fois la meme feuille. Gain mesure : 4381 ms -> 4087 ms. Cf.
  # Commun/scripts_installation/spyder_patch/patch_spyder_menu_stylesheet_cache.py pour le detail complet.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_menu_stylesheet_cache.py" "$ROOT/spyder/api/widgets/menus.py"

  # qstylizer : chaque regle de style recalculait dans son __init__ la liste de ses attributs,
  # qui ne depend que de sa classe. Memorisee par classe (05/10/2026) : construction des
  # feuilles 230 -> 80 ms, fenetre visible -325 ms sur 4064 (A/B entrelace x6, plages
  # disjointes), feuilles produites identiques. Complete le cache des menus ci-dessus.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_qstylizer_memo.py" "$ROOT/spyder/utils/stylesheet.py"
  # feuille de style de l'application gardee sur disque (05/10/2026) : sa construction (analyse
  # de la feuille de QDarkStyle par qstylizer, en python pur) passe de 78 a 11 ms ; la cle du
  # cache reprend theme, palette, police, plateforme et date des deux fichiers de code.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_feuille_app_cache.py" "$ROOT/spyder/utils/stylesheet.py"
  # trois recalculs repetes au demarrage (05/10/2026) : icones SVG rendues une fois par nom
  # (129 appels pour 44 icones), feuille « liste fermee » posee des la construction des listes
  # deroulantes, une seule conversion en texte par feuille de panneau. Avec le cache ci-dessus :
  # editeur utilisable 2941 -> 2598 ms (A/B entrelace x7).
  python3 "$GEN_DIR/spyder_patch/patch_spyder_styles_icones_demarrage.py" "$ROOT"
  # configuration : chaque lecture d'option reanalysait sa valeur (2334 ast.literal_eval au
  # demarrage, dont un dictionnaire de 9 Ko relu 325 fois) et chaque ecriture reecrivait le
  # .ini entier (447 fois). Analyses memorisees par chaine, ecritures regroupees sur 300 ms
  # (05/10/2026) : editeur utilisable 4068 -> 3746 ms (A/B entrelace x8).
  python3 "$GEN_DIR/spyder_patch/patch_spyder_config_rapide.py" "$ROOT/spyder/config/user.py"
  # differe le chargement de trois bibliotheques lourdes (chardet, sphinx, keyring),
  # importees a la volee au demarrage pour un usage ponctuel (deviner un encodage, rendre
  # le panneau Aide, stocker un mot de passe securise) : le profilage (-X importtime)
  # montre qu'elles pesent a elles seules ~2 s sur les ~3 s que coute
  # "from spyder.app import mainwindow", pour des fonctions que la plupart des sessions
  # n'utilisent jamais. Cf. Commun/scripts_installation/spyder_patch/patch_spyder_lazy_imports.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_lazy_imports.py" \
    "$ROOT/spyder/utils/encoding.py" \
    "$ROOT/spyder/plugins/help/utils/sphinxify.py" \
    "$ROOT/spyder/config/manager.py"
  # complement generique du precedent (05/10/2026) : une quinzaine d'imports de tete qui ne
  # servent pas au demarrage (nbconvert, requests, github, jsonschema, markdown_it, pylint,
  # pylsp._utils) sont deplaces dans les fonctions qui s'en servent, et chardet n'est plus
  # appele pour un fichier purement ASCII. Mesure d'import : ~1550 -> ~1150 ms, 2742 -> 1906
  # modules. DOIT passer APRES patch_spyder_lazy_imports.py (meme fichier encoding.py).
  python3 "$GEN_DIR/spyder_patch/patch_spyder_lazy_imports_demarrage.py" "$ROOT"
  # les 13 expressions regulieres de coloration (une par langage) etaient compilees a l'import
  # du module, 30 ms, alors qu'une session n'en utilise qu'une ou deux : elles le sont au
  # premier usage (05/10/2026). Import du module 39 -> 9 ms, mesure isolee.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_regex_coloration_paresseuses.py" \
    "$ROOT/spyder/utils/syntaxhighlighters.py"
  # PySide6 relit le SOURCE de chaque module importe apres lui (inspect.getsource, 1393 fichiers
  # au demarrage) pour savoir s'il utilise PySide : meme question, lecture brute du fichier
  # (05/10/2026). Editeur utilisable 2340 -> 2240 ms (A/B entrelace x7), dictionnaire identique.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_pyside_feature_rapide.py" "$ROOT/spyder/app/mainwindow.py"
  # l'interface n'utilise que quelques sous-modules d'IPython, mais en importer un execute
  # IPython/__init__.py, qui charge tout le terminal interactif (prompt_toolkit, jedi, ultratb) :
  # l'initialisation du paquet est repoussee a son premier usage reel (05/10/2026). Fenetre
  # visible 1624 -> 1424 ms, editeur utilisable 2054 -> 1896 ms (A/B entrelace x7). Garde de version
  # dans le correctif : a completer a chaque montee d'IPython.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_ipython_paresseux.py" "$ROOT/spyder/app/mainwindow.py"
  # Ramasse-miettes cyclique suspendu pendant le demarrage (gc.disable() en tete de start.py),
  # retabli 3 s apres sig_setup_finished : ~500 collectes inutiles en moins. A/B 7 runs :
  # fenetre visible 1565 -> 1482 ms, editeur utilisable 2046 -> 1920 ms.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_gc_demarrage.py" "$ROOT/spyder/app/start.py" "$ROOT/spyder/app/mainwindow.py"
  # asttokens (charge par IPython via stack_data) importe SANS astroid dans l'interface : 94
  # modules de moins, ~15 ms (releve d'imports in situ ; sous la resolution du banc A/B).
  python3 "$GEN_DIR/spyder_patch/patch_spyder_asttokens_sans_astroid.py" "$ROOT/spyder/app/mainwindow.py"
  # Points d'entree des paquets lus UNE fois pendant le demarrage au lieu de cinq
  # (importlib.metadata.entry_points : 37 -> 8 ms mesures in situ, 05/10/2026).
  python3 "$GEN_DIR/spyder_patch/patch_spyder_points_entree_memo.py" "$ROOT/spyder/app/start.py"
  # Defaut AMONT, plus expose depuis que le demarrage est court : Spyder ferme pendant que le
  # noyau repond a sa premiere requete restait vivant sans fenetre, a 100 % d'un coeur
  # (KernelComm._wait boucle sans fin, QEventLoop.exec() rendant -1 une fois quit() appele).
  # Second bloc : une console fermee avant la reponse asynchrone qui lance son noyau n'en lance
  # plus (noyaux orphelins, abandon de Qt a la sortie). Test du premier bloc :
  # outils/banc_demarrage/test_attente_noyau_fermeture.py (05/10/2026).
  python3 "$GEN_DIR/spyder_patch/patch_spyder_attente_noyau_fermeture.py" \
    "$ROOT/spyder/plugins/ipythonconsole"

  # --- Deux defauts AMONT de PySide6 >= 6.9 face au modele objet de Spyder 6.1.5 (26/07/2026).
  #     Sans eux, Spyder ne demarre PAS du tout sous PySide6 6.11 : « Target signal has been
  #     deleted » a l'enregistrement du premier greffon, puis un segfault dans show(). Les deux
  #     patchs sont sans effet de bord sous 6.8.x (le code corrige y est equivalent) : on les
  #     applique donc inconditionnellement, ce qui rend le venv insensible a la version installee.
  # 1. Tout Signal LU pendant la construction de l'objet est definitivement mort ensuite, et
  #    _gather_observers() parcourt dir(self) depuis le constructeur de presque tout Spyder. Le
  #    patch cherche les methodes decorees dans les CLASSES, sans jamais toucher a l'instance.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_pyside611_signaux.py" \
    "$ROOT/spyder/api/config/mixins.py"
  python3 "$GEN_DIR/spyder_patch/patch_spyder_pyside611_signaux.py" \
    "$ROOT/spyder/plugins/completion/api.py"
  # 2. Un signal declare par le NOM de son type — Signal("QMoveEvent") — fait sauter le processus
  #    a l'emission. Le patch remplace la chaine par la classe, importee. Six declarations, dans
  #    trois fichiers, chainees entre elles : il faut les trois.
  for _fichier_signal in \
      "spyder/app/mainwindow.py" "spyder/api/plugins/new_api.py" \
      "spyder/plugins/tours/widgets.py"; do
    python3 "$GEN_DIR/spyder_patch/patch_spyder_pyside611_signaux_evenements.py" \
      "$ROOT/${_fichier_signal}"
  done
  # --- Retouches cosmetiques (TODO CachyOS "TODO - Spyder - cosmetique.txt", 22/07/2026, demande
  #     explicite de l'utilisateur). Chaque script est idempotent, ancre par ast/texte, et echoue
  #     bruyamment si son point d'insertion a disparu. Cf. sa docstring pour le detail complet.
  # Points d'arret du debogueur en BLEU (ICON_2), du meme bleu que les icones de debogage, au lieu
  # du rouge (ICON_4). Cf. Commun/scripts_installation/spyder_patch/patch_spyder_breakpoint_color.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_breakpoint_color.py" \
    "$ROOT/spyder/utils/icon_manager.py"
  # Erreurs de code signalees par un FOND ROUGE derriere le numero de ligne au lieu d'un cercle
  # barre d'une croix dans la marge. Cf. Commun/scripts_installation/spyder_patch/patch_spyder_error_margin.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_error_margin.py" \
    "$ROOT/spyder/plugins/editor/panels/linenumber.py"
  # Zone d'infos par panneau d'edition : overlay FLOTTANT (ligne/colonne + encodage + fin de ligne)
  # en bas a droite de chaque editeur, verbeux en francais (via le catalogue de traduction), avec
  # fond ROUGE si l'encodage n'est pas compatible UTF-8 ou si la fin de ligne est Windows (alerte
  # pedagogique, version destinee a des etudiants). La barre de statut globale est masquee par
  # ailleurs (statusbar/show_status_bar=False, plus bas). Cf.
  # Commun/scripts_installation/spyder_patch/patch_spyder_editor_file_status.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_editor_file_status.py" \
    "$ROOT/spyder/plugins/editor/widgets/editorstack/editorstack.py"
  # Options de l'overlay (verbeux/abrege ; n'afficher encodage & fin de ligne que si non standard) :
  # 2 cases dans Preferences > Editeur > Affichage. Cf. Commun/scripts_installation/spyder_patch/patch_spyder_overlay_prefs.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_overlay_prefs.py" \
    "$ROOT/spyder/config/main.py" \
    "$ROOT/spyder/plugins/editor/confpage.py"
  # Masque le bouton "Browse tabs" (navigation entre onglets) sur TOUS les panneaux a onglets, y
  # compris ceux des plugins. Cf. Commun/scripts_installation/spyder_patch/patch_spyder_dock_browse_tabs.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_dock_browse_tabs.py" \
    "$ROOT/spyder/widgets/tabs.py"
  # Retire de la barre d'outils les boutons execution par cellules / selection-ligne (y compris
  # variantes debogueur/profileur), creation de cellule, Preferences et gestionnaire de PYTHONPATH
  # (l'execution du fichier reste). SUPPRIME reellement les boutons (retires de _item_map et
  # _section_items, section videe supprimee -> aucun trou), pas un simple masquage : reecrit
  # SpyderToolbar.render pour les retirer une fois. Cf. Commun/scripts_installation/spyder_patch/patch_spyder_toolbar_trim.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_toolbar_trim.py" \
    "$ROOT/spyder/api/widgets/toolbars.py"
  # Supprime le vide a droite de "Deboguer le fichier" (barre Debug) : les 5 boutons de controle du
  # debogueur, masques au repos par setFixedWidth(0) (mis en echec par la feuille de style -> slot
  # reserve ~14px/bouton), sont desormais reellement retires/reintroduits (removeAction/addAction, le
  # menu n'est pas touche). Cf. Commun/scripts_installation/spyder_patch/patch_spyder_debug_toolbar_gap.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_debug_toolbar_gap.py" \
    "$ROOT/spyder/plugins/debugger/widgets/main_widget.py"
  # Ordre des boutons de la barre d'outils Fichier : [Ouvrir, Nouveau, Enregistrer, Tout enregistrer]
  # au lieu du defaut [Nouveau, Ouvrir, ...] (demande utilisateur). Reordonne la liste dans
  # Application.on_toolbar_available. Cf. Commun/scripts_installation/spyder_patch/patch_spyder_file_toolbar_order.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_file_toolbar_order.py" \
    "$ROOT/spyder/plugins/application/plugin.py"
  # La fenetre d'appel aux dons ("Help keep Spyder strong"), que Spyder ouvre tout seul au 5e
  # puis au 25e demarrage, ne s'ouvre plus - demande de l'utilisateur du 09/08/2026. Le coeur
  # de la barre d'etat et l'entree de menu, eux, restent : on retire la sollicitation non
  # demandee, pas la possibilite de donner. Cf.
  # spyder_patch/patch_spyder_no_appeal_dialog.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_no_appeal_dialog.py" \
    "$ROOT/spyder/plugins/application/plugin.py"
  # ORDRE DES BARRES de la rangee du haut, rendu explicite (demande utilisateur du
  # 26/07/2026) : les quatre lanceurs se suivent - Executer, Deboguer, Profiler, Python Tutor -
  # puis "Tout arreter" qui en est la contrepartie, puis les outils (Docteur, Agrandir le
  # volet). Spyder les ordonnait par une liste en dur suivie des barres de greffons dans leur
  # ordre de CREATION, ce qui plantait "Agrandir le volet" - une action de vue - au milieu des
  # lanceurs. Impose UNE fois (drapeau toolbar/smartos_order_applied), puis le choix de
  # l'utilisateur est respecte. Cf. Commun/scripts_installation/spyder_patch/patch_spyder_toolbar_order.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_toolbar_order.py" \
    "$ROOT/spyder/plugins/toolbar/container.py"
  # Icones personnalisees du bouton "Agrandir le volet courant" (demande utilisateur du
  # 26/07/2026) : deux fleches vers l'exterieur pour agrandir, vers l'interieur pour revenir.
  # Les SVG sont copies dans les images de Spyder AVANT le patch qui les nomme : le gestionnaire
  # d'images les indexe par leur nom de fichier, et une icone absente rendrait un "not_found"
  # muet. Sous dark/ parce qu'elles sont en blanc pur - cf. Commun/icones/spyder/README.txt,
  # qui documente aussi le piege des marqueurs SVG que Qt ne rend pas.
  cp "$GEN_DIR/ressources/icones/spyder/window_full_screen.svg" \
     "$GEN_DIR/ressources/icones/spyder/window_collapse.svg" \
     "$ROOT/spyder/images/dark/"
  # Horloge du profileur, en violet a la place du rouge livre par Spyder (demande
  # utilisateur du 26/07/2026). Ici on ECRASE le fichier de Spyder au lieu d'ajouter un
  # nom : "profiler" est un nom d'icone que Spyder resout DEJA par son dossier images, et
  # un fichier de plus, sous un autre nom, aurait exige de patcher en outre l'action qui
  # le nomme. Meme geometrie, seule la couleur change - verifie, 62 % du cadre dans les
  # deux cas. Seul dark/ est touche : l'icone etant coloree et non blanche, elle passerait
  # sur les deux themes, mais le rendu clair n'a pas ete verifie faute de machine en
  # theme clair.
  cp "$GEN_DIR/ressources/icones/spyder/profiler.svg" \
     "$ROOT/spyder/images/dark/profiler.svg"
  # Icone "Nouveau fichier" dessinee par l'utilisateur (demande du 26/07/2026) : un document portant
  # le mot "New". Ce cas est le TROISIEME de figure, et le seul qui demande un patch :
  #   - window_full_screen / window_collapse : noms NEUFS, il suffit de deposer les fichiers ;
  #   - profiler : nom que Spyder resout DEJA par son dossier d'images, on ecrase le fichier ;
  #   - filenew : nom declare comme GLYPHE DE POLICE dans le dictionnaire _qtaargs
  #     (mdi.file). icon() consultant ce dictionnaire AVANT le dossier d'images, deposer le
  #     fichier ne suffit PAS - il faut retirer l'entree pour que le repli par fichier joue.
  # D'ou la paire copie + patch ci-dessous, dans cet ordre (une icone absente rendrait un
  # "not_found" muet). Les deux themes sont servis : le dessin porte ses propres couleurs, il ne
  # suit plus MAIN_FG_COLOR - c'est le prix d'un dessin sur mesure, cf. l'en-tete du patch.
  cp "$GEN_DIR/ressources/icones/spyder/filenew.svg" \
     "$ROOT/spyder/images/dark/filenew.svg"
  cp "$GEN_DIR/ressources/icones/spyder/filenew.svg" \
     "$ROOT/spyder/images/light/filenew.svg"
  python3 "$GEN_DIR/spyder_patch/patch_spyder_icones_fichier.py" \
    "$ROOT/spyder/utils/icon_manager.py"
  # Bascule de l'icone selon l'etat du volet, que Spyder ne faisait pas.
  # Cf. Commun/scripts_installation/spyder_patch/patch_spyder_maximize_icons.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_maximize_icons.py" \
    "$ROOT/spyder/plugins/layout/container.py"
  # Deplace la barre "repertoire courant" (combo de chemin + Selectionner un repertoire + Aller au
  # parent) de la barre d'outils principale vers le HAUT du dock Fichiers (elle est deja synchronisee
  # avec l'explorateur). Cf. Commun/scripts_installation/spyder_patch/patch_spyder_workingdir_in_files.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_workingdir_in_files.py" \
    "$ROOT/spyder/plugins/explorer/plugin.py"
  # Barre du dock Fichiers : retire Precedent/Suivant (debordaient dans "...") et deplace le filtre
  # dans le menu hamburger. Cf. Commun/scripts_installation/spyder_patch/patch_spyder_explorer_toolbar.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_explorer_toolbar.py" \
    "$ROOT/spyder/plugins/explorer/widgets/main_widget.py"
  # Tete du panneau Projets, calquee sur celle du panneau Fichiers : combo de selection du projet
  # (projet ouvert + recents + projets trouves dans /DATA/Python), "Nouveau projet" et "Ouvrir un
  # projet" a gauche du burger, "Fermer le projet" et "Supprimer le projet" dans le burger. Le
  # panneau etait le seul sans rien en tete : tout passait par le menu Projets de la barre de menus.
  # Cf. Commun/scripts_installation/spyder_patch/patch_spyder_projects_toolbar.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_projects_toolbar.py" \
    "$ROOT/spyder/plugins/projects/widgets/main_widget.py"
  # Dialogue "Creer un nouveau projet" : champ "Repertoire" pre-rempli avec la racine des projets
  # (il arrivait vide, et le bouton Parcourir partait du dossier personnel).
  # Cf. Commun/scripts_installation/spyder_patch/patch_spyder_projects_dialog.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_projects_dialog.py" \
    "$ROOT/spyder/plugins/projects/widgets/projectdialog.py"
  # Barre "repertoire courant" reduite au seul combo (Parent retire = doublon ; Selectionner deplace
  # dans la barre de l'Explorer). Cf. Commun/scripts_installation/spyder_patch/patch_spyder_workingdir_bar_trim.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_workingdir_bar_trim.py" \
    "$ROOT/spyder/plugins/workingdirectory/container.py"
  # Chapitre "Dock2" de CachyOS/Documentation/TODO - Spyder - cosmetique.txt : allegement des barres
  # d'outils des docks, dock par dock, ce qui est rare ou purement de reglage partant dans le menu
  # burger du panneau. Les actions ne sont jamais supprimees, seulement deplacees.
  # Organisation du code : barre reduite a Tout replier/Tout deplier (les six boutons d'origine
  # debordaient dans le "..." de Qt). Cf. Commun/scripts_installation/spyder_patch/patch_spyder_outline_toolbar.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_outline_toolbar.py" \
    "$ROOT/spyder/plugins/outlineexplorer/main_widget.py"
  # Profileur : les trois bascules d'affichage et Enregistrer/Charger/Effacer la comparaison passent
  # dans le menu burger, qui etait vide. Cf. Commun/scripts_installation/spyder_patch/patch_spyder_profiler_toolbar.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_profiler_toolbar.py" \
    "$ROOT/spyder/plugins/profiler/widgets/main_widget.py"
  # Explorateur de variables : Importer/Enregistrer/Enregistrer sous passent dans le menu burger, la
  # barre ne gardant que "Supprimer toutes les variables". Cf. Commun/scripts_installation/spyder_patch/patch_spyder_varexp_toolbar.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_varexp_toolbar.py" \
    "$ROOT/spyder/plugins/variableexplorer/widgets/main_widget.py"
  # Analyse de code : "Sortie" (sortie brute de pylint) passe de la barre d'etat au menu burger.
  # Cf. Commun/scripts_installation/spyder_patch/patch_spyder_pylint_toolbar.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_pylint_toolbar.py" \
    "$ROOT/spyder/plugins/pylint/main_widget.py"
  # 2e passe du meme chapitre (26/07/2026), sur les docks restants. Les patchs ci-dessus ont ete
  # etendus au passage : leur idempotence est desormais PAR BLOC (chaque bloc porte son marqueur),
  # sans quoi une 2e passe serait restee sans effet sur une installation deja patchee.
  # Console IPython : le coin ne garde que le temps ecoule (Interrompre et Se reconnecter etaient des
  # doublons du burger ; Effacer la console y est ajoutee). Cf. patch_spyder_ipython_toolbar.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_ipython_toolbar.py" \
    "$ROOT/spyder/plugins/ipythonconsole/widgets/main_widget.py"
  # (le patch de la barre du Terminal a disparu le 26/07/2026 avec spyder-terminal lui-meme :
  #  le greffon maison n'a qu'un bouton, place dans le coin de sa barre d'onglets.)
  # Recherche : les trois bascules (Expression reguliere, Sensible a la casse, Options avancees)
  # passent dans le menu burger. Cf. Commun/scripts_installation/spyder_patch/patch_spyder_findinfiles_toolbar.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_findinfiles_toolbar.py" \
    "$ROOT/spyder/plugins/findinfiles/widgets/main_widget.py"
  # Debogueur : les points d'entree dans le debogage, le saut a la ligne courante et l'affichage des
  # points d'arret passent dans le menu burger. Cf. Commun/scripts_installation/spyder_patch/patch_spyder_debugger_toolbar.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_debugger_toolbar.py" \
    "$ROOT/spyder/plugins/debugger/widgets/main_widget.py"
  # Graphiques : les variantes "tous les graphiques" et "Copier l'image" passent dans le menu burger.
  # Cf. Commun/scripts_installation/spyder_patch/patch_spyder_plots_toolbar.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_plots_toolbar.py" \
    "$ROOT/spyder/plugins/plots/widgets/main_widget.py"
  # Aide : "Accueil" et le verrou passent dans le menu burger.
  # Cf. Commun/scripts_installation/spyder_patch/patch_spyder_help_toolbar.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_help_toolbar.py" \
    "$ROOT/spyder/plugins/help/widgets.py"
  # Aide en ligne : "Accueil" et les deux zooms passent dans le menu burger (qui etait vide).
  # Cf. Commun/scripts_installation/spyder_patch/patch_spyder_onlinehelp_toolbar.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_onlinehelp_toolbar.py" \
    "$ROOT/spyder/plugins/onlinehelp/widgets.py"
  # Traductions FR personnalisees dans le catalogue gettext (.mo edite sans recompiler tout le
  # catalogue) : ajout de "Filter files" -> "Filtrer les fichiers" (bouton de filtre du dock Fichiers,
  # deplace dans le menu hamburger, qui l'utilise via _()) et correction du doublon "Exclure les
  # variables en majuscule", affiche DEUX FOIS dans le menu de l'Explorateur de variables.
  # Cf. Commun/scripts_installation/spyder_patch/patch_spyder_add_translations.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_add_translations.py" \
    "$ROOT/spyder/locale/fr/LC_MESSAGES/spyder.mo"
  # Activation PAR WIDGET de la barre de statut : chaque widget (position curseur, encodage, fin de
  # ligne, VCS, LSP, RW, interpreteur, matplotlib) honore statusbar/<ID>/enable, avec une case dans
  # Preferences > Barre d'etat (decoche par defaut : l'overlay par editeur reprend ces infos). Ce
  # patch REMPLACE les anciens patch_spyder_statusbar_hide.py et patch_spyder_pythonenv_keep_hidden.py
  # (il retire leurs blocs s'ils sont encore presents, transition sans reinstallation). Cf.
  # Commun/scripts_installation/spyder_patch/patch_spyder_statusbar_enable.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_statusbar_enable.py" \
    "$ROOT/spyder"
  # Masque PAR DEFAUT (une seule fois par passe, puis respecte le choix de l'utilisateur) les docks
  # Line Profiler (tableau par ligne redondant avec les timings deja peints dans l'editeur) et
  # Debogueur (chapitre Dock2), puis VizTracer, Profileur, Historique et Terminal (item 6 du
  # 26/07/2026) - cf. TODO - Spyder - cosmetique.txt. Ne desactive PAS les greffons (profilage F10
  # intact). Cf. Commun/scripts_installation/spyder_patch/patch_spyder_hide_docks.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_hide_docks.py" \
    "$ROOT/spyder/plugins/layout/plugin.py"
  # Bouton "Agrandir le volet" dans le COIN des panneaux qui en ont l'usage, la barre globale
  # etant masquee (cf. le retrait de main_toolbar plus bas). ⚠ DOIT venir APRES
  # patch_spyder_hide_docks.py : il s'ancre sur le bloc de celui-ci.
  # Cf. Commun/scripts_installation/spyder_patch/patch_spyder_pane_maximize_button.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_pane_maximize_button.py" \
    "$ROOT/spyder/plugins/layout/plugin.py"
  # Mode DEUX ECRANS : barre « Écrans » et bouton qui bascule les dix panneaux de droite dans une
  # seconde fenetre de la MEME instance, chaque fenetre gardant sa propre disposition (demande de
  # l'utilisateur du 27/07/2026). Cf. Commun/scripts_installation/spyder_patch/patch_spyder_deux_ecrans.py.
  # L'ordre par rapport a patch_spyder_pane_maximize_button.py, qui ecrit dans le meme fichier, est
  # INDIFFERENT : verifie le 31/07/2026 en appliquant les deux dans un sens puis dans l'autre sur le
  # plugin.py de la roue d'origine - meme fichier a la ligne pres, seul l'ordre des blocs change. Le
  # commentaire precedent l'annoncait obligatoire ; c'etait une precaution, pas une mesure.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_deux_ecrans.py" \
    "$ROOT/spyder/plugins/layout/plugin.py"
  # Agrandir un panneau du SECOND ECRAN l'agrandissait dans la fenetre principale a la place (TODO
  # - Spyder - General.txt, 01/08/2026) : maximize_dockwidget() excluait ces panneaux de sa boucle
  # de selection (patch ci-dessus) et retombait donc toujours sur l'Editeur. DOIT venir APRES
  # patch_spyder_deux_ecrans.py : il patche le texte que celui-ci a deja ecrit. Cf.
  # Commun/scripts_installation/spyder_patch/patch_spyder_deux_ecrans_maximize.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_deux_ecrans_maximize.py" \
    "$ROOT/spyder/plugins/layout/plugin.py"
  # Retire "Deplacer", "Detacher" et "Fermer" du menu burger de TOUS les panneaux (item 2 du
  # 26/07/2026 ; "Ancrer" reste, invisible tant que le panneau est ancre). Avec ses deux corollaires,
  # sans lesquels l'interface se degraderait : plus de separateur orphelin en fin de menu, et bouton
  # burger masque sur les six panneaux dont le menu devient vide.
  # Cf. Commun/scripts_installation/spyder_patch/patch_spyder_dock_actions.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_dock_actions.py" \
    "$ROOT/spyder/api/widgets/main_widget.py" \
    "$ROOT/spyder/api/widgets/menus.py"
  # Boutons de VOLET dans le coin de la barre d'onglets de CHAQUE volet d'edition : separation
  # horizontale, fermer ce volet, agrandir le volet. Pas de bouton pour la separation VERTICALE :
  # l'utilisateur ne s'en sert pas souvent (27/07/2026) et elle est deja dans le burger. Le bouton
  # d'agrandissement n'etait servi que dans le volet ne du demarrage (mesure du 27/07/2026, vue
  # scindee) - d'ou le retrait de "editor" de la liste de patch_spyder_pane_maximize_button.py.
  # Retire aussi Deplacer/Detacher/Fermer de CE burger, le seul auquel patch_spyder_dock_actions.py
  # ne touchait pas. Cf. Commun/scripts_installation/spyder_patch/patch_spyder_editor_split_buttons.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_editor_split_buttons.py" \
    "$ROOT/spyder/plugins/editor/widgets/editorstack/editorstack.py" \
    "$ROOT/spyder/plugins/editor/widgets/main_widget.py"
  # Fond des widgets cliquables de la barre de statut remis a TRANSPARENT au repos, pour qu'ils ne
  # restent pas eclaircis apres un clic (effet de bord de patch_spyder_colors.py, qui a assombri la
  # barre de statut). Cf. Commun/scripts_installation/spyder_patch/patch_spyder_status_reset.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_status_reset.py" \
    "$ROOT/spyder/api/widgets/status.py"
  # Retire le prefixe "Personnalise:" (Custom:) devant le nom de l'interpreteur dans la barre de
  # statut. Cf. Commun/scripts_installation/spyder_patch/patch_spyder_interpreter_prefix.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_interpreter_prefix.py" \
    "$ROOT/spyder/plugins/ipythonconsole/widgets/status.py"
  # Liste deroulante "Recent custom interpreters" (Preferences > Interpreteur) : Qt limite a 10
  # lignes visibles par defaut, insuffisant des que la liste depasse cette taille. Cf.
  # Commun/scripts_installation/spyder_patch/patch_spyder_interpreter_max_visible.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_interpreter_max_visible.py" \
    "$ROOT/spyder/plugins/maininterpreter/confpage.py"
  # CONTOURNEMENT D'UN BUG AMONT DE SPYDER, revele par PySide6 6.11 : lancer le profileur levait
  # AttributeError: 'TreeWidgetItem' object has no attribute 'ShowIndicator', et l'arbre des resultats
  # restait vide. Le code amont lit une ENUMERATION Qt sur l'INSTANCE, ce que PySide6 n'expose plus -
  # les membres d'enumeration ne vivent que sur la CLASSE. Cf.
  # Commun/scripts_installation/spyder_patch/patch_spyder_profiler_enum_indicateur.py et
  # CachyOS/Documentation/Contournement_bugs_a_supprimer_quand_corrigés.txt.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_profiler_enum_indicateur.py" \
    "$ROOT/spyder/plugins/profiler/widgets/profiler_data_tree.py"
  # CONTOURNEMENT D'UN BUG AMONT DE SPYDER : la marge gauche de l'editeur n'affichait AUCUN
  # avertissement ni erreur. ruff est a la fois linter et formateur, et pylsp-ruff a deux cles
  # distinctes (enabled / formatEnabled) ; Spyder ecrit les deux sur `enabled`, si bien que le choix
  # d'un AUTRE formateur (black) eteignait le LINTER ruff - et pylsp desenregistre tout greffon dont
  # `enabled` est faux. Avec pyflakes coupe par ailleurs, il ne restait aucun linter et le serveur
  # publiait une liste vide. Cf. Commun/scripts_installation/spyder_patch/patch_spyder_ruff_linter.py et
  # CachyOS/Documentation/Contournement_bugs_a_supprimer_quand_corrigés.txt.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_ruff_linter.py" \
    "$ROOT/spyder/plugins/completion/providers/languageserver/provider.py"
  # AJOUT DE FONCTION (demande utilisateur du 26/07/2026) : les remarques de pylint - convention,
  # factorisation, avertissement - apparaissent dans la MARGE de l'editeur, avec DEUX exigences :
  # une SEULE passe de pylint pour les deux affichages, et des marques qui restent ANCREES sur leur
  # ligne de code quand des lignes sont inserees au-dessus.
  #
  # Le panneau « Analyse de code » reste donc le seul a lancer pylint (il a deja sa note, son
  # historique et sa sortie brute), il previent de la fin de son analyse, et le greffon
  # spyder_code_analysis reporte ses resultats sur les BLOCS DE TEXTE de l'editeur. Qt deplace un
  # bloc avec sa ligne - comme pour les points d'arret - et tout l'affichage lit le bloc, jamais un
  # numero de ligne : l'ancrage est donc acquis, a condition que Spyder cesse d'effacer ces marques
  # a chaque publication du serveur, ce que fait le premier patch ci-dessous.
  #
  # ⚠ CE QUI A ETE ABANDONNE, ET POURQUOI : activer le greffon pylint de pylsp (fait plus tot le
  # 26/07/2026) donnait bien les remarques dans la marge, mais avec des numeros de ligne FIGES - donc
  # decalees des qu'on inserait une ligne - et une seconde passe de pylint. Le greffon pylint de pylsp
  # doit rester ETEINT : ses marques, de meme source, seraient preservees elles aussi et mal ancrees.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_marques_pylint_ancrees.py" \
    "$ROOT/spyder/plugins/editor/widgets/codeeditor/lsp_mixin.py"
  python3 "$GEN_DIR/spyder_patch/patch_spyder_pylint_signal_fin.py" \
    "$ROOT/spyder/plugins/pylint/main_widget.py"
  # Memes icones dans la marge que dans le panneau « Analyse de code » (demande utilisateur du
  # 26/07/2026) : un « C » cercle pour une convention, un « R » pour une factorisation. Les erreurs et
  # les avertissements partageaient DEJA leur icone de part et d'autre - mesure faite avant d'y
  # toucher. ⚠ APRES patch_spyder_error_margin.py (ligne ~369), qui REMPLACE integralement paintEvent
  # : applique avant, ce patch serait efface sans bruit.
  # Cf. Commun/scripts_installation/spyder_patch/patch_spyder_marge_icones_pylint.py.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_marge_icones_pylint.py" \
    "$ROOT/spyder/plugins/editor/panels/linenumber.py"
  # --- Habillage SmartPythonEditor (08/08/2026, visuels fournis par l'utilisateur) --------
  # Ecran de demarrage et icone d'application : remplacement des fichiers que Spyder charge
  # deja (QSvgRenderer sur images/splash.svg ; QIcon sur images/spyder.svg pour l'icone de
  # fenetre posee par create_application). Les sources vivent dans le depot SmartOS
  # (Commun/scripts_installation/spyder_fork/) - PAS a la racine du fork, que la
  # reconstruction efface entierement.
  cp -f "$GEN_DIR/fork_files/SmartPythonEditor_splash.svg" \
        "$ROOT/spyder/images/splash.svg"
  cp -f "$GEN_DIR/fork_files/SmartPythonEditor_icon.svg" \
        "$ROOT/spyder/images/spyder.svg"
  # Le canevas du splash est en proportions fixes cote code : aligne sur le nouveau visuel.
  python3 "$GEN_DIR/spyder_patch/patch_spyder_splash_size.py" \
    "$ROOT/spyder/app/utils.py"
  # Ecran de demarrage MASQUE « pour l'instant » (demande de l'utilisateur, 05/10/2026) : sur
  # le banc hors ecran, le premier QSplashScreen.show() bloque 1,0 s fixe (fenetre visible
  # 4023 -> 3008 ms). Sous Wayland reel, NON MESURE : a juger a la trace de demarrage, et
  # retirer cette ligne si l'ecran ne coute rien la-bas. Le visuel ci-dessus reste pose (il
  # sert encore au redemarrage, restart.py).
  python3 "$GEN_DIR/spyder_patch/patch_spyder_splash_off.py" "$ROOT"
  # --- Dependances pip du fork : PySide6 par defaut (08/08/2026, demande utilisateur) ----
  # Seulement sur l'ARBRE du fork (setup.py) - un site-packages n'en a pas, et ses
  # dependances sont deja resolues. La plage vient de qt_bindings_Spyder-<v>.txt du fork
  # (releve du check_qt() officiel par l'outil de montee de version).
  if [ -f "$ROOT/setup.py" ]; then
    QT_BINDINGS_FICHIER=$(ls "$ROOT"/requirements-smartos/qt_bindings_Spyder-*.txt 2>/dev/null | head -1)
    if [ -z "$QT_BINDINGS_FICHIER" ]; then
      echo "ERREUR : qt_bindings_Spyder-*.txt introuvable dans $ROOT/requirements-smartos/" >&2
      echo "         (lancer outils/generate_spyder_requirements.sh d'abord)." >&2
      exit 1
    fi
    LIGNE_PYSIDE6=$(grep '^pyside6=' "$QT_BINDINGS_FICHIER")
    PYSIDE6_MINI=$(echo "$LIGNE_PYSIDE6" | cut -d, -f2)
    PYSIDE6_MAXI=$(echo "$LIGNE_PYSIDE6" | cut -d, -f3)
    python3 "$GEN_DIR/spyder_patch/patch_spyder_pyside6_deps.py" \
      "$ROOT/setup.py" "$PYSIDE6_MINI" "$PYSIDE6_MAXI"
  fi
