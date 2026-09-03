import json

from normalization.normalize import (
    normalize_market,
    normalize_order_book,
    normalize_price_point,
    normalize_tokens,
    normalize_trade,
)


def test_normalize_market_basic_fields():
    raw = {
        "conditionId": "0xabc",
        "eventId": "evt1",
        "question": "Will X happen?",
        "slug": "will-x-happen",
        "active": True,
        "closed": False,
        "negRisk": False,
        "startDate": "2024-01-01T00:00:00Z",
        "endDate": "2024-06-01T00:00:00Z",
        "category": "Politics",
    }
    market = normalize_market(raw)
    assert market["market_id"] == "0xabc"
    assert market["event_id"] == "evt1"
    assert market["status"] == "active"
    assert market["neg_risk"] == 0
    assert market["mutually_exclusive"] is None  # nunca inferido
    assert market["start_time"] is not None


def test_normalize_market_closed_status():
    raw = {"conditionId": "0xabc", "active": False, "closed": True}
    market = normalize_market(raw)
    assert market["status"] == "closed"


def test_normalize_tokens_pairs_ids_with_outcomes():
    raw_market = {
        "conditionId": "0xabc",
        "clobTokenIds": json.dumps(["tok_yes", "tok_no"]),
        "outcomes": json.dumps(["Yes", "No"]),
    }
    tokens = normalize_tokens(raw_market)
    assert len(tokens) == 2
    assert tokens[0] == {"token_id": "tok_yes", "market_id": "0xabc", "outcome": "Yes", "outcome_index": 0}
    assert tokens[1]["outcome"] == "No"


def test_normalize_tokens_handles_missing_outcomes_list():
    raw_market = {"conditionId": "0xabc", "clobTokenIds": json.dumps(["tok_yes"])}
    tokens = normalize_tokens(raw_market)
    assert tokens[0]["outcome"] is None


def test_normalize_order_book_sorts_and_picks_best():
    raw = {
        "bids": [{"price": "0.48", "size": "10"}, {"price": "0.50", "size": "5"}],
        "asks": [{"price": "0.55", "size": "20"}, {"price": "0.52", "size": "8"}],
    }
    snapshot = normalize_order_book(raw, token_id="tok_yes", timestamp=1_700_000_000)
    assert snapshot["best_bid"] == 0.50
    assert snapshot["best_ask"] == 0.52
    assert snapshot["bid_depth"] == 15.0
    assert snapshot["ask_depth"] == 28.0
    parsed_book = json.loads(snapshot["book_data"])
    assert parsed_book["asks"][0] == [0.52, 8.0]


def test_normalize_order_book_handles_empty_sides():
    raw = {"bids": [], "asks": [{"price": "0.5", "size": "1"}]}
    snapshot = normalize_order_book(raw, "tok", 1)
    assert snapshot["best_bid"] is None
    assert snapshot["best_ask"] == 0.5


def test_normalize_trade_basic():
    raw = {"timestamp": 1_700_000_000, "price": "0.51", "size": "10", "side": "buy"}
    trade = normalize_trade(raw, token_id="tok_yes")
    assert trade["price"] == 0.51
    assert trade["size"] == 10.0
    assert trade["side"] == "buy"


def test_normalize_price_point_short_keys():
    raw = {"t": 1_700_000_000, "p": "0.42"}
    point = normalize_price_point(raw, token_id="tok_yes")
    assert point["timestamp"] == 1_700_000_000
    assert point["price"] == 0.42
    assert point["source"] == "clob_prices_history"
