# type: ignore
# TODO: Reanble type checking for this file

from typing import Union
import pytest

from polymath.base.dataclasses import config, empty, omit_empties_factory, create_doc


def test_omit_empties_factory():
    items = [('bar', 'simple'), ('baz', 42), ('items', []), ('bag', {})]
    result = omit_empties_factory(items)
    assert result == {'bar': 'simple', 'baz': 42}

    items = [('bar', 'simple'), ('items', None), ('bag', {})]
    result = omit_empties_factory(items)
    assert result == {'bar': 'simple', 'items': None}


@config
class SimpleConfig:
    '''
    A Simple Config

    Attributes:
        bar: A simple string
        baz: A simple integer
        items: A simple list of items
        bag: A simple dictionary of items
    '''
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
    assert config.to_dict() == simple_args

    no_args = {}
    config = SimpleConfig(no_args)
    assert config.bar == 'simple'
    assert config.baz == 42
    assert config.items == []
    assert config.bag == {}
    assert config.to_dict() == {
        'bar': 'simple',
        'baz': 42,
    }


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
    assert qux.to_dict() == nested_args

    optional_nested_args = {}
    qux = OptionalNestedConfig(optional_nested_args)
    assert qux.foo == None
    assert qux.roh == False
    assert qux.to_dict() == {
        'foo': None,
        'roh': False
    }


@config
class OptionalDefaultsNestedConfig:
    foo: SimpleConfig = SimpleConfig()
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
    assert qux.to_dict() == {
        'foo': {
            'bar': 'simple',
            'baz': 42,
        },
        'roh': False
    }

    qux = OptionalDefaultsNestedConfig2(optional_defaults_nested_args)
    assert qux.foo.bar == 'woo'
    assert qux.foo.baz == 0
    assert qux.roh == False
    assert qux.to_dict() == {
        'foo': {
            'bar': 'woo',
            'baz': 0,
        },
        'roh': False
    }


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
    assert config.to_dict() == empty_args


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
    assert config.foo['wdl'].bar == 'one'
    assert config.foo['flux'].bar == 'simple'
    assert config.to_dict() == {
        'foo': {
            'flux': {
                'bar': 'simple',
                'baz': 42,
            },
            'wdl': {
                'bar': 'one',
                'baz': 42,
            }
        }
    }

    empty_args = {}
    config = DictsOfConfigsConfig(empty_args)
    assert config.foo == {}
    assert config.to_dict() == empty_args


@config
class DocumentedConfig:
    """This is a documented config.

    Stuff goes here.

    Attributes:
        bar: This is a documented attribute.
        baz: This is another documented attribute.
        simple: This is a documented SimpleConfig.
            It goes on for multiple lines.
    """
    bar: str = 'simple'
    baz: Union[int,str]
    simple: SimpleConfig = SimpleConfig()

def test_create_doc():
    config_doc = create_doc(DocumentedConfig)
    print(config_doc)
    assert config_doc.description == 'This is a documented config.'
    assert len(config_doc.attributes) == 3
    assert config_doc.attributes[0].description == 'This is a documented attribute.'
    assert config_doc.attributes[0].type == 'str'
    assert config_doc.attributes[1].description == 'This is another documented attribute.'
    assert config_doc.attributes[1].type == 'Union'
    assert config_doc.attributes[2].description == 'This is a documented SimpleConfig.\nIt goes on for multiple lines.'
    assert config_doc.attributes[2].type == 'SimpleConfig'
    assert config_doc.attributes[2].doc.description == 'A Simple Config'
    assert len(config_doc.attributes[2].doc.attributes) == 4
