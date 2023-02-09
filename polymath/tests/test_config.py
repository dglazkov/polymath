import pytest

from polymath.config.types import EnvironmentConfig

def test_environment_config():
    args = {
      'openai_api_key': 'test_key',
      'library_filename': 'test_library',
    }
    config = EnvironmentConfig(args)
    assert config.openai_api_key == 'test_key'
    assert config.library_filename == 'test_library'
