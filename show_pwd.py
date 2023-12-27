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

    def on_loaded(self):
        logging.info("show_pwd loaded")

    def on_ui_setup(self, ui):
        if self.options['orientation'] == "vertical":
            ui.add_element('show_pwd', LabeledValue(color=BLACK, label='', value='', position=(180, 61),
                                                    label_font=fonts.Bold, text_font=fonts.Small))
        else:
            # default to horizontal
            ui.add_element('show_pwd', LabeledValue(color=BLACK, label='', value='', position=(0, 91),
                                                    label_font=fonts.Bold, text_font=fonts.Small))

    def on_unload(self, ui):
        with ui._lock:
            ui.remove_element('show_pwd')

    def on_ui_update(self, ui):
        last_line = os.popen('tail -n 1 /root/handshakes/wpa-sec.cracked.potfile | awk -F: \'{print $3 " - " $4}\'')
        last_line = last_line.read().rstrip()
        ui.set('show_pwd', "%s" % last_line)
