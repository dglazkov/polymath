
from dataclasses import asdict, dataclass, field, is_dataclass

import inspect
from typing import Any


def empty(factory):
    return field(default_factory=factory)


def is_a_dataclass_dict(type):
    is_a_dict_subclass = type is not dict and type.__subclasscheck__(dict)
    return is_a_dict_subclass and is_dataclass(type.__args__[1])


def omit_empties_factory(items):
    def is_empty(value):
        if isinstance(value, list):
            return len(value) == 0
        if isinstance(value, dict):
            return len(value) == 0
        return False

    items = [(k, v) for k, v in items if is_empty(v) is False]
    return dict(items)


def to_dict(self):
    result = asdict(self, dict_factory=omit_empties_factory)
    return result


def build_config_kwards(cls, config_args):
    config_kwargs = {}
    for name in cls.__annotations__.keys():
        field_type = cls.__annotations__.get(name)
        value = config_args.get(name)
        if is_a_dataclass_dict(field_type) and value is not None:
            dataclass_dict = {}
            dataclass_type = field_type.__args__[1]
            for key, sub_value in value.items():
                dataclass_dict[key] = dataclass_type(sub_value)
            config_kwargs[name] = dataclass_dict
        elif is_dataclass(field_type) and isinstance(value, dict):
            config_kwargs[name] = field_type(value)
        elif value is not None:
            config_kwargs[name] = value
    return config_kwargs


def is_config(type, value):
    return is_dataclass(type) and isinstance(value, dict)


def config(*args, **kwargs):
    def wrapper(cls):
        id = kwargs.get('id')
        if id:
            cls.__id__ = id
            kwargs.__delitem__('id')
        kwargs['kw_only'] = True
        cls = dataclass(cls, **kwargs)
        dataclass_init = cls.__init__

        def init(self, config_args=None):
            if config_args is None:
                dataclass_init(self)
            else:
                dataclass_init(self,
                               **build_config_kwards(cls, config_args))
        setattr(cls, 'to_dict', to_dict)
        cls.__init__ = init
        return cls
    return wrapper(args[0]) if args else wrapper
