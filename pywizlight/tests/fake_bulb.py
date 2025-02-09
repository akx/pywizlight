"""Start up a fake bulb to test features without a real bulb."""
import json
import socketserver
import threading
from typing import Any, Callable, Dict


def get_initial_pilot() -> Dict[str, Any]:
    return {
        "method": "getPilot",
        "env": "pro",
        "result": {
            "mac": "ABCABCABCABC",
            "rssi": -62,
            "src": "",
            "state": False,
            "sceneId": 0,
            "r": 255,
            "g": 127,
            "b": 0,
            "c": 0,
            "w": 0,
            "temp": 0,
            "dimming": 13,
        },
    }


def get_initial_sys_config() -> Dict[str, Any]:
    return {
        "method": "getSystemConfig",
        "env": "pro",
        "result": {
            "mac": "a8bb5006033d",
            "homeId": 653906,
            "roomId": 989983,
            "moduleName": "",
            "fwVersion": "1.21.0",
            "groupId": 0,
            "drvConf": [20, 2],
            "ewf": [255, 0, 255, 255, 0, 0, 0],
            "ewfHex": "ff00ffff000000",
            "ping": 0,
        },
    }


BULB_JSON_ERROR = b'{"env":"pro","error":{"code":-32700,"message":"Parse error"}}'


class BulbUDPRequestHandlerBase(socketserver.DatagramRequestHandler):
    """Class for UDP handler."""

    pilot_state: Dict[str, Any]  # Will be set by constructor for the actual class
    sys_config: Dict[str, Any]  # Will be set by constructor for the actual class

    def handle(self) -> None:
        """Handle the request."""
        data = self.rfile.readline().strip()
        print(f"Request:{data!r}")
        try:
            json_data: Dict[str, Any] = dict(json.loads(data.decode()))
        except json.JSONDecodeError:
            self.wfile.write(BULB_JSON_ERROR)
            return

        method = str(json_data["method"])
        if method == "setPilot":
            return_data = self.setPilot(json_data)
            self.wfile.write(return_data)
        if method == "getPilot":
            print(f"Response:{json.dumps(self.pilot_state)!r}")
            self.wfile.write(bytes(json.dumps(self.pilot_state), "utf-8"))
        if method == "getSystemConfig":
            self.wfile.write(bytes(json.dumps(self.sys_config), "utf-8"))

    def setPilot(self, json_data: Dict[str, Any]) -> bytes:
        """Change the values in the state."""
        for name, value in json_data["params"].items():
            self.pilot_state["result"][name] = value
        return b'{"method":"setPilot","env":"pro","result":{"success":true}}'


def make_udp_fake_bulb_server(module_name: str) -> socketserver.ThreadingUDPServer:
    """Configure a fake bulb instance."""
    pilot_state = get_initial_pilot()
    sys_config = get_initial_sys_config()
    sys_config["result"]["moduleName"] = module_name

    BulbUDPRequestHandler = type(
        "BulbUDPRequestHandler",
        (BulbUDPRequestHandlerBase,),
        {
            "pilot_state": pilot_state,
            "sys_config": sys_config,
        },
    )

    udp_server = socketserver.ThreadingUDPServer(
        server_address=("127.0.0.1", 38899),
        RequestHandlerClass=BulbUDPRequestHandler,
    )
    return udp_server


def startup_bulb(module_name: str = "ESP01_SHRGB_03") -> Callable[[], Any]:
    """Start up the bulb. Returns a function to shut it down."""
    server = make_udp_fake_bulb_server(module_name)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    return server.shutdown
