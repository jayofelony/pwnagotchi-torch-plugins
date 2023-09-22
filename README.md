# pwnagotchi-torch-plugins
Custom plugin repository

Edit your `/etc/pwnagotchi/config.toml` to look like this

```
main.custom_plugin_repos = [
    "https://github.com/jayofelony/pwnagotchi-torch-plugins/archive/master.zip",
    "https://github.com/evilsocket/pwnagotchi-plugins-contrib/archive/master.zip"
    ]
```
Then run this command: `sudo pwnagotchi plugins update`


# Bluetooth-Sniffer
Run the following command to install BtS

`sudo pwnagotchi plugins install bluetoothsniffer`

Add the following lines to your `/etc/pwnagotchi.config.toml`

``` 
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

`main.plugins.internet-connection.enabled = true`

# Memtemp-Plus
Run the following command to install Memtemp-Plus

`sudo pwnagotchi plugins install memtemp-plus`

Add the following lines to your `/etc/pwnagotchi/config.toml`

```angular2html
main.plugins.memtemp-plus.enabled = true
main.plugins.memtemp-plus.scale = "celsius"  # options are celsius, fahrenheit, kelvin
main.plugins.memtemp-plus.orientation = "vertical"  # options are vertical or horizontal
main.plugins.memtemp-plus.fields = "mem,cpu,temp,freq"  # you can change order
main.plugins.memtemp-plus.position = "200,70"
main.plugins.memtemp-plus.linespacing = 12
```