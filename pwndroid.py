import json
import logging
import asyncio
import os
import threading

import websockets
from flask import render_template_string, jsonify

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK


def _first(d, *keys):
    """First truthy value among the given keys of a dict, or None."""
    if not isinstance(d, dict):
        return None
    for k in keys:
        v = d.get(k)
        if v:
            return v
    return None


class PwnDroid(plugins.Plugin):
    __author__ = "Jayofelony"
    __version__ = "1.2.0"
    __license__ = "GPL3"
    __description__ = (
        "Companion plugin for the PwnDroid Android app: receives phone GPS over a local "
        "WebSocket and reports captured handshakes (with network details) back to it."
    )

    LINE_SPACING = 10
    LABEL_SPACING = 0

    def __init__(self):
        self.running = False
        self.options = dict()
        self.coordinates = dict()
        self._agent = None
        self._loop = None
        self._outbox = None
        self._thread = None

    # ------------------------------------------------------------------ lifecycle

    def on_loaded(self):
        self.running = True
        self._thread = threading.Thread(target=self._run, name="pwndroid-ws", daemon=True)
        self._thread.start()
        logging.info("[PwnDroid] plugin loaded")

    def on_ready(self, agent):
        self._agent = agent

    def on_unload(self, ui):
        self.running = False
        loop = self._loop
        if loop is not None:
            try:
                loop.call_soon_threadsafe(loop.stop)
            except RuntimeError:
                pass
        if self.options.get("display", False):
            with ui._lock:
                for element in ("latitude", "longitude", "altitude"):
                    try:
                        ui.remove_element(element)
                    except Exception:
                        pass
        logging.info("[PwnDroid] plugin unloaded")

    # ----------------------------------------------------------- websocket client

    def _run(self):
        """Owns a dedicated event loop for the whole life of the plugin."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._outbox = asyncio.Queue()
        try:
            self._loop.run_until_complete(self._client())
        except Exception as e:  # noqa: BLE001 - last-resort guard for the daemon thread
            logging.error("[PwnDroid] websocket thread stopped: %s", e)
        finally:
            try:
                self._loop.close()
            except Exception:
                pass

    async def _client(self):
        """Connect to the phone and stay connected, retrying forever with backoff."""
        backoff = 2
        while self.running:
            uri = "ws://%s:%d" % (
                self.options.get("gateway", "192.168.44.1"),
                int(self.options.get("port", 8080)),
            )
            try:
                async with websockets.connect(
                    uri, ping_interval=20, ping_timeout=20, close_timeout=5
                ) as ws:
                    logging.info("[PwnDroid] connected to %s", uri)
                    backoff = 2
                    receiver = asyncio.ensure_future(self._receive(ws))
                    sender = asyncio.ensure_future(self._send(ws))
                    done, pending = await asyncio.wait(
                        {receiver, sender}, return_when=asyncio.FIRST_COMPLETED
                    )
                    for task in pending:
                        task.cancel()
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001
                logging.warning("[PwnDroid] connection to %s failed: %s", uri, e)

            if not self.running:
                break
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)

    async def _receive(self, ws):
        async for message in ws:
            if not message:
                continue
            try:
                data = json.loads(message)
            except (ValueError, TypeError):
                continue
            if isinstance(data, dict) and "Latitude" in data:
                self.coordinates = data

    async def _send(self, ws):
        while True:
            payload = await self._outbox.get()
            try:
                await ws.send(json.dumps(payload))
                logging.info(
                    "[PwnDroid] reported handshake %s",
                    payload.get("essid") or payload.get("bssid") or payload.get("filename"),
                )
            except Exception as e:  # noqa: BLE001
                logging.warning("[PwnDroid] failed to send handshake: %s", e)

    def _enqueue(self, payload):
        """Hand a message to the websocket loop from any thread."""
        loop, outbox = self._loop, self._outbox
        if loop is None or outbox is None:
            return
        try:
            loop.call_soon_threadsafe(outbox.put_nowait, payload)
        except RuntimeError:
            pass

    # ------------------------------------------------------------------ handshakes

    def on_handshake(self, agent, filename, access_point, client_station):
        coords = dict(self.coordinates) if self.coordinates else {}
        lat = coords.get("Latitude")
        lon = coords.get("Longitude")
        has_fix = bool(lat) and bool(lon)

        if has_fix:
            gps_filename = filename.replace(".pcap", ".gps.json")
            try:
                with open(gps_filename, "w+t") as fp:
                    json.dump(coords, fp)
                logging.info("[PwnDroid] saved GPS to %s", gps_filename)
            except Exception as e:  # noqa: BLE001
                logging.error("[PwnDroid] could not write %s: %s", gps_filename, e)
        else:
            logging.info("[PwnDroid] no GPS fix for %s", os.path.basename(filename))

        payload = {
            "type": "handshake",
            "filename": os.path.basename(filename),
            "essid": _first(access_point, "hostname", "essid", "ssid", "name"),
            "bssid": _first(access_point, "mac", "bssid"),
            "station": _first(client_station, "mac", "bssid"),
        }
        if has_fix:
            payload["gps"] = {
                "Latitude": lat,
                "Longitude": lon,
                "Altitude": coords.get("Altitude"),
            }
        self._enqueue(payload)

    # -------------------------------------------------------------------- display

    def on_ui_setup(self, ui):
        if not self.options.get("display", False):
            return

        try:
            line_spacing = int(self.options["linespacing"])
        except Exception:
            line_spacing = self.LINE_SPACING

        try:
            pos = [int(x.strip()) for x in self.options["position"].split(",")]
            lat_pos = (pos[0] + 5, pos[1])
            lon_pos = (pos[0], pos[1] + line_spacing)
            alt_pos = (pos[0] + 5, pos[1] + (2 * line_spacing))
        except Exception:
            lat_pos = (127, 64)
            lon_pos = (127, 74)
            alt_pos = (127, 84)

        show_altitude = self.options.get("display_altitude", False)
        ui.add_element(
            "latitude",
            LabeledValue(
                color=BLACK, label="lat:", value="", position=lat_pos,
                label_font=fonts.Small, text_font=fonts.Small, label_spacing=self.LABEL_SPACING,
            ),
        )
        ui.add_element(
            "longitude",
            LabeledValue(
                color=BLACK, label="long:", value="", position=lon_pos,
                label_font=fonts.Small, text_font=fonts.Small, label_spacing=self.LABEL_SPACING,
            ),
        )
        if show_altitude:
            ui.add_element(
                "altitude",
                LabeledValue(
                    color=BLACK, label="alt:", value="", position=alt_pos,
                    label_font=fonts.Small, text_font=fonts.Small, label_spacing=self.LABEL_SPACING,
                ),
            )

    def on_ui_update(self, ui):
        if not self.options.get("display", False):
            return
        with ui._lock:
            lat = self.coordinates.get("Latitude") if self.coordinates else None
            lon = self.coordinates.get("Longitude") if self.coordinates else None
            if not (lat and lon):
                return
            ui.set("latitude", f"{lat} ")
            ui.set("longitude", f"{lon} ")
            if self.options.get("display_altitude", False):
                alt = self.coordinates.get("Altitude") or 0.0
                ui.set("altitude", f"{alt:.1f}m ")

    # -------------------------------------------------------------------- webhook

    def on_webhook(self, path, request):
        """Expose captured handshakes (with GPS) for the app to pull as a full sync."""
        from flask import send_file, abort

        clean_path = path.lstrip("/") if path else ""

        if not clean_path or clean_path == "handshakes":
            handshakes = json.loads(self._get_handshakes_json()).get("handshakes", [])
            return render_template_string(HANDSHAKES_TEMPLATE, handshakes=handshakes)

        if clean_path == "handshakes.json":
            return jsonify(json.loads(self._get_handshakes_json()))

        if clean_path.startswith("download/"):
            from pathlib import Path
            file_path = clean_path.replace("download/", "", 1)
            try:
                full_path = Path(file_path)
                if full_path.exists() and full_path.is_file():
                    return send_file(str(full_path), as_attachment=True)
            except Exception as e:  # noqa: BLE001
                logging.error("[PwnDroid] download error: %s", e)
            abort(404)

        return "OK"

    def _handshakes_dir(self):
        from pathlib import Path
        try:
            configured = self._agent.config()["bettercap"]["handshakes"]
            if configured:
                return Path(configured)
        except Exception:
            pass
        for candidate in ("/root/handshakes", "/home/pi/handshakes", "/etc/pwnagotchi/handshakes"):
            p = Path(candidate)
            if p.exists():
                return p
        return Path("/root/handshakes")

    def _get_handshakes_json(self):
        from datetime import datetime

        pwd_dir = self._handshakes_dir()
        if not pwd_dir.exists():
            logging.warning("[PwnDroid] handshakes directory not found: %s", pwd_dir)
            return json.dumps({"handshakes": [], "count": 0})

        handshakes = []
        try:
            for pcap_file in pwd_dir.glob("**/*.pcap"):
                try:
                    gps_file = pcap_file.with_suffix(".gps.json")
                    ctime = pcap_file.stat().st_ctime
                    info = {
                        "name": pcap_file.stem,
                        "pcap_path": str(pcap_file),
                        "created": datetime.fromtimestamp(ctime).strftime("%Y-%m-%d %H:%M:%S"),
                        "created_ts": ctime,
                        "size": pcap_file.stat().st_size,
                        "gps": None,
                    }
                    if gps_file.exists():
                        try:
                            with open(gps_file, "r") as f:
                                info["gps"] = json.load(f)
                        except Exception:
                            pass
                    handshakes.append(info)
                except Exception as e:  # noqa: BLE001
                    logging.error("[PwnDroid] error processing %s: %s", pcap_file, e)

            handshakes.sort(key=lambda x: x["created_ts"], reverse=True)
            return json.dumps({"handshakes": handshakes, "count": len(handshakes)})
        except Exception as e:  # noqa: BLE001
            logging.error("[PwnDroid] error scanning handshakes: %s", e)
            return json.dumps({"error": str(e), "handshakes": []})


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
        <h1>PwnDroid Handshakes</h1>
        {% if handshakes %}
            <div class="toolbar">
                <label><input type="checkbox" id="selectAll"> Select All</label>
                <button id="downloadBtn" onclick="downloadSelected()" disabled>Download Selected</button>
            </div>
            <form id="handshakesForm">
                {% for handshake in handshakes %}
                <div class="handshake">
                    <input type="checkbox" class="handshake-checkbox" value="{{ handshake.pcap_path }}">
                    <div class="handshake-content">
                        <h3><a href="/plugins/pwndroid/download/{{ handshake.pcap_path | urlencode }}" download>{{ handshake.name }}.pcap</a></h3>
                        <div class="info">
                            <div><strong>Size:</strong> {{ (handshake.size / 1024) | int }} KB</div>
                            <div><strong>Created:</strong> {{ handshake.created }}</div>
                        </div>
                        {% if handshake.gps %}
                        <div class="gps">
                            <h4>GPS: Lat {{ handshake.gps.Latitude | round(5) }}, Lon {{ handshake.gps.Longitude | round(5) }}, Alt {{ handshake.gps.Altitude | round(1) }}m</h4>
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

                checkboxes.forEach(cb => cb.addEventListener('change', updateDownloadBtn));

                function updateDownloadBtn() {
                    downloadBtn.disabled = !Array.from(checkboxes).some(cb => cb.checked);
                }

                function downloadSelected() {
                    Array.from(checkboxes).filter(cb => cb.checked).forEach(cb => {
                        window.location.href = '/plugins/pwndroid/download/' + encodeURIComponent(cb.value);
                    });
                }
            </script>
        {% else %}
            <div class="empty"><p>No handshakes found</p></div>
        {% endif %}
    </div>
</body>
</html>
"""
