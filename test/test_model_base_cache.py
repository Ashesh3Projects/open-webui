import asyncio
from types import SimpleNamespace

import pytest


class MemoryRedis:
    def __init__(self):
        self.values = {}

    async def get(self, key):
        return self.values.get(key)

    async def set(self, key, value):
        self.values[key] = value


class ModelParams:
    def model_dump(self):
        return {}


class PublicModelOverride:
    id = 'gpt-6-astra'
    name = 'GPT-6 Astra'
    base_model_id = None
    is_active = True
    params = ModelParams()
    meta = None

    def model_dump(self):
        return {
            'id': self.id,
            'name': self.name,
            'base_model_id': self.base_model_id,
            'is_active': self.is_active,
            'user_id': 'admin-user',
            'params': {},
            'meta': {'hidden': False},
            'access_grants': [
                {
                    'principal_type': 'user',
                    'principal_id': '*',
                    'permission': 'read',
                }
            ],
        }


def model(model_id):
    return {
        'id': model_id,
        'name': model_id,
        'object': 'model',
        'owned_by': 'openai',
    }


def request_with_cache(redis=None):
    return SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                redis=redis,
                MODELS={'old': model('old')},
                BASE_MODELS=[model('old')],
            )
        )
    )


@pytest.fixture
def model_utils(monkeypatch, tmp_path):
    monkeypatch.setenv('DATA_DIR', str(tmp_path / 'data'))
    monkeypatch.setenv('STATIC_DIR', str(tmp_path / 'static'))
    monkeypatch.setenv('FRONTEND_BUILD_DIR', str(tmp_path / 'frontend'))
    monkeypatch.setenv(
        'WEBUI_SECRET_KEY',
        'test-only-secret-key-that-is-long-enough-for-pytest',
    )
    monkeypatch.setenv('ENABLE_DB_MIGRATIONS', 'False')

    from open_webui.utils import models

    return models


@pytest.mark.parametrize('use_redis', [False, True])
def test_fresh_base_discovery_updates_cached_picker_for_public_model(  # noqa: C901
    monkeypatch, model_utils, use_redis
):
    redis = MemoryRedis() if use_redis else None
    request = request_with_cache(redis)
    discovered = [model('old'), model('gpt-6-astra')]

    async def get_many(*keys):
        return {
            'openai.enable': True,
            'ollama.enable': False,
            'models.base_models_cache': True,
            'evaluation.arena.enable': False,
            'evaluation.arena.models': [],
            'models.default_metadata': {},
        }

    async def fetch_openai_models(request, user=None):
        return discovered

    async def get_function_models(request):
        return []

    async def get_saved_models():
        return [PublicModelOverride()]

    async def get_functions_by_ids(function_ids):
        return []

    async def get_function_valves_by_ids(function_ids):
        return {}

    async def get_groups(user_id, db=None):
        return []

    async def get_accessible_resource_ids(**kwargs):
        return {'gpt-6-astra'}

    monkeypatch.setattr(model_utils.Config, 'get_many', get_many)
    monkeypatch.setattr(model_utils, 'fetch_openai_models', fetch_openai_models)
    monkeypatch.setattr(model_utils, 'get_function_models', get_function_models)
    monkeypatch.setattr(model_utils, 'ENABLE_PLUGINS', False)
    monkeypatch.setattr(model_utils.Models, 'get_all_models', get_saved_models)
    monkeypatch.setattr(model_utils.Functions, 'get_functions_by_ids', get_functions_by_ids)
    monkeypatch.setattr(model_utils.Functions, 'get_function_valves_by_ids', get_function_valves_by_ids)
    monkeypatch.setattr(model_utils.Groups, 'get_groups_by_member_id', get_groups)
    monkeypatch.setattr(
        model_utils.AccessGrants,
        'get_accessible_resource_ids',
        get_accessible_resource_ids,
    )
    monkeypatch.setattr(model_utils, 'get_chat_variables_schema', lambda system: None)

    result = asyncio.run(model_utils.get_all_base_models(request))

    assert [item['id'] for item in result] == ['old', 'gpt-6-astra']
    assert [item['id'] for item in request.app.state.BASE_MODELS] == ['old', 'gpt-6-astra']
    if redis is not None:
        cached = model_utils.JSONCodec.loads(redis.values[model_utils.BASE_MODELS_CACHE_KEY])
        assert [item['id'] for item in cached] == ['old', 'gpt-6-astra']

    async def unexpected_provider_fetch(request, user=None):
        raise AssertionError('cached picker assembly fetched the provider again')

    monkeypatch.setattr(model_utils, 'fetch_openai_models', unexpected_provider_fetch)
    assembled = asyncio.run(
        model_utils.get_all_models(
            request,
            user=SimpleNamespace(id='normal-user', role='user'),
        )
    )
    visible = asyncio.run(
        model_utils.get_filtered_models(
            assembled,
            SimpleNamespace(id='normal-user', role='user'),
        )
    )

    assert [item['id'] for item in visible] == ['gpt-6-astra']
    assert visible[0]['info']['access_grants'] == [
        {
            'principal_type': 'user',
            'principal_id': '*',
            'permission': 'read',
        }
    ]


@pytest.mark.parametrize('use_redis', [False, True])
def test_empty_base_discovery_keeps_last_nonempty_catalog(monkeypatch, model_utils, use_redis):
    redis = MemoryRedis() if use_redis else None
    request = request_with_cache(redis)
    old_catalog = [model('old')]
    if redis is not None:
        redis.values[model_utils.BASE_MODELS_CACHE_KEY] = model_utils.JSONCodec.dumps(old_catalog)

    async def get_many(*keys):
        return {
            'openai.enable': True,
            'ollama.enable': False,
            'models.base_models_cache': True,
            'evaluation.arena.enable': False,
            'evaluation.arena.models': [],
            'models.default_metadata': {},
        }

    async def fetch_openai_models(request, user=None):
        return []

    async def get_function_models(request):
        return []

    monkeypatch.setattr(model_utils.Config, 'get_many', get_many)
    monkeypatch.setattr(model_utils, 'fetch_openai_models', fetch_openai_models)
    monkeypatch.setattr(model_utils, 'get_function_models', get_function_models)

    result = asyncio.run(model_utils.get_all_base_models(request))

    assert result == []
    assert request.app.state.BASE_MODELS == old_catalog
    if redis is not None:
        assert model_utils.JSONCodec.loads(redis.values[model_utils.BASE_MODELS_CACHE_KEY]) == old_catalog
