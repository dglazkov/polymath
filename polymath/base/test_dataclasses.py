from dataclasses import field

import pytest

from polymath.base.dataclasses import config, empty


@config
class SimpleConfig:
    bar: str = 'simple'
    baz: int = 42
    items: list = empty(list)
    bag: dict = empty(dict)


def test_config():
    simple_args = {
        'bar': 'bar',
        'baz': 0,
        'items': [1, 2, 3],
        'bag': {'a': 1}
    }
    config = SimpleConfig(simple_args)
    assert config.bar == 'bar'
    assert config.baz == 0
    assert config.items == [1, 2, 3]
    assert config.bag == {'a': 1}

    no_args = {}
    config = SimpleConfig(no_args)
    assert config.bar == 'simple'
    assert config.baz == 42
    assert config.items == []
    assert config.bag == {}


@config(id='marked')
class MarkedConfig:
    bar: str = 'simple'


def test_config_id():
    config_type = MarkedConfig
    assert MarkedConfig.__id__ == 'marked'
    assert not hasattr(SimpleConfig, '__id__')


@config
class RequiredFieldConfig:
    bar: str
    baz: int = 42


def test_required_field_config():
    required_args = {'bar': 'bar'}
    foo = RequiredFieldConfig(required_args)
    assert foo.bar == 'bar'
    assert foo.baz == 42

    missing_args = {}
    with pytest.raises(TypeError):
        RequiredFieldConfig(missing_args)

    extra_args = {'bar': 'bar', 'baz': 42, 'qux': 'qux'}
    foo = RequiredFieldConfig(extra_args)
    assert foo.bar == 'bar'
    assert foo.baz == 42
    assert not hasattr(foo, 'qux')


@config
class NestedConfig:
    foo: RequiredFieldConfig
    roh: bool = False


@config
class OptionalNestedConfig:
    foo: SimpleConfig = None
    roh: bool = False


def test_nested_config():
    nested_args = {
        'foo': {
            'bar': 'bar',
            'baz': 0
        },
        'roh': True
    }
    qux = NestedConfig(nested_args)
    assert qux.foo.bar == 'bar'
    assert qux.foo.baz == 0
    assert qux.roh == True

    optional_nested_args = {}
    qux = OptionalNestedConfig(optional_nested_args)
    assert qux.foo == None
    assert qux.roh == False


@config
class OptionalDefaultsNestedConfig:
    foo: SimpleConfig = SimpleConfig
    roh: bool = False


@config
class OptionalDefaultsNestedConfig2:
    foo: SimpleConfig = SimpleConfig({'bar': 'woo', 'baz': 0})
    roh: bool = False


def test_optional_defaults_nested_config():
    optional_defaults_nested_args = {}
    qux = OptionalDefaultsNestedConfig(optional_defaults_nested_args)
    assert qux.foo.bar == 'simple'
    assert qux.foo.baz == 42
    assert qux.roh == False

    qux = OptionalDefaultsNestedConfig2(optional_defaults_nested_args)
    assert qux.foo.bar == 'woo'
    assert qux.foo.baz == 0
    assert qux.roh == False


@config
class MultipleDictsConfig:
    foo: dict = empty(dict)
    bar: dict = empty(dict)
    baz: dict = empty(dict)


def test_multiple_dicts():
    empty_args = {}
    config = MultipleDictsConfig(empty_args)
    assert config.foo == {}
    assert config.bar == {}
    assert config.baz == {}


@config
class DictsOfConfigsConfig:
    foo: dict[str, SimpleConfig] = empty(dict)
    bar: dict = empty(dict)


def test_dicts_of_configs():
    dicts_of_configs_args = {
        'foo': {
            'wdl': {'bar': 'one'},
            'flux': {}
        },
    }
    config = DictsOfConfigsConfig(dicts_of_configs_args)
    print(config)
    print(config.foo)
    assert config.foo['wdl'].bar == 'one'
    assert config.foo['flux'].bar == 'simple'
