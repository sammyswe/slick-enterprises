from slick_shared.cost import crossed_alert_boundary


def test_crosses_boundary():
    assert crossed_alert_boundary(19.0, 21.0, 20.0) is True


def test_does_not_cross():
    assert crossed_alert_boundary(5.0, 10.0, 20.0) is False


def test_exact_boundary():
    assert crossed_alert_boundary(0.0, 20.0, 20.0) is True


def test_zero_step_never_crosses():
    assert crossed_alert_boundary(0.0, 100.0, 0.0) is False
