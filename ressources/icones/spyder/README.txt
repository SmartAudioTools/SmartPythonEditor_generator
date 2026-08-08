Icônes personnalisées déployées dans les images de Spyder
========================================================

Ce dossier contient les icônes SVG que nos patchs font utiliser à Spyder à la place des siennes.
`CachyOS/Installation/installation_Spyder.sh` les copie dans le venv, sous
`<venv>/lib/pythonX.Y/site-packages/spyder/images/dark/`.

POURQUOI CE DOSSIER, ET POURQUOI `dark/`
    Le gestionnaire d'images de Spyder (`spyder/utils/image_path_manager.py`) parcourt
    `spyder/images/` au démarrage et indexe chaque fichier PAR SON NOM SANS EXTENSION. Un fichier
    déposé là devient donc utilisable par `self.create_icon("<nom du fichier>")` depuis n'importe
    quel widget, sans autre déclaration. Deux détails du parcours comptent :
      - les sous-dossiers `light/` et `dark/` sont FILTRÉS selon le thème actif : celui qui ne
        correspond pas est ignoré. Nos icônes étant en BLANC PUR, elles n'ont de sens que sur le
        thème sombre — c'est donc dans `dark/` qu'elles vont. Sur un thème clair, Spyder rendra son
        icône « not_found » plutôt qu'un dessin blanc invisible : c'est le bon échec, il se voit.
      - un nom déjà indexé est écrasé AVEC UN AVERTISSEMENT sur stderr. Or la console interne de
        Spyder traite toute ligne de stderr comme une erreur et ouvre une fenêtre « problème
        interne ». Ne JAMAIS AJOUTER un fichier portant le nom d'une icône déjà livrée par Spyder :
        pour reprendre un nom existant, on ÉCRASE son fichier (cf. `profiler.svg` ci-dessous), ce qui
        ne crée pas de doublon. Déposer le même fichier dans `dark/` ET `light/` ne déclenche
        d'ailleurs aucun avertissement : le parcours saute le dossier du thème inactif.


TROIS CAS DE FIGURE POUR REMPLACER UNE ICÔNE, ET UN SEUL DEMANDE UN PATCH
    Établi le 26/07/2026 en remplaçant « Nouveau fichier ». Savoir DUQUEL on relève est la première
    chose à déterminer, faute de quoi on dépose un fichier qui ne sera jamais servi.

    1. NOM NEUF, inventé par nous — `window_full_screen`, `window_collapse`.
       Déposer le fichier suffit ; c'est notre code qui le nomme, par `create_icon("<nom>")`.

    2. NOM QUE SPYDER RÉSOUT DÉJÀ PAR SON DOSSIER D'IMAGES — `profiler`.
       Écraser son fichier suffit. Aucun patch : l'action continue de demander le même nom, et le
       gestionnaire d'images sert le nôtre.

    3. NOM DÉCLARÉ COMME GLYPHE DE POLICE — `filenew` (`mdi.file`), et c'est le cas de la MAJORITÉ
       des icônes de Spyder. Elles vivent dans le dictionnaire `_qtaargs` de
       `spyder/utils/icon_manager.py`, et n'ont AUCUN chemin : ce sont des caractères de
       `qtawesome/fonts/materialdesignicons*.ttf`. Or `IconManager.icon()` consulte ce dictionnaire
       AVANT le dossier d'images, et ne se rabat sur le fichier que sur `KeyError`. Déposer un
       fichier du même nom ne sert donc à RIEN tant que l'entrée est là.
       → `Commun/scripts_installation/spyder_patch/patch_spyder_icones_fichier.py` retire l'entrée. Ajouter un nom à sa liste
         `ICONES_FICHIER` suffit à basculer une icône de plus.
       → Pour PARTIR du dessin existant plutôt que d'une page blanche,
         `Commun/scripts_installation/glyphe_qtawesome_en_svg.py` extrait le contour exact du glyphe en SVG
         modifiable (par `QPainterPath.addText`, donc sans vectorisation approximative).

    ⚠ Le cas 3 a un prix, à accepter en connaissance de cause : une icône de fichier NE SUIT PLUS LE
    THÈME. Un glyphe était recolorié à la volée (`color=MAIN_FG_COLOR`) ; un SVG porte ses couleurs.
    L'état grisé reste correct — `get_icon()` repeint en `COLOR_DISABLED` — mais un dessin conçu pour
    le thème sombre restera tel quel sur le thème clair. D'où la règle : ne basculer que les icônes
    explicitement demandées, jamais « pendant qu'on y est ».

⚠ LE PIÈGE À NE PAS REFAIRE : LES MARQUEURS SVG NE SONT PAS RENDUS PAR Qt
    Les pointes de flèche dessinées dans Inkscape sont des éléments `<marker>` référencés par
    `marker-end`, et une largeur de trait `fill:context-stroke`. Le moteur SVG de Qt (SVG Tiny 1.2)
    ne connaît NI les marqueurs NI `context-stroke` : il les ignore silencieusement. Les deux
    icônes de ce dossier, telles qu'elles sortaient d'Inkscape, s'affichaient donc comme deux
    simples traits diagonaux, sans aucune flèche — constaté le 26/07/2026 en rendant les fichiers
    par Qt, PAS en les regardant dans Inkscape, où ils étaient parfaits.

    Les fichiers de CE dossier sont la version APLATIE, celle qui se rend correctement. Les
    originaux modifiables sont dans `sources_inkscape/`. Après toute retouche d'un original,
    REGÉNÉRER l'aplati :

        inkscape --actions="select-all:all;object-stroke-to-path;\
                            export-filename:<sortie>.svg;export-plain-svg;export-do" \
                 sources_inkscape/<nom>.svg

    C'est bien `object-stroke-to-path` (Chemin > Contour en chemin) et NON `object-to-path`
    (Objet en chemin) : ce dernier ne touche pas aux marqueurs, l'icône reste sans flèches, et
    l'échec est muet.


TAILLE DU DESSIN DANS SON VIEWBOX : 12 UNITÉS SUR 16, SOIT 2 DE MARGE
    Mesuré le 26/07/2026, l'étendue d'encre (boîte englobante des pixels non transparents, rapportée
    au côté du rendu) des icônes voisines dans la barre d'outils :

        maximize.svg de Spyder, celle que l'on remplace .... 75 %
        mdi.stethoscope (bouton Docteur) ................... 73 %
        collapse / expand, fromcursor ...................... 72-73 %
        profiler ........................................... 62 %

    Nos deux icônes, telles que dessinées au départ, occupaient 100 % : coin à coin, donc
    visiblement plus grosses que toutes leurs voisines. Le viewBox n'y était pour rien - Spyder rend
    l'icône à la taille du bouton quel que soit le viewBox, seule compte la PART OCCUPÉE à
    l'intérieur.

    LA RÈGLE : un dessin de 12 × 12 unités centré dans le viewBox 16 × 16, soit 2 unités de marge
    tout autour - exactement ce que fait `maximize.svg`, l'icône de Spyder que l'on remplace.

    Cette taille est portée par la SOURCE (redessinée en conséquence le 26/07/2026) : la conversion
    ci-dessus n'y touche pas, et l'aplati la reproduit tel quel. C'est le bon endroit pour elle - une
    mise à l'échelle appliquée après coup sur l'aplati diviserait aussi l'épaisseur du trait, et il
    faudrait la rattraper dans la source de toute façon.

    Si un jour une source ne peut pas être redessinée, le repli consiste à envelopper le contenu de
    l'aplati (tout ce qui suit `</defs>`) dans `<g transform="translate(2,2) scale(0.75)">` - mais
    c'est un pis-aller, pour la raison ci-dessus.

    ⚠ La mesure se fait sur l'ENCRE, pas sur le viewBox ni sur les dimensions déclarées : deux
    icônes de même viewBox peuvent occuper l'une 100 % et l'autre 60 % de leur cadre. Se rendre à
    l'évidence par la mesure, pas par la lecture du fichier.

VÉRIFIER LE SENS DES FLÈCHES SANS SE FIER À L'ŒIL
    Les deux dessins ne diffèrent que par l'orientation des pointes, et il est arrivé qu'une source
    en écrase l'autre sans que rien ne le signale (26/07/2026 : les deux fichiers sont devenus
    identiques à l'octet près, tous deux portant le dessin rentrant). Un contrôle objectif existe :
    dans la version SORTANTE, ce sont les POINTES - larges - qui occupent les extrémités de la
    diagonale ; dans la RENTRANTE, ce sont les QUEUES, fines. La part d'encre contenue dans le coin
    haut-droit de la boîte du dessin (fenêtre de 28 % du côté) les sépare nettement :

        sortante ..... ~37 % de l'encre dans ce coin
        rentrante .... ~21 %

    Deux fichiers qui donnent la même valeur sont le même dessin.

    La version aplatie est VERSIONNÉE plutôt que reconstruite à l'installation, contrairement à
    l'habitude du dépôt. Raison : la conversion exige Inkscape, qu'on ne veut pas rendre nécessaire
    à l'installation de Spyder sur les trois distributions, et qui écrit du bruit GTK sur stderr.

    VÉRIFIER une icône se fait en la rendant par Qt sur le fond réel de l'interface (#232627), pas
    en l'ouvrant dans un éditeur de dessin. Un rendu correct dans Inkscape ne prouve rien.


CE QUE CHAQUE ICÔNE REMPLACE

    window_full_screen.svg   deux flèches vers l'EXTÉRIEUR — « Agrandir le volet courant »
    window_collapse.svg      deux flèches vers l'INTÉRIEUR — même action, volet déjà agrandi
    profiler.svg             horloge VIOLETTE — remplace l'horloge rouge livrée par Spyder (cas 2)
    filenew.svg              document portant « New » — « Nouveau fichier », remplace le glyphe
                             `mdi.file` (cas 3 : demande le patch qui retire l'entrée `_qtaargs`)

    Les deux servent à la MÊME action (`LayoutContainerActions.MaximizeCurrentDockwidget`), dont
    Spyder ne changeait pas l'icône selon l'état. C'est
    `Commun/scripts_installation/spyder_patch/patch_spyder_maximize_icons.py` qui pose la première et fait basculer sur la
    seconde quand le volet est agrandi.
