#!/bin/bash
# Reconstruit le fork SmartOS de Spyder (depot GitHub "SmartPythonEditor") depuis une etiquette
# OFFICIELLE de spyder-ide/spyder, en rejouant les correctifs deja ecrits et verses dans
# spyder_patch/ - sans jamais rebaser a la main. Cf. le plan qui a
# motive ce script pour le detail du choix ("reconstruit, pas rebase").
#
# Usage : reconstruire_fork_spyder.sh [--push] [<version>]
#   --push     pousse la branche "smartos" et le tag "smartos-<version>" vers
#              github.com/SmartAudioTools/SmartPythonEditor. SANS cette option (par defaut) :
#              reconstruction strictement LOCALE, rien n'est publie - pour verifier que tous les
#              correctifs s'appliquent avant de rendre le resultat visible/installable.
#   <version>  version Spyder visee (ex. 6.1.5). Par defaut, la plus recente detectee dans
#              requirements-smartos/ du fork (meme detection que installation_SmartPythonEditor.sh).
#
# Ce que fait ce script, dans l'ordre :
#   1. Determine la version visee.
#   2. Clone (ou met a jour) /DATA/Python/FORKS/SmartPythonEditor, meme convention que les autres
#      forks locaux (black, dlib, qtpy, line_profiler, pyrtmidi).
#   3. Recupere l'etiquette officielle v<version> depuis spyder-ide/spyder (remote "upstream").
#   4. Repart d'un arbre entierement PROPRE a cette etiquette (git clean -fdx + reset --hard) :
#      aucune trace d'une reconstruction precedente ne doit survivre - c'est ce qui garantit que
#      "reconstruire" veut bien dire repartir de zero, jamais fusionner avec l'etat d'avant.
#   5. Rejoue spyder_patch/appliquer_correctifs_spyder.sh sur cet
#      arbre. Un correctif qui echoue (cible AST introuvable) arrete tout ICI : rien n'est
#      committe ni publie sur un etat partiellement patche.
#   6. Committe le resultat, tague "smartos-<version>" (deplace le tag si la meme version est
#      reconstruite a nouveau - attendu tant qu'elle n'a pas encore ete referencee par un
#      requirements_Spyder-*.txt publie ; a eviter une fois qu'elle l'a ete).
#   7. Avec --push : pousse la branche "smartos" (mise a jour a chaque reconstruction, c'est
#      elle la branche par defaut du depot) et le tag vers GitHub.
set -eu

GEN_DIR=$(dirname "$(realpath "${BASH_SOURCE[0]}")")
FORK_DIR="/DATA/Python/FORKS/SmartPythonEditor"
FORK_URL="https://github.com/SmartAudioTools/SmartPythonEditor.git"
UPSTREAM_URL="https://github.com/spyder-ide/spyder.git"
BRANCH="smartos"

PUSH=false
VERSION=""
for arg in "$@"; do
  case "$arg" in
    --push) PUSH=true ;;
    *) VERSION="$arg" ;;
  esac
done

if [ -z "$VERSION" ]; then
  # Meme detection que installation_SmartPythonEditor.sh (dernier requirements_Spyder-*_py*.txt disponible).
  REQ_FILENAME=$(find "$FORK_DIR/requirements-smartos" -maxdepth 1 -name "requirements_Spyder-*_py*.txt" ! -name "*_full.txt" -printf '%f\n' \
    | sed -E 's/^requirements_Spyder-([^_]+(_[^_]+)*)_py([0-9]+\.[0-9]+)\.txt$/\1 \3/' \
    | sort -k1,1V | tail -1 | awk '{print $1}')
  VERSION="$REQ_FILENAME"
fi
if [ -z "$VERSION" ]; then
  echo "Version Spyder introuvable (aucun requirements_Spyder-*.txt dans $FORK_DIR/requirements-smartos/)." >&2
  echo "Lancez d'abord outils/generate_spyder_requirements.sh, ou passez la version en argument." >&2
  exit 1
fi
echo "Version Spyder visee : $VERSION"

if [ ! -d "$FORK_DIR/.git" ]; then
  # Le depot GitHub peut ne pas encore exister (reconstruction locale avant toute publication,
  # cf. l'option --push) : on n'essaie de le CLONER que s'il repond deja, sinon on initialise un
  # depot local nu et on l'y raccrochera au premier "git push".
  mkdir -p "$(dirname "$FORK_DIR")"
  if git ls-remote "$FORK_URL" >/dev/null 2>&1; then
    echo "Clone initial de $FORK_URL dans $FORK_DIR..."
    git clone "$FORK_URL" "$FORK_DIR"
  else
    echo "$FORK_URL indisponible (pas encore cree ou pas d'identifiants ici) - depot local seul,"
    echo "initialise dans $FORK_DIR."
    git init -q "$FORK_DIR"
  fi
fi
cd "$FORK_DIR"
git remote get-url origin >/dev/null 2>&1 || git remote add origin "$FORK_URL"
git remote get-url upstream >/dev/null 2>&1 || git remote add upstream "$UPSTREAM_URL"
# Identite LOCALE au depot (pas --global, pour ne rien changer hors de ce fork) : meme identite
# que celle versionnee pour Mercurial (Commun/config_files/mercurial/*/hgrc), a defaut de mieux.
git config user.name >/dev/null 2>&1 || git config user.name "Baptiste de La Gorce"
git config user.email >/dev/null 2>&1 || git config user.email "baptiste.delagorce@smartaudiotools.com"

echo "Recuperation de l'etiquette officielle v${VERSION}..."
git fetch upstream "refs/tags/v${VERSION}:refs/tags/v${VERSION}" --force
if ! git rev-parse -q --verify "refs/tags/v${VERSION}^{commit}" >/dev/null; then
  echo "ERREUR : etiquette v${VERSION} introuvable dans spyder-ide/spyder." >&2
  exit 1
fi

echo "Reconstruction de la branche $BRANCH depuis v${VERSION} (arbre entierement remplace)..."
# requirements-smartos/ appartient au PRODUIT (nom dedie : l'amont a DEJA un
# dossier requirements/ a lui, ses env conda - ne jamais melanger) (version gelee, dependances, plages Qt - ecrits par
# outils/generate_spyder_requirements.sh) : il est PRESERVE a travers la reconstruction,
# comme les modules du fork spyder_line_profiler par son reappliquer_sur_amont.sh.
SAUVE_REQUIREMENTS=""
if [ -d "$FORK_DIR/requirements-smartos" ]; then
  SAUVE_REQUIREMENTS="$(mktemp -d)"
  cp -r "$FORK_DIR/requirements-smartos/." "$SAUVE_REQUIREMENTS/"
fi
git checkout -B "$BRANCH" "refs/tags/v${VERSION}"
git clean -fdx
git reset --hard "refs/tags/v${VERSION}"
if [ -n "$SAUVE_REQUIREMENTS" ]; then
  mkdir -p "$FORK_DIR/requirements-smartos"
  cp -r "$SAUVE_REQUIREMENTS/." "$FORK_DIR/requirements-smartos/"
  rm -rf "$SAUVE_REQUIREMENTS"
fi

echo "Application des correctifs SmartOS (spyder_patch/)..."
bash "$GEN_DIR/spyder_patch/appliquer_correctifs_spyder.sh" "$FORK_DIR" "$GEN_DIR"

# ----- Support de distribution (installeur autonome, cf. plan "SmartPythonEditor
# distribuable") : tout ce qu'install.sh consomme sans acces au depot SmartOS. Le code des
# GREFFONS n'est PAS ici : un depot Git par greffon dans
# /DATA/Python/FORKS/SmartPythonEditorPlugins/ (leur REFERENCE de developpement depuis le
# 08/08/2026), reference par le catalogue ci-dessous.
echo "Population du support de distribution (smartos-support/, install.sh)..."
SUPPORT="$FORK_DIR/smartos-support"
rm -rf "$SUPPORT" "$FORK_DIR/install.sh" "$FORK_DIR/smartos-requirements.txt"
mkdir -p "$SUPPORT/patchs-tiers"

cp "$GEN_DIR/fork_files/install.sh" "$FORK_DIR/install.sh"
chmod 755 "$FORK_DIR/install.sh"

# Patch du paquet tiers spyder_kernels - le SEUL qui reste applique a l'installation. Les
# correctifs du line-profiler ne se rejouent plus : ils vivent en dur dans le fork du
# greffon (depot spyder_line_profiler du catalogue, 08/08/2026), installe comme les autres.
cp "$GEN_DIR/spyder_patch/patch_spyder_kernels_profile_interrupt.py" \
   "$SUPPORT/patchs-tiers/patch_spyder_kernels_profile_interrupt.py"

# Configuration de reference : la version PURGEE committee dans derives/ (rafraichie depuis
# une machine SmartOS par outils/preparer_config_reference.py, cf. README) - une
# reconstruction n'a donc besoin de rien d'autre que ce depot.
cp -r "$GEN_DIR/derives/config-reference" "$SUPPORT/config-reference"

cp "$GEN_DIR/outils/substituer_home.sh" "$SUPPORT/substituer_home.sh"
cp "$FORK_DIR/requirements-smartos/qt_bindings_Spyder-${VERSION}.txt" "$SUPPORT/qt_bindings.txt"

# Version de Python exigee : celle du requirements gele le plus recent pour CETTE version.
PY_REQUISE=$(find "$FORK_DIR/requirements-smartos" -maxdepth 1 \
  -name "requirements_Spyder-${VERSION}_py*.txt" ! -name "*_full.txt" -printf '%f\n' \
  | sed -E 's/^.*_py([0-9]+\.[0-9]+)\.txt$/\1/' | head -1)
[ -n "$PY_REQUISE" ] || { echo "ERREUR : requirements-smartos/requirements_Spyder-${VERSION}_py*.txt introuvable dans le fork." >&2; exit 1; }
echo "$PY_REQUISE" > "$SUPPORT/python-version.txt"

# Catalogue des greffons : un depot GitHub par greffon (installables a la carte). Derive de
# la liste UNIQUE greffons-distribues.txt, partagee avec installation_Create_Repositories.sh
# (clonage des depots sur machine neuve) - un greffon s'ajoute la-bas, une seule fois.
while read -r NOM; do
  [ -n "$NOM" ] && echo "$NOM https://github.com/SmartAudioTools/$NOM.git"
done < "$GEN_DIR/fork_files/greffons-distribues.txt" \
  > "$SUPPORT/plugins-catalogue.txt"

# Requirements agrege : la pile figee du requirements SmartOS, ou la ligne spyder (PyPI ou
# fork git) devient "." - l'editeur s'installe depuis le clone lui-meme, deja patche.
sed -E 's|^spyder==.*$|.|; s|^spyder @ .*$|.|' \
  "$FORK_DIR/requirements-smartos/requirements_Spyder-${VERSION}_py${PY_REQUISE}.txt" \
  > "$FORK_DIR/smartos-requirements.txt"
grep -q '^\.$' "$FORK_DIR/smartos-requirements.txt" || {
  echo "ERREUR : la ligne spyder n'a pas ete trouvee/remplacee dans le requirements." >&2
  exit 1
}

if git diff --quiet && [ -z "$(git status --porcelain)" ]; then
  echo "ERREUR : aucun correctif n'a modifie l'arbre - appliquer_correctifs_spyder.sh a-t-il vraiment tourne ?" >&2
  exit 1
fi

git add -A
git commit -q -m "Spyder ${VERSION} + correctifs SmartOS + support de distribution"
TAG="smartos-${VERSION}"
git tag -f "$TAG"

echo ""
echo "Reconstruction LOCALE terminee : branche $BRANCH, tag $TAG, dans $FORK_DIR."

if [ "$PUSH" = true ]; then
  echo "Publication vers $FORK_URL..."
  git push origin "$BRANCH"
  git push origin "refs/tags/$TAG" --force
  echo "Publie."
else
  echo "Rien publie (defaut) : relancer avec --push pour envoyer sur GitHub."
fi

echo ""
echo "Prochaine etape, une fois publie : Commun/requirements/generate_spyder_requirements.sh"
echo "ira lire ce tag pour ecrire la reference dans requirements_Spyder-${VERSION}_py*.txt."
