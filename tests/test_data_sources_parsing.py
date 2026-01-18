import types

from core.data_sources.base import QuoteRecord, RequestManager
from core.data_sources.china import ChinaStockProvider


class DummyResponse:
    def __init__(self, text="", data=None):
        self.text = text
        self._data = data or {}

    def json(self):
        return self._data


def _patch_request(monkeypatch, text="", json_data=None):
    def fake_request(self, *args, **kwargs):
        resp = DummyResponse(text=text, data=json_data)
        return resp

    monkeypatch.setattr(RequestManager, "request", fake_request, raising=False)


def test_parse_sina_line(monkeypatch):
    record_line = (
        'var hq_str_sh600000="平安银行,10.00,9.80,10.50,10.70,9.90,0,0,1000,2000,'
        '0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2024-01-01,09:30:00";'
    )
    _patch_request(monkeypatch, text=record_line)
    provider = ChinaStockProvider(RequestManager())
    data = provider._fetch_from_sina(["600000"])
    assert "sh600000" in data
    quote = data["sh600000"]
    assert isinstance(quote, QuoteRecord)
    assert quote.price == 10.5
    assert quote.pre_close == 9.8
    assert quote.volume == 1000


def test_parse_tencent_line(monkeypatch):
    line = 'v_sh600000="1~平安银行~600000~10.50~9.80~10.10~1000~2000~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~20240101093000~0~0~10.70~9.90~0~0~0~0~0~0";'
    _patch_request(monkeypatch, text=line)
    provider = ChinaStockProvider(RequestManager())
    data = provider._fetch_from_tencent(["600000"])
    assert "sh600000" in data
    quote = data["sh600000"]
    assert quote.price == 10.5
    assert quote.high == 10.7
    assert quote.low == 9.9
