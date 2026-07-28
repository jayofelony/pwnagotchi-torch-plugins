import json
import logging
import asyncio
import websockets
from flask import render_template_string, jsonify

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK


class PwnDroid(plugins.Plugin):
    __author__ = "Jayofelony"
    __version__ = "1.1.009"
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
        self.message = None
        self.fetch_task = None

    def on_loaded(self):
        self.running = True
        logging.info("[PwnDroid] Plugin loaded")
        import threading
        fetch_thread = threading.Thread(target=lambda: asyncio.run(self.start_fetching_location_data()), daemon=True)
        fetch_thread.start()

    async def start_fetching_location_data(self):
        gateway = self.options.get("gateway", "192.168.44.1")
        uri = f"ws://{gateway}:8080"
        retry_count = 0
        max_retries = 3

        while self.running:
            try:
                async with websockets.connect(uri) as websocket:
                    self.websocket = websocket
                    retry_count = 0
                    logging.info("[PwnDroid] WebSocket connected successfully")
                    while self.running:
                        try:
                            self.message = await websocket.recv()
                            if self.message != "":
                                try:
                                    self.coordinates = json.loads(self.message)
                                except json.JSONDecodeError:
                                    await asyncio.sleep(5)
                                    self.coordinates = {}
                            else:
                                logging.error("Received empty message from WebSocket")
                                await asyncio.sleep(5)
                        except websockets.ConnectionClosed:
                            break
            except Exception as e:
                retry_count += 1
                logging.error(f"[PwnDroid] Connection error (attempt {retry_count}/{max_retries}): {e}")

                if retry_count >= max_retries:
                    logging.error(f"[PwnDroid] Failed to connect after {max_retries} attempts. WebSocket connection disabled.")
                    await self.close_websocket()
                    return

                await asyncio.sleep(5)

    async def close_websocket(self):
        if self.websocket:
            await self.websocket.close()
            logging.info("[PwnDroid] WebSocket connection closed")

    def on_unload(self, ui):
        self.running = False
        asyncio.run(self.close_websocket())
        with ui._lock:
            if self.options['display']:
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

    def on_webhook(self, path, request):
        """
        Handle webhook requests. Expose handshakes data via web UI
        """
        from flask import send_file, abort
        clean_path = path.lstrip("/") if path else ""

        if not clean_path or clean_path == 'handshakes':
            handshakes_json = json.loads(self._get_handshakes_json())
            return render_template_string(HANDSHAKES_TEMPLATE, handshakes=handshakes_json.get('handshakes', []))

        if clean_path == 'handshakes.json':
            return jsonify(json.loads(self._get_handshakes_json()))

        if clean_path.startswith('download/'):
            file_path = clean_path.replace('download/', '', 1)
            from pathlib import Path
            try:
                full_path = Path(file_path)
                if full_path.exists() and full_path.is_file():
                    return send_file(str(full_path), as_attachment=True)
            except Exception as e:
                logging.error(f"[PwnDroid] Download error: {e}")
                abort(404)

        return "OK"

    def _get_handshakes_json(self):
        """
        Scan for captured handshakes and return them as JSON
        """
        import json
        import os
        from pathlib import Path
        from datetime import datetime

        handshakes = []

        # Look for PCAP files - they're typically stored in the pwd directory
        try:
            pwd_dir = Path(self.agent.pwn.path) if hasattr(self, 'agent') and hasattr(self.agent, 'pwn') else Path('/etc/pwnagotchi/handshakes')
        except Exception:
            pwd_dir = Path('/etc/pwnagotchi/handshakes')

        try:
            if not pwd_dir.exists():
                logging.warning(f"[PwnDroid] Handshakes directory not found: {pwd_dir}")
                return json.dumps({'handshakes': [], 'count': 0})

            # Search for .pcap files and their corresponding .gps.json files
            for pcap_file in pwd_dir.glob('**/*.pcap'):
                try:
                    gps_file = pcap_file.with_suffix('.gps.json')
                    ctime = pcap_file.stat().st_ctime
                    created_date = datetime.fromtimestamp(ctime).strftime('%Y-%m-%d %H:%M:%S')

                    handshake_info = {
                        'name': pcap_file.stem,
                        'pcap_path': str(pcap_file),
                        'created': created_date,
                        'created_ts': ctime,
                        'size': pcap_file.stat().st_size,
                        'gps': None
                    }

                    # Try to load GPS data if available
                    if gps_file.exists():
                        try:
                            with open(gps_file, 'r') as f:
                                handshake_info['gps'] = json.load(f)
                        except Exception as e:
                            pass

                    handshakes.append(handshake_info)

                except Exception as e:
                    logging.error(f"[PwnDroid] Error processing {pcap_file}: {e}")

            # Sort by creation time, newest first
            handshakes.sort(key=lambda x: x['created_ts'], reverse=True)

            return json.dumps({'handshakes': handshakes, 'count': len(handshakes)})

        except Exception as e:
            logging.error(f"[PwnDroid] Error scanning handshakes: {e}")
            return json.dumps({'error': str(e), 'handshakes': []})


HANDSHAKES_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>PwnDroid Handshakes</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: #1a1a1a; color: #fff; padding: 20px; }
        .container { max-width: 1000px; margin: 0 auto; }
        h1 { margin-bottom: 20px; }
        .toolbar { background: #2a2a2a; padding: 15px; border-radius: 5px; margin-bottom: 20px; display: flex; gap: 10px; align-items: center; }
        .toolbar button { background: #0f0; color: #000; border: none; padding: 8px 15px; border-radius: 3px; cursor: pointer; font-weight: bold; }
        .toolbar button:hover { background: #0d0; }
        .toolbar button:disabled { background: #666; cursor: not-allowed; }
        .toolbar label { display: flex; align-items: center; gap: 8px; cursor: pointer; }
        .handshake { background: #2a2a2a; border: 1px solid #444; border-radius: 5px; padding: 15px; margin-bottom: 15px; display: flex; gap: 15px; }
        .handshake input[type="checkbox"] { margin-top: 2px; cursor: pointer; }
        .handshake-content { flex: 1; }
        .handshake h3 { color: #0f0; margin-bottom: 10px; }
        .handshake h3 a { color: #0f0; text-decoration: none; }
        .handshake h3 a:hover { text-decoration: underline; }
        .info { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 14px; }
        .gps { background: #1a1a1a; padding: 10px; border-radius: 3px; margin-top: 10px; border-left: 3px solid #0f0; }
        .gps h4 { color: #0f0; margin-bottom: 5px; font-size: 12px; }
        .empty { text-align: center; padding: 40px; color: #888; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🛰️ PwnDroid Handshakes</h1>
        {% if handshakes %}
            <div class="toolbar">
                <label><input type="checkbox" id="selectAll"> Select All</label>
                <button id="downloadBtn" onclick="downloadSelected()" disabled>📥 Download Selected</button>
            </div>
            <form id="handshakesForm">
                {% for handshake in handshakes %}
                <div class="handshake">
                    <input type="checkbox" class="handshake-checkbox" value="{{ handshake.pcap_path }}">
                    <div class="handshake-content">
                        <h3><a href="/plugins/pwndroid/download/{{ handshake.pcap_path | urlencode }}" download>📄 {{ handshake.name }}.pcap</a></h3>
                        <div class="info">
                            <div><strong>Size:</strong> {{ (handshake.size / 1024) | int }} KB</div>
                            <div><strong>Created:</strong> {{ handshake.created }}</div>
                        </div>
                        {% if handshake.gps %}
                        <div class="gps">
                            <h4>📍 GPS Data: Lat {{ handshake.gps.Latitude | round(5) }}, Lon {{ handshake.gps.Longitude | round(5) }}, Alt {{ handshake.gps.Altitude | round(1) }}m</h4>
                        </div>
                        {% endif %}
                    </div>
                </div>
                {% endfor %}
            </form>
            <script>
                const selectAllCheckbox = document.getElementById('selectAll');
                const checkboxes = document.querySelectorAll('.handshake-checkbox');
                const downloadBtn = document.getElementById('downloadBtn');

                selectAllCheckbox.addEventListener('change', function() {
                    checkboxes.forEach(cb => cb.checked = this.checked);
                    updateDownloadBtn();
                });

                checkboxes.forEach(cb => {
                    cb.addEventListener('change', updateDownloadBtn);
                });

                function updateDownloadBtn() {
                    const anyChecked = Array.from(checkboxes).some(cb => cb.checked);
                    downloadBtn.disabled = !anyChecked;
                }

                function downloadSelected() {
                    const selected = Array.from(checkboxes).filter(cb => cb.checked);
                    selected.forEach(cb => {
                        window.location.href = '/plugins/pwndroid/download/' + encodeURIComponent(cb.value);
                    });
                }
            </script>
        {% else %}
            <div class="empty">
                <p>No handshakes found</p>
            </div>
        {% endif %}
    </div>
</body>
</html>
"""

