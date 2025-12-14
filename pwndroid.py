import json
import logging
import asyncio
import websockets

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK


class PwnDroid(plugins.Plugin):
    __author__ = "Jayofelony"
    __version__ = "1.1.004"
    __license__ = "GPL3"
    __description__ = "Plugin for the companion app PwnDroid to display GPS data on the Pwnagotchi screen."

    LINE_SPACING = 10
    LABEL_SPACING = 0

    def __init__(self):
        self.running = False
        self.coordinates = dict()
        self.options = dict()
        self.websocket = None
        self.handshake = bool()

    def on_loaded(self):
        self.running = True
        logging.info("[PwnDroid] Plugin loaded")
        asyncio.run(self.start_fetching_location_data())
        if self.message == "Connection established":
            logging.info("[PwnDroid] Connection established")

    async def start_fetching_location_data(self):
        gateway = self.options.get("gateway", "192.168.44.1")
        uri = f"ws://{gateway}:8080"  # Replace with your WebSocket server URI
        while True:
            try:
                async with websockets.connect(uri) as websocket:
                    self.websocket = websocket
                    while True:
                        try:
                            self.message = await websocket.recv()
                            if self.message != "":  # Check if the message is not empty
                                try:
                                    self.coordinates = json.loads(self.message)
                                except json.JSONDecodeError as e:
                                    await asyncio.sleep(5)  # Retry after 5 seconds
                                    self.coordinates = {}
                            else:
                                logging.error("Received empty message from WebSocket")
                                await asyncio.sleep(5)  # Retry after 5 seconds
                        except websockets.ConnectionClosed:
                            break
            except Exception as e:
                logging.error(f"Connection error: {e}")
                await asyncio.sleep(5)  # Retry after 5 seconds

    async def close_websocket(self):
        if self.websocket:
            await self.websocket.close()
            logging.info("[PwnDroid] WebSocket connection closed")

    def on_unload(self, ui):
        self.running = False
        asyncio.run(self.close_websocket())
        with ui._lock:
            ui.remove_element('latitude')
            ui.remove_element('longitude')
            if self.options['display_altitude']:
                ui.remove_element('altitude')

    def on_handshake(self, agent, filename, access_point, client_station):
        if self.coordinates:
            logging.info("Location Data:")
            logging.info(f"Latitude: {self.coordinates['Latitude']}")
            logging.info(f"Longitude: {self.coordinates['Longitude']}")
            logging.info(f"Altitude: {self.coordinates['Altitude']}")
            logging.info(f"Speed: {self.coordinates['Speed']}")
            logging.info(f"Accuracy: {self.coordinates['Accuracy']}")
            logging.info(f"Bearing: {self.coordinates['Bearing']}")

            gps_filename = filename.replace(".pcap", ".gps.json")

            # avoid 0.000... measurements
            if all([self.coordinates.get("Latitude"), self.coordinates.get("Longitude")]):
                logging.info(f"saving GPS to {gps_filename} ({self.coordinates})")
                with open(gps_filename, "w+t") as fp:
                    json.dump(self.coordinates, fp)
            else:
                logging.info("[PwnDroid] not saving GPS. Couldn't find location.")
            self.handshake = True
            asyncio.run(self.send_message("New handshake", access_point))

    async def send_message(self, message, ap):
        while self.handshake:
            if self.websocket:
                await self.websocket.send(message)
                logging.info(f"Sent message: {message}")
                self.handshake = False

    def on_ui_setup(self, ui):
        try:
            # Configure line_spacing
            line_spacing = int(self.options['linespacing'])
        except Exception as e:
            # Set default value
            logging.debug(f"[PwnDroid] Error on_ui_setup: {e}")
            line_spacing = self.LINE_SPACING

        try:
            # Configure position
            pos = self.options['position'].split(',')
            pos = [int(x.strip()) for x in pos]
            lat_pos = (pos[0] + 5, pos[1])
            lon_pos = (pos[0], pos[1] + line_spacing)
            alt_pos = (pos[0] + 5, pos[1] + (2 * line_spacing))
        except Exception as e:
            # Set default value based on display type
            logging.debug(f"[PwnDroid] Error on_ui_setup: {e}")
            lat_pos = (127, 64)
            lon_pos = (127, 74)
            alt_pos = (127, 84)
        if self.options['display']:
            if self.options['display_altitude']:
                ui.add_element(
                    "latitude",
                    LabeledValue(
                        color=BLACK,
                        label="lat:",
                        value="",
                        position=lat_pos,
                        label_font=fonts.Small,
                        text_font=fonts.Small,
                        label_spacing=self.LABEL_SPACING,
                    ),
                )
                ui.add_element(
                    "longitude",
                    LabeledValue(
                        color=BLACK,
                        label="long:",
                        value="",
                        position=lon_pos,
                        label_font=fonts.Small,
                        text_font=fonts.Small,
                        label_spacing=self.LABEL_SPACING,
                    ),
                )
                ui.add_element(
                    "altitude",
                    LabeledValue(
                        color=BLACK,
                        label="alt:",
                        value="",
                        position=alt_pos,
                        label_font=fonts.Small,
                        text_font=fonts.Small,
                        label_spacing=self.LABEL_SPACING,
                    ),
                )
            else:
                ui.add_element(
                    "latitude",
                    LabeledValue(
                        color=BLACK,
                        label="lat:",
                        value="",
                        position=lon_pos,
                        label_font=fonts.Small,
                        text_font=fonts.Small,
                        label_spacing=self.LABEL_SPACING,
                    ),
                )
                ui.add_element(
                    "longitude",
                    LabeledValue(
                        color=BLACK,
                        label="long:",
                        value="",
                        position=alt_pos,
                        label_font=fonts.Small,
                        text_font=fonts.Small,
                        label_spacing=self.LABEL_SPACING,
                    ),
                )

    def on_ui_update(self, ui):
        if self.options['display']:
            with ui._lock:
                if self.coordinates and all([
                    # avoid 0.000... measurements
                    self.coordinates["Latitude"], self.coordinates["Longitude"]
                ]):
                    ui.set("latitude", f"{self.coordinates['Latitude']} ")
                    ui.set("longitude", f"{self.coordinates['Longitude']} ")
                    if self.options['display_altitude']:
                        ui.set("altitude", f"{self.coordinates['Altitude']:.1f}m ")
