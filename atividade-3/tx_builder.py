# tx_builder.py
from decimal import Decimal, ROUND_DOWN

from rpc import BitcoinRPC
from config import RPC_URL, COOKIE_FILE
from wallet import get_utxos, get_selected_wallet

rpc = BitcoinRPC(RPC_URL, COOKIE_FILE)

SAT = Decimal("0.00000001")


def btc(value) -> Decimal:
    return Decimal(str(value)).quantize(SAT, rounding=ROUND_DOWN)


def build_transaction(to_address: str, amount_btc: float) -> str:
    wallet = get_selected_wallet()
    if not wallet:
        raise Exception("Nenhuma wallet selecionada")

    amount = btc(amount_btc)
    fee = btc("0.00001")
    target = amount + fee

    utxos = get_utxos()
    if not utxos:
        raise Exception("Nenhum UTXO disponível (listunspent vazio)")

    selected = []
    total_in = btc("0")

    for utxo in utxos:
        selected.append(utxo)
        total_in += btc(utxo["amount"])
        if total_in >= target:
            break

    if total_in < target:
        missing = target - total_in
        raise Exception(
            "Saldo insuficiente para amount+fee: "
            f"total_utxos={total_in:.8f} precisa={target:.8f} "
            f"(amount={amount:.8f} + fee={fee:.8f}) falta={missing:.8f}"
        )

    change = total_in - amount - fee

    inputs = [{"txid": utxo["txid"], "vout": int(utxo["vout"])} for utxo in selected]

    outputs = [{to_address: float(amount)}]

    dust_like_threshold = btc("0.00001")
    if change >= dust_like_threshold:
        change_address = rpc.call("getrawchangeaddress", [], wallet=wallet)
        outputs.append({change_address: float(change)})
    else:
        fee = fee + change
        change = btc("0")

    print("TX build:")
    print(" - inputs:", inputs)
    print(" - total_in:", f"{total_in:.8f}")
    print(" - amount:", f"{amount:.8f}")
    print(" - fee:", f"{fee:.8f}")
    print(" - change:", f"{change:.8f}")
    print(" - outputs:", outputs)

    # createrawtransaction é node-level (sem wallet)
    raw_tx = rpc.call("createrawtransaction", [inputs, outputs])
    return raw_tx
