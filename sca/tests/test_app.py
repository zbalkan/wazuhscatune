import logging

import pytest

import sca.app as app_module


def test_sanitizing_formatter_preserves_named_logger():
    formatter = app_module.SanitizingFormatter('%(name)s:%(message)s')
    record = logging.LogRecord(
        name='sca.routes.upload',
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='\x1b[31mmessage\x1b[0m',
        args=(),
        exc_info=None,
    )

    assert formatter.format(record) == 'sca.routes.upload:message'
    assert record.name == 'sca.routes.upload'
    assert record.msg == '\x1b[31mmessage\x1b[0m'


def test_sanitizing_formatter_labels_root_logger():
    formatter = app_module.SanitizingFormatter('%(name)s:%(message)s')
    record = logging.LogRecord(
        name='root',
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='message',
        args=(),
        exc_info=None,
    )

    assert formatter.format(record) == 'wazuhscatune:message'
    assert record.name == 'root'


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

    monkeypatch.setattr(app_module, '_configure_logging',
                        lambda: calls.append('logging'))
    monkeypatch.setattr(app_module, 'create_app', lambda: FakeApp())
    monkeypatch.setattr(app_module, 'Timer', FakeTimer)

    app_module.main()

    assert calls[0] == 'logging'
    assert calls[1] == {
        'debug': False,
        'use_reloader': False,
        'host': '127.0.0.1',
        'port': 5000,
    }


def test_main_handles_logging_setup_failure(monkeypatch, capsys):
    monkeypatch.setattr(
        app_module,
        '_configure_logging',
        lambda: (_ for _ in ()).throw(OSError('log directory unavailable')),
    )
    monkeypatch.setattr(app_module.os, '_exit',
                        lambda code: (_ for _ in ()).throw(SystemExit(code)))

    with pytest.raises(SystemExit) as error:
        app_module.main()

    assert error.value.code == 1
    assert 'ERROR: log directory unavailable' in capsys.readouterr().out
