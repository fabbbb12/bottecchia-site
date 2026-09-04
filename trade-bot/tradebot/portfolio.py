"""Carteira de papel (paper trading): dinheiro e posições são simulados,
nenhuma ordem real é enviada a corretora nenhuma."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Fill:
    timestamp: datetime
    symbol: str
    side: str  # "BUY", "SELL", "SHORT" ou "COVER"
    quantity: float
    price: float
    fee: float

    @property
    def notional(self) -> float:
        return self.quantity * self.price


@dataclass
class Position:
    quantity: float = 0.0
    avg_price: float = 0.0
    peak_price: float = 0.0


class Portfolio:
    """Carteira simulada com uma única moeda de referência (ex: USD/BRL)."""

    def __init__(
        self,
        starting_cash: float,
        fee_rate: float = 0.001,
        slippage_rate: float = 0.0005,
    ):
        self.cash = starting_cash
        self.starting_cash = starting_cash
        self.fee_rate = fee_rate
        self.slippage_rate = slippage_rate
        self.positions: dict[str, Position] = {}
        self.fills: list[Fill] = []

    def position(self, symbol: str) -> Position:
        return self.positions.setdefault(symbol, Position())

    def _fill_price(self, side: str, market_price: float) -> float:
        """Aplica slippage simples: compra um pouco mais cara, vende um pouco mais barata."""
        if side == "BUY":
            return market_price * (1 + self.slippage_rate)
        return market_price * (1 - self.slippage_rate)

    def buy(self, timestamp: datetime, symbol: str, market_price: float, cash_fraction: float) -> Fill | None:
        """Compra usando uma fração do caixa disponível."""
        spend = self.cash * cash_fraction
        if spend <= 0:
            return None
        fill_price = self._fill_price("BUY", market_price)
        fee = spend * self.fee_rate
        quantity = (spend - fee) / fill_price
        if quantity <= 0:
            return None

        pos = self.position(symbol)
        total_cost = pos.avg_price * pos.quantity + quantity * fill_price
        pos.quantity += quantity
        pos.avg_price = total_cost / pos.quantity if pos.quantity else 0.0
        self.cash -= spend

        fill = Fill(timestamp, symbol, "BUY", quantity, fill_price, fee)
        self.fills.append(fill)
        return fill

    def sell(self, timestamp: datetime, symbol: str, market_price: float, position_fraction: float = 1.0) -> Fill | None:
        """Vende uma fração da posição atual."""
        pos = self.position(symbol)
        quantity = pos.quantity * position_fraction
        if quantity <= 0:
            return None
        fill_price = self._fill_price("SELL", market_price)
        proceeds = quantity * fill_price
        fee = proceeds * self.fee_rate

        pos.quantity -= quantity
        if pos.quantity <= 1e-12:
            pos.quantity = 0.0
            pos.avg_price = 0.0
            pos.peak_price = 0.0
        self.cash += proceeds - fee

        fill = Fill(timestamp, symbol, "SELL", quantity, fill_price, fee)
        self.fills.append(fill)
        return fill

    def short(self, timestamp: datetime, symbol: str, market_price: float, cash_fraction: float) -> Fill | None:
        """Abre/aumenta uma posição vendida (short), tamanho como fração do
        caixa disponível — mesma lógica de `buy()`, só invertida (quantidade
        fica negativa).

        SIMPLIFICAÇÃO IMPORTANTE: não modela chamada de margem nem custo de
        aluguel de ação (borrow cost) — o caixa recebido na venda a
        descoberto é tratado como caixa disponível pra uso, o que é
        otimista frente a uma conta margem real (que bloqueia colateral e
        cobra juros sobre o aluguel). Documentado aqui de propósito, do
        mesmo jeito que as outras simplificações do projeto."""
        notional = self.cash * cash_fraction
        if notional <= 0:
            return None
        fill_price = self._fill_price("SELL", market_price)
        fee = notional * self.fee_rate
        quantity = (notional - fee) / fill_price
        if quantity <= 0:
            return None

        pos = self.position(symbol)
        prior_short_qty = -pos.quantity if pos.quantity < 0 else 0.0
        total_value = pos.avg_price * prior_short_qty + quantity * fill_price
        pos.quantity -= quantity
        new_short_qty = -pos.quantity
        pos.avg_price = total_value / new_short_qty if new_short_qty else 0.0
        self.cash += notional - fee

        fill = Fill(timestamp, symbol, "SHORT", quantity, fill_price, fee)
        self.fills.append(fill)
        return fill

    def cover(
        self, timestamp: datetime, symbol: str, market_price: float, position_fraction: float = 1.0
    ) -> Fill | None:
        """Recompra (fecha) uma fração da posição vendida atual."""
        pos = self.position(symbol)
        short_qty = -pos.quantity if pos.quantity < 0 else 0.0
        quantity = short_qty * position_fraction
        if quantity <= 0:
            return None
        fill_price = self._fill_price("BUY", market_price)
        cost = quantity * fill_price
        fee = cost * self.fee_rate

        pos.quantity += quantity
        if pos.quantity >= -1e-12:
            pos.quantity = 0.0
            pos.avg_price = 0.0
            pos.peak_price = 0.0
        self.cash -= cost + fee

        fill = Fill(timestamp, symbol, "COVER", quantity, fill_price, fee)
        self.fills.append(fill)
        return fill

    def equity(self, prices: dict[str, float]) -> float:
        total = self.cash
        for symbol, pos in self.positions.items():
            total += pos.quantity * prices.get(symbol, pos.avg_price)
        return total

    def summary(self, prices: dict[str, float]) -> dict:
        equity = self.equity(prices)
        pnl = equity - self.starting_cash
        pnl_pct = (pnl / self.starting_cash * 100) if self.starting_cash else 0.0
        return {
            "cash": self.cash,
            "equity": equity,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "positions": {s: p.quantity for s, p in self.positions.items() if p.quantity != 0},
            "num_fills": len(self.fills),
        }


def compute_round_trip_pnls(fills: list[Fill]) -> list[float]:
    """Agrupa os fills em operações completas (posição zerada -> aberta ->
    zerada de novo) e devolve o resultado líquido (já com taxas) de cada
    uma. Um "trade" pode conter vários fills de abertura seguidos antes do
    fill que zera a posição. Trata posições compradas (BUY/SELL) e vendidas
    a descoberto (SHORT/COVER) simetricamente, cada lado só fecha com o
    fill do tipo oposto correspondente."""
    trades: list[float] = []
    open_value = 0.0
    open_side: str | None = None  # "LONG" ou "SHORT"
    for fill in fills:
        if fill.side == "BUY" and open_side in (None, "LONG"):
            open_value += fill.notional + fill.fee
            open_side = "LONG"
        elif fill.side == "SELL" and open_side == "LONG":
            proceeds = fill.notional - fill.fee
            trades.append(proceeds - open_value)
            open_value = 0.0
            open_side = None
        elif fill.side == "SHORT" and open_side in (None, "SHORT"):
            open_value += fill.notional - fill.fee
            open_side = "SHORT"
        elif fill.side == "COVER" and open_side == "SHORT":
            cost = fill.notional + fill.fee
            trades.append(open_value - cost)
            open_value = 0.0
            open_side = None
    return trades


def profit_factor(trade_pnls: list[float]) -> float:
    """Soma dos ganhos dividida pela soma das perdas (em módulo). > 1
    significa que os ganhos superam as perdas; sem perdas, é infinito."""
    gains = sum(p for p in trade_pnls if p > 0)
    losses = -sum(p for p in trade_pnls if p < 0)
    if losses == 0:
        return float("inf") if gains > 0 else 0.0
    return gains / losses
