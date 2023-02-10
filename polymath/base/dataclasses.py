
from dataclasses import dataclass, field, is_dataclass

import inspect


def empty(factory):
    return field(default_factory=factory)


def config(*args, **kwargs):
    def wrapper(cls):
        kwargs['kw_only'] = True
        cls = dataclass(cls, **kwargs)
        dataclass_init = cls.__init__

        def init(self, config_args=None):
            if config_args is None:
                dataclass_init(self)
                return
            config_kwargs = {}
            for name in cls.__annotations__.keys():
                field_type = cls.__annotations__.get(name, None)
                value = config_args.get(name, None)
                if is_dataclass(field_type) and isinstance(value, dict):
                    config_kwargs[name] = field_type(value)
                elif value is not None:
                    config_kwargs[name] = value
            dataclass_init(self, **config_kwargs)
        cls.__init__ = init
        return cls
    return wrapper(args[0]) if args else wrapper
