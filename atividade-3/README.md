# CoreCraft — Atividade 3: Múltiplas Wallets e Estado Interpretado

Sistema web para criação, envio e monitoramento de transações Bitcoin em **signet**, com suporte a **múltiplas wallets** e **interpretação de estado** em tempo real.

---

## Visão geral (o que o sistema faz)

- Conecta a um nó Bitcoin Core via **RPC** com autenticação por **cookie file**
- Escuta eventos de **mempool** e **novos blocos** via **ZMQ**
- Expõe uma **API REST** em Flask para criação e acompanhamento de transações
- Serve um frontend para:
  - selecionar wallet
  - consultar saldo/UTXOs
  - enviar transações
  - acompanhar o ciclo **broadcast → mempool → confirmado**
- Interpreta o estado de cada transação com mensagens descritivas e avisos contextuais (ex.: tempo excessivo na mempool)

---

## Pré-requisitos

- Python 3.10 ou superior
- Bitcoin Core rodando em modo **signet** com **ZMQ** habilitado

Exemplo de configuração no `bitcoin.conf`:

```conf
signet=1
datadir=/mnt/dados2
server=1
zmqpubhashtx=tcp://127.0.0.1:18123
zmqpubhashblock=tcp://127.0.0.1:18123
```

---

## Configuração

A autenticação com o nó usa o cookie file gerado automaticamente pelo Bitcoin Core.  
O arquivo é lido a cada chamada RPC, então continua funcionando mesmo após reinicializações do nó.

Todas as configurações têm valores padrão e podem ser sobrescritas por variáveis de ambiente:

| Variável | Padrão | Descrição |
| --- | --- | --- |
| `BITCOIN_DATADIR` | `/mnt/dados2` | Diretório de dados do Bitcoin Core |
| `BITCOIN_COOKIE` | `$BITCOIN_DATADIR/signet/.cookie` | Caminho completo do cookie file |
| `RPC_HOST` | `127.0.0.1` | Host do RPC do Bitcoin Core |
| `RPC_PORT` | `38332` | Porta RPC (signet) |
| `ZMQ_HOST` | `127.0.0.1` | Host do ZMQ |
| `ZMQ_PORT` | `18123` | Porta ZMQ |
| `FLASK_HOST` | `0.0.0.0` | Interface de escuta do Flask |
| `FLASK_PORT` | `5000` | Porta do Flask |

---

## Como rodar

```bash
cd atividade-3
pip install -r requirements.txt
python3 backend.py
```

Frontend: `http://localhost:5000`.

---

## Arquitetura

```text
┌──────────────────────────────────────────────────┐
│                   Frontend                        │
│              (frontend.html)                      │
│  ┌────────────┐ ┌──────────┐ ┌────────────────┐  │
│  │ Seletor    │ │ Card     │ │ Lista de       │  │
│  │ Wallet     │ │ Saldo    │ │ Transações     │  │
│  └─────┬──────┘ └────┬─────┘ └───────┬────────┘  │
│        │             │               │            │
│        ▼             ▼               ▼            │
│   POST /wallet  GET /wallet    GET /tx/<txid>     │
│   /select       /status                           │
└──────────────────────┬───────────────────────────┘
                       │ HTTP (porta 5000)
┌──────────────────────▼───────────────────────────┐
│                 Backend (Flask)                    │
│                  backend.py                        │
│  ┌──────────┐ ┌────────────┐ ┌────────────────┐  │
│  │ wallet.py │ │ tx_builder │ │ interpreter.py │  │
│  │ (estado)  │ │ (constrói) │ │ (interpreta)   │  │
│  └─────┬─────┘ └─────┬──────┘ └───────┬────────┘  │
│        │             │               │            │
│        ▼             ▼               ▼            │
│              rpc.py (cookie auth)                  │
│        ┌─────────────┴─────────────┐              │
│        │ node-level  │ wallet-level│              │
│        │ /           │ /wallet/X   │              │
│        └─────────────┴─────────────┘              │
└──────────────────────┬───────────────────────────┘
                       │ RPC (porta 38332)
                       │ ZMQ (porta 18123)
┌──────────────────────▼───────────────────────────┐
│            Bitcoin Core (signet)                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │ wallet1  │ │ wallet2  │ │ wallet3  │          │
│  └──────────┘ └──────────┘ └──────────┘          │
└──────────────────────────────────────────────────┘
```

---

## API

| Método | Endpoint | Descrição |
| --- | --- | --- |
| GET | `/` | Serve o frontend |
| GET | `/wallets` | Lista wallets disponíveis, carregadas e selecionada |
| POST | `/wallet/select` | Seleciona a wallet ativa (carrega se necessário) |
| GET | `/wallet/status` | Saldo e contagem de UTXOs da wallet selecionada |
| POST | `/send` | Constrói, assina e transmite uma transação |
| GET | `/tx/<txid>` | Status enriquecido com interpretação e `age_seconds` |
| GET | `/status` | Estado global da última transação acompanhada |

### Exemplo: enviar transação

```bash
curl -X POST http://localhost:5000/send \
  -H "Content-Type: application/json" \
  -d '{"address": "tb1q...", "amount": 0.0001}'
```

### Exemplo: consultar status enriquecido

```bash
curl http://localhost:5000/tx/<txid>
```

Resposta (exemplo):

```json
{
  "txid": "...",
  "wallet": "minha-wallet",
  "status": "mempool",
  "confirmed": false,
  "confirmations": 0,
  "block_hash": null,
  "age_seconds": 45,
  "message": "Transação aceita na mempool, aguardando inclusão em bloco.",
  "warning": null
}
```

---

## Funcionalidades implementadas

1. **Cookie auth dinâmica** — leitura do `.cookie` a cada chamada RPC (sem cache), compatível com reinicializações do nó
2. **Suporte a múltiplas wallets** — listagem via `listwalletdir`, carregamento sob demanda via `loadwallet`, seleção de wallet ativa com contexto isolado por endpoint
3. **Construção manual de transações** — seleção de UTXOs, cálculo de fee fixa e troco, serialização via `createrawtransaction` (node-level), assinatura via `signrawtransactionwithwallet` (wallet-level)
4. **Monitoramento ZMQ** — dois sockets para `hashtx` e `hashblock`, confirmação via `gettransaction` (wallet) com fallback para varredura de bloco
5. **Interpretação de estado** — `interpret_tx` classifica em `broadcast`, `mempool`, `confirmed` ou `unknown`, com mensagens e aviso de tempo excessivo na mempool (> 2 minutos)

---

## Deploy em produção

**URL:** https://atividade3corecraft.wakeupanon.com

### Arquitetura (produção)

```text
Cloudflare (DNS + SSL) → Nginx (443, reverse proxy) → Flask (5000, local)
```

- **Cloudflare** gerencia DNS e termina SSL/TLS
- **Nginx** recebe requisições HTTPS e encaminha para o Flask local
- **Flask** roda na porta 5000 e serve API + frontend
- Configuração do Nginx em `/etc/nginx/sites-available/atividade3corecraft`

### Serviço systemd

O backend é gerenciado pelo serviço `corecraft3`:

```bash
sudo systemctl status corecraft3
sudo systemctl restart corecraft3
sudo systemctl stop corecraft3
sudo journalctl -u corecraft3 -f
```

### Ambiente de produção

- `BITCOIN_DATADIR` aponta para o datadir do Bitcoin Core em signet
- Nó em signet com 3 wallets configuradas para testes
- Autenticação via cookie file compatível com reinicializações do nó (sem alterações de configuração)