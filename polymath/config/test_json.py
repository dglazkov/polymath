import os
from polymath.base.dataclasses import config, empty
from polymath.config.json import JSONConfigStore


@config(id='test')
class Config:
    bar: str = 'simple'
    baz: int = 42
    items: list = empty(list)
    bag: dict = empty(dict)


def test_save(tmp_path):
    config = Config()
    location = os.path.join(tmp_path, 'test.SECRET.json')
    assert not os.path.exists(location)
    JSONConfigStore(tmp_path).save(config)
    assert os.path.exists(location)
    with open(location) as f:
        assert f.read() == '{\n    "bar": "simple",\n    "baz": 42\n}'
