from class_demo.user_app.stats.stats_controller import StatsController


class _FakeStatsService:
    def __init__(self):
        self.calls = 0

    def get_player_points_leaders(self, top_n=10):
        self.calls += 1
        return [{"player": "A", "team": "AAA", "points": float(top_n)}]


def test_stats_controller_caches_by_top_n():
    service = _FakeStatsService()
    controller = StatsController(service)

    first = controller.get_points_leaders(10)
    second = controller.get_points_leaders(10)

    assert first == second
    assert service.calls == 1


def test_stats_controller_force_refresh_bypasses_cache():
    service = _FakeStatsService()
    controller = StatsController(service)

    controller.get_points_leaders(8)
    controller.get_points_leaders(8, force_refresh=True)

    assert service.calls == 2
