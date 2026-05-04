# CoreCraft — Atividade 2: Eventos em Tempo Real (RPC + ZMQ)

Sistema que se conecta ao Bitcoin Core via **RPC** e **ZMQ**, processa eventos de blocos e transações em tempo real e expõe um estado derivado via **API HTTP** com **frontend web**.

**URL de produção:** https://atividade2corecraft.wakeupanon.com

---

## Visão geral

O backend mantém dois canais abertos com o nó Bitcoin Core:

- **RPC (HTTP)**: chamadas pontuais para obter o estado atual da chain (“fotografia”)
- **ZMQ (tcp)**: stream contínuo de eventos de novos blocos (`hashblock`) e transações (`hashtx`)

À medida que os eventos chegam via ZMQ, o estado é acumulado em memória. O frontend consome a API HTTP a cada **1,5 s** e exibe blocos, transações, contadores e um indicador de divergência em tempo real.

---

## Arquitetura

```text
Bitcoin Core
  │
  ├── ZMQ (tcp) ──► threads Python ──► InMemoryState (deque)
  │                                          │
  └── RPC (HTTP) ◄── Flask endpoints ◄───────┘
                           │
                       Frontend (HTML/JS)
```

### Evento → interpretação → estado derivado

O ZMQ entrega apenas o hash (bloco ou tx). O backend registra o timestamp, acumula contadores e mantém os últimos N eventos em um deque circular.  
O RPC é usado para consultas pontuais (altura, mempool, bestblockhash) e para comparação com o último bloco visto via ZMQ.

---

## API

### Produção

Base URL: `https://atividade2corecraft.wakeupanon.com`

| Endpoint | Descrição |
| --- | --- |
| `GET /api/health` | Verifica conectividade RPC e idade do último evento ZMQ |
| `GET /api/state` | Estado completo: dados RPC + eventos ZMQ acumulados + análise de divergência |
| `GET /api/events/summary` | Resumo: contadores de blocos/txs e taxa de tx/s calculada sobre o deque |
| `GET /api/events/latest` | Últimos eventos em formato limpo (`{hash, ts}` para blocos; `{txid, ts}` para txs) |
| `GET /api/events/state-comparison` | Compara `getbestblockhash` (RPC) vs último bloco via ZMQ; retorna `divergence: true/false/null` |

---

## Deploy (produção)

- **Servidor:** Contabo, Ubuntu 24.04
- **Bitcoin Core:** v31.0, modo signet, `txindex=1`
- **Proxy reverso:** nginx
- **HTTPS:** Cloudflare Origin Certificate
- **Backend:** systemd service rodando `gunicorn app:app`

Exemplo de estrutura do service unit:

```ini
[Service]
WorkingDirectory=/caminho/atividade-2/backend
ExecStart=/caminho/venv/bin/gunicorn app:app -b 127.0.0.1:8000
Restart=always
```

O nginx recebe requisições HTTPS e faz proxy para `127.0.0.1:8000`.

---

## Stack

- **Python 3 / Flask** — servidor HTTP e roteamento da API
- **pyzmq** — subscrição ao stream ZMQ do Bitcoin Core
- **requests** — chamadas JSON-RPC ao Bitcoin Core
- **gunicorn** — servidor WSGI para produção
- **Bitcoin Core** — nó rodando em modo signet

---

## Rodando localmente

### Pré-requisitos

- Bitcoin Core rodando em signet com ZMQ habilitado no `bitcoin.conf`:
  ```
  zmqpubhashblock=tcp://127.0.0.1:18123
  zmqpubhashtx=tcp://127.0.0.1:18123
  ```
- Cookie de autenticação disponível em `/mnt/dados2/signet/.cookie`

### Variáveis de ambiente (opcionais)

Os defaults já apontam para signet local.

| Variável | Default | Descrição |
| --- | --- | --- |
| `BITCOIN_RPC_URL` | `http://127.0.0.1:38332` | Endereço RPC do nó |
| `BITCOIN_COOKIE` | `/mnt/dados2/signet/.cookie` | Caminho do cookie de autenticação |
| `ZMQ_HASHBLOCK` | `tcp://127.0.0.1:18123` | Endpoint ZMQ para eventos de bloco |
| `ZMQ_HASHTX` | `tcp://127.0.0.1:18123` | Endpoint ZMQ para eventos de tx |
| `PORT` | `8000` | Porta do servidor Flask |

### Instalação de dependências

```bash
python3 -m venv ~/corecraft/venv
source ~/corecraft/venv/bin/activate
pip install flask requests pyzmq gunicorn
```

### Subir o backend

```bash
source ~/corecraft/venv/bin/activate
cd ~/corecraft/atividade-2/backend
python app.py
```

O frontend é servido pelo próprio Flask em `http://127.0.0.1:8000`.

### Testar endpoints

```bash
curl -s http://127.0.0.1:8000/api/health                  | python3 -m json.tool
curl -s http://127.0.0.1:8000/api/state                   | python3 -m json.tool
curl -s http://127.0.0.1:8000/api/events/summary          | python3 -m json.tool
curl -s http://127.0.0.1:8000/api/events/latest           | python3 -m json.tool
curl -s http://127.0.0.1:8000/api/events/state-comparison | python3 -m json.tool
```

---

## Estrutura de pastas

```text
atividade-2/
├── backend/
│   ├── app.py           # servidor Flask, threads ZMQ e endpoints da API
│   └── requirements.txt # dependências Python
└── frontend/
    ├── index.html       # interface web
    ├── app.js           # lógica de fetch e atualização do DOM
    └── styles.css       # tema dark
```