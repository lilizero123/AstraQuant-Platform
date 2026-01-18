from core.realtime.data_feed import CSVDataFeed


class DummyQuoteManager:
    def __init__(self):
        self.snapshots = []

    def on_snapshot(self, snapshot):
        self.snapshots.append(snapshot)


def test_csv_data_feed_replay(tmp_path):
    csv_file = tmp_path / "quotes.csv"
    csv_file.write_text(
        "code,datetime,open,high,low,close,volume\n"
        "000001,2024-01-01 09:30:00,10,10.2,9.8,10.1,1000\n"
        "000001,2024-01-01 09:31:00,10.1,10.3,9.9,10.0,900\n",
        encoding="utf-8",
    )
    feed = CSVDataFeed(str(csv_file), loop=False, speed=10.0)
    dummy = DummyQuoteManager()
    feed.set_quote_manager(dummy)
    assert feed.connect() is True
    feed.subscribe(["000001"])
    feed.replay_once()
    assert len(dummy.snapshots) == 2
    assert dummy.snapshots[0].code == "000001"
    assert dummy.snapshots[0].price == 10.1
