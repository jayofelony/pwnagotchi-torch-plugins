from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK
import pwnagotchi.ui.fonts as fonts
import pwnagotchi.plugins as plugins
import logging
import os


class ShowPwd(plugins.Plugin):
    __author__ = '@nagy_craig'
    __version__ = '1.0.0'
    __name__ = "Show Pwd"
    __license__ = 'GPL3'
    __description__ = 'A plugin to display recently cracked passwords'
    __dependencies__ = {
        'pip': ['scapy']
    }

    def on_loaded(self):
        logging.info("show_pwd loaded")

    def on_ui_setup(self, ui):
        if ui.is_waveshare_v2():
            h_pos = (0, 95)
            v_pos = (180, 61)
        elif ui.is_waveshare_v1():
            h_pos = (0, 95)
            v_pos = (170, 61)
        elif ui.is_waveshare144lcd():
            h_pos = (0, 92)
            v_pos = (78, 67)
        elif ui.is_inky():
            h_pos = (0, 83)
            v_pos = (165, 54)
        elif ui.is_waveshare27inch():
            h_pos = (0, 153)
            v_pos = (216, 122)
        else:
            h_pos = (0, 91)
            v_pos = (180, 61)

        if self.options['orientation'] == "vertical":
            with ui._lock:
                ui.add_element('show_pwd', LabeledValue(color=BLACK, label='', value='', position=v_pos,
                                                        label_font=fonts.Bold, text_font=fonts.Small))
        else:
            # default to horizontal
            with ui._lock:
                ui.add_element('show_pwd', LabeledValue(color=BLACK, label='', value='', position=h_pos,
                                                        label_font=fonts.Bold, text_font=fonts.Small))

    def on_unload(self, ui):
        with ui._lock:
            ui.remove_element('show_pwd')

    def on_ui_update(self, ui):
        last_line = os.popen('tail -n 1 /root/handshakes/wpa-sec.cracked.potfile | awk -F: \'{print $3 " - " $4}\'').read().rstrip()
        ui.set('show_pwd', "%s" % last_line)
