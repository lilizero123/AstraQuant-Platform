from datetime import datetime

from core.risk.risk_manager import RiskConfig, RiskManager, RiskLevel
from core.strategy.base import Order, OrderSide, OrderStatus, OrderType, Position


def _build_order(price=10.0):
    return Order(
        order_id="o1",
        code="000001",
        side=OrderSide.BUY,
        price=price,
        quantity=100,
        order_type=OrderType.LIMIT,
        status=OrderStatus.SUBMITTED,
        create_time=datetime.now(),
    )


def test_risk_journal_written(tmp_path):
    journal_path = tmp_path / "risk.csv"
    manager = RiskManager(RiskConfig(max_price_deviation=1.0), journal_path=str(journal_path))
    allowed, reason = manager.check_order(
        order=_build_order(price=15.0),
        positions={},
        cash=100000,
        total_value=100000,
        current_price=10.0,
    )
    assert allowed is False
    assert journal_path.exists()
    content = journal_path.read_text(encoding="utf-8")
    assert "价格偏离" in content
