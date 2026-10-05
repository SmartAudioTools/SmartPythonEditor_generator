import json, sys, traceback
from qtpy.QtCore import QTimer
_out = {}
def _etat(nom):
    def f():
        try:
            from spyder.api.plugin_registration.registry import PLUGIN_REGISTRY as R
            e = {"mercurial": "mercurial.commands" in sys.modules, "setting_up": main.is_setting_up}
            for n in ("native_terminal", "claude_pane", "tortoisehg"):
                if n not in R:
                    e[n] = "absent"; continue
                w = R.get_plugin(n).get_widget()
                e[n] = w.nombre_de_sessions() if hasattr(w, "nombre_de_sessions") else (w._registre is not None)
            _out[nom] = e
        except Exception:
            _out[nom] = traceback.format_exc()
        json.dump(_out, open("/tmp/claude-1001/-DATA-Python-FORKS-SmartPythonEditor/dfbb5e16-ea1c-41dc-9658-653ffbf537d8/scratchpad/bed/p/verif-i.json", "w"), indent=1)
    return f
_etat("t0")()
main._verif_f = _etat("t1200")
QTimer.singleShot(1200, main._verif_f)
