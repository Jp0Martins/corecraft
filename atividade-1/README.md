# CoreCraft — Atividade 1: Painel RPC Bitcoin

Painel web local que se comunica com um node Bitcoin via **JSON-RPC** (sem uso de ZMQ).  
Stack utilizada: **Bitcoin Core → Backend Python (Flask) → Frontend JavaScript**.

---

## Sobre esta entrega

Este diretório contém a implementação da **Atividade 1** do CoreCraft: um painel para visualizar informações do node, mempool e blocos recentes, além de consultas por **bloco** e **transação**.

## O que o painel exibe

| Seção | Dados |
| --- | --- |
| Estado do node | chain, blocos, headers, dificuldade, best block hash |
| Mempool | contagem de txs, bytes, uso de memória, minfee |
| Mempool Intelligence | distribuição de fee rates (low/medium/high), vsize total, médias |
| Node Sync Status | lag entre headers e blocks, status de sincronização |
| Blocos recentes | height, txs, avg fee rate, total fee, timestamp, hash |
| Consultar bloco | resumo completo por hash |
| Consultar transação | detalhes por txid (requer `txindex=1` ou tx na mempool) |

---

## Estrutura do projeto

```text
atividade-1/
├── backend/
│   ├── app.py        # servidor Flask com os endpoints /api/*
│   └── rpc.py        # cliente JSON-RPC (cookie auth ou RPC_USER/RPC_PASS)
└── frontend/
    ├── index.html
    ├── app.js
    └── styles.css
```

---

## Como executar

### Pré-requisito

- Node Bitcoin rodando localmente (**mainnet**, **signet**, **testnet** ou **regtest**)

### Passo a passo

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install flask requests
python app.py
```

A aplicação ficará disponível em: `http://127.0.0.1:8080`.

---

## Configuração RPC

Por padrão, o backend usa **cookie auth** (`~/.bitcoin/.cookie`).

Se preferir configurar manualmente, exporte as variáveis antes de rodar:

```bash
export RPC_USER=seu_usuario
export RPC_PASS=sua_senha
export RPC_PORT=8332        # porta padrão mainnet
export BTC_NETWORK=main     # main | testnet | regtest | signet
```

---

## API (endpoints)

| Método | Rota | Descrição |
| --- | --- | --- |
| GET | `/api/node` | snapshot do node (blockchain + mempool + rede) |
| GET | `/api/blocks/recent?n=10` | N blocos mais recentes com stats |
| GET | `/api/block/<hash>` | resumo de um bloco |
| GET | `/api/tx/<txid>` | detalhes de uma transação |
| GET | `/api/mempool/summary` | análise de fee rates da mempool |
| GET | `/api/blockchain/lag` | diferença entre headers e blocks |