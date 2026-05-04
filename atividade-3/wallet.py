# wallet.py
from rpc import BitcoinRPC
from config import RPC_URL, COOKIE_FILE

rpc = BitcoinRPC(RPC_URL, COOKIE_FILE)

_selected_wallet = None

def get_selected_wallet():
    return _selected_wallet

def set_selected_wallet(name):
    global _selected_wallet
    _selected_wallet = name

def get_utxos():
    w = get_selected_wallet()
    if not w:
        raise Exception("Nenhuma wallet selecionada")
    return rpc.call("listunspent", [1, 9999999], wallet=w)

def get_new_address():
    w = get_selected_wallet()
    if not w:
        raise Exception("Nenhuma wallet selecionada")
    return rpc.call("getnewaddress", [], wallet=w)

def get_balance():
    w = get_selected_wallet()
    if not w:
        raise Exception("Nenhuma wallet selecionada")
    return rpc.call("getbalance", [], wallet=w)
