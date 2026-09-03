"""Geração de gráficos com preço, indicadores e sinais de compra/venda.

Salva uma imagem PNG (não abre janela interativa) — funciona tanto em
backtest quanto no modo `live`, onde o arquivo é sobrescrito a cada ciclo
(basta manter um visualizador de imagens aberto apontando pro arquivo para
acompanhar "em tempo real", ou reabrir depois de cada atualização).
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def plot_signals(signals: pd.DataFrame, symbol: str, output_path: Path, title_suffix: str = "") -> Path:
    """Recebe o DataFrame já enriquecido por `generate_signals` (precisa ter
    close, sma_fast, sma_slow, bb_upper/mid/lower, rsi, macd/macd_signal/
    macd_hist e action) e salva um PNG com 3 painéis: preço, RSI e MACD."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, (ax_price, ax_rsi, ax_macd) = plt.subplots(
        3, 1, figsize=(12, 9), sharex=True, gridspec_kw={"height_ratios": [3, 1, 1]}
    )

    ax_price.plot(signals.index, signals["close"], label="Preço", color="black", linewidth=1.2)
    ax_price.plot(signals.index, signals["sma_fast"], label="Média rápida", color="tab:blue", linewidth=0.9)
    ax_price.plot(signals.index, signals["sma_slow"], label="Média lenta", color="tab:orange", linewidth=0.9)
    ax_price.fill_between(signals.index, signals["bb_lower"], signals["bb_upper"], color="gray", alpha=0.12, label="Bollinger")

    buys = signals[signals["action"] == "BUY"]
    sells = signals[signals["action"] == "SELL"]
    ax_price.scatter(buys.index, buys["close"], marker="^", color="green", s=60, zorder=5, label="Compra")
    ax_price.scatter(sells.index, sells["close"], marker="v", color="red", s=60, zorder=5, label="Venda")

    suffix = f" — {title_suffix}" if title_suffix else ""
    ax_price.set_title(f"{symbol}{suffix} (SIMULADO / PAPER)")
    ax_price.legend(loc="upper left", fontsize=8)
    ax_price.grid(alpha=0.2)

    ax_rsi.plot(signals.index, signals["rsi"], color="purple", linewidth=1.0)
    ax_rsi.axhline(70, color="red", linestyle="--", linewidth=0.7)
    ax_rsi.axhline(30, color="green", linestyle="--", linewidth=0.7)
    ax_rsi.set_ylabel("RSI")
    ax_rsi.grid(alpha=0.2)

    ax_macd.plot(signals.index, signals["macd"], label="MACD", color="tab:blue", linewidth=1.0)
    ax_macd.plot(signals.index, signals["macd_signal"], label="Sinal", color="tab:orange", linewidth=1.0)
    ax_macd.bar(signals.index, signals["macd_hist"], color="gray", alpha=0.4, width=1.0)
    ax_macd.legend(loc="upper left", fontsize=8)
    ax_macd.set_ylabel("MACD")
    ax_macd.grid(alpha=0.2)

    fig.tight_layout()
    fig.savefig(output_path, dpi=120)
    plt.close(fig)
    return output_path
