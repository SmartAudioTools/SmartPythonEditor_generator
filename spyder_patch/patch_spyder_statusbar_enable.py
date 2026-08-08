#!/usr/bin/env python3
"""Patch Spyder : ACTIVATION PAR WIDGET de la barre d'etat, avec des cases dans
Preferences > Barre d'etat.

But (TODO CachyOS "TODO - Spyder - cosmetique.txt"). La barre d'etat globale est masquee et un overlay
par editeur reprend ligne/colonne/encodage/fin de ligne. On veut neanmoins pouvoir RE-ACTIVER
individuellement chaque widget de la barre d'etat (position du curseur, encodage, fin de ligne, VCS,
LSP, lecture/ecriture, interpreteur de la console, backend Matplotlib) depuis les Preferences.

APPROCHE IDIOMATIQUE (celle que Spyder utilise deja pour Mem/CPU/horloge), plutot qu'un detournement
global de setVisible :
  - chaque widget honore l'option statusbar/<ID>/enable (defaut False = masque) ;
  - StatusBarContainer expose une case par widget via @on_conf_change et emet un signal ;
  - StatusBar (plugin) applique en direct (get_status_widget(id).setVisible(value)) ;
  - le point de disposition _organize_status_widgets consulte l'option au lieu de forcer
    setVisible(True) ;
  - les rares points de RE-affichage dynamique (VCS quand une branche existe, pythonenv/matplotlib
    a on_kernel_start) consultent aussi l'option, sinon ils ressusciteraient un widget desactive.

Ce patch REMPLACE et rend inutiles deux anciens patchs hardcodes (dont il retire les blocs si
presents, transition sans reinstallation) :
  - patch_spyder_statusbar_hide.py  (masquage en dur de lsp_status/read_write_status ; exclusion de
    pythonenv_status de la disposition) ;
  - patch_spyder_pythonenv_keep_hidden.py  (self.hide() force dans PythonEnvironmentStatus.on_kernel_start).

Fichiers modifies (chemins derives de la racine site-packages/spyder passee en argument) :
  plugins/statusbar/plugin.py                 (retrait blocs hardcodes + gate _organize + methodes + wiring)
  plugins/statusbar/container.py              (signal + une @on_conf_change par widget)
  plugins/statusbar/confpage.py               (8 cases dans la page Barre d'etat)
  config/main.py                              (8 options statusbar/<ID>/enable = False)
  plugins/editor/widgets/status.py            (VCS : gate sur l'option)
  plugins/ipythonconsole/widgets/status.py    (pythonenv + matplotlib : gate sur l'option)

Chaque modification a son propre marqueur d'idempotence. Localisation par le module ast (classe /
methode nommee) la ou c'est structurel, par texte exact la ou on retire un ancien bloc SmartOS connu.
Re-parse de CHAQUE fichier avant ecriture ; on echoue BRUYAMMENT (code 1) si un ancrage attendu est
introuvable - jamais deviner.

Usage : patch_spyder_statusbar_enable.py <racine .../site-packages/spyder>
"""
import ast
import os
import re
import sys

# Widgets exposes (ID de barre d'etat) et libelle francais de leur case.
TOGGLES = [
    ("cursor_position_status", "Position du curseur (ligne, colonne)"),
    ("encoding_status", "Encodage du fichier"),
    ("eol_status", "Type de fin de ligne"),
    ("vcs_status", "Branche de controle de version (Git)"),
    ("lsp_status", "Etat du serveur de langage (LSP)"),
    ("read_write_status", "Indicateur lecture seule / ecriture"),
    ("pythonenv_status", "Interpreteur Python de la console"),
    ("matplotlib_status", "Backend graphique Matplotlib"),
]


def require(condition, message):
    """Echoue bruyamment si une hypothese d'ancrage n'est pas verifiee."""
    if not condition:
        print(f"[patch_spyder_statusbar_enable] {message}", file=sys.stderr)
        sys.exit(1)


def reparse_or_die(source, path):
    try:
        ast.parse(source)
    except SyntaxError as error:
        print(f"[patch_spyder_statusbar_enable] {path} patche invalide ({error}) - rien ecrit.",
              file=sys.stderr)
        sys.exit(1)


def method_range(source, class_name, method_name):
    """(start, end) 1-indexes inclus de <class>.<methode>, ou None."""
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                        and item.name == method_name:
                    return item.lineno, item.end_lineno
    return None


# =====================================================================================
# 1) plugins/statusbar/plugin.py
# =====================================================================================
# Marqueur d'idempotence du bloc de methodes (PLUGIN_METHODS_BLOCK), corrige le 25/07/2026 : il
# valait "_smartos_status_enabled", mais cette chaine figure aussi dans ORG_INTERNAL_NEW /
# ORG_EXTERNAL_NEW, inseres QUELQUES LIGNES PLUS HAUT dans la meme fonction (ils APPELLENT la
# methode). Sur une installation NEUVE, le marqueur etait donc deja "present" quand patch_plugin
# testait s'il fallait ajouter les methodes : le bloc n'etait jamais insere, et l'etape suivante
# echouait sur "ancien _smartos_apply_status_enable introuvable" - le script exigeait alors le texte
# d'une version ANTERIEURE du patch, qui n'existe evidemment pas dans un Spyder fraichement
# installe. Le patch ne passait donc que sur un venv DEJA patche, jamais sur un venv neuf (constate
# en direct pendant une reinstallation, puis reproduit hors ligne sur le plugin.py vierge).
# On vise desormais la DEFINITION de la methode, presente dans le seul bloc qu'elle garde - les
# appels s'ecrivent "self._smartos_status_enabled(id_)" et ne peuvent pas la confondre.
PLUGIN_MARKER = "def _smartos_status_enabled(self, id_):"

# --- Anciens blocs hardcodes a retirer (transition depuis patch_spyder_statusbar_hide.py) ---
OLD_GUARD_HIDE = (
    "        # Widgets de barre de statut masques (SmartOS). Cf.\n"
    "        # Commun/scripts/patch_spyder_statusbar_hide.py : LSP:Python et l'indicateur\n"
    "        # lecture/ecriture (RW), juges non essentiels (demande utilisateur). Ils n'ont pas\n"
    "        # d'option de configuration, contrairement a Mem/CPU/heure (desactives par config).\n"
    '        if getattr(widget, "ID", None) in ("lsp_status", "read_write_status"):\n'
    "            # hide() est indispensable : le widget est deja cree, parente au widget principal de\n"
    '            # l\'editeur ; se contenter d\'un "return" (sans l\'ajouter a la barre de statut) le\n'
    "            # laisserait s'afficher en widget orphelin quelque part dans l'editeur. On le cache.\n"
    "            widget.hide()\n"
    "            return\n"
)
OLD_FILTER_PYENV = (
    "        # pythonenv_status retire de la disposition (SmartOS, cf.\n"
    "        # Commun/scripts/patch_spyder_statusbar_hide.py) : l'interpreteur de la console est\n"
    '        # desormais choisi depuis la barre d\'outils togglable "Interpreteur" (greffon\n'
    "        # spyder_interpreter_toolbar). On le sort de la disposition pour qu'il ne soit ni\n"
    "        # re-ajoute ni re-affiche ici (setVisible(True) plus bas ne le concerne plus). Il reste\n"
    "        # enregistre dans STATUS_WIDGETS : le plugin console peut toujours le re-chercher par ID\n"
    "        # et le retirer proprement a son teardown (ipythonconsole/plugin.py on_statusbar_teardown).\n"
    '        internal_layout = [_id for _id in internal_layout if _id != "pythonenv_status"]\n'
)

PLUGIN_IMPORT_ANCHOR = "from spyder.api.translations import _\n"
PLUGIN_IMPORT_ADD = "from spyder.api.config.decorators import on_conf_change\n"

ORG_INTERNAL_OLD = "                self.INTERNAL_WIDGETS[id_].setVisible(True)\n"
ORG_INTERNAL_NEW = (
    "                self.INTERNAL_WIDGETS[id_].setVisible(\n"
    "                    self._smartos_status_enabled(id_)\n"
    "                )\n"
)
ORG_EXTERNAL_OLD = "            self.EXTERNAL_LEFT_WIDGETS[id_].setVisible(True)\n"
ORG_EXTERNAL_NEW = (
    "            self.EXTERNAL_LEFT_WIDGETS[id_].setVisible(\n"
    "                self._smartos_status_enabled(id_)\n"
    "            )\n"
)

PLUGIN_METHODS_ANCHOR = "    # ---- Private API\n"
PLUGIN_HELPER_BLOCK = (
    "    # ---- Activation par widget de la barre d'etat (SmartOS, patch_spyder_statusbar_enable.py)\n"
    "    def _smartos_status_enabled(self, id_):\n"
    "        \"\"\"Vrai si le widget <id_> de la barre d'etat doit etre visible, d'apres l'option\n"
    "        statusbar/<id_>/enable. Defaut True pour tout widget non gere par SmartOS (update_manager,\n"
    "        inapp_appeal, mem/cpu/heure...) : aucun impact sur eux.\"\"\"\n"
    "        return bool(self.get_conf(f\"{id_}/enable\", True))\n"
    "\n"
)
# Ancien bloc apply (1re version, SANS auto-visibilite de la barre) - detecte pour la transition.
OLD_APPLY_BLOCK = (
    "    def _smartos_apply_status_enable(self, id_, value):\n"
    "        \"\"\"Applique en direct (sans redemarrage) l'activation d'un widget de la barre d'etat.\"\"\"\n"
    "        if id_ in self.STATUS_WIDGETS:\n"
    "            self.STATUS_WIDGETS[id_].setVisible(bool(value))\n"
    "\n"
)
# apply + AUTO-VISIBILITE : la barre d'etat est montree SSI au moins un widget est active (demande
# utilisateur : pas de bascule separee, la barre suit la selection des widgets).
APPLY_AND_REFRESH = (
    "    def _smartos_apply_status_enable(self, id_, value):\n"
    "        \"\"\"Applique en direct (sans redemarrage) l'activation d'un widget de la barre d'etat,\n"
    "        puis montre la barre d'etat s'il reste au moins un widget actif, la masque sinon.\"\"\"\n"
    "        if id_ in self.STATUS_WIDGETS:\n"
    "            self.STATUS_WIDGETS[id_].setVisible(bool(value))\n"
    "        self._smartos_refresh_status_bar_visibility()\n"
    "\n"
    "    def _smartos_refresh_status_bar_visibility(self):\n"
    "        \"\"\"Barre d'etat visible SSI au moins un de ses widgets est active (demande utilisateur :\n"
    "        la barre suit la selection des widgets, pas de bascule separee).\"\"\"\n"
    "        options = [\n"
    "            \"memory_usage/enable\", \"cpu_usage/enable\", \"clock/enable\",\n"
    "            \"cursor_position_status/enable\", \"encoding_status/enable\",\n"
    "            \"eol_status/enable\", \"vcs_status/enable\", \"lsp_status/enable\",\n"
    "            \"read_write_status/enable\", \"pythonenv_status/enable\",\n"
    "            \"matplotlib_status/enable\",\n"
    "        ]\n"
    "        self._statusbar.setVisible(any(self.get_conf(o, False) for o in options))\n"
    "\n"
    "    @on_conf_change(option=\"memory_usage/enable\")\n"
    "    def _smartos_on_mem_enable(self, value):\n"
    "        self._smartos_refresh_status_bar_visibility()\n"
    "\n"
    "    @on_conf_change(option=\"cpu_usage/enable\")\n"
    "    def _smartos_on_cpu_enable(self, value):\n"
    "        self._smartos_refresh_status_bar_visibility()\n"
    "\n"
    "    @on_conf_change(option=\"clock/enable\")\n"
    "    def _smartos_on_clock_enable(self, value):\n"
    "        self._smartos_refresh_status_bar_visibility()\n"
    "\n"
)
PLUGIN_METHODS_BLOCK = PLUGIN_HELPER_BLOCK + APPLY_AND_REFRESH

# before_mainwindow_visible : calcul INITIAL de la visibilite de la barre (au demarrage).
BMW_ANCHOR = (
    "        self._statusbar.setVisible(False)\n"
    "        self._organize_status_widgets()\n"
)
BMW_MARKER = "auto-visibilite initiale de la barre d'etat"
BMW_ADD = (
    "        # SmartOS : auto-visibilite initiale de la barre d'etat (patch_spyder_statusbar_enable.py)\n"
    "        # -> visible SSI au moins un widget est active (elle suit la selection des widgets).\n"
    "        self._smartos_refresh_status_bar_visibility()\n"
)

PLUGIN_CONNECT_ANCHOR = (
    "        container.sig_show_status_bar_requested.connect(\n"
    "            self.show_status_bar\n"
    "        )\n"
)
PLUGIN_CONNECT_ADD = (
    "        # SmartOS (patch_spyder_statusbar_enable.py) : activation par widget de la barre d'etat.\n"
    "        container.sig_status_widget_enable_requested.connect(\n"
    "            self._smartos_apply_status_enable\n"
    "        )\n"
)

# Gate a l'AJOUT : _organize_status_widgets ne s'execute qu'une fois au demarrage. Les widgets
# ajoutes APRES (ex. lsp_status a la connexion du serveur de langage, pythonenv/matplotlib au
# demarrage d'un noyau) echapperaient a son gate et s'afficheraient malgre enable=False. On applique
# donc l'option des l'ajout, dans add_status_widget.
ADD_ANCHOR = (
    "        self._statusbar.layout().setContentsMargins(0, 0, 0, 0)\n"
    "        self._statusbar.layout().setSpacing(0)\n"
)
ADD_GATE_MARKER = "# gate de disposition d'add_status_widget"
ADD_GATE = (
    "        # SmartOS (patch_spyder_statusbar_enable.py) : appliquer l'activation par widget des\n"
    "        # l'ajout - y compris pour les widgets ajoutes APRES _organize_status_widgets (ex.\n"
    "        # lsp_status, a la connexion du serveur de langage), qui echapperaient sinon au\n"
    "        # gate de disposition d'add_status_widget.\n"
    "        widget.setVisible(self._smartos_status_enabled(id_))\n"
)


def patch_plugin(source):
    changed = False
    # Retrait des anciens blocs hardcodes (transition depuis patch_spyder_statusbar_hide.py).
    for old in (OLD_GUARD_HIDE, OLD_FILTER_PYENV):
        if old in source:
            source = source.replace(old, "", 1)
            changed = True

    # Chaque piece est gardee independamment (patch rejouable, y compris pour ajouter une piece
    # apres coup sur une installation deja partiellement patchee).
    if PLUGIN_IMPORT_ADD not in source:
        require(PLUGIN_IMPORT_ANCHOR in source, "plugin.py : import _ introuvable.")
        source = source.replace(PLUGIN_IMPORT_ANCHOR,
                                PLUGIN_IMPORT_ANCHOR + PLUGIN_IMPORT_ADD, 1)
        changed = True

    if ORG_INTERNAL_NEW not in source:
        require(ORG_INTERNAL_OLD in source, "plugin.py : setVisible(True) interne (_organize) introuvable.")
        source = source.replace(ORG_INTERNAL_OLD, ORG_INTERNAL_NEW, 1)
        changed = True

    if ORG_EXTERNAL_NEW not in source:
        require(ORG_EXTERNAL_OLD in source, "plugin.py : setVisible(True) externe (_organize) introuvable.")
        source = source.replace(ORG_EXTERNAL_OLD, ORG_EXTERNAL_NEW, 1)
        changed = True

    if ADD_GATE_MARKER not in source:
        require(ADD_ANCHOR in source, "plugin.py : fin de add_status_widget introuvable.")
        source = source.replace(ADD_ANCHOR, ADD_ANCHOR + ADD_GATE, 1)
        changed = True

    if PLUGIN_MARKER not in source:
        require(PLUGIN_METHODS_ANCHOR in source, "plugin.py : ancre '# ---- Private API' introuvable.")
        source = source.replace(PLUGIN_METHODS_ANCHOR,
                                PLUGIN_METHODS_BLOCK + PLUGIN_METHODS_ANCHOR, 1)
        changed = True

    if "container.sig_status_widget_enable_requested.connect" not in source:
        require(PLUGIN_CONNECT_ANCHOR in source,
                "plugin.py : connexion sig_show_status_bar_requested introuvable (after_container_creation).")
        source = source.replace(PLUGIN_CONNECT_ANCHOR,
                                PLUGIN_CONNECT_ANCHOR + PLUGIN_CONNECT_ADD, 1)
        changed = True

    # Auto-visibilite de la barre : mise a niveau depuis une 1re version sans elle (transition), ou
    # deja incluse via PLUGIN_METHODS_BLOCK (fresh). Le bloc apply devient apply + refresh + 3
    # observateurs mem/cpu/heure.
    if "_smartos_refresh_status_bar_visibility" not in source:
        require(OLD_APPLY_BLOCK in source,
                "plugin.py : ancien _smartos_apply_status_enable introuvable (transition auto-visibilite).")
        source = source.replace(OLD_APPLY_BLOCK, APPLY_AND_REFRESH, 1)
        changed = True

    # Calcul initial de la visibilite de la barre au demarrage.
    if BMW_MARKER not in source:
        require(BMW_ANCHOR in source,
                "plugin.py : before_mainwindow_visible (setVisible(False)/_organize) introuvable.")
        source = source.replace(BMW_ANCHOR, BMW_ANCHOR + BMW_ADD, 1)
        changed = True
    return source, changed


# =====================================================================================
# 2) plugins/statusbar/container.py
# =====================================================================================
CONTAINER_MARKER = "sig_status_widget_enable_requested"

CONTAINER_SIGNAL_ANCHOR = (
    "    sig_show_status_bar_requested = Signal(bool)\n"
    "    \"\"\"\n"
    "    This signal is emmitted when the user wants to show/hide the\n"
    "    status bar.\n"
    "    \"\"\"\n"
)
CONTAINER_SIGNAL_ADD = (
    "\n"
    "    sig_status_widget_enable_requested = Signal(str, bool)\n"
    "    \"\"\"\n"
    "    SmartOS (patch_spyder_statusbar_enable.py) : demande d'activer/desactiver un widget de la\n"
    "    barre d'etat par son ID (cases de Preferences > Barre d'etat).\n"
    "    \"\"\"\n"
)

CONTAINER_HANDLERS_ANCHOR = "    def update_actions(self):\n"


def container_handlers_block():
    lines = [
        "    # ---- Activation par widget de la barre d'etat (SmartOS, patch_spyder_statusbar_enable.py)\n"
    ]
    for id_, _label in TOGGLES:
        lines.append(f"    @on_conf_change(option='{id_}/enable')\n")
        lines.append(f"    def _smartos_enable_{id_}(self, value):\n")
        lines.append(f"        self.sig_status_widget_enable_requested.emit('{id_}', value)\n")
        lines.append("\n")
    return "".join(lines)


def patch_container(source):
    if CONTAINER_MARKER in source:
        return source, False
    require(CONTAINER_SIGNAL_ANCHOR in source,
            "container.py : signal sig_show_status_bar_requested introuvable.")
    source = source.replace(CONTAINER_SIGNAL_ANCHOR,
                            CONTAINER_SIGNAL_ANCHOR + CONTAINER_SIGNAL_ADD, 1)
    require(CONTAINER_HANDLERS_ANCHOR in source, "container.py : 'def update_actions' introuvable.")
    source = source.replace(CONTAINER_HANDLERS_ANCHOR,
                            container_handlers_block() + CONTAINER_HANDLERS_ANCHOR, 1)
    return source, True


# =====================================================================================
# 3) plugins/statusbar/confpage.py
# =====================================================================================
CONFPAGE_MARKER = "cursor_position_status/enable"

CONFPAGE_VLAYOUT_OLD = (
    "        vlayout = QVBoxLayout()\n"
    "        vlayout.addWidget(sbar_group)\n"
    "        vlayout.addStretch(1)\n"
)


def confpage_group_block():
    lines = [
        "        # Activation par widget (SmartOS, patch_spyder_statusbar_enable.py) : une case par\n"
        "        # widget de la barre d'etat. Decoche par defaut (l'overlay par editeur reprend\n"
        "        # ligne/colonne/encodage/fin de ligne). Chaque case pilote statusbar/<ID>/enable.\n"
        "        widgets_group = QGroupBox(_(\"Widgets individuels de la barre d'etat\"))\n",
    ]
    names = []
    for i, (id_, label) in enumerate(TOGGLES):
        var = f"smartos_box_{i}"
        names.append(var)
        lines.append(f"        {var} = newcb(_(\"{label}\"), '{id_}/enable')\n")
    lines.append("        widgets_layout = QVBoxLayout()\n")
    lines.append(f"        for _b in ({', '.join(names)}):\n")
    lines.append("            widgets_layout.addWidget(_b)\n")
    lines.append("        widgets_group.setLayout(widgets_layout)\n\n")
    return "".join(lines)


CONFPAGE_VLAYOUT_NEW_TAIL = (
    "        vlayout = QVBoxLayout()\n"
    "        vlayout.addWidget(sbar_group)\n"
    "        vlayout.addWidget(widgets_group)\n"
    "        vlayout.addStretch(1)\n"
)


def patch_confpage(source):
    if CONFPAGE_MARKER in source:
        return source, False
    require(CONFPAGE_VLAYOUT_OLD in source,
            "confpage.py : bloc vlayout (sbar_group) introuvable.")
    source = source.replace(
        CONFPAGE_VLAYOUT_OLD,
        confpage_group_block() + CONFPAGE_VLAYOUT_NEW_TAIL, 1)
    return source, True


# =====================================================================================
# 4) config/main.py
# =====================================================================================
CONFIG_MARKER = "cursor_position_status/enable"
CONFIG_ANCHOR = "              'clock/timeout': 1000,\n"


def config_block():
    lines = [
        "              # Activation par widget de la barre d'etat (SmartOS,\n"
        "              # patch_spyder_statusbar_enable.py) : chaque widget honore statusbar/<ID>/enable.\n"
        "              # Defaut False = masque (l'overlay par editeur reprend ces infos) ; re-activable\n"
        "              # dans Preferences > Barre d'etat.\n"
    ]
    for id_, _label in TOGGLES:
        lines.append(f"              '{id_}/enable': False,\n")
    return "".join(lines)


def patch_config(source):
    if CONFIG_MARKER in source:
        return source, False
    require(CONFIG_ANCHOR in source, "config/main.py : ancre 'clock/timeout': 1000 introuvable.")
    source = source.replace(CONFIG_ANCHOR, CONFIG_ANCHOR + config_block(), 1)
    return source, True


# =====================================================================================
# 5) plugins/editor/widgets/status.py  (VCSStatus.process_git_data)
# =====================================================================================
VCS_MARKER = "vcs_status/enable"
VCS_OLD = "        self.setVisible(bool(branch))\n"
VCS_NEW = (
    "        # Activation du widget VCS honoree (SmartOS, patch_spyder_statusbar_enable.py) : ne\n"
    "        # l'afficher que s'il y a une branche ET que statusbar/vcs_status/enable est vrai.\n"
    "        from spyder.config.manager import CONF as _smartos_CONF\n"
    "        self.setVisible(bool(branch) and bool(\n"
    "            _smartos_CONF.get(\"statusbar\", \"vcs_status/enable\", True)))\n"
)


def patch_vcs(source):
    if VCS_MARKER in source:
        return source, False
    require(VCS_OLD in source,
            "editor/widgets/status.py : 'self.setVisible(bool(branch))' introuvable.")
    source = source.replace(VCS_OLD, VCS_NEW, 1)
    return source, True


# =====================================================================================
# 6) plugins/ipythonconsole/widgets/status.py  (pythonenv + matplotlib on_kernel_start)
# =====================================================================================
KERNEL_MARKER = "matplotlib_status/enable"

# Ancien bloc SmartOS a retirer (depuis patch_spyder_pythonenv_keep_hidden.py), s'il est present.
PYENV_OLD_SMARTOS = (
    "            # pythonenv_status maintenu masque (SmartOS, cf.\n"
    "            # Commun/scripts/patch_spyder_pythonenv_keep_hidden.py) : le selecteur\n"
    '            # d\'interpreteur est desormais dans la barre d\'outils togglable "Interpreteur"\n'
    "            # (greffon spyder_interpreter_toolbar) et le widget a ete retire de la barre de\n"
    "            # statut. set_shellwidget (ci-dessus) reste appele -> update_status et\n"
    "            # sig_interpreter_changed fonctionnent toujours ; on ne montre simplement pas le\n"
    '            # widget, sinon il apparait en orphelin (")" tronque) hors de la barre de statut.\n'
    "            self.hide()\n"
)
PYENV_NEW = (
    "            # Interpreteur de la console (SmartOS, patch_spyder_statusbar_enable.py) : affiche\n"
    "            # seulement si statusbar/pythonenv_status/enable est vrai (masque par defaut, le\n"
    "            # selecteur etant dans la barre d'outils \"Interpreteur\"). set_shellwidget ci-dessus\n"
    "            # reste appele -> update_status et sig_interpreter_changed fonctionnent.\n"
    "            from spyder.config.manager import CONF as _smartos_CONF\n"
    "            self.setVisible(bool(\n"
    "                _smartos_CONF.get(\"statusbar\", \"pythonenv_status/enable\", True)))\n"
)

SHOW_LINE = "            self.show()\n"
MPL_NEW = (
    "            # Backend Matplotlib (SmartOS, patch_spyder_statusbar_enable.py) : affiche seulement\n"
    "            # si statusbar/matplotlib_status/enable est vrai (masque par defaut).\n"
    "            from spyder.config.manager import CONF as _smartos_CONF\n"
    "            if _smartos_CONF.get(\"statusbar\", \"matplotlib_status/enable\", True):\n"
    "                self.show()\n"
    "            else:\n"
    "                self.hide()\n"
)


def replace_in_method_range(lines, source, class_name, method_name, old_line, new_block, ctx):
    """Remplace la 1ere occurrence de <old_line> DANS la plage de <class>.<methode>. Echoue si
    la methode ou la ligne est introuvable dans cette plage."""
    rng = method_range(source, class_name, method_name)
    require(rng is not None, f"{ctx} : methode {class_name}.{method_name} introuvable.")
    start, end = rng
    for i in range(start - 1, end):
        if lines[i] == old_line:
            lines[i] = new_block
            return True
    require(False, f"{ctx} : ligne cible introuvable dans {class_name}.{method_name}.")


def patch_kernel(source):
    if KERNEL_MARKER in source:
        return source, False

    # a) pythonenv : retirer l'ancien bloc SmartOS s'il est la (le remettre a l'etat d'origine
    #    'self.show()'), puis remplacer ce show() par la version qui honore l'option.
    if PYENV_OLD_SMARTOS in source:
        source = source.replace(PYENV_OLD_SMARTOS, SHOW_LINE, 1)
    lines = source.splitlines(keepends=True)
    replace_in_method_range(
        lines, source, "PythonEnvironmentStatus", "on_kernel_start",
        SHOW_LINE, PYENV_NEW, "ipythonconsole/widgets/status.py (pythonenv)")
    source = "".join(lines)

    # b) matplotlib : remplacer son self.show() (scope a MatplotlibStatus.on_kernel_start).
    lines = source.splitlines(keepends=True)
    replace_in_method_range(
        lines, source, "MatplotlibStatus", "on_kernel_start",
        SHOW_LINE, MPL_NEW, "ipythonconsole/widgets/status.py (matplotlib)")
    source = "".join(lines)
    return source, True


# =====================================================================================
# 7) plugins/completion/providers/languageserver/widgets/status.py  (LSPStatusWidget)
# =====================================================================================
# update_status() rappelle setVisible(True) quand le serveur de langage se connecte : comme le VCS,
# ce widget s'auto-affiche apres le gate de disposition. On honore donc l'option a ces deux points.
LSP_MARKER = "lsp_status/enable"
_LSP_SETVISIBLE = re.compile(r"^(\s*)self\.setVisible\(True\)\n$")


def gated_lsp(indent):
    return (
        f"{indent}# LSP (SmartOS, patch_spyder_statusbar_enable.py) : n'afficher que si\n"
        f"{indent}# statusbar/lsp_status/enable est vrai (masque par defaut).\n"
        f"{indent}from spyder.config.manager import CONF as _smartos_CONF\n"
        f"{indent}self.setVisible(bool(\n"
        f'{indent}    _smartos_CONF.get("statusbar", "lsp_status/enable", True)))\n'
    )


def patch_lsp(source):
    if LSP_MARKER in source:
        return source, False
    rng = method_range(source, "LSPStatusWidget", "update_status")
    require(rng is not None,
            "languageserver/widgets/status.py : LSPStatusWidget.update_status introuvable.")
    start, end = rng
    lines = source.splitlines(keepends=True)
    n = 0
    for i in range(start - 1, end):
        m = _LSP_SETVISIBLE.match(lines[i])
        if m:
            lines[i] = gated_lsp(m.group(1))
            n += 1
    require(n >= 1,
            "languageserver/widgets/status.py : aucun self.setVisible(True) dans update_status.")
    return "".join(lines), True


# =====================================================================================
# Orchestration
# =====================================================================================
FILES = [
    ("plugins/statusbar/plugin.py", patch_plugin),
    ("plugins/statusbar/container.py", patch_container),
    ("plugins/statusbar/confpage.py", patch_confpage),
    ("config/main.py", patch_config),
    ("plugins/editor/widgets/status.py", patch_vcs),
    ("plugins/ipythonconsole/widgets/status.py", patch_kernel),
    ("plugins/completion/providers/languageserver/widgets/status.py", patch_lsp),
]


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <racine .../site-packages/spyder>", file=sys.stderr)
        return 1
    root = sys.argv[1]
    if not os.path.isdir(root):
        print(f"[patch_spyder_statusbar_enable] racine spyder introuvable : {root}", file=sys.stderr)
        return 1

    faits = []
    for rel, fn in FILES:
        path = os.path.join(root, rel)
        try:
            with open(path, encoding="utf-8") as f:
                source = f.read()
        except OSError as error:
            print(f"[patch_spyder_statusbar_enable] {rel} illisible ({error}).", file=sys.stderr)
            return 1
        new_source, changed = fn(source)
        if changed:
            reparse_or_die(new_source, rel)
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_source)
            faits.append(rel)

    if faits:
        print("Patch activation par widget de la barre d'etat applique :")
        for rel in faits:
            print(f"    {rel}")
    else:
        print("Patch activation par widget de la barre d'etat deja applique (rien a faire).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
