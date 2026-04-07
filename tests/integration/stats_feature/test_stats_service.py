from class_demo.stats_service.stats_service import StatsService


class _FakeFrame:
    def __init__(self, records):
        self._records = records

    def to_dict(self, orient="records"):
        assert orient == "records"
        return list(self._records)


class _FakeEndpoint:
    def __init__(self, records):
        self._records = records

    def get_data_frames(self):
        return [_FakeFrame(self._records)]


def test_get_player_points_leaders_sorts_and_limits():
    records = [
        {"PLAYER": "Player B", "TEAM_ABBREVIATION": "BBB", "PTS": 21.1},
        {"PLAYER": "Player A", "TEAM_ABBREVIATION": "AAA", "PTS": 30.2},
        {"PLAYER": "Player C", "TEAM_ABBREVIATION": "CCC", "PTS": 10.0},
    ]

    service = StatsService(
        season="2023-24",
        leaders_client_factory=lambda **kwargs: _FakeEndpoint(records),
    )

    leaders = service.get_player_points_leaders(top_n=2)

    assert len(leaders) == 2
    assert leaders[0]["player"] == "Player A"
    assert leaders[0]["team"] == "AAA"
    assert leaders[0]["points"] == 30.2
    assert leaders[1]["player"] == "Player B"
