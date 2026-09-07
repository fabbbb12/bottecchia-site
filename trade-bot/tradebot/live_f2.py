"""Paper trading ao vivo pra F2 (cash-and-carry com filtro de funding
mínimo) — igual ao resto do projeto, 100% simulado, nenhuma ordem real
enviada a lugar nenhum. Diferente de `tradebot/live.py` (que segue
preço/sinal técnico), aqui o "preço" que importa é a taxa de funding do
perpétuo — então este módulo é pensado pra ser chamado periodicamente
(a cada ciclo de funding, ~8h), não num loop contínuo local, e cada
chamada busca só os eventos novos desde a última vez que rodou.

Mesma lógica de `tradebot/backtest_f2.py`, mas incremental: mantém um
histórico rolante de funding (o suficiente pra calcular a média móvel
de `LOOKBACK_EVENTS`) e o estado da posição (dentro/fora, capital,
basis de referência) num arquivo JSON, pra sobreviver entre execuções.
"""

import json
import logging
from pathlib import Path

import pandas as pd

from tradebot.backtest_f2 import ENTRY_FEE_RATE, LOOKBACK_EVENTS, MIN_FUNDING_RATE_THRESHOLD
from tradebot.binance_data import fetch_binance_funding_rates, fetch_binance_futures_klines
from tradebot.data import fetch_ohlcv

logger = logging.getLogger("tradebot.live_f2")

BOOTSTRAP_PERIOD = "35d"  # cobre LOOKBACK_EVENTS (90 eventos de 8h = 30 dias) com folga


def _state_path(state_dir: Path, symbol: str) -> Path:
    safe_symbol = symbol.replace("/", "_")
    return state_dir / f"f2_{safe_symbol}.json"


def _log_path(state_dir: Path, symbol: str) -> Path:
    safe_symbol = symbol.replace("/", "_")
    return state_dir / f"f2_{safe_symbol}_eventos.jsonl"


def _append_events_log(path: Path, events: list[dict]) -> None:
    """Log append-only (uma linha JSON por evento) com o histórico completo
    de decisões -- diferente do `funding_history` no estado, que só guarda
    a janela rolante. É o que o dashboard (`scripts/f2_dashboard.py`) lê
    pra desenhar a curva de patrimônio com marcações de entrada/saída."""
    if not events:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")


def _default_state(starting_cash: float) -> dict:
    return {
        "starting_cash": starting_cash,
        "capital": starting_cash,
        "in_position": False,
        "prev_basis": None,
        "last_processed_ts": None,
        "funding_history": [],  # últimas LOOKBACK_EVENTS taxas, mais recente por último
        "num_entries": 0,
        "events_processed": 0,
    }


def _load_state(path: Path, starting_cash: float) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return _default_state(starting_cash)


def _save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2))


def process_new_events(
    state: dict,
    funding_rates: pd.Series,
    basis: pd.Series,
    entry_fee_rate: float = ENTRY_FEE_RATE,
    lookback_events: int = LOOKBACK_EVENTS,
    min_funding_rate_threshold: float = MIN_FUNDING_RATE_THRESHOLD,
) -> tuple[dict, list[dict]]:
    """Aplica, em ordem, os eventos novos (não vistos ainda) descritos por
    `funding_rates`/`basis` (mesmo índice de timestamps) ao estado
    existente. Função pura, sem rede — testável isoladamente. Devolve o
    estado atualizado e a lista de eventos processados (pra log/relatório)."""
    history = list(state["funding_history"])
    capital = state["capital"]
    in_position = state["in_position"]
    prev_basis = state["prev_basis"]
    events_log = []

    for ts in funding_rates.index:
        trailing_avg = sum(history[-lookback_events:]) / len(history[-lookback_events:]) if len(history) >= lookback_events else None
        want_in = trailing_avg is not None and trailing_avg >= min_funding_rate_threshold

        transitioned = None
        if want_in and not in_position:
            capital *= (1 - 2 * entry_fee_rate)
            in_position = True
            prev_basis = basis.loc[ts]
            transitioned = "ENTROU"
        elif not want_in and in_position:
            capital *= (1 - 2 * entry_fee_rate)
            in_position = False
            prev_basis = None
            transitioned = "SAIU"

        r_funding = None
        r_basis = None
        if in_position:
            r_funding = float(funding_rates.loc[ts])
            r_basis = -(float(basis.loc[ts]) - float(prev_basis))
            prev_basis = float(basis.loc[ts])
            capital *= (1 + r_funding + r_basis)

        history.append(float(funding_rates.loc[ts]))
        history = history[-lookback_events:]

        events_log.append(
            {
                "timestamp": str(ts),
                "funding_rate": float(funding_rates.loc[ts]),
                "trailing_avg": trailing_avg,
                "in_position": in_position,
                "transitioned": transitioned,
                "r_funding": r_funding,
                "r_basis": r_basis,
                "capital_after": capital,
            }
        )

    state = dict(state)
    state["capital"] = capital
    state["in_position"] = in_position
    state["prev_basis"] = prev_basis
    state["funding_history"] = history
    state["last_processed_ts"] = str(funding_rates.index[-1]) if len(funding_rates) else state["last_processed_ts"]
    state["num_entries"] = state["num_entries"] + sum(1 for e in events_log if e["transitioned"] == "ENTROU")
    state["events_processed"] = state["events_processed"] + len(events_log)
    return state, events_log


def run_once(symbol: str, state_dir: Path = Path("state"), starting_cash: float = 10_000.0) -> dict:
    path = _state_path(state_dir, symbol)
    state = _load_state(path, starting_cash)
    is_bootstrap = state["last_processed_ts"] is None

    if is_bootstrap:
        # primeira vez: só primer o histórico de funding (sem simular
        # P&L retroativo -- isso já é coberto pelo backtest, não aqui)
        funding = fetch_binance_funding_rates(symbol, period=BOOTSTRAP_PERIOD)
        state["funding_history"] = [float(r) for r in funding["funding_rate"].tail(LOOKBACK_EVENTS)]
        state["last_processed_ts"] = str(funding.index[-1])
        _save_state(path, state)
        logger.info(
            "[%s] Bootstrap: histórico de funding primado com %d eventos (até %s). "
            "Nenhuma posição aberta ainda -- primeira decisão real acontece na próxima chamada.",
            symbol,
            len(state["funding_history"]),
            state["last_processed_ts"],
        )
        return {"symbol": symbol, "bootstrap": True, "state": state, "events": []}

    last_ts = pd.Timestamp(state["last_processed_ts"])
    start = (last_ts + pd.Timedelta(milliseconds=1)).strftime("%Y-%m-%d")
    funding = fetch_binance_funding_rates(symbol, start=start)
    funding = funding[funding.index > last_ts]
    if funding.empty:
        logger.info("[%s] Nenhum evento novo de funding desde %s.", symbol, last_ts)
        return {"symbol": symbol, "bootstrap": False, "state": state, "events": []}

    spot = fetch_ohlcv(symbol, interval="1h", start=start)
    perp = fetch_binance_futures_klines(symbol, interval="1h", start=start)
    spot_aligned = spot["close"].reindex(funding.index, method="ffill")
    perp_aligned = perp["close"].reindex(funding.index, method="ffill")
    basis = (perp_aligned - spot_aligned) / spot_aligned
    valid = basis.dropna().index
    funding = funding.loc[valid]
    basis = basis.loc[valid]

    state, events = process_new_events(state, funding["funding_rate"], basis)
    _save_state(path, state)
    _append_events_log(_log_path(state_dir, symbol), events)

    for e in events:
        logger.info(
            "[%s] %s funding=%.5f%% media_movel=%s posicao=%s%s capital=%.2f",
            symbol,
            e["timestamp"],
            e["funding_rate"] * 100,
            f"{e['trailing_avg']*100:.5f}%" if e["trailing_avg"] is not None else "n/d",
            "DENTRO" if e["in_position"] else "FORA",
            f" [{e['transitioned']}]" if e["transitioned"] else "",
            e["capital_after"],
        )

    return {"symbol": symbol, "bootstrap": False, "state": state, "events": events}


def print_status(symbol: str, result: dict) -> None:
    state = result["state"]
    print(f"\n=== F2 ao vivo (PAPER TRADING) — {symbol} ===")
    if result["bootstrap"]:
        print("Histórico de funding primado. Nenhuma posição aberta ainda.")
        print(f"Próxima chamada já decide com base em {len(state['funding_history'])} eventos.")
        return
    print(f"Capital atual:        {state['capital']:.2f}")
    print(f"Posição:              {'DENTRO' if state['in_position'] else 'FORA'}")
    print(f"Eventos novos processados agora: {len(result['events'])}")
    print(f"Total de entradas até agora:      {state['num_entries']}")
    print(f"Total de eventos processados:     {state['events_processed']}")
    print(f"Último evento visto:              {state['last_processed_ts']}")
