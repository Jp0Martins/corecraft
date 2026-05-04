# backend.py
from flask import Flask, request, jsonify, send_file

from rpc import BitcoinRPC
from config import RPC_URL, COOKIE_FILE, FLASK_HOST, FLASK_PORT
from wallet import get_selected_wallet, set_selected_wallet
from tx_builder import build_transaction
from zmq_listener import start_zmq_listeners
from state import state, track_tx
from interpreter import interpret_tx

app = Flask(__name__)

rpc = BitcoinRPC(RPC_URL, COOKIE_FILE)


@app.route("/", methods=["GET"])
def index():
    return send_file("frontend.html")


@app.route("/send", methods=["POST"])
def send_tx():
    try:
        print("\n>>> ENTROU NO /send (POST)")
        print("Content-Type:", request.headers.get("Content-Type"))
        print("Raw body:", request.data)

        data = request.get_json(silent=True)
        print("JSON parseado:", data)

        if not data:
            return jsonify({"error": "JSON inválido ou ausente"}), 400

        to_address = data.get("address")
        amount = data.get("amount")

        if not to_address or amount is None:
            return jsonify({"error": "Campos obrigatórios: address, amount"}), 400

        wallet = get_selected_wallet()
        if not wallet:
            return jsonify({"error": "Nenhuma wallet selecionada"}), 400

        amount = float(amount)
        print(f"Construindo TX -> address={to_address} amount={amount} wallet={wallet}")

        raw_tx = build_transaction(to_address, amount)
        print("Raw TX gerada (hex, início):", raw_tx[:80] + "...")

        # signrawtransactionwithwallet é wallet-level
        signed = rpc.call("signrawtransactionwithwallet", [raw_tx], wallet=wallet)
        if not signed.get("complete"):
            raise Exception(f"Falha ao assinar TX: {signed}")

        signed_tx = signed["hex"]
        print("Signed TX (hex, início):", signed_tx[:80] + "...")

        # sendrawtransaction é node-level (sem wallet)
        txid = rpc.call("sendrawtransaction", [signed_tx])
        print("TX enviada! txid =", txid)

        track_tx(txid, wallet)

        state["current_txid"] = txid
        state["status"] = "broadcast"
        state["seen_in_mempool"] = False
        state["confirmed"] = False
        state["block_hash"] = None

        try:
            rpc.call("getmempoolentry", [txid])
            state["seen_in_mempool"] = True
            state["status"] = "mempool"
            print("[RPC mempool] tx já está na mempool, marcando state=mempool")
        except Exception:
            print("[RPC mempool] tx ainda não está na mempool (ou já confirmou)")

        return jsonify({"txid": txid, "wallet": wallet})

    except Exception as e:
        print("ERRO no /send:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/wallets", methods=["GET"])
def list_wallets():
    available = [w["name"] for w in rpc.call("listwalletdir").get("wallets", [])]
    loaded = rpc.call("listwallets")
    return jsonify({
        "available_wallets": available,
        "loaded_wallets": loaded,
        "selected_wallet": get_selected_wallet()
    })


@app.route("/wallet/select", methods=["POST"])
def select_wallet():
    data = request.get_json(silent=True)
    if not data or not data.get("wallet"):
        return jsonify({"error": "Campo obrigatório: wallet"}), 400

    name = data["wallet"]

    available = [w["name"] for w in rpc.call("listwalletdir").get("wallets", [])]
    if name not in available:
        return jsonify({"error": f"Wallet '{name}' não encontrada"}), 404

    loaded = rpc.call("listwallets")
    if name not in loaded:
        try:
            rpc.call("loadwallet", [name])
        except Exception as e:
            if "already loaded" not in str(e).lower():
                raise

    set_selected_wallet(name)

    wallet_info = rpc.call("getwalletinfo", [], wallet=name)
    print(f"[getwalletinfo] {name}: {wallet_info}")
    balance = rpc.call("getbalance", [], wallet=name)
    return jsonify({
        "selected_wallet": name,
        "wallet_info": {
            "walletname": wallet_info.get("walletname"),
            "balance": balance,
            "txcount": wallet_info.get("txcount")
        }
    })


@app.route("/wallet/status", methods=["GET"])
def wallet_status():
    wallet = get_selected_wallet()
    if not wallet:
        return jsonify({"error": "Nenhuma wallet selecionada"}), 400

    balance = rpc.call("getbalance", [], wallet=wallet)
    utxos = rpc.call("listunspent", [1, 9999999], wallet=wallet)
    return jsonify({
        "wallet": wallet,
        "balance": balance,
        "utxos": len(utxos)
    })


@app.route("/tx/<txid>", methods=["GET"])
def tx_status(txid):
    wallet = get_selected_wallet()
    if not wallet:
        return jsonify({"error": "Nenhuma wallet selecionada"}), 400

    result = interpret_tx(txid, wallet, rpc)
    status_code = 404 if result["status"] == "unknown" else 200
    return jsonify(result), status_code


@app.route("/status", methods=["GET"])
def status():
    try:
        cur = state.get("current_txid")
        wallet = get_selected_wallet()

        if state.get("seen_in_mempool") and cur and not state.get("confirmed"):
            tx = rpc.call("gettransaction", [cur], wallet=wallet)
            bh = tx.get("blockhash")
            conf = int(tx.get("confirmations", 0) or 0)

            if bh and conf > 0:
                state["confirmed"] = True
                state["block_hash"] = bh
                state["status"] = "confirmed"

    except Exception as e:
        print("[/status confirm-check] erro:", e)

    return jsonify(state)


if __name__ == "__main__":
    # Auto-seleciona a primeira wallet carregada
    try:
        wallets = rpc.call("listwallets")
        if wallets:
            set_selected_wallet(wallets[0])
            print(f"Wallet selecionada: {wallets[0]}")
        else:
            print("Aviso: nenhuma wallet carregada no nó")
    except Exception as e:
        print(f"Aviso: não foi possível listar wallets: {e}")

    start_zmq_listeners()
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=True, use_reloader=False)
