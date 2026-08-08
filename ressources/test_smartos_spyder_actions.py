"""Banc de test du moteur d'actions (smartos_spyder_actions.py), SANS Spyder ni Qt.

    python3 Commun/scripts/test_smartos_spyder_actions.py

POURQUOI CE BANC PEUT EXISTER, ET POURQUOI C'EST LE POINT IMPORTANT
-------------------------------------------------------------------
Le moteur ne connait de Spyder que trois methodes (get_plugin, close, grab) et une constante de
chaine ("editor"). Il n'importe RIEN de Spyder. On peut donc lui donner un faux `main` et
derouler le scenario a la main, sans serveur graphique, en quelques dixiemes de seconde - la ou
un vrai lancement coute plusieurs minutes et mobilise l'unique instance de Spyder de la machine,
que d'autres sessions peuvent vouloir au meme moment.

Le vrai lancement reste indispensable, mais il ne prouve qu'UNE chose : que le branchement dans
Spyder fonctionne. Tout le reste - l'enchainement, les delais, les echecs, le rapport - se
prouve ici, et se rejoue apres chaque retouche sans rien deranger.

CE QUI EST COUVERT (26 assertions)
    enchainement d'actions instantanees, etat partage entre actions, appel de l'editeur et du
    profileur, attente satisfaite / jamais satisfaite / satisfaite par un artefact TROP ANCIEN
    (le piege : un artefact d'un run precedent ferait croire au succes), arret sur echec et
    poursuite malgre l'echec, verbe inconnu, captures et taille en pixels PHYSIQUES, fermeture
    qui aboutit et fermeture qui reste bloquee (fichier non sauvegarde), le rapport ecrit AVANT
    toute action - c'est lui qui rend un scenario fige diagnosticable - et le point de reference
    de "plus_recent_que_depart", dans les DEUX sens : un artefact anterieur a l'action
    declenchante doit etre rejete, un artefact ecrit PAR elle doit etre accepte.

Les stubs sont volontairement betes : ce qu'on teste est le moteur, pas Spyder.
"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from smartos_spyder_actions import MoteurActions

echecs = []
def ok(nom, cond, detail=""):
    print(("  OK   " if cond else "  ECHEC") + " " + nom + (("  " + str(detail)) if detail else ""))
    if not cond: echecs.append(nom)

class ImageBidon:
    def width(self): return 2560
    def height(self): return 1440
    def save(self, chemin, fmt):
        open(chemin, "wb").write(b"PNG-bidon"); return True

class GreffonBidon:
    def __init__(self, w): self._w = w
    def get_widget(self): return self._w

class WidgetBidon:
    def __init__(self, journal=None): self.journal = journal
    def grab(self): return ImageBidon()
    def analyze(self, chemin, wdir=None): self.journal.append(chemin)

class GestionnaireMarqueursBidon:
    """Tient lieu de ProfileTargetsManager : pas de veritable resolution de `def`, la ligne
    visee EST la cible (le vrai recalage sur le `def` est teste par les tests unitaires de
    profile_targets.py lui-meme, pas par le moteur de scenarios)."""
    def __init__(self):
        self.cibles = set()
    def def_line_for(self, ligne): return ligne
    def get_targets(self): return sorted(self.cibles)
    def toggle_target(self, ligne):
        if ligne in self.cibles: self.cibles.discard(ligne)
        else: self.cibles.add(ligne)

class CodeEditorBidon:
    def __init__(self, chemin, sans_gestionnaire=False):
        self.filename = chemin
        self.profile_targets_manager = None if sans_gestionnaire else GestionnaireMarqueursBidon()

class MainBidon:
    def __init__(self):
        self.visible = True
        self.charges = []
        self.profiles = []
        self.ferme = False
        self.editeur_courant = None
    def devicePixelRatioF(self): return 1.3
    def isVisible(self): return self.visible
    def close(self): self.ferme = True; self.visible = False
    def grab(self): return ImageBidon()
    def get_plugin(self, nom, error=True):
        if nom == "spyder_line_profiler": return GreffonBidon(WidgetBidon(self.profiles))
        if nom == "absent": return None
        return self
    # tient lieu de greffon Editor
    def load(self, chemin):
        self.charges.append(chemin)
        self.editeur_courant = CodeEditorBidon(chemin)
    def get_current_editor(self): return self.editeur_courant
    def analyze(self, chemin, wdir=None): self.profiles.append(chemin)

def jouer(scenario, limite=20):
    open("sc.json", "w").write(json.dumps(scenario))
    main = MainBidon()
    m = MoteurActions(main, "APP", os.path.abspath("sc.json"))
    m.debut_action = time.time()      # pas d'amorcage dans un test
    depart = time.time()
    while not m.termine and time.time() - depart < limite:
        m._pas(); time.sleep(0.02)
    return m, main, json.load(open(m.chemin_rapport))

print("1. enchainement d'actions instantanees + etat partage")
m, main, r = jouer({"actions": [
    {"action": "python", "code": "etat['a'] = 1"},
    {"action": "python", "code": "etat['b'] = etat['a'] + 1"},
    {"action": "ouvrir", "fichier": "/tmp/x.py"},
    {"action": "profiler", "fichier": "/tmp/x.py"},
]})
ok("scenario termine", m.termine, r["raison_fin"])
ok("4 actions, toutes ok", [a["etat"] for a in r["actions"]] == ["ok"]*4, [a["etat"] for a in r["actions"]])
ok("etat partage entre actions", r["etat"].get("b") == "2", r["etat"])
ok("editeur sollicite", main.charges == ["/tmp/x.py"], main.charges)
ok("profilage sollicite", main.profiles == ["/tmp/x.py"], main.profiles)
ok("devicePixelRatio consigne", r["device_pixel_ratio"] == 1.3, r["device_pixel_ratio"])

print("2. attente d'un fichier : ECHOUE si le fichier n'arrive pas")
for f in ("temoin.txt",):
    if os.path.exists(f): os.unlink(f)
m, main, r = jouer({"actions": [{"action": "attendre", "fichier": "temoin.txt", "delai": 1}]})
ok("delai depasse consigne comme tel", r["actions"][0]["etat"] == "delai_depasse", r["actions"][0])

print("3. attente d'un fichier : REUSSIT quand il arrive")
open("temoin.txt", "w").write("x")
m, main, r = jouer({"actions": [{"action": "attendre", "fichier": "temoin.txt", "delai": 2}]})
ok("condition satisfaite", r["actions"][0]["etat"] == "ok", r["actions"][0])

print("4. plus_recent_que_depart : un artefact ANCIEN ne compte pas")
os.utime("temoin.txt", (1, 1))
m, main, r = jouer({"actions": [{"action": "attendre", "fichier": "temoin.txt",
                                "plus_recent_que_depart": True, "delai": 1}]})
ok("artefact anterieur rejete", r["actions"][0]["etat"] == "delai_depasse", r["actions"][0]["message"])

print("5. arreter_si_echec")
m, main, r = jouer({"arreter_si_echec": True, "actions": [
    {"action": "python", "code": "raise RuntimeError('boum')"},
    {"action": "python", "code": "etat['jamais'] = True"},
]})
ok("premiere action en echec", r["actions"][0]["etat"] == "echec")
ok("la suivante n'est PAS jouee", len(r["actions"]) == 1, len(r["actions"]))
ok("le traceback est dans le rapport", "boum" in r["actions"][0]["message"])

print("6. sans arreter_si_echec, le scenario continue")
m, main, r = jouer({"actions": [
    {"action": "python", "code": "raise RuntimeError('boum')"},
    {"action": "python", "code": "etat['suite'] = True"},
]})
ok("les deux actions sont consignees", len(r["actions"]) == 2, len(r["actions"]))
ok("la seconde a bien tourne", r["etat"].get("suite") == "True", r["etat"])

print("7. verbe inconnu")
m, main, r = jouer({"actions": [{"action": "trifouiller"}]})
ok("verbe inconnu = echec, pas plantage", r["actions"][0]["etat"] == "echec")
ok("message explicite", "verbe inconnu" in r["actions"][0]["message"])

print("8. capture et fermeture")
m, main, r = jouer({"actions": [
    {"action": "capture", "fichier": "cap.png"},
    {"action": "capture", "fichier": "cap2.png", "widget": "spyder_line_profiler"},
    {"action": "fermer"},
]})
ok("les deux captures ecrites", os.path.exists("cap.png") and os.path.exists("cap2.png"))
ok("taille physique consignee", "2560x1440" in r["actions"][0]["message"], r["actions"][0]["message"])
ok("Spyder ferme", main.ferme and r["raison_fin"] == "Spyder ferme", r["raison_fin"])

print("9. fermeture qui n'aboutit pas (fichier non sauvegarde)")
class MainTetue(MainBidon):
    def close(self): self.ferme = True     # mais reste visible : boite modale
m, main, r = jouer({"actions": [{"action": "fermer", "delai": 1}]})
open("sc.json", "w").write(json.dumps({"actions": [{"action": "fermer", "delai": 1}]}))
mt = MoteurActions(MainTetue(), "APP", os.path.abspath("sc.json"))
mt.debut_action = time.time(); d = time.time()
while not mt.termine and time.time() - d < 5: mt._pas(); time.sleep(0.02)
rt = json.load(open(mt.chemin_rapport))
ok("blocage signale par un delai depasse, pas par un silence",
   rt["actions"][0]["etat"] == "delai_depasse" and "non sauvegarde" in rt["actions"][0]["message"],
   rt["actions"][0])

print("10. le rapport existe DES le depart (scenario fige = diagnostic possible)")
open("sc.json", "w").write(json.dumps({"actions": [{"action": "attendre", "fichier": "jamais", "delai": 30}]}))
m2 = MoteurActions(MainBidon(), "APP", os.path.abspath("sc.json"))
m2.debut_action = time.time(); m2.ecrire_rapport()
ok("rapport ecrit avant toute action", os.path.exists(m2.chemin_rapport))
m2._pas()
r2 = json.load(open(m2.chemin_rapport))
ok("l'action bloquante est visible en 'en_cours'",
   r2["actions"][0]["etat"] == "en_cours", r2["actions"])

print("11. point de reference de plus_recent_que_depart : le debut de l'ACTION PRECEDENTE")
# Un artefact ecrit AVANT l'action declenchante (bruit d'amorcage de Spyder) ne doit pas
# valider l'attente ; ecrit APRES, il doit la valider. C'est la difference entre les deux
# versions du moteur : avec le depart du SCENARIO comme reference, le premier cas passait.
open("vieux.txt", "w").write("x")
time.sleep(0.3)
m, main, r = jouer({"actions": [
    {"action": "pause", "secondes": 0.2},
    {"action": "attendre", "fichier": "vieux.txt", "plus_recent_que_depart": True, "delai": 1},
]})
ok("artefact anterieur a l'action declenchante REJETE",
   r["actions"][1]["etat"] == "delai_depasse", r["actions"][1]["message"])

open("sc.json", "w").write(json.dumps({"actions": [
    {"action": "python", "code": "open('neuf.txt','w').write('x')"},
    {"action": "attendre", "fichier": "neuf.txt", "plus_recent_que_depart": True, "delai": 2},
]}))
if os.path.exists("neuf.txt"): os.unlink("neuf.txt")
m3 = MoteurActions(MainBidon(), "APP", os.path.abspath("sc.json"))
m3.debut_action = time.time(); d3 = time.time()
while not m3.termine and time.time() - d3 < 5: m3._pas(); time.sleep(0.02)
r3 = json.load(open(m3.chemin_rapport))
ok("artefact ecrit PAR l'action precedente accepte",
   r3["actions"][1]["etat"] == "ok", r3["actions"][1]["message"])


print("12. fermeture : le rapport est finalise meme si aucun tic ne suit (signal aboutToQuit)")
# Reproduit la course constatee au 2e lancement reel : le processus Qt meurt juste apres
# main.close(), sans laisser passer un tic de scrutation. Sans le raccrochage a aboutToQuit,
# le rapport resterait fige sur "fermer / en_cours" alors que tout s'est bien passe.
class SignalBidon:
    def __init__(self): self.abonnes = []
    def connect(self, f): self.abonnes.append(f)
    def emettre(self):
        for f in self.abonnes: f()
class AppBidon:
    def __init__(self): self.aboutToQuit = SignalBidon()
class MainQuiMeurt(MainBidon):
    def __init__(self, app): super().__init__(); self.app = app
    def close(self):
        self.ferme = True
        self.app.aboutToQuit.emettre()      # Qt sort : plus aucun tic ne viendra
open("sc.json", "w").write(json.dumps({"actions": [{"action": "fermer", "delai": 5}]}))
appb = AppBidon()
m4 = MoteurActions(MainQuiMeurt(appb), appb, os.path.abspath("sc.json"))
m4.debut_action = time.time()
m4._pas()                                    # UN SEUL pas : aucun tic ulterieur
r4 = json.load(open(m4.chemin_rapport))
ok("scenario marque termine sans tic supplementaire", r4["termine"] is True, r4["raison_fin"])
ok("l'action fermer est close en ok", r4["actions"][0]["etat"] == "ok", r4["actions"][0])


print("13. poser_marqueur : pose, idempotence, et gardes-fous")
m, main, r = jouer({"actions": [
    {"action": "ouvrir", "fichier": "/tmp/x.py"},
    {"action": "poser_marqueur", "fichier": "/tmp/x.py", "ligne": 4},
    {"action": "poser_marqueur", "fichier": "/tmp/x.py", "ligne": 4},   # idempotent
]})
ok("3 actions, toutes ok", [a["etat"] for a in r["actions"]] == ["ok"]*3, r["actions"])
ok("un seul marqueur (pas de toggle-off au 2e appel)",
   main.editeur_courant.profile_targets_manager.get_targets() == [4],
   main.editeur_courant.profile_targets_manager.get_targets())

m, main, r = jouer({"actions": [
    {"action": "poser_marqueur", "fichier": "/tmp/x.py", "ligne": 4},
]})
ok("sans 'ouvrir' avant : echec explicite",
   r["actions"][0]["etat"] == "echec" and "aucun editeur courant" in r["actions"][0]["message"],
   r["actions"][0])

m, main, r = jouer({"actions": [
    {"action": "ouvrir", "fichier": "/tmp/x.py"},
    {"action": "poser_marqueur", "fichier": "/tmp/autre.py", "ligne": 4},
]})
ok("fichier different de l'editeur courant : echec explicite",
   r["actions"][1]["etat"] == "echec" and "editeur courant sur" in r["actions"][1]["message"],
   r["actions"][1])

open("sc.json", "w").write(json.dumps({"actions": [
    {"action": "poser_marqueur", "fichier": "/tmp/x.py", "ligne": 4},
]}))
main_sg = MainBidon()
main_sg.editeur_courant = CodeEditorBidon("/tmp/x.py", sans_gestionnaire=True)
m5 = MoteurActions(main_sg, "APP", os.path.abspath("sc.json"))
m5.debut_action = time.time(); d5 = time.time()
while not m5.termine and time.time() - d5 < 5: m5._pas(); time.sleep(0.02)
r5 = json.load(open(m5.chemin_rapport))
ok("editeur sans gestionnaire de marqueurs : echec explicite",
   r5["actions"][0]["etat"] == "echec" and "gestionnaire de marqueurs" in r5["actions"][0]["message"],
   r5["actions"][0])


print()
print("RESULTAT : " + ("TOUT PASSE" if not echecs else "ECHECS -> " + ", ".join(echecs)))
