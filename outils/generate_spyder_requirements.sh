#!/bin/bash
# Genere requirements_Spyder-<version>_py<major.minor>.txt (et _full.txt) a partir de la derniere
# release officielle de Spyder (installeur autonome base sur `constructor`, meme outil que
# Miniconda), plutot que de laisser pip resoudre les dependances de "spyder==X.Y.Z" depuis PyPI
# (resolveur tres lent sur ce paquet, cf. TODO du 16/07/2026 - un essai a depasse 2 minutes sans
# terminer). L'installeur officiel est deja teste par l'equipe Spyder avec un jeu de versions qui
# fonctionne ensemble, donc geler les versions qu'il installe donne un requirements.txt fiable sans
# avoir a resoudre quoi que ce soit nous-memes.
#
# ⚠ L'environnement "spyder-runtime" cree par cet installeur est un environnement conda, PAS un
# venv pip classique : pip lui-meme n'y est pas installe (verifie en direct le 16/07/2026,
# `python3 -m pip` echoue avec "No module named pip"). "pip freeze"/pip-chill sont donc
# inutilisables tels quels - on interroge directement les métadonnées des paquets installes via
# le module standard importlib.metadata (fonctionne sans pip), et on determine nous-memes la
# liste "simplifiee" (dependances directes de spyder uniquement, pas les dependances de
# dependances) en lisant les Requires-Dist de spyder lui-meme.
#
# La version de Python embarquee par l'installeur officiel est incluse dans le nom des fichiers
# generes (ex. "_py3.12") - elle peut changer d'une release de Spyder a l'autre (rencontre en
# direct : Sphinx==9.1.0, present dans le bundle Spyder 6.1.5, exige Python >=3.12 - un pin qui
# aurait ete propage tel quel dans un venv pyenv reste sur une version de Python plus ancienne,
# cassant "pip install"). Plutot que de fixer une version de Python cible et corriger les paquets
# incompatibles au cas par cas, le nom du fichier permet a installation_SmartPythonEditor.sh de detecter
# automatiquement quelle version de Python utiliser pour le venv pyenv (et de l'installer via
# pyenv si absente) - toujours la MEME version que celle reellement utilisee par le bundle
# officiel, donc jamais de pin incompatible a corriger.
#
# Usage : ./generate_spyder_requirements.sh
# Ecrit dans ce meme dossier :
#   requirements_Spyder-<version>_py<major.minor>_full.txt   (toutes les distributions installees)
#   requirements_Spyder-<version>_py<major.minor>.txt        (spyder + uniquement ses dependances
#                                                              directes - equivalent a "pip freeze"
#                                                              sans les dependances de dependances)

set -eu

DEST_DIR="$(dirname "$(dirname "$(realpath "${BASH_SOURCE[0]}")")")/derives"
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

INSTALLER_URL="https://github.com/spyder-ide/spyder/releases/latest/download/Spyder-Linux-x86_64.sh"
INSTALLER="$TMP_DIR/Spyder-Linux-x86_64.sh"

echo "Telechargement de la derniere release Spyder..."
curl -sL -o "$INSTALLER" "$INSTALLER_URL"
chmod +x "$INSTALLER"

# Le numero de version est ecrit en clair dans l'en-tete du script genere par `constructor`
# (# VER:   X.Y.Z), pas besoin d'attendre la fin de l'installation pour le connaitre. Le fichier
# est un script shell auto-extractible : en-tete texte suivie d'une charge binaire concatenee -
# grep sur le fichier entier le detecte comme binaire et n'affiche que "binary file matches" sans
# la ligne elle-meme, d'ou le `head` prealable pour ne lire que l'en-tete texte.
SPYDER_VERSION=$(head -c 2000 "$INSTALLER" | grep -a -m1 "^# VER:" | awk '{print $3}')
if [ -z "$SPYDER_VERSION" ]; then
	echo "Impossible de determiner la version de Spyder depuis l'installeur." >&2
	exit 1
fi
echo "Version detectee : $SPYDER_VERSION"

INSTALL_PREFIX="$TMP_DIR/spyder_install"
echo "Installation (batch, silencieuse) dans $INSTALL_PREFIX..."
# -m : ne cree pas de raccourcis/entrees de menu (installation purement jetable, juste pour lire
# les versions installees). Ne supprime pas les alias ajoutes a .bashrc/.zshrc ("Added by Spyder"),
# l'installeur ne fournit pas d'option pour ca - nettoyage explicite ci-dessous a la place
# (constate en direct le 16/07/2026 : sans ce nettoyage, ces alias pointent vers le prefixe
# temporaire qui vient d'etre supprime des la fin du script, cassant "spyder"/"uninstall-spyder"
# dans un nouveau shell).
"$INSTALLER" -b -f -m -p "$INSTALL_PREFIX"
for RC_FILE in "$HOME/.bashrc" "$HOME/.zshrc"; do
	[ -f "$RC_FILE" ] && sed -i '/# >>> Added by Spyder >>>/,/# <<< Added by Spyder <<</d' "$RC_FILE"
done
rm -f "$HOME/.local/share/applications/spyder-install-"*.desktop

# L'installeur `constructor` cree une base + un environnement separe "spyder-runtime" (structure
# conda standard : <prefix>/envs/spyder-runtime/) - c'est LA que vivent spyder et ses dependances
# reelles, pas dans <prefix>/bin directement. Nom d'environnement stable (verifie en direct le
# 16/07/2026, convention propre a l'installeur Spyder).
RUNTIME_PYTHON="$INSTALL_PREFIX/envs/spyder-runtime/bin/python3"
if [ ! -x "$RUNTIME_PYTHON" ]; then
	echo "Python de l'environnement runtime introuvable sous $RUNTIME_PYTHON." >&2
	exit 1
fi
echo "Python runtime : $RUNTIME_PYTHON"

PY_MAJOR_MINOR=$("$RUNTIME_PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Version de Python du bundle : $PY_MAJOR_MINOR"

FULL_FILE="$DEST_DIR/requirements_Spyder-${SPYDER_VERSION}_py${PY_MAJOR_MINOR}_full.txt"
SIMPLE_FILE="$DEST_DIR/requirements_Spyder-${SPYDER_VERSION}_py${PY_MAJOR_MINOR}.txt"
# Pas de suffixe _py ici : les plages de versions de binding Qt ne dependent que de la version de
# Spyder, et les installation_SmartPythonEditor.sh y accedent en ne connaissant que $SPYDER_VERSION.
QT_FILE="$DEST_DIR/qt_bindings_Spyder-${SPYDER_VERSION}.txt"

# Requirements simplifie le plus recent deja present (hors _full) : sert de reference pour ne
# perdre aucun ajout manuel (cf. garde-fou plus bas). Quand on regenere la MEME version de Spyder,
# c'est le fichier cible lui-meme - il est lu avant d'etre reecrit, donc ses ajouts survivent.
PREV_SIMPLE=$(find "$DEST_DIR" -maxdepth 1 -type f -name 'requirements_Spyder-*_py*.txt' \
	! -name '*_full.txt' -printf '%f\n' \
	| sed -E 's/^requirements_Spyder-(.+)_py.+\.txt$/\1 &/' | sort -V | tail -1 | awk '{print $2}')
if [ -n "${PREV_SIMPLE:-}" ]; then
	PREV_SIMPLE="$DEST_DIR/$PREV_SIMPLE"
	echo "Reference pour les ajouts manuels : $PREV_SIMPLE"
else
	echo "Aucun requirements precedent trouve - rien a reporter."
fi

echo "Ecriture de $FULL_FILE, $SIMPLE_FILE et $QT_FILE..."
"$RUNTIME_PYTHON" - "$FULL_FILE" "$SIMPLE_FILE" "${PREV_SIMPLE:-}" "$QT_FILE" <<'PYEOF'
import importlib.metadata as md
import re
import sys

full_path, simple_path = sys.argv[1], sys.argv[2]
prev_path = sys.argv[3] if len(sys.argv) > 3 else ""
qt_path = sys.argv[4]


def norm(name):
    return re.sub(r"[-_.]+", "-", name).lower()


dists = {}
for d in md.distributions():
    name = d.metadata.get("Name")
    if name:
        dists[norm(name)] = d

# packaging est deja installe (dependance de spyder lui-meme) - sert ici a evaluer les marqueurs
# d'environnement des dependances directes ET les contraintes de version des extras ci-dessous.
from packaging.requirements import Requirement
from packaging.version import InvalidVersion, Version

# Extras absents du bundle officiel Spyder, ajoutes ici manuellement. Resolus EN PREMIER, avant
# d'ecrire le moindre fichier : si l'un d'eux n'a aucune version compatible avec le Spyder de ce
# bundle, mieux vaut echouer sans avoir laisse derriere soi un requirements a moitie ecrit.
#
#   setproctitle, spyder-line-profiler : utilises par nos propres correctifs sed dans
#     installation_SmartPythonEditor.sh (patch "instance unique" / "line profiler avec interpreteurs externes" -
#     rencontre en direct le 16/07/2026, leur absence du fichier genere a fait echouer ces sed,
#     "site-packages/spyder_line_profiler/..." introuvable).
#   pylsp-mypy : ajoute la verification de types mypy au linting temps reel de Spyder (TODO du
#     18/07/2026, absent par defaut de l'installeur officiel) - se greffe sur python-lsp-server
#     deja present via son point d'entree "pylsp", aucune config cote Spyder necessaire. mypy
#     lui-meme n'a pas besoin d'etre epingle : simple dependance transitive de pylsp-mypy, deja
#     resolue par pip a l'installation (meme principe que "black" pour python-lsp-server).
#   (spyder-terminal a ete RETIRE le 26/07/2026 : le plugin "Terminal" maison
#     Commun/spyder_plugins/spyder_native_terminal le remplace, avec le vrai moteur de Konsole
#     via QTermWidget, sans navigateur embarque ni serveur local - et sans les quatre patchs Qt6
#     qu'il fallait maintenir, ni les serveurs tornado qui survivaient a la fermeture de Spyder.)
#   pyxel : moteur de jeu retro requis par le plugin Spyder "Pyxel" (cf.
#     Commun/spyder_plugins/spyder_pyxel).
#
# ⚠ POURQUOI ON NE PREND PAS SIMPLEMENT LA DERNIERE VERSION PUBLIEE (ajoute le 25/07/2026) :
# certains greffons epinglent une PLAGE DE VERSIONS DE SPYDER (spyder-terminal 1.3.1 declarait
# "spyder<6.2.0,>=6.1.0" - il a depuis ete retire, mais le cas se reproduira). Ecrire la derniere
# version sans regarder produirait, des que le bundle officiel passera a une version de Spyder hors
# de cette plage, un requirements que pip refuserait d'installer - et l'echec surviendrait a
# l'installation, pas ici. On redescend donc dans l'historique des versions jusqu'a en trouver une
# qui accepte le Spyder de ce bundle, et on echoue bruyamment s'il n'y en a aucune, plutot que
# d'ecrire un fichier silencieusement inutilisable.
import json
import urllib.request

EXTRA_PACKAGES = ["setproctitle", "spyder-line-profiler", "pylsp-mypy", "pyxel"]

# Commentaires reportes tels quels dans le fichier genere, au-dessus de la ligne du paquet - le
# requirements se lit seul, sans ce script a cote.
EXTRA_COMMENTS = {
    "pyxel": (
        "# Moteur de jeu retro, requis par le plugin Spyder \"Pyxel\" (docks jeu + editeur de\n"
        "# ressources, cf. Commun/spyder_plugins/spyder_pyxel). Installe dans le venv de Spyder\n"
        "# et non ailleurs parce que c'est cet interpreteur qui execute les jeux depuis le dock,\n"
        "# et que c'est aussi celui de la console IPython : un jeu se comporte donc pareil qu'il\n"
        "# soit lance depuis le dock ou depuis la console.\n"
    ),
}

# Lignes ecrites TELLES QUELLES dans le requirements, sans passer par PyPI (ajoute le 25/07/2026).
#
# EXTRA_PACKAGES ne sait traiter qu'un nom de paquet publie : resoudre_extra() interroge
# https://pypi.org/pypi/<nom>/json pour en choisir la version. Une reference directe (URL git,
# chemin local) n'a pas de page PyPI - elle ne peut donc pas transiter par ce mecanisme, d'ou ce
# second registre, dont le contenu est recopie mot pour mot.
#
# La cle est le nom NORMALISE du paquet : elle sert a ne pas resoudre deux fois le meme paquet
# (le garde-fou "ne rien perdre" plus bas relit le requirements precedent, ou la ligne brute
# figure deja) et a l'exclure des pins compares en fin de generation.
RAW_REQUIREMENTS = {
    "spyder": (
        "# Fork SmartOS de Spyder (depot GitHub \"SmartPythonEditor\", branche par defaut\n"
        "# \"smartos\"). Contient TOUS les correctifs qui touchent Spyder lui-meme\n"
        "# (Commun/scripts_installation/spyder_patch/), deja appliques a la construction du fork -\n"
        "# rien a rejouer a l'installation. Reconstruit depuis l'etiquette officielle correspondante\n"
        "# par Commun/scripts_installation/reconstruire_fork_spyder.sh, jamais rebase a la main.\n"
        "#\n"
        "# Le tag suit la version EXACTE detectee dans ce bundle (smartos-{VERSION}) : il doit exister\n"
        "# sur le fork AVANT de generer ce requirements, sans quoi 'pip install' echouera plus tard\n"
        "# sur une reference introuvable - lancer reconstruire_fork_spyder.sh --push d'abord si besoin.\n",
        "spyder @ git+https://github.com/SmartAudioTools/SmartPythonEditor.git@smartos-{VERSION}\n",
    ),
    "line-profiler": (
        "# Fork SmartOS de line_profiler (branche par defaut du depot). Le module amont arme ses\n"
        "# evenements de line-tracing sys.monitoring en GLOBAL des qu'un profileur est actif, ce qui\n"
        "# ralentit x7 a x9 TOUT le programme et pas seulement les fonctions marquees ; le fork les\n"
        "# arme PAR OBJET-CODE (x1,00 sur le code non profile, mesure), et optimise le chemin chaud.\n"
        "# Il porte aussi le marqueur SMARTOS_LOCAL_EVENTS attendu par lp_launcher.py du plugin\n"
        "# fork du greffon spyder_line_profiler, qui sait ainsi qu'il n'a pas a re-scoper lui-meme.\n"
        "#\n"
        "# line_profiler n'est PAS une dependance directe de spyder : il arrive par\n"
        "# spyder-line-profiler ci-dessus, qui prendrait la 5.0.2 nue de PyPI. Cette ligne, etant une\n"
        "# reference directe, a la priorite dans la resolution de pip et la remplace.\n"
        "#\n"
        "# En HTTPS et non en SSH : le venv doit pouvoir se construire sur une machine ou la cle du\n"
        "# depot n'est pas deployee. Et par URL plutot qu'en editable sur /DATA/Python/FORKS, pour\n"
        "# que le venv de Spyder reste fige et reproductible - l'editable, lui, reste reserve a\n"
        "# requirements_SmartPython.in, ou le clone local EST l'arbre de developpement.\n",
        "line_profiler @ git+https://github.com/SmartAudioTools/line_profiler.git@smartos-optimisations\n",
    ),
}

# Profondeur d'historique exploree avant d'abandonner. Large de sorte qu'un plugin ayant publie
# plusieurs correctifs pour une serie de Spyder plus recente reste trouvable, mais borne pour ne
# pas parcourir tout l'historique d'un paquet ancien a chaque generation (une requete par version).
MAX_CANDIDATES = 15

spyder_version = dists["spyder"].version


def _pypi(url):
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.load(resp)


def _accepte_ce_spyder(requires_dist):
    """La version candidate accepte-t-elle le Spyder installe par ce bundle ?

    Vrai aussi quand le paquet ne mentionne pas spyder du tout (setproctitle, pyxel...) : il n'y
    a alors rien a verifier.
    """
    for raw in requires_dist or []:
        req = Requirement(raw)
        if norm(req.name) != "spyder":
            continue
        if req.marker is not None and not req.marker.evaluate({"extra": ""}):
            continue
        if not req.specifier.contains(spyder_version, prereleases=True):
            return False
    return True


def resoudre_extra(pkg_name):
    """Retourne (version, statut) - statut vaut "", "repli" ou "incompatible".

    "incompatible" ne fait PAS echouer la generation : une montee de version de Spyder ne doit
    jamais etre bloquee par un greffon en retard. La ligne est alors ecrite COMMENTEE dans le
    requirements (rien n'est perdu, tout reste visible) et rappelee dans le bilan de fin.
    """
    data = _pypi(f"https://pypi.org/pypi/{pkg_name}/json")
    if _accepte_ce_spyder(data["info"].get("requires_dist")):
        return data["info"]["version"], ""

    # La derniere version exclut ce Spyder : on remonte l'historique, du plus recent au plus
    # ancien, en ignorant les pre-versions (jamais souhaitables dans un requirements fige).
    versions = []
    for v in data.get("releases", {}):
        try:
            parsed = Version(v)
        except InvalidVersion:
            continue
        if not parsed.is_prerelease:
            versions.append(parsed)

    for parsed in sorted(versions, reverse=True)[:MAX_CANDIDATES]:
        detail = _pypi(f"https://pypi.org/pypi/{pkg_name}/{parsed}/json")
        if _accepte_ce_spyder(detail["info"].get("requires_dist")):
            return str(parsed), "repli"

    return data["info"]["version"], "incompatible"


extra_versions = {}
incompatibles = []
for pkg_name in EXTRA_PACKAGES:
    version, statut = resoudre_extra(pkg_name)
    if statut == "repli":
        print(f"  extra : {pkg_name}=={version}  (repli - la derniere version publiee exclut "
              f"spyder=={spyder_version})")
    elif statut == "incompatible":
        print(f"  extra : {pkg_name}  AUCUNE version compatible avec spyder=={spyder_version} "
              f"-> ligne COMMENTEE")
        incompatibles.append((pkg_name, version))
    else:
        print(f"  extra : {pkg_name}=={version}")
    extra_versions[norm(pkg_name)] = (pkg_name, version, statut)

# full : toutes les distributions installees par l'installeur officiel
with open(full_path, "w") as f:
    for key in sorted(dists):
        d = dists[key]
        f.write(f"{d.metadata['Name']}=={d.version}\n")

# simplifie : spyder + uniquement ses dependances directes (pas les dependances de dependances) -
# on utilise packaging.requirements pour evaluer correctement les marqueurs d'environnement
# (extras de test, plateformes autres que Linux, etc.). Les versions sont celles du bundle officiel
# telles quelles : comme le venv pyenv utilisera la MEME version de Python que ce bundle (cf. nom
# du fichier), aucun pin ne peut etre incompatible - pas besoin de verifier version par version.
spyder = dists["spyder"]
direct_deps = set()
for raw in spyder.requires or []:
    req = Requirement(raw)
    if req.marker is not None and not req.marker.evaluate({"extra": ""}):
        continue
    direct_deps.add(norm(req.name))

keep = {"spyder"} | direct_deps

# Une reference directe REMPLACE le paquet homonyme : si l'un d'eux devenait un jour dependance
# directe de spyder, l'ecrire aussi en version epinglee donnerait deux lignes contradictoires pour
# le meme paquet, et pip refuserait d'installer.
keep -= set(RAW_REQUIREMENTS)

# GARDE-FOU "ne rien perdre" (ajoute le 25/07/2026). EXTRA_PACKAGES ne protege que ce a quoi on a
# pense le jour ou on l'a ecrit : toute ligne ajoutee a la main dans un requirements genere serait
# effacee a la generation suivante, silencieusement (ce fichier est ecrit en "w"). On relit donc le
# requirements precedent et on reporte tout paquet qu'il contenait et que ce nouveau fichier ne
# reprendrait pas.
#
# Critere de report - il faut distinguer deux absences opposees :
#   - paquet absent du BUNDLE entier (pas dans dists) : il ne peut venir que d'un ajout manuel ou
#     d'EXTRA_PACKAGES -> on le reporte ;
#   - paquet present dans le bundle mais qui n'est plus une dependance DIRECTE de spyder : c'est un
#     changement d'amont legitime (Spyder a reorganise ses dependances) -> on ne le reporte pas, il
#     sera de toute facon installe comme dependance transitive.
# Le commentaire qui precedait la ligne dans l'ancien fichier est repris avec elle : il explique
# souvent pourquoi le paquet est la, et c'est precisement ce qu'on ne veut pas perdre.
prev_versions = {}
prev_comments = {}
if prev_path:
    commentaire_en_cours = []
    try:
        lignes = open(prev_path, encoding="utf-8").read().splitlines()
    except OSError:
        lignes = []
    for ligne in lignes:
        nu = ligne.strip()
        if not nu:
            commentaire_en_cours = []
            continue
        if nu.startswith("#"):
            commentaire_en_cours.append(ligne)
            continue
        if nu.startswith("-"):
            # Ligne d'OPTION pip (--extra-index-url, -e, -r...) : ce n'est pas un paquet, en tirer
            # un nom donnerait "-e" et le ferait chercher sur PyPI. Les references directes que
            # nous ecrivons nous-memes sont dans RAW_REQUIREMENTS, elles seront reecrites.
            commentaire_en_cours = []
            continue
        nom = re.split(r"[=<>!~ ]", nu, maxsplit=1)[0]
        if nom:
            prev_versions[norm(nom)] = nu
            if commentaire_en_cours:
                prev_comments[norm(nom)] = "\n".join(commentaire_en_cours) + "\n"
        commentaire_en_cours = []

reportes = []
for key, ligne in sorted(prev_versions.items()):
    if key in keep or key in extra_versions or key in dists or key in RAW_REQUIREMENTS:
        continue
    pkg_name = re.split(r"[=<>!~ ]", ligne, maxsplit=1)[0]
    version, statut = resoudre_extra(pkg_name)
    if statut == "incompatible":
        incompatibles.append((pkg_name, version))
    extra_versions[key] = (pkg_name, version, statut)
    if key in prev_comments:
        EXTRA_COMMENTS.setdefault(key, prev_comments[key])
    reportes.append(f"{pkg_name}=={version}")

if reportes:
    print("  Ajouts manuels repris du requirements precedent : " + ", ".join(reportes))

nouveaux_pins = {}
with open(simple_path, "w") as f:
    for key in sorted(keep):
        if key in dists:
            d = dists[key]
            f.write(f"{d.metadata['Name']}=={d.version}\n")
            nouveaux_pins[key] = d.version
        else:
            print(f"  (ignore, absent du bundle : {key})")
    for key in sorted(extra_versions):
        pkg_name, version, statut = extra_versions[key]
        nouveaux_pins[key] = version
        commentaire = EXTRA_COMMENTS.get(key)
        if commentaire:
            f.write(commentaire)
        if statut == "incompatible":
            # Ligne commentee, jamais supprimee : pip peut installer le reste (donc une montee de
            # version de Spyder n'est pas bloquee), et le paquet reste sous les yeux avec la raison.
            f.write(f"# EN ATTENTE : aucune version de {pkg_name} n'accepte "
                    f"spyder=={spyder_version}.\n"
                    f"# Decommenter des qu'une version compatible parait (la derniere publiee est "
                    f"la {version}).\n")
            f.write(f"# {pkg_name}=={version}\n")
        else:
            f.write(f"{pkg_name}=={version}\n")
    for key in sorted(RAW_REQUIREMENTS):
        commentaire, ligne_brute = RAW_REQUIREMENTS[key]
        # {VERSION} : seul gabarit du registre (les autres references, ex. line-profiler, sont
        # figees sur une branche stable) - substitue ici, au moment ou spyder_version est connu.
        ligne_brute = ligne_brute.replace("{VERSION}", spyder_version)
        f.write(commentaire)
        f.write(ligne_brute)
        print(f"  reference directe : {ligne_brute.strip()}")

if incompatibles:
    print("")
    print("  ⚠ NON INSTALLES (lignes commentees dans le requirements genere) :")
    for pkg_name, version in incompatibles:
        print(f"      {pkg_name} - derniere version publiee {version}, incompatible avec "
              f"spyder=={spyder_version}")

# Deuxieme moitie du garde-fou "ne rien perdre" (ajoutee le 25/07/2026 apres une generation reelle
# qui l'a rendue evidente) : le report ci-dessus rattrape les paquets ABSENTS du nouveau fichier,
# mais pas les VERSIONS changees a la main sur un paquet que le bundle fournit deja. Une telle
# modification est ecrasee sans un mot - c'est arrive ce jour-la avec Sphinx (9.0.4 dans le
# requirements, 9.1.0 dans le _full genere au meme moment : une divergence que personne n'avait vue
# depuis le 17/07/2026). Le bundle officiel reste la reference - on ne restaure pas l'ancienne
# valeur, elle serait invalidee par la suite - mais l'ecart est desormais ANNONCE, pour que le cas
# ou l'epinglage etait volontaire (contournement d'un bug) soit vu et refait sciemment.
#
# Le signalement ne vaut que si la version de Spyder est INCHANGEE : lors d'une montee de version,
# les dependances du bundle changent en masse et c'est justement l'effet recherche - lister ces
# dizaines d'ecarts noierait le seul cas interessant.
prev_spyder = prev_versions.get("spyder", "").split("==", 1)[-1].strip()
meme_version = prev_spyder == spyder_version

ecarts = []
if meme_version:
    for key, ancienne_ligne in sorted(prev_versions.items()):
        if "==" not in ancienne_ligne or key not in nouveaux_pins:
            continue
        ancienne = ancienne_ligne.split("==", 1)[1].strip()
        if ancienne and ancienne != nouveaux_pins[key]:
            ecarts.append((ancienne_ligne.split("==", 1)[0], ancienne, nouveaux_pins[key]))
elif prev_spyder:
    print(f"\n  Montee de version : spyder {prev_spyder} -> {spyder_version} (les versions du "
          f"bundle changent, ecarts non listes).")

if ecarts:
    print("")
    print("  ⚠ VERSIONS MODIFIEES par rapport au requirements precedent :")
    for pkg_name, avant, apres in ecarts:
        print(f"      {pkg_name} : {avant} -> {apres}")
    print("     Si l'une de ces versions avait ete epinglee VOLONTAIREMENT (contournement d'un")
    print("     bug), la generation vient de l'annuler - reepingler a la main et documenter.")

# --- Plages de versions des bindings Qt exigees par ce Spyder (ajoute le 25/07/2026) ------------
# Spyder refuse de DEMARRER si la version du binding Qt sort de la plage codee en dur dans
# spyder/requirements.py:check_qt() (ex. 6.1.5 : PySide6 >=6.8.0,<6.9.0 - il rejette la 6.11
# pourtant installee par defaut par "pip install PySide6"). Cette plage etait jusqu'ici recopiee a
# la main dans les TROIS installation_SmartPythonEditor.sh, donc a corriger trois fois a chaque montee de version -
# et elle avait deja diverge (RaspberryPi5 demandait "PyQt6>=6.9" SANS borne haute, alors qu'un
# PyQt6 7.x fait refuser le demarrage). On la lit donc une fois ici, dans le bundle officiel qui
# fait autorite, et les installation_SmartPythonEditor.sh la consultent.
#
# Lecture par ast plutot que par recherche de texte (convention du depot) : le format amont peut
# changer, mais alors on echoue bruyamment au lieu d'ecrire une plage fausse. find_spec("spyder")
# donne l'emplacement du paquet SANS l'importer - inutile d'executer quoi que ce soit de Spyder.
import ast
import importlib.util
import os

spec_pkg = importlib.util.find_spec("spyder")
if spec_pkg is None or not spec_pkg.submodule_search_locations:
    raise SystemExit("ERREUR : le paquet spyder est introuvable dans le bundle officiel.")
chemin_req = os.path.join(list(spec_pkg.submodule_search_locations)[0], "requirements.py")

qt_infos = None
arbre = ast.parse(open(chemin_req, encoding="utf-8").read())
for noeud in ast.walk(arbre):
    if not (isinstance(noeud, ast.FunctionDef) and noeud.name == "check_qt"):
        continue
    for sous in ast.walk(noeud):
        if not isinstance(sous, ast.Assign):
            continue
        if not any(getattr(cible, "id", None) == "qt_infos" for cible in sous.targets):
            continue
        appel = sous.value
        if isinstance(appel, ast.Call) and getattr(appel.func, "id", "") == "dict":
            qt_infos = {kw.arg: ast.literal_eval(kw.value) for kw in appel.keywords}

if not qt_infos:
    raise SystemExit(
        f"ERREUR : table qt_infos de check_qt() introuvable dans {chemin_req} - le format amont "
        f"a-t-il change ?\n"
        f"         Sans elle, impossible de connaitre les plages de versions de binding Qt "
        f"acceptees par ce Spyder."
    )

with open(qt_path, "w") as f:
    f.write("# Plages de versions des bindings Qt acceptees par Spyder "
            f"{spyder_version}.\n")
    f.write("# GENERE par generate_spyder_requirements.sh - ne pas editer a la main.\n")
    f.write("# Source : spyder/requirements.py, fonction check_qt(), du bundle officiel.\n")
    f.write("# Format : <cle qtpy>=<nom du paquet pip>,<version mini incluse>,<version maxi exclue>\n")
    for cle in sorted(qt_infos):
        paquet, (mini, maxi) = qt_infos[cle]
        f.write(f"{cle}={paquet},{mini},{maxi}\n")
        print(f"  binding : {cle} -> {paquet}>={mini},<{maxi}")
PYEOF

# Dossier de config (spyder.ini/transient.ini) attendu par installation_SmartPythonEditor.sh
# ($COMMUN_DIR/config_files/spyder_<version>/) - genere en copiant celui de la version existante la
# plus recente (settings/mise en page/etc. reportes tels quels d'une version a l'autre, comme le
# ferait une vraie mise a jour de Spyder en place), plutot que de regenerer une config neuve a
# partir de zero (perdrait les reglages/chemins d'interpreteurs deja personnalises). current_version
# mis a jour dans transient.ini ; le reste (css_path etc.) est deja recalcule dynamiquement par
# installation_SmartPythonEditor.sh apres la copie.
# Etape propre aux machines SmartOS (le dossier de config de reference de LEURS
# installations) : sans ce depot Mercurial sur la machine, on la saute simplement.
CONFIG_BASE_DIR="/DATA/Python/SmartOS/Commun/config_files"
if [ ! -d "$CONFIG_BASE_DIR" ]; then
	echo "(pas de depot SmartOS sur cette machine : etape config_files/spyder_<version> sautee)"
	CONFIG_BASE_DIR=""
fi
[ -n "$CONFIG_BASE_DIR" ] && CONFIG_BASE_DIR="$CONFIG_BASE_DIR"
NEW_CONFIG_DIR=""
if [ -n "$CONFIG_BASE_DIR" ]; then
NEW_CONFIG_DIR="$CONFIG_BASE_DIR/spyder_${SPYDER_VERSION}"
if [ -d "$NEW_CONFIG_DIR" ]; then
	echo "Dossier de config deja present : $NEW_CONFIG_DIR (rien a faire)"
else
	PREVIOUS_CONFIG_DIR=$(find "$CONFIG_BASE_DIR" -maxdepth 1 -type d -name "spyder_*" -printf '%f\n' \
		| sed -E 's/^spyder_(.+)$/\1/' | sort -V | tail -1)
	if [ -z "${PREVIOUS_CONFIG_DIR:-}" ]; then
		echo "Aucun dossier config_files/spyder_<version>/ existant a partir duquel copier - $NEW_CONFIG_DIR non cree." >&2
	else
		echo "Copie de $CONFIG_BASE_DIR/spyder_${PREVIOUS_CONFIG_DIR} vers $NEW_CONFIG_DIR..."
		cp -r "$CONFIG_BASE_DIR/spyder_${PREVIOUS_CONFIG_DIR}" "$NEW_CONFIG_DIR"
		if [ -f "$NEW_CONFIG_DIR/transient.ini" ]; then
			sed -i "s/^current_version = .*/current_version = ${SPYDER_VERSION}/" "$NEW_CONFIG_DIR/transient.ini"
		fi
	fi
fi

fi

echo "Termine :"
echo "  $FULL_FILE"
echo "  $SIMPLE_FILE"
echo "  $QT_FILE"
echo "  $NEW_CONFIG_DIR"
