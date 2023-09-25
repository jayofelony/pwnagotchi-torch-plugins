from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK
import pwnagotchi.ui.fonts as fonts
import pwnagotchi.plugins as plugins
import logging
import os


class InternetConnectionPlugin(plugins.Plugin):
    __author__ = '@jayofelony'
    __version__ = '1.2'
    __license__ = 'GPL3'
    __description__ = 'A plugin that displays the Internet connection status on the pwnagotchi display.'
    __name__ = 'InternetConnectionPlugin'
    __help__ = """
    A plugin that displays the Internet connection status on the pwnagotchi display.
    """
    __dependencies__ = {
        'pip': ['scapy']
    }

    def on_loaded(self):
        logging.info("[Internet-Connection] plugin loaded.")

    def on_ui_setup(self, ui):
        if ui.is_waveshare35lcd():
            v_pos = (280, 61)
            with ui._lock:
                ui.add_element('connection_ip', LabeledValue(color=BLACK, label='eth0: ', value='',
                                                             position=v_pos, label_font=fonts.Bold,
                                                             text_font=fonts.Small))
        with ui._lock:
            # add a LabeledValue element to the UI with the given label and value
            # the position and font can also be specified
            ui.add_element('connection_status', LabeledValue(color=BLACK, label='WWW ', value='D',
                                                             position=(ui.width() / 2 - 35, 0),
                                                             label_font=fonts.Bold, text_font=fonts.Medium))

    def on_internet_available(self, agent):
        display = agent.view()
        display.set('connection_status', 'C')

    def on_ui_update(self, ui):
        if ui.is_wavehare35lcd():
            ip = os.popen('ip addr show eth0 | grep "inet\b" | awk \'{print $2}\' | cut -d/ -f1').read()
            ui.set('connection_ip', ip)

    def on_unload(self, ui):
        with ui._lock:
            logging.info("[Internet-Connection] plugin unloaded")
            ui.remove_element('connection_status')
            if ui.is_waveshare35lcd():
                ui.remove_element('connection_ip')
