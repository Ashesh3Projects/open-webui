import os
import subprocess
import sys
import tempfile


def _load_webui_name(webui_name=None):
    env = os.environ.copy()
    env['WEBUI_SECRET_KEY'] = 'test-only-secret-key-that-is-long-enough-for-pytest'
    if webui_name is None:
        env.pop('WEBUI_NAME', None)
    else:
        env['WEBUI_NAME'] = webui_name

    with tempfile.TemporaryDirectory() as data_dir:
        env['DATA_DIR'] = data_dir
        result = subprocess.run(
            [
                sys.executable,
                '-c',
                "from open_webui.env import WEBUI_NAME; print('WEBUI_NAME_RESULT=' + WEBUI_NAME)",
            ],
            check=True,
            capture_output=True,
            env=env,
            text=True,
        )
    return next(
        line.removeprefix('WEBUI_NAME_RESULT=')
        for line in result.stdout.splitlines()
        if line.startswith('WEBUI_NAME_RESULT=')
    )


def test_default_webui_name_is_chatgpt():
    assert _load_webui_name() == 'ChatGPT'


def test_explicit_webui_name_is_not_suffixed():
    assert _load_webui_name('My Workspace') == 'My Workspace'
