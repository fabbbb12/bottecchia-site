"""Modo 'ao vivo' — continua sendo PAPER TRADING: a cada intervalo, busca o
preço mais recente, calcula o sinal e simula a ordem em uma carteira local.
Nenhuma ordem é enviada a corretora ou exchange real."""

import json
import logging
import time
from pathlib import Path

from tradebot.data import fetch_ohlcv
from tradebot.portfolio import Portfolio
from tradebot.strategy import StrategyConfig, generate_signals

logger = logging.getLogger("tradebot.live")


def _state_path(state_dir: Path, symbol: str) -> Path:
    safe_symbol = symbol.replace("/", "_")
    return state_dir / f"portfolio_{safe_symbol}.json"


def _load_or_create_portfolio(path: Path, starting_cash: float) -> Portfolio:
    portfolio = Portfolio(starting_cash)
    if path.exists():
        data = json.loads(path.read_text())
        portfolio.cash = data["cash"]
        for symbol, pos in data.get("positions", {}).items():
            p = portfolio.position(symbol)
            p.quantity = pos["quantity"]
            p.avg_price = pos["avg_price"]
    return portfolio


def _save_portfolio(path: Path, portfolio: Portfolio) -> None:
    data = {
        "cash": portfolio.cash,
        "positions": {
            s: {"quantity": p.quantity, "avg_price": p.avg_price}
            for s, p in portfolio.positions.items()
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def run_once(
    symbol: str,
    strategy_cfg: StrategyConfig,
    portfolio: Portfolio,
    period: str = "6mo",
    interval: str = "1d",
    cash_fraction: float = 0.5,
) -> dict:
    df = fetch_ohlcv(symbol, period=period, interval=interval)
    signals = generate_signals(df, strategy_cfg)
    last = signals.iloc[-1]
    price = float(last["close"])
    action = last["action"]
    score = float(last["score"])

    fill = None
    if action == "BUY":
        fill = portfolio.buy(last.name, symbol, price, cash_fraction)
    elif action == "SELL":
        fill = portfolio.sell(last.name, symbol, price, position_fraction=1.0)

    summary = portfolio.summary({symbol: price})
    return {
        "symbol": symbol,
        "timestamp": str(last.name),
        "price": price,
        "score": score,
        "action": action,
        "fill": fill,
        "summary": summary,
    }


def run_loop(
    symbol: str,
    strategy_cfg: StrategyConfig,
    starting_cash: float = 10_000.0,
    period: str = "6mo",
    interval: str = "1d",
    cash_fraction: float = 0.5,
    poll_seconds: int = 3600,
    state_dir: Path = Path("state"),
    max_iterations: int | None = None,
) -> None:
    path = _state_path(state_dir, symbol)
    portfolio = _load_or_create_portfolio(path, starting_cash)

    iteration = 0
    while max_iterations is None or iteration < max_iterations:
        try:
            result = run_once(symbol, strategy_cfg, portfolio, period, interval, cash_fraction)
            _save_portfolio(path, portfolio)
            logger.info(
                "[%s] preco=%.4f score=%.2f acao=%s equity=%.2f pnl=%.2f%%",
                result["timestamp"],
                result["price"],
                result["score"],
                result["action"],
                result["summary"]["equity"],
                result["summary"]["pnl_pct"],
            )
        except Exception:
            logger.exception("Erro ao processar %s, tentando de novo no proximo ciclo", symbol)

        iteration += 1
        if max_iterations is not None and iteration >= max_iterations:
            break
        time.sleep(poll_seconds)
