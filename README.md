# pwnagotchi-torch-plugins
Custom plugin repository

Edit your `/etc/pwnagotchi/config.toml` to look like this

```TOML
main.custom_plugin_repos = [
    "https://github.com/jayofelony/pwnagotchi-torch-plugins/archive/master.zip",
    ]
```
Then run this command: `sudo pwnagotchi plugins update`


# Bluetooth-Sniffer
**Warning: This might not work with bt-tether enabled.**

Run the following command to install BtS

`sudo pwnagotchi plugins install bluetoothsniffer`

Add the following lines to your `/etc/pwnagotchi.config.toml`

```TOML
main.plugins.bluetoothsniffer.enabled = true
main.plugins.bluetoothsniffer.timer = 45 # On how may seconds to scan for bluetooth devices
main.plugins.bluetoothsniffer.devices_file = "/root/handshakes/bluetooth_devices.json"  # Path to the JSON file with bluetooth devices
main.plugins.bluetoothsniffer.count_interval = 86400 # On how may seconds to update count bluetooth devices
main.plugins.bluetoothsniffer.bt_x_coord = 160
main.plugins.bluetoothsniffer.bt_y_coord = 66
```

# Internet-Connection
Run the following command to install Internet-Connection

`sudo pwnagotchi plugins install internet-connection`

Add the following line to your `/etc/pwnagotchi/config.toml`

```TOML
main.plugins.internet-connection.enabled = true
main.plugins.internet-connection.www_y_coord = 0
main.plugins.internet-connection.www_x_coord = 85
```

# Memtemp-Plus
Run the following command to install Memtemp-Plus

`sudo pwnagotchi plugins install memtemp-plus`

Add the following lines to your `/etc/pwnagotchi/config.toml`

```TOML
main.plugins.memtemp-plus.enabled = true
main.plugins.memtemp-plus.scale = "celsius"  # options are celsius, fahrenheit, kelvin
main.plugins.memtemp-plus.orientation = "vertical"  # options are vertical or horizontal
main.plugins.memtemp-plus.fields = ["mem,cpu,temp,freq"]  # you can change order
main.plugins.memtemp-plus.position = "200,70"
main.plugins.memtemp-plus.linespacing = 12
```

# Show_Pwd
Run the following command to install Show_Pwd

`sudo pwnagotchi plugins install show_pwd`

Add the following lines to your `/etc/pwnagotchi/config.toml`

```TOML
main.plugins.show_pwd.enabled = true
main.plugins.show_pwd.orientation = "horizontal"  # options are horizontal or vertical
```

# GPSdeasy

## There is no reason to reboot during this installation, you may interrupt the apt install that is in the background and this will make your pi go bonk
 
1. install the python file. 
2. find the serial link of your GPS and its baudrate and add them to your config
3. get internet and load the plugin
 
## Example config
### Required, require but if they are not given the values below are defaults
```
main.plugins.gpsdeasy.enabled = true
main.plugins.gpsdeasy.host = '127.0.0.1'
main.plugins.gpsdeasy.port = 2947
main.plugins.gpsdeasy.device = '/dev/ttyS0' #<--- change to your device
main.plugins.gpsdeasy.baud = 9600 #<--- change to fit yuor device
```
### Optional, below values are defaults if not specified
```
main.plugins.gpsdeasy.fields = ['fix','lat','lon','alt','spd'] #<-- Any order or amount, you can also use custom values from POLL.TPV; on gpsd documents (https://gpsd.gitlab.io/gpsd/gpsd_json.html#_tpv)
main.plugins.gpsdeasy.speedUnit = 'kph' #or 'mph' or 'ms' #(m/s)
main.plugins.gpsdeasy.distanceUnit = 'm' #or 'ft'
main.plugins.gpsdeasy.bettercap = true #<--- report to bettercap
main.plugins.gpsdeasy.topleft_x = 130
main.plugins.gpsdeasy.topleft_y = 47
main.plugins.gpsdeasy.auto = true #<--- auto setup systemd service for gpsd. use false if using custom service and you know what you are doing.
```


