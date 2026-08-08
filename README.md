# SmartPythonEditor generator

Tout ce qui permet de GENERER le fork [SmartPythonEditor](https://github.com/SmartAudioTools/SmartPythonEditor)
a partir d'une version officielle de [Spyder](https://github.com/spyder-ide/spyder) - sans rebasage,
par reconstruction complete :

    ./reconstruire.sh [--push] [<version>]

repart de l'etiquette officielle `v<version>` (par defaut : la version lue dans `requirements-smartos/` du fork),
rejoue les ~67 correctifs de `spyder_patch/` (ancres par AST, idempotents, echec bruyant si un point
d'insertion a disparu), pose l'habillage (`fork_files/`) et le support d'installation autonome
(`smartos-support/`, `install.sh`, `smartos-requirements.txt`), committe et tague `smartos-<version>`.
Sans `--push`, tout reste local.

## Arborescence

- `reconstruire.sh` - reconstruit le fork (voir ci-dessus).
- `spyder_patch/` - les correctifs du coeur de Spyder + `appliquer_correctifs_spyder.sh` qui les
  rejoue dans l'ordre sur un arbre (`<ROOT>` = clone du fork ou site-packages).
- `fork_files/` - ce qui est depose tel quel dans le fork : `install.sh` (installeur autonome),
  catalogue des greffons (`greffons-distribues.txt`, un depot GitHub par greffon), ecran de
  demarrage et icone.
- `ressources/` - fichiers consommes par les correctifs (icones, module du moteur de scenarios).
- `outils/generate_spyder_requirements.sh` - recupere la DERNIERE release officielle de Spyder
  (installeur `constructor`), gele les versions de toutes ses dependances et les plages de binding
  Qt acceptees, et les ecrit dans le depot du FORK (`SmartPythonEditor/requirements-smartos/`,
  clone a cote de ce depot) : la version du produit appartient au produit. `reconstruire.sh` les
  y PRESERVE a travers ses reconstructions. C'est l'outil de montee de version.
- `outils/preparer_config_reference.py` - regenere `derives/config-reference/` (configuration
  initiale purgee) depuis une configuration SmartOS de reference.
- `derives/` - artefacts generes committes ici : la config de reference purgee
  (`config-reference/`). Les requirements figes, eux, vivent dans le fork
  (`requirements-smartos/`).

## Montee de version de Spyder

1. `outils/generate_spyder_requirements.sh` (met a jour `requirements-smartos/` du fork).
2. `./reconstruire.sh` - les correctifs dont l'ancrage a disparu echouent bruyamment : les
   corriger dans `spyder_patch/`, relancer.
3. `./reconstruire.sh --push` puis committer/pousser ce depot.
