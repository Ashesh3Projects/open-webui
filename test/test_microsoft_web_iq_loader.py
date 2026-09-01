from langchain_core.documents import Document


def test_safe_microsoft_web_iq_loader_forwards_custom_api_base_url(monkeypatch, tmp_path):
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    monkeypatch.setenv('DATA_DIR', str(data_dir))
    monkeypatch.setenv('ENABLE_DB_MIGRATIONS', 'False')
    monkeypatch.setenv('VECTOR_DB', 'external')
    monkeypatch.setenv(
        'WEBUI_SECRET_KEY',
        'test-only-secret-key-that-is-long-enough-for-pytest',
    )

    from open_webui.retrieval.web import utils as web_utils

    captured_kwargs = {}

    class RecordingMicrosoftWebIQLoader:
        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)

        def lazy_load(self):
            yield Document(page_content='loaded', metadata={'source': 'https://example.com'})

    monkeypatch.setattr(web_utils, 'MicrosoftWebIQLoader', RecordingMicrosoftWebIQLoader)
    monkeypatch.setattr(
        web_utils.SafeMicrosoftWebIQLoader,
        '_safe_process_url_sync',
        lambda self, url: None,
    )

    loader = web_utils.SafeMicrosoftWebIQLoader(
        web_paths=['https://example.com'],
        api_key='test-key',
        api_base_url='https://web-iq.example.test/v4',
    )

    documents = list(loader.lazy_load())

    assert [document.page_content for document in documents] == ['loaded']
    assert captured_kwargs['api_base_url'] == 'https://web-iq.example.test/v4'
