#!/usr/bin/env python3
#
# Rust server status collector
#
# 2026-10-17 - v0.01 - Exaga/Iana : initial script code
# 2026-10-17 - v0.02 - Exaga/Iana : cleaned A2S cache fields; fixed query port
# 2026-10-17 - v0.03 - Exaga/Iana : merged A2S and WebRCON server data
# 2026-10-17 - v0.04 - Exaga/Iana : load RCON password from private dotenv
# 2026-10-17 - v1.05 - Exaga/Iana : LIVE deployment paths
# 2026-10-19 - v1.06 - Exaga/Iana : system-agnostic configurable paths
# 2026-10-19 - v1.07 - Exaga/Iana : portable configuration block and import fix
# 2026-10-19 - v1.08 - Exaga/Iana : GitHub release defaults and repository alignment
#
# Queries a Rust server via Steam A2S_INFO and WebRCON and writes
# a local JSON cache.
#
###

# Library imports
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Required 3rd party modules
import a2s
import websocket
from dotenv import load_dotenv

# Rust server configuration
SERVER_HOST = "192.168.2.10" # Rust server IP address or domain name
GAME_PORT = 28015            # Port used by players to connect in-game
QUERY_PORT = 28016           # Steam A2S query port for server details
RCON_PORT = 28017            # WebRCON port for remote server management
QUERY_TIMEOUT = 3.0          # Seconds to wait for Steam query response
RCON_TIMEOUT = 6.0           # Seconds to wait for WebRCON socket connection
ENVIRONMENT = "LIVE"         # Text label used to identify this setup (e.g. TEST, LIVE)

# Configuration Paths - Set absolute paths to your environment and data folders/files
ENV_PATH = Path(r"/home/user/PATH/TO/.rustserver.env")                        # Path to private password file
JSON_PATH = Path(r"/home/user/PATH/TO/rustserver_json/rust_status_test.json") # Path where the cache is saved

# Load the RCON passwd dotenv
load_dotenv(ENV_PATH)


# Set UTC timestamp for data cache records
def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# Write cache atomically via a temporary file
def write_json(data):
    temp_path = JSON_PATH.with_suffix(JSON_PATH.suffix + ".tmp")

    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")

    os.replace(temp_path, JSON_PATH)


# Query public Steam A2S server info
def query_a2s():
    try:
        info = a2s.info((SERVER_HOST, QUERY_PORT), timeout=QUERY_TIMEOUT)

        return {
            "server_name": info.server_name,
            "players": info.player_count,
            "max_players": info.max_players,
            "map": info.map_name,
            "ping_ms": round(info.ping * 1000, 1),
            "version": info.version,
            "vac_enabled": info.vac_enabled,
        }, None
    except Exception as exc:
        return {}, f"{type(exc).__name__}: {exc}"


# Query auth Rust WebRCON serverinfo data
def query_rcon():
    rcon_password = os.environ.get("RCON_PASSWORD")

    if not rcon_password:
        return {}, "RCON_PASSWORD environment variable is not set"

    connection = None

    try:
        connection = websocket.create_connection(
            f"ws://{SERVER_HOST}:{RCON_PORT}/{rcon_password}",
            timeout=RCON_TIMEOUT,
        )

        connection.send(json.dumps({
            "Identifier": 1,
            "Message": "serverinfo",
            "Name": "WebRcon",
        }))

        while True:
            response = json.loads(connection.recv())

            if response.get("Identifier") != 1:
                continue

            server_info = json.loads(response["Message"])

            return {
                "queued": server_info.get("Queued"),
                "joining": server_info.get("Joining"),
                "reserved_slots": server_info.get("ReservedSlots"),
                "uptime_seconds": server_info.get("Uptime"),
                "entity_count": server_info.get("EntityCount"),
                "server_fps": server_info.get("Framerate"),
                "memory_mb": server_info.get("Memory"),
                "restarting": server_info.get("Restarting"),
                "save_created_time": server_info.get("SaveCreatedTime"),
                "protocol": server_info.get("Protocol"),
                "rcon_server_name": server_info.get("Hostname"),
                "rcon_players": server_info.get("Players"),
                "rcon_max_players": server_info.get("MaxPlayers"),
                "rcon_map": server_info.get("Map"),
                "rcon_version": server_info.get("Version"),
            }, None
    except Exception as exc:
        return {}, f"{type(exc).__name__}: {exc}"
    finally:
        if connection is not None:
            connection.close()


# Query both sources and merge results into one cache record
def main():
    a2s_data, a2s_error = query_a2s()
    rcon_data, rcon_error = query_rcon()

    # Prefer A2S public fields with RCON fallback; use RCON max players when available
    result = {
        "environment": ENVIRONMENT,
        "collected_at": utc_now(),
        "status": "ONLINE" if a2s_data or rcon_data else "OFFLINE",
        "server_name": a2s_data.get("server_name", rcon_data.get("rcon_server_name")),
        "players": a2s_data.get("players", rcon_data.get("rcon_players")),
        "max_players": rcon_data.get("rcon_max_players", a2s_data.get("max_players")),
        "queued": rcon_data.get("queued"),
        "joining": rcon_data.get("joining"),
        "reserved_slots": rcon_data.get("reserved_slots"),
        "map": a2s_data.get("map", rcon_data.get("rcon_map")),
        "ping_ms": a2s_data.get("ping_ms"),
        "version": a2s_data.get("version", rcon_data.get("rcon_version")),
        "protocol": rcon_data.get("protocol"),
        "vac_enabled": a2s_data.get("vac_enabled"),
        "uptime_seconds": rcon_data.get("uptime_seconds"),
        "entity_count": rcon_data.get("entity_count"),
        "server_fps": rcon_data.get("server_fps"),
        "memory_mb": rcon_data.get("memory_mb"),
        "restarting": rcon_data.get("restarting"),
        "save_created_time": rcon_data.get("save_created_time"),
        "game_host": SERVER_HOST,
        "game_port": GAME_PORT,
        "query_port": QUERY_PORT,
        "rcon_port": RCON_PORT,
    }

    # Include query-specific errors only when source fails
    errors = {}

    if a2s_error:
        errors["a2s"] = a2s_error

    if rcon_error:
        errors["rcon"] = rcon_error

    if errors:
        result["errors"] = errors

    # Save cache, echo for manual runs, return server status
    write_json(result)
    print(json.dumps(result, indent=2, sort_keys=True))

    return 0 if result["status"] == "ONLINE" else 1


# Script entry point
if __name__ == "__main__":
    sys.exit(main())


#EOF<*>
# 14N4<3:*
