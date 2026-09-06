import pytest

import sca.app as app_module


def test_main_configures_logging_and_runs_local_only(monkeypatch):
    calls = []

    class FakeApp:
        def run(self, **kwargs):
            calls.append(kwargs)

    class FakeTimer:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            pass

    monkeypatch.setattr(app_module, '_configure_logging', lambda: calls.append('logging'))
    monkeypatch.setattr(app_module, 'create_app', lambda: FakeApp())
    monkeypatch.setattr(app_module, 'Timer', FakeTimer)

    app_module.main()

    assert calls == [
        'logging',
        {'debug': False, 'use_reloader': False, 'host': '127.0.0.1', 'port': 5000},
    ]


def test_main_handles_logging_setup_failure(monkeypatch, capsys):
    monkeypatch.setattr(
        app_module,
        '_configure_logging',
        lambda: (_ for _ in ()).throw(OSError('log directory unavailable')),
    )

    with pytest.raises(SystemExit) as error:
        app_module.main()

    assert error.value.code == 1
    assert 'ERROR: log directory unavailable' in capsys.readouterr().out
