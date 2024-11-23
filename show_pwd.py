from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK
import pwnagotchi.ui.fonts as fonts
import pwnagotchi.plugins as plugins
import logging
import os

class ShowPwd(plugins.Plugin):
    __author__ = '@jayofelony - Modified by linton85'
    __version__ = '1.0.1'
    __name__ = "Show Pwd"
    __license__ = 'GPL3'
    __description__ = 'A plugin to display recently cracked passwords'

    def __init__(self):
        self.options = dict()

    def on_loaded(self):
        logging.info("show_pwd loaded")

    def on_ui_setup(self, ui):
        # Setup for horizontal orientation with adjustable positions
        x_position = 121  # X position for both SSID and password
        ssid_y_position = 62  # Y position for SSID
        password_y_offset = 12  # Y offset for password from SSID

        ssid_position = (x_position, ssid_y_position)
        password_position = (x_position, ssid_y_position + password_y_offset)

        ui.add_element('ssid', LabeledValue(color=BLACK, label='', value='', position=ssid_position,
                                            label_font=fonts.Bold, text_font=fonts.Small))
        ui.add_element('password', LabeledValue(color=BLACK, label='', value='', position=password_position,
                                                label_font=fonts.Bold, text_font=fonts.Small))

    def on_unload(self, ui):
        with ui._lock:
            ui.remove_element('ssid')
            ui.remove_element('password')

    def on_ui_update(self, ui):
        last_line = os.popen('awk -F: \'!seen[$3]++ {print $3 " - " $4}\' /root/handshakes/wpa-sec.cracked.potfile | tail -n 1')
        last_line = last_line.read().rstrip()
        if " - " in last_line:
            ssid, password = last_line.split(" - ", 1)
        else:
            ssid = last_line
            password = ""
        ui.set('ssid', ssid)
        ui.set('password', password)