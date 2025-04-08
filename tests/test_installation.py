import pyfreedts


def test_run_functions():
    """Test that the run functions exist."""
    assert callable(pyfreedts.run_dts), "run_dts is not callable"
    assert callable(pyfreedts.run_cnv), "run_cnv is not callable"
    assert callable(pyfreedts.run_gen), "run_gen is not callable"
