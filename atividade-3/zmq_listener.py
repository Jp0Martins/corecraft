# zmq_listener.py
import zmq
import threading

from state import state, update_tracked_tx
from rpc import BitcoinRPC
from config import ZMQ_URL, RPC_URL, COOKIE_FILE
from wallet import get_selected_wallet

rpc = BitcoinRPC(RPC_URL, COOKIE_FILE)


def start_zmq_listeners():
    context = zmq.Context()

    socket_tx = context.socket(zmq.SUB)
    socket_tx.connect(ZMQ_URL)
    socket_tx.setsockopt(zmq.SUBSCRIBE, b"hashtx")

    socket_block = context.socket(zmq.SUB)
    socket_block.connect(ZMQ_URL)
    socket_block.setsockopt(zmq.SUBSCRIBE, b"hashblock")

    def listen_tx():
        while True:
            parts = socket_tx.recv_multipart()
            if len(parts) < 2:
                continue

            topic = parts[0]
            payload = parts[1]
            if len(payload) != 32:
                print("[ZMQ hashtx] payload len inesperado:", len(payload), "topic=", topic)
                continue

            txid = payload.hex()
            cur = state.get("current_txid")
            print(f"[ZMQ hashtx] topic={topic} txid={txid} current={cur}")

            if cur and txid == cur:
                state["seen_in_mempool"] = True
                state["status"] = "mempool"
                update_tracked_tx(txid, status="mempool")
                print(f"[ZMQ hashtx] MATCH! {txid} entrou na mempool")

    def _confirm_via_wallet(txid: str) -> bool:
        wallet = get_selected_wallet()
        try:
            wtx = rpc.call("gettransaction", [txid], wallet=wallet)
            conf = wtx.get("confirmations", 0)
            bh = wtx.get("blockhash")
            if conf and conf > 0 and bh:
                state["confirmed"] = True
                state["block_hash"] = bh
                state["status"] = "confirmed"
                update_tracked_tx(txid, status="confirmed")
                print(f"[CONFIRM gettransaction] {txid} confirmado no bloco {bh} (conf={conf})")
                return True
        except Exception as e:
            print(f"[CONFIRM gettransaction] não deu (ok, vamos fallback): {e}")
        return False

    def _confirm_via_block(block_hash_hex: str, txid: str) -> bool:
        try:
            blk = rpc.call("getblock", [block_hash_hex, 1])
            txs = blk.get("tx", [])
            if txid in txs:
                state["confirmed"] = True
                state["block_hash"] = blk.get("hash", block_hash_hex)
                state["status"] = "confirmed"
                update_tracked_tx(txid, status="confirmed")
                print(f"[CONFIRM getblock] {txid} está no bloco {state['block_hash']}")
                return True
        except Exception as e:
            print(f"[CONFIRM getblock] falhou para {block_hash_hex[:16]}...: {e}")
        return False

    def listen_block():
        while True:
            parts = socket_block.recv_multipart()
            if len(parts) < 2:
                continue

            topic = parts[0]
            payload = parts[1]
            if len(payload) != 32:
                print("[ZMQ hashblock] payload len inesperado:", len(payload), "topic=", topic)
                continue

            block_raw = payload.hex()
            block_rev = payload[::-1].hex()

            state["last_block_seen_raw"] = block_raw
            state["last_block_seen_rev"] = block_rev
            print(f"[ZMQ hashblock] topic={topic} raw={block_raw} rev={block_rev}")

            cur = state.get("current_txid")
            if not (state.get("seen_in_mempool") and cur and not state.get("confirmed")):
                continue

            if _confirm_via_wallet(cur):
                continue

            if _confirm_via_block(block_raw, cur):
                continue
            _confirm_via_block(block_rev, cur)

    threading.Thread(target=listen_tx, daemon=True).start()
    threading.Thread(target=listen_block, daemon=True).start()
