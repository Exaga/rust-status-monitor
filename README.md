# Rust Server Status

A small Python script and HTML page for showing the status of a RustDedicated server.

The Python script queries the server with Steam A2S and WebRCON, then writes the results to a JSON file. The HTML page reads that JSON file and displays the current server information.

There is no database and no background service. Run the script from cron at whatever interval you want the page updated.

## Files

`rust_server_status.py`
: Queries the Rust server and writes the JSON status file.

`.rustserver.env`
: Template for the RCON password. Keep the real copy private.

`rust_server_status.json`
: Example output. This is useful for testing the HTML page before the collector is running.

`rust_server_status.html`
: The status page. It reads `rust_status.json` from the same web directory by default.

`README.md`
: This file.

## Requirements

You need Python 3 and these three Python modules:

```text
python-a2s
websocket-client
python-dotenv
```

Install them with:

```bash
python3 -m pip install python-a2s websocket-client python-dotenv
```

The machine running the collector also needs network access to the Rust server's A2S query port and WebRCON port.

You will need to know:

- the Rust server IP address or hostname
- game port
- A2S query port
- WebRCON port
- RCON password

WebRCON must already be enabled on the Rust server.

## Installation

The paths below are examples. Change them to suit your system.

This example keeps the collector and RCON password in:

```text
/opt/rust-status/
```

and serves the web files from:

```text
/var/www/html/rust-status/
```

Create the directories:

```bash
mkdir -p /opt/rust-status
mkdir -p /var/www/html/rust-status
```

Copy the collector and password template into the private directory:

```bash
cp rust_server_status.py /opt/rust-status/
cp .rustserver.env /opt/rust-status/
```

Copy the HTML page into the web directory:

```bash
cp rust_server_status.html /var/www/html/rust-status/
```

Do not put `.rustserver.env` in the web directory.

## Set the RCON password

Edit the private copy:

```bash
vi /opt/rust-status/.rustserver.env
```

Set your real RCON password:

```text
RCON_PASSWORD=your_actual_rcon_password
```

If it needs quoting:

```text
RCON_PASSWORD="your_actual_rcon_password"
```

Protect the file:

```bash
chmod 600 /opt/rust-status/.rustserver.env
```

The user running the collector must be able to read it.

## Configure the collector

Edit:

```bash
vi /opt/rust-status/rust_server_status.py
```

The settings are near the top of the file:

```python
SERVER_HOST = "192.168.2.10" # Rust server IP address or domain name
GAME_PORT = 28015            # Port used by players to connect in-game
QUERY_PORT = 28016           # Steam A2S query port for server details
RCON_PORT = 28017            # WebRCON port for remote server management
QUERY_TIMEOUT = 3.0          # Seconds to wait for Steam query response
RCON_TIMEOUT = 6.0           # Seconds to wait for WebRCON socket connection
ENVIRONMENT = "LIVE"         # Text label used to identify this setup

ENV_PATH = Path(r"/home/user/PATH/TO/.rustserver.env")
JSON_PATH = Path(r"/home/user/PATH/TO/rustserver_json/rust_status_test.json")
```

Change the server address and ports to match your Rust server.

For the example installation in this README, the two paths would be:

```python
ENV_PATH = Path(r"/opt/rust-status/.rustserver.env")
JSON_PATH = Path(r"/var/www/html/rust-status/rust_status.json")
```

The filename `rust_status.json` matters if you are using the supplied HTML without changing it. The page contains:

```javascript
const STATUS_JSON = "rust_status.json";
```

The directory used by `JSON_PATH` must already exist and the user running the collector must be able to write to it.

## Run it by hand first

Do this before adding anything to cron:

```bash
python3 /opt/rust-status/rust_server_status.py
```

The script prints the collected data to the terminal and writes the same data to `JSON_PATH`.

Check that the file was created:

```bash
ls -l /var/www/html/rust-status/rust_status.json
```

Then look at it:

```bash
cat /var/www/html/rust-status/rust_status.json
```

A working result will contain data similar to:

```json
{
  "environment": "LIVE",
  "game_host": "192.168.2.10",
  "game_port": 28015,
  "map": "Procedural Map",
  "max_players": 125,
  "players": 0,
  "query_port": 28016,
  "rcon_port": 28017,
  "server_name": "Example Server",
  "status": "ONLINE"
}
```

There will normally be more fields than shown above.

If A2S fails but WebRCON works, or WebRCON fails but A2S works, the script still writes whatever information it managed to collect. An `errors` section is added to the JSON for the failed query.

If both queries fail, the status is `OFFLINE` and the script exits with status `1`.

A successful or partially successful collection exits with status `0`.

You can check the exit status immediately after running it:

```bash
echo $?
```

## Test the web page

The supplied HTML expects `rust_status.json` to be in the same web directory.

With the example layout you should have:

```text
/var/www/html/rust-status/rust_server_status.html
/var/www/html/rust-status/rust_status.json
```

If the page is available at:

```text
https://example.com/rust-status/rust_server_status.html
```

the browser will fetch:

```text
https://example.com/rust-status/rust_status.json
```

Open the page through your normal web server and check that the server details appear.

### Testing the HTML before the collector is installed

The supplied `rust_server_status.json` is example data. Copy it to the filename expected by the HTML:

```bash
cp rust_server_status.json rust_status.json
```

Then run a temporary web server from that directory:

```bash
python3 -m http.server 8000
```

Open:

```text
http://localhost:8000/rust_server_status.html
```

Do not open the HTML directly with a `file://` URL. The page uses `fetch()` to read the JSON and should be tested through HTTP or HTTPS.

Press `Ctrl-C` to stop the temporary web server.

## Using a different JSON URL

If the JSON is not in the same directory as the HTML, edit this line in `rust_server_status.html`:

```javascript
const STATUS_JSON = "rust_status.json";
```

For example:

```javascript
const STATUS_JSON = "/status/rust_status.json";
```

or:

```javascript
const STATUS_JSON = "json/rust_status.json";
```

This is a URL used by the browser. It is not a filesystem path.

## Run it from cron

Once the collector works by hand and the web page can read the JSON, add it to cron.

Edit the crontab for the user that will run the collector:

```bash
crontab -e
```

To update the status once per minute:

```cron
* * * * * /usr/bin/python3 /opt/rust-status/rust_server_status.py >/dev/null 2>&1
```

Check the path to Python on your system:

```bash
command -v python3
```

Use that full path in the crontab.

Check the installed cron entry with:

```bash
crontab -l
```

After a minute or two, check that the JSON is being updated:

```bash
ls -l /var/www/html/rust-status/rust_status.json
```

or:

```bash
grep 'collected_at' /var/www/html/rust-status/rust_status.json
```

If it works by hand but not from cron, temporarily log the output:

```cron
* * * * * /usr/bin/python3 /opt/rust-status/rust_server_status.py >>/tmp/rust-status.log 2>&1
```

Then check:

```bash
cat /tmp/rust-status.log
```

Cron has a small environment, so use full paths. The script already uses absolute paths for the password file and JSON file for the same reason.

## Permissions

The collector user needs to be able to:

- read `rust_server_status.py`
- read `.rustserver.env`
- create and replace `rust_status.json`

The web server only needs read access to:

- `rust_server_status.html`
- `rust_status.json`

Do not make `.rustserver.env` world-readable to get around a permissions problem. Fix the ownership or permissions properly.

## Security

The RCON password must remain private.

Do not put it in:

- the public repository
- the Python script
- the HTML
- the generated JSON
- a web-accessible directory

The collector currently connects to WebRCON with `ws://`, so the WebRCON connection itself is not encrypted. If the collector and Rust server are on different or untrusted networks, protect that traffic with appropriate firewalling, private networking or a trusted tunnel/VPN.

The generated JSON includes the server host and port numbers. If you do not want those published, do not expose the JSON publicly.

## Troubleshooting

### Python says a module is missing

Check the imports:

```bash
python3 -c 'import a2s, websocket, dotenv; print("OK")'
```

If that fails, install the required modules using the same Python interpreter that runs the collector:

```bash
python3 -m pip install python-a2s websocket-client python-dotenv
```

### `RCON_PASSWORD environment variable is not set`

Check `ENV_PATH` in `rust_server_status.py`.

Make sure the file exists, contains `RCON_PASSWORD=...`, and can be read by the user running the script.

### `FileNotFoundError` for the JSON or `.tmp` file

Check `JSON_PATH`.

The parent directory must already exist.

### `PermissionError` writing the JSON

The collector user cannot write to the directory or replace the existing file.

Check:

```bash
ls -ld /var/www/html/rust-status
ls -l /var/www/html/rust-status/rust_status.json
```

Fix the ownership or permissions as needed.

### A2S fails but WebRCON works

Check `SERVER_HOST`, `QUERY_PORT`, routing and firewall rules.

The script can still produce useful output from WebRCON.

### WebRCON fails but A2S works

Check `SERVER_HOST`, `RCON_PORT`, the RCON password, `ENV_PATH`, WebRCON configuration and firewall rules.

The script can still produce useful output from A2S.

### The page loads but the values stay blank or show `-`

Check the error shown at the bottom of the page.

Make sure:

- the page is being served through HTTP or HTTPS
- `rust_status.json` exists
- the web server can read it
- `STATUS_JSON` points to the right URL

If you get:

```text
Unable to load rust_status.json: HTTP 404
```

the HTML page loaded but the JSON is not where the page expects it to be.

### The JSON never updates

Run the collector by hand:

```bash
python3 /opt/rust-status/rust_server_status.py
```

If that updates the file, the collector is fine and cron is the problem.

Check:

```bash
crontab -l
command -v python3
```

Then use the temporary cron log shown earlier instead of sending output to `/dev/null`.

## Updating

Keep your private `.rustserver.env` and local configuration when replacing the collector or HTML with newer versions.

It is sensible to keep a copy of the working files before replacing them:

```bash
cp /opt/rust-status/rust_server_status.py /opt/rust-status/rust_server_status.py.old
cp /var/www/html/rust-status/rust_server_status.html /var/www/html/rust-status/rust_server_status.html.old
```

Install the new files and run the collector by hand once before leaving cron to run it again.

Do not overwrite your private `.rustserver.env` with the public template.

## Quick install check

Before calling it finished, make sure all of these work:

1. Python can import `a2s`, `websocket` and `dotenv`.
2. `.rustserver.env` contains the correct RCON password and is not web accessible.
3. The server address and ports in `rust_server_status.py` are correct.
4. `ENV_PATH` points to the private password file.
5. `JSON_PATH` points to the live `rust_status.json` file.
6. Running the collector by hand creates or updates the JSON.
7. The HTML page loads through the web server and displays the JSON data.
8. Cron keeps the JSON updated.

Copyright © 2026 Exaga/Kara - rust.penthux.net

\#EOF\<\*\>     
\# K4R4\<3\:\*
