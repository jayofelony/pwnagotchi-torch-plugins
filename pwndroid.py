import json
import time
import logging
import requests
import subprocess

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK


class PwnDroid(plugins.Plugin):
    __author__ = "Jayofelony"
    __version__ = "1.0.5"
    __license__ = "GPL3"
    __description__ = "Plugin for the companion app PwnDroid to display GPS data on the Pwnagotchi screen."

    LINE_SPACING = 10
    LABEL_SPACING = 0

    def __init__(self):
        self.running = False
        self.coordinates = dict()
        self.options = dict()
        self.last_update_time = 0
        self.update_interval = 120

    def on_loaded(self):
        logging.info("[PwnDroid] Plugin loaded")

    def on_ready(self, agent):
        # Check connection to 192.168.44.1:4555
        while True:
            if (subprocess.run(['bluetoothctl', 'info'], capture_output=True, text=True)).stdout.find('Connected: yes') != -1:
                self.running = True
                self.last_update_time = time.time()
                return False

    def get_location_data(self, server_url):
        try:
            response = requests.get(server_url)
            response.raise_for_status()  # Raise an exception for HTTP errors
            return response.json()  # Parse the JSON response
        except requests.exceptions.RequestException as e:
            logging.warning(f"Error connecting to the server: {e}")
            return None

    def on_handshake(self, agent, filename, access_point, client_station):
        if self.running:
            server_url = f"http://192.168.44.1:8080"
            location_data = self.get_location_data(server_url)
            if location_data:
                logging.info("Location Data:")
                logging.info(f"Latitude: {location_data['latitude']}")
                logging.info(f"Longitude: {location_data['longitude']}")
                logging.info(f"Altitude: {location_data['altitude']}")
                logging.info(f"Speed: {location_data['speed']}")
            else:
                logging.info("Failed to retrieve location data.")

            self.coordinates = location_data
            gps_filename = filename.replace(".pcap", ".gps.json")

            if self.coordinates and all([
                # avoid 0.000... measurements
                self.coordinates["latitude"], self.coordinates["longitude"]
            ]):
                logging.info(f"saving GPS to {gps_filename} ({self.coordinates})")
                with open(gps_filename, "w+t") as fp:
                    json.dump(self.coordinates, fp)
            else:
                logging.info("[PwnDroid] not saving GPS. Couldn't find location.")

    def on_ui_setup(self, ui):
        try:
            # Configure line_spacing
            line_spacing = int(self.options['linespacing'])
        except Exception:
            # Set default value
            line_spacing = self.LINE_SPACING

        try:
            # Configure position
            pos = self.options['position'].split(',')
            pos = [int(x.strip()) for x in pos]
            lat_pos = (pos[0] + 5, pos[1])
            lon_pos = (pos[0], pos[1] + line_spacing)
            alt_pos = (pos[0] + 5, pos[1] + (2 * line_spacing))
            spd_pos = (pos[0], pos[1] + (3 * line_spacing))
        except Exception:
            # Set default value based on display type
            lat_pos = (127, 64)
            lon_pos = (127, 74)
            alt_pos = (127, 84)
            spd_pos = (127, 94)
        if self.options['lat']:
            ui.add_element(
                "latitude",
                LabeledValue(
                    color=BLACK,
                    label="lat:",
                    value="-",
                    position=lat_pos,
                    label_font=fonts.Small,
                    text_font=fonts.Small,
                    label_spacing=self.LABEL_SPACING,
                ),
            )
        if self.options['long']:
            ui.add_element(
                "longitude",
                LabeledValue(
                    color=BLACK,
                    label="long:",
                    value="-",
                    position=lon_pos,
                    label_font=fonts.Small,
                    text_font=fonts.Small,
                    label_spacing=self.LABEL_SPACING,
                ),
            )
        if self.options['alt']:
            ui.add_element(
                "altitude",
                LabeledValue(
                    color=BLACK,
                    label="alt:",
                    value="-",
                    position=alt_pos,
                    label_font=fonts.Small,
                    text_font=fonts.Small,
                    label_spacing=self.LABEL_SPACING,
                ),
            )
        if self.options['spd']:
            ui.add_element(
                "speed",
                LabeledValue(
                    color=BLACK,
                    label="spd:",
                    value="-",
                    position=spd_pos,
                    label_font=fonts.Small,
                    text_font=fonts.Small,
                    label_spacing=self.LABEL_SPACING,
                ),
            )

    def on_unload(self, ui):
        with ui._lock:
            if self.options['lat']:
                ui.remove_element('latitude')
            if self.options['long']:
                ui.remove_element('longitude')
            if self.options['alt']:
                ui.remove_element('altitude')
            if self.options['spd']:
                ui.remove_element('speed')

    def on_ui_update(self, ui):
        """Update the UI elements and fetch new coordinates if the interval has passed."""
        if self.options['display']:
            current_time = time.time()
            if self.running and current_time - self.last_update_time >= self.update_interval:
                server_url = f"http://192.168.44.1:8080"
                location_data = self.get_location_data(server_url)
                if location_data:
                    self.coordinates = location_data
                    logging.info("[PwnDroid] Updated coordinates successfully.")
                else:
                    logging.info("[PwnDroid] Failed to retrieve updated coordinates.")
                self.last_update_time = current_time
            with ui._lock:
                if self.coordinates and all([
                    # avoid 0.000... measurements
                    self.coordinates["latitude"], self.coordinates["longitude"]
                ]):
                    if self.options['lat']:
                        ui.set("latitude", f"{self.coordinates['latitude']:.4f} ")
                    if self.options['long']:
                        ui.set("longitude", f"{self.coordinates['longitude']:.4f} ")
                    if self.options['alt']:
                        ui.set("altitude", f"{self.coordinates['altitude']:.1f}m ")
                    if self.options['spd']:
                        ui.set("speed", f"{self.coordinates['speed']:.1f}m ")
