#!/usr/bin/env python3
"""Ajoute (ou corrige) des traductions personnalisees SmartOS dans le catalogue gettext de Spyder
(.mo), sans recompiler tout le catalogue.

Contexte (TODO CachyOS "TODO - Spyder - cosmetique.txt" + retours utilisateur du 22/07/2026). On veut
que le bouton de filtre du dock Fichiers s'affiche "Filtrer les fichiers" (et non "les noms de
fichiers" : on filtre aussi par extension), TOUT en passant par le vrai mecanisme de traduction _()
comme les autres items du menu. Or le catalogue Spyder n'a pas de traduction pour "Filter files".
On l'ajoute donc au catalogue : ensuite `_("Filter files")` renvoie "Filtrer les fichiers".

DEUX DICTIONNAIRES, deux intentions distinctes :
  - TRANSLATIONS : msgid ABSENT du catalogue Spyder, qu'on ajoute ;
  - OVERRIDES    : msgid deja traduit par Spyder, dont la traduction livree est FAUSSE ou ambigue et
                   qu'on remplace. A n'utiliser qu'a bon escient : on ecrase le travail des
                   traducteurs de Spyder, et le remplacement vaut partout ou le msgid est utilise.
Les deux sont appliques par le meme mecanisme (comparaison de la VALEUR, pas seulement presence de
la cle), ce qui garde le script idempotent dans les deux cas.

POURQUOI PAS msgfmt : recompiler spyder.po -> spyder.mo signale des erreurs (incoherences \n dans le
.po livre) et produit un .mo de taille differente -> risque d'alterer d'AUTRES traductions. On edite
donc le .mo binaire directement pour AJOUTER une seule entree, en preservant toutes les autres a
l'octet pres. Le .mo est reecrit avec la table de chaines triee par cle et SANS table de hachage
(champ mis a 0) : gettext retombe alors sur une recherche binaire (table de hachage facultative).

Le format .mo (GNU gettext) : en-tete de 7 uint32 (magic, version, N, offset table des cles, offset
table des valeurs, taille table de hachage, offset table de hachage), puis les deux tables de N
paires (longueur, offset) et le bloc de chaines (chaque chaine suivie d'un octet NUL non compte dans
la longueur).

Usage : patch_spyder_add_translations.py <chemin vers .../LC_MESSAGES/spyder.mo>

Idempotent (si les entrees sont deja presentes, ne fait rien). Verifie le magic. Ecrit d'abord dans
un fichier temporaire relu/valide (gettext) avant de remplacer, pour ne jamais laisser un .mo casse.
Met aussi a jour le .po voisin (documentation) si present, sans le recompiler.
"""
import os
import re
import struct
import sys

# Traductions personnalisees a garantir dans le catalogue (msgid anglais -> traduction FR).
TRANSLATIONS = {
    "Filter files": "Filtrer les fichiers",
    # Overlay d'infos de fichier par panneau d'edition (cf.
    # Commun/scripts/patch_spyder_editor_file_status.py) : libelles verbeux en francais, via _().
    "Line {line}, Column {column}": "Ligne {line}, Colonne {column}",
    "encoding {encoding}": "encodage {encoding}",
    "end of line {eol}": "fin de ligne {eol}",
    # Infobulle du combo de projet, en tete du panneau Projets (cf.
    # Commun/scripts/patch_spyder_projects_toolbar.py) : le pendant du "repertoire courant" du
    # panneau Fichiers, dont il reprend la classe de combo.
    "Current project": "Projet courant",
}

# Traductions livrees par Spyder a REMPLACER (cf. docstring : on ecrase le catalogue amont).
OVERRIDES = {
    # Menu burger de l'Explorateur de variables : "Exclude all-uppercase variables" et "Exclude
    # capitalized variables" sont DEUX options differentes, mais la traduction francaise livree rend
    # les deux par "Exclure les variables en majuscule" - le menu affichait donc deux fois la meme
    # ligne, dont l'une est sans effet apparent (constate le 25/07/2026, chapitre Dock2 de
    # TODO - Spyder - cosmetique.txt). On les distingue explicitement. Les infobulles, elles, etaient
    # deja correctes et distinctes ; on ne les touche pas.
    "Exclude all-uppercase variables": "Exclure les variables tout en majuscules",
    "Exclude capitalized variables": "Exclure les variables commençant par une majuscule",
    # Dialogue "Creer un nouveau projet", page "Selectionner un repertoire" : ses deux champs
    # s'appelaient "Repertoire du projet" (le NOM a creer) et "Repertoire" (le dossier qui le
    # contiendra). Deux libelles quasi identiques pour deux choses differentes - retour utilisateur
    # du 03/08/2026 : "trop ambigu". On nomme le second par ce qu'il est.
    # "Location" n'est utilise qu'a CET endroit dans tout Spyder (verifie par grep sur
    # site-packages/spyder : une seule occurrence, projectdialog.py) : l'override ne deborde nulle
    # part ailleurs.
    "Location": "Répertoire parent",
}

# Ce que le catalogue doit contenir au final, ajouts et remplacements confondus.
WANTED = {**TRANSLATIONS, **OVERRIDES}

MAGIC_LE = 0x950412de
MAGIC_BE = 0xde120495


def read_mo(path):
    """Renvoie (liste de (cle_bytes, valeur_bytes))."""
    with open(path, "rb") as f:
        data = f.read()
    magic = struct.unpack("<I", data[:4])[0]
    if magic == MAGIC_LE:
        e = "<"
    elif magic == MAGIC_BE:
        e = ">"
    else:
        raise ValueError(f"{path} : magic .mo invalide ({magic:#010x})")
    _version, n, key_off, val_off, _hsz, _hoff = struct.unpack(e + "IIIIII", data[4:28])
    entries = []
    for i in range(n):
        klen, koff = struct.unpack(e + "II", data[key_off + i * 8: key_off + i * 8 + 8])
        vlen, voff = struct.unpack(e + "II", data[val_off + i * 8: val_off + i * 8 + 8])
        entries.append((data[koff:koff + klen], data[voff:voff + vlen]))
    return entries


def write_mo(path, entries):
    """Ecrit un .mo little-endian, cles triees, sans table de hachage."""
    entries = sorted(entries, key=lambda kv: kv[0])
    n = len(entries)
    key_tab_off = 28
    val_tab_off = key_tab_off + n * 8
    strings_off = val_tab_off + n * 8

    blob = bytearray()
    key_index = []  # (len, offset)
    val_index = []
    offset = strings_off
    for key, _val in entries:
        key_index.append((len(key), offset))
        blob += key + b"\x00"
        offset += len(key) + 1
    for _key, val in entries:
        val_index.append((len(val), offset))
        blob += val + b"\x00"
        offset += len(val) + 1

    out = bytearray()
    out += struct.pack("<IIIIIII", MAGIC_LE, 0, n, key_tab_off, val_tab_off, 0, 0)
    for klen, koff in key_index:
        out += struct.pack("<II", klen, koff)
    for vlen, voff in val_index:
        out += struct.pack("<II", vlen, voff)
    out += blob

    with open(path, "wb") as f:
        f.write(out)


def maybe_update_po(po_path):
    """Repercute les entrees sur le .po voisin (documentation ; non recompile ici).

    Les msgid ABSENTS sont ajoutes en fin de fichier ; les msgid PRESENTS (cas des OVERRIDES) voient
    leur msgstr remplace SUR PLACE - ajouter un second bloc pour le meme msgid produirait un .po
    invalide. Le remplacement n'est tente que sur la forme simple `msgid "X"\\nmsgstr "..."` sur une
    seule ligne, et seulement si elle est UNIQUE : le .po n'est que de la documentation ici (c'est le
    .mo qui est lu a l'execution), mieux vaut le laisser tel quel que de le corrompre.
    """
    if not os.path.isfile(po_path):
        return
    with open(po_path, encoding="utf-8") as f:
        po = f.read()
    modifie = False

    ajouts = []
    for msgid, msgstr in WANTED.items():
        bloc = re.search(
            r'^msgid "%s"\n(msgstr "[^"\n]*"\n)' % re.escape(msgid), po, re.M)
        if bloc is None:
            if f'\nmsgid "{msgid}"\n' not in ("\n" + po):
                ajouts.append(f'\nmsgid "{msgid}"\nmsgstr "{msgstr}"\n')
            continue  # present mais sous une forme non traitee (msgstr multiligne) : on n'y touche pas
        attendu = f'msgstr "{msgstr}"\n'
        if bloc.group(1) == attendu:
            continue
        if po.count(bloc.group(0)) != 1:
            continue  # bloc non unique : on n'y touche pas
        po = po.replace(bloc.group(0), f'msgid "{msgid}"\n{attendu}')
        modifie = True

    if ajouts:
        if not po.endswith("\n"):
            po += "\n"
        po += "\n# Traductions personnalisees SmartOS (cf. Commun/scripts/patch_spyder_add_translations.py)\n"
        po += "".join(ajouts)
        modifie = True

    if modifie:
        with open(po_path, "w", encoding="utf-8") as f:
            f.write(po)


def main():
    if len(sys.argv) != 2:
        print(f"Usage : {sys.argv[0]} <chemin vers LC_MESSAGES/spyder.mo>", file=sys.stderr)
        return 1

    mo_path = sys.argv[1]
    try:
        entries = read_mo(mo_path)
    except (OSError, ValueError) as error:
        print(f".mo illisible/invalide ({error}) - traductions non ajoutees.", file=sys.stderr)
        return 1

    keys = {k for k, _v in entries}
    courant = dict(entries)
    # Comparaison sur la VALEUR (et non la seule presence de la cle) : c'est ce qui permet de
    # traiter par le meme chemin les ajouts (cle absente) et les remplacements (cle presente avec
    # une autre traduction), tout en restant idempotent.
    a_ecrire = {m: t for m, t in WANTED.items()
                if courant.get(m.encode("utf-8")) != t.encode("utf-8")}
    if not a_ecrire:
        print("Traductions personnalisees deja presentes dans le catalogue.")
        maybe_update_po(os.path.join(os.path.dirname(mo_path), "spyder.po"))
        return 0

    a_remplacer = {m.encode("utf-8") for m in a_ecrire}
    entries = [(k, v) for k, v in entries if k not in a_remplacer]
    for msgid, msgstr in a_ecrire.items():
        entries.append((msgid.encode("utf-8"), msgstr.encode("utf-8")))

    # Ecriture dans un temporaire, relecture/validation, puis remplacement atomique.
    tmp_path = mo_path + ".smartos_tmp"
    write_mo(tmp_path, entries)
    try:
        check = dict(read_mo(tmp_path))
        for msgid, msgstr in WANTED.items():
            if check.get(msgid.encode("utf-8")) != msgstr.encode("utf-8"):
                raise ValueError(f"entree {msgid!r} absente/incorrecte apres ecriture")
        # Verifier qu'on n'a rien perdu.
        if len(check) < len(keys):
            raise ValueError("des entrees existantes ont disparu")
    except (OSError, ValueError, struct.error) as error:
        os.remove(tmp_path)
        print(f"Le .mo reecrit est invalide ({error}) - catalogue INCHANGE.", file=sys.stderr)
        return 1

    os.replace(tmp_path, mo_path)
    maybe_update_po(os.path.join(os.path.dirname(mo_path), "spyder.po"))
    print(f"Traductions personnalisees ecrites dans le catalogue ({', '.join(a_ecrire)}) : {mo_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
