from class_demo.user_app.stats.stats_gui import build_points_figure


def test_build_points_figure_contains_expected_axes_and_title():
    leaders = [
        {"player": "Player A", "team": "AAA", "points": 30.2},
        {"player": "Player B", "team": "BBB", "points": 27.4},
    ]

    fig = build_points_figure(leaders)

    assert fig.layout.title.text == "NBA Points Leaders"
    assert len(fig.data) >= 1
    assert fig.data[0].type == "bar"
