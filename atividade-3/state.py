# state.py
import time

state = {
    "current_txid": None,
    "status": "idle",
    "seen_in_mempool": False,
    "confirmed": False,
    "block_hash": None
}

tracked_txs = {}

def track_tx(txid, wallet):
    tracked_txs[txid] = {
        "txid": txid,
        "wallet": wallet,
        "status": "broadcast",
        "created_at": time.time()
    }

def get_tracked_tx(txid):
    return tracked_txs.get(txid)

def update_tracked_tx(txid, **kwargs):
    if txid in tracked_txs:
        tracked_txs[txid].update(kwargs)
