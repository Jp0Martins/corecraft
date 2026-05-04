# interpreter.py
import time
from state import get_tracked_tx


def interpret_tx(txid, wallet, rpc):
    tracked = get_tracked_tx(txid)
    created_at = tracked["created_at"] if tracked else None
    age_seconds = int(time.time() - created_at) if created_at else 0

    # Tenta gettransaction (wallet-level)
    try:
        info = rpc.call("gettransaction", [txid], wallet=wallet)
        conf = int(info.get("confirmations", 0) or 0)
        bh = info.get("blockhash") or None

        if conf > 0 and bh:
            return {
                "txid": txid,
                "wallet": wallet,
                "status": "confirmed",
                "confirmed": True,
                "confirmations": conf,
                "block_hash": bh,
                "age_seconds": age_seconds,
                "message": "Transação confirmada em bloco.",
                "warning": None
            }

        warning = "Transação está na mempool há mais de 2 minutos." if age_seconds > 120 else None
        return {
            "txid": txid,
            "wallet": wallet,
            "status": "mempool",
            "confirmed": False,
            "confirmations": conf,
            "block_hash": None,
            "age_seconds": age_seconds,
            "message": "Transação aceita na mempool, aguardando inclusão em bloco.",
            "warning": warning
        }

    except Exception:
        pass

    # Fallback: getmempoolentry (node-level)
    try:
        rpc.call("getmempoolentry", [txid])
        warning = "Transação está na mempool há mais de 2 minutos." if age_seconds > 120 else None
        return {
            "txid": txid,
            "wallet": wallet,
            "status": "mempool",
            "confirmed": False,
            "confirmations": 0,
            "block_hash": None,
            "age_seconds": age_seconds,
            "message": "Transação aceita na mempool, aguardando inclusão em bloco.",
            "warning": warning
        }
    except Exception:
        pass

    # Ainda no estado broadcast (acabou de ser enviada)
    if tracked and tracked.get("status") == "broadcast":
        return {
            "txid": txid,
            "wallet": wallet,
            "status": "broadcast",
            "confirmed": False,
            "confirmations": 0,
            "block_hash": None,
            "age_seconds": age_seconds,
            "message": "Transação enviada ao node, aguardando aceitação na mempool.",
            "warning": None
        }

    return {
        "txid": txid,
        "wallet": wallet,
        "status": "unknown",
        "confirmed": False,
        "confirmations": 0,
        "block_hash": None,
        "age_seconds": age_seconds,
        "message": None,
        "warning": "Transação não localizada na wallet selecionada."
    }
