"""Gera um dashboard HTML autocontido (um arquivo só, abre em qualquer
navegador, sem servidor nem internet) a partir do estado e do log de
eventos do paper trading ao vivo de F2 (`tradebot/live_f2.py`).

Uso: python scripts/f2_dashboard.py SYMBOL [--state-dir state]
Ex.:  python scripts/f2_dashboard.py BTCUSDT

Lê `state/f2_BTCUSDT.json` (estado atual) e
`state/f2_BTCUSDT_eventos.jsonl` (histórico completo de decisões) e
gera `state/f2_BTCUSDT_dashboard.html`.
"""

import argparse
import base64
import json
from io import BytesIO
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def _load_events(log_path: Path) -> pd.DataFrame:
    if not log_path.exists():
        return pd.DataFrame()
    rows = [json.loads(line) for line in log_path.read_text().splitlines() if line.strip()]
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df.sort_values("timestamp").reset_index(drop=True)


def _build_chart_base64(events: pd.DataFrame, symbol: str) -> str:
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(events["timestamp"], events["capital_after"], color="#2563eb", linewidth=1.5, label="Capital (F2)")

    entries = events[events["transitioned"] == "ENTROU"]
    exits = events[events["transitioned"] == "SAIU"]
    ax.scatter(entries["timestamp"], entries["capital_after"], color="#16a34a", marker="^", s=90, zorder=5, label="Entrada")
    ax.scatter(exits["timestamp"], exits["capital_after"], color="#dc2626", marker="v", s=90, zorder=5, label="Saída")

    ax.set_title(f"F2 (paper trading) — {symbol}")
    ax.set_ylabel("Capital (USD)")
    ax.legend(loc="upper left")
    ax.grid(alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=110)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _events_table_html(events: pd.DataFrame, max_rows: int = 200) -> str:
    view = events.tail(max_rows).iloc[::-1]
    rows = []
    for _, e in view.iterrows():
        badge = ""
        if e["transitioned"] == "ENTROU":
            badge = '<span style="color:#16a34a;font-weight:600">ENTROU</span>'
        elif e["transitioned"] == "SAIU":
            badge = '<span style="color:#dc2626;font-weight:600">SAIU</span>'
        rows.append(
            f"<tr><td>{e['timestamp']}</td><td>{e['funding_rate']*100:.5f}%</td>"
            f"<td>{'DENTRO' if e['in_position'] else 'FORA'}</td><td>{badge}</td>"
            f"<td>{e['capital_after']:.2f}</td></tr>"
        )
    return "\n".join(rows)


def build_dashboard(symbol: str, state_dir: Path) -> Path:
    safe_symbol = symbol.replace("/", "_")
    state_path = state_dir / f"f2_{safe_symbol}.json"
    log_path = state_dir / f"f2_{safe_symbol}_eventos.jsonl"
    out_path = state_dir / f"f2_{safe_symbol}_dashboard.html"

    if not state_path.exists():
        raise SystemExit(f"Nenhum estado encontrado em {state_path} -- roda o live_f2 pelo menos uma vez antes.")

    state = json.loads(state_path.read_text())
    events = _load_events(log_path)

    starting_cash = state.get("starting_cash", 10_000.0)
    capital = state["capital"]
    pnl_pct = (capital - starting_cash) / starting_cash * 100 if starting_cash else 0.0

    if not events.empty:
        chart_b64 = _build_chart_base64(events, symbol)
        chart_html = f'<img src="data:image/png;base64,{chart_b64}" style="max-width:100%">'
        table_html = _events_table_html(events)
    else:
        chart_html = "<p>Ainda sem eventos processados (só bootstrap) -- roda de novo depois do próximo ciclo de funding.</p>"
        table_html = ""

    html = f"""<!doctype html>
<html lang="pt-br"><head><meta charset="utf-8"><title>F2 Dashboard — {symbol}</title>
<style>
body {{ font-family: system-ui, sans-serif; background:#0f172a; color:#e2e8f0; margin:0; padding:24px; }}
.cards {{ display:flex; gap:16px; margin-bottom:24px; flex-wrap:wrap; }}
.card {{ background:#1e293b; border-radius:12px; padding:16px 20px; min-width:160px; }}
.card .label {{ font-size:12px; color:#94a3b8; text-transform:uppercase; }}
.card .value {{ font-size:24px; font-weight:700; margin-top:4px; }}
.positive {{ color:#4ade80; }}
.negative {{ color:#f87171; }}
table {{ border-collapse:collapse; width:100%; font-size:13px; }}
th, td {{ text-align:left; padding:6px 10px; border-bottom:1px solid #334155; }}
th {{ color:#94a3b8; font-weight:600; }}
h2 {{ margin-top:32px; }}
.disclaimer {{ color:#94a3b8; font-size:12px; margin-top:24px; }}
</style></head>
<body>
<h1>F2 — Cash-and-Carry com Filtro de Funding ({symbol})</h1>
<p class="disclaimer">100% PAPER TRADING — simulação, nenhuma ordem real foi enviada.</p>

<div class="cards">
  <div class="card"><div class="label">Saldo atual</div><div class="value">${capital:,.2f}</div></div>
  <div class="card"><div class="label">PnL</div><div class="value {'positive' if pnl_pct >= 0 else 'negative'}">{pnl_pct:+.2f}%</div></div>
  <div class="card"><div class="label">Posição</div><div class="value">{'DENTRO' if state['in_position'] else 'FORA'}</div></div>
  <div class="card"><div class="label">Nº de entradas</div><div class="value">{state['num_entries']}</div></div>
  <div class="card"><div class="label">Eventos processados</div><div class="value">{state['events_processed']}</div></div>
</div>

<h2>Curva de capital</h2>
{chart_html}

<h2>Histórico de eventos (mais recente primeiro)</h2>
<table>
<tr><th>Timestamp</th><th>Funding</th><th>Posição</th><th>Transição</th><th>Capital</th></tr>
{table_html}
</table>
</body></html>
"""
    out_path.write_text(html, encoding="utf-8")
    return out_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol")
    parser.add_argument("--state-dir", default="state")
    args = parser.parse_args()
    out_path = build_dashboard(args.symbol, Path(args.state_dir))
    print(f"Dashboard gerado em: {out_path.resolve()}")


if __name__ == "__main__":
    main()
