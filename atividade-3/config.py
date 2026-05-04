# config.py
import os

BITCOIN_DATADIR = os.environ.get("BITCOIN_DATADIR", "/mnt/dados2")
COOKIE_FILE = os.environ.get("BITCOIN_COOKIE", os.path.join(BITCOIN_DATADIR, "signet", ".cookie"))

RPC_HOST = os.environ.get("RPC_HOST", "127.0.0.1")
RPC_PORT = int(os.environ.get("RPC_PORT", "38332"))
RPC_URL = f"http://{RPC_HOST}:{RPC_PORT}"

ZMQ_HOST = os.environ.get("ZMQ_HOST", "127.0.0.1")
ZMQ_PORT = int(os.environ.get("ZMQ_PORT", "18123"))
ZMQ_URL = f"tcp://{ZMQ_HOST}:{ZMQ_PORT}"

FLASK_HOST = os.environ.get("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.environ.get("FLASK_PORT", "5000"))
