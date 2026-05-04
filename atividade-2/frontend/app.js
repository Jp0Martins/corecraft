async function getJSON(url){
  const r = await fetch(url, { cache: "no-store" });
  if(!r.ok) throw new Error(`HTTP ${r.status}`);
  return await r.json();
}

function shortHex(h){
  if(!h) return "—";
  if(h.length <= 20) return h;
  return h.slice(0,10) + "…" + h.slice(-10);
}

function tsToLocal(ts){
  if(!ts) return "—";
  const d = new Date(ts * 1000);
  return d.toLocaleString();
}

function renderLatestList(el, items, field, label){
  el.innerHTML = "";
  if(!items || items.length === 0){
    el.innerHTML = `<div class="muted">Nenhum evento ainda.</div>`;
    return;
  }
  for(const it of items){
    const row = document.createElement("div");
    row.className = "item";
    row.innerHTML = `
      <div class="mono">${shortHex(it[field])}</div>
      <div class="badge">${label} • ${tsToLocal(it.ts)}</div>
    `;
    el.appendChild(row);
  }
}

function renderList(el, items, label){
  el.innerHTML = "";
  if(!items || items.length === 0){
    el.innerHTML = `<div class="muted">Nenhum evento ainda. (Em signet/mainnet isso aparece naturalmente; em regtest, gere blocos/txs.)</div>`;
    return;
  }
  for(const it of items){
    const row = document.createElement("div");
    row.className = "item";
    row.innerHTML = `
      <div class="mono">${shortHex(it.value)}</div>
      <div class="badge">${label} • ${tsToLocal(it.ts)}</div>
    `;
    el.appendChild(row);
  }
}

async function refresh(){
  const [health, state] = await Promise.all([
    getJSON("/api/health"),
    getJSON("/api/state")
  ]);

  // Novos endpoints em paralelo — falha individual não interrompe os cards existentes
  const [resSummary, resLatest, resComparison] = await Promise.allSettled([
    getJSON("/api/events/summary"),
    getJSON("/api/events/latest"),
    getJSON("/api/events/state-comparison")
  ]);

  const pill = document.getElementById("healthPill");
  if(health.rpc_ok){
    const age = (health.zmq_last_event_age_s === null || health.zmq_last_event_age_s === undefined)
      ? "—"
      : `${health.zmq_last_event_age_s}s`;
    pill.textContent = `RPC ok • ZMQ age: ${age}`;
    pill.style.borderColor = "rgba(110,243,165,.28)";
  } else {
    pill.textContent = `RPC falhou • ${String(health.rpc_error || "").slice(0,80)}`;
    pill.style.borderColor = "rgba(255,107,107,.35)";
  }

  const rpc = state.rpc || {};
  document.getElementById("chain").textContent = rpc.chain ?? "—";
  document.getElementById("height").textContent = rpc.height ?? "—";
  document.getElementById("bestblockhash").textContent = rpc.bestblockhash ?? "—";
  document.getElementById("mempoolSize").textContent = rpc.mempool_size ?? "—";

  const zmq = state.zmq || {};
  document.getElementById("lastSeenBlock").textContent = zmq.last_seen_blockhash ?? "—";
  document.getElementById("blockCount").textContent = zmq.counters?.block_events ?? "—";
  document.getElementById("txCount").textContent = zmq.counters?.tx_events ?? "—";

  const warn = document.getElementById("divergenceWarn");
  warn.style.display = (state.analysis?.bestblock_vs_last_seen_diverged) ? "block" : "none";

  renderList(document.getElementById("blockList"), zmq.blocks || [], "hashblock");
  renderList(document.getElementById("txList"), zmq.txs || [], "hashtx");

  document.getElementById("serverTime").textContent = `server_time: ${tsToLocal(state.server_time)}`;

  if(resSummary.status === "fulfilled"){
    const s = resSummary.value;
    document.getElementById("sumBlocks").textContent   = s.blocks_observed ?? "—";
    document.getElementById("sumTxs").textContent      = s.tx_observed ?? "—";
    document.getElementById("sumTxRate").textContent   = s.tx_per_second !== null && s.tx_per_second !== undefined
      ? `${s.tx_per_second} tx/s` : "—";
    document.getElementById("sumLastEvent").textContent = tsToLocal(s.last_event_time);
  }

  if(resComparison.status === "fulfilled"){
    const c = resComparison.value;
    const statusEl = document.getElementById("divStatus");
    document.getElementById("divBest").textContent = shortHex(c.best_block);
    document.getElementById("divLast").textContent = shortHex(c.last_seen_block);
    statusEl.className = "divStatus";
    if(c.divergence === null){
      statusEl.classList.add("divWaiting");
      statusEl.textContent = "⏳ Aguardando primeiro bloco via ZMQ";
    } else if(c.divergence){
      statusEl.classList.add("divAlert");
      statusEl.textContent = "⚠ Divergência detectada: bestblockhash (RPC) ≠ último bloco visto (ZMQ)";
    } else {
      statusEl.classList.add("divOk");
      statusEl.textContent = "✅ Sincronizado";
    }
  }

  if(resLatest.status === "fulfilled"){
    const l = resLatest.value;
    renderLatestList(document.getElementById("latestBlocks"), l.blocks || [], "hash",  "bloco");
    renderLatestList(document.getElementById("latestTxs"),   l.txs   || [], "txid", "tx");
  }
}

document.getElementById("btnRefresh").addEventListener("click", () => refresh().catch(console.error));

refresh().catch(console.error);
setInterval(() => refresh().catch(()=>{}), 1500);

