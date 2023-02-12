# Configuring Polymath

This directory contains the configuration system for Polymath. It's a little hand-rolled ditty that is designed to accommodate multiple types of stores and allow expressing configuration flexibly and reliably.

## Lay of the land

There are two key groups of files:

* Files that end with `*Config` are the configuration classes. They are effectively [dataclasses](https://docs.python.org/3/library/dataclasses.html) with some extra features. They are used to define the configuration schema.

* Files that end with `*ConfigStore` are the configuration stores. They are responsible for loading (and hopefully soon, saving) configuration data. They are specific to the kind of store, but not to any particular configuration class. There are currently three stores::
  * `FilestoreConfigStore`
  * `EnvConfigStore`
  * `JSONConfigStore`

## Configuration classes

When you need to change what is stored in the configuration, you probably need to muck with a configuration class. They are all stored in `polymath/config/types.py`. If you want to add a new configuration class, add it there.

Configuration classes are defined using the `@config` decorator and must follow the convention of ending with a `Config`.

The basic idea here is to define a class that has a bunch of fields.
Fields are typed for more sanity. For example:

```python
from polymath.base.dataclasses import config

@config
class InfoConfig:
    headername: str = ''
    placeholder: str = ''
```

To define default empty values for lists and dicts, use the special `empty` function:

```python
from polymath.base.dataclasses import config, empty

@config
class InfoConfig:
    headername: str = ''
    placeholder: str = ''
    fun_queries: FunQueriesType = empty(list)
    source_prefixes: SourcePrefixesType = empty(dict)
```

Configuration classes can be nested. For example, `InfoConfig` is nested inside `HostConfig`. The nifty `@config` decorator will ensure that the configuration store automatically creates the right instances and populates them.

```python
from polymath.base.dataclasses import config, empty

@config
class InfoConfig:
    headername: str = ''
    placeholder: str = ''
    fun_queries: FunQueriesType = empty(list)
    source_prefixes: SourcePrefixesType = empty(dict)


@config
class HostConfig:
    info: InfoConfig = InfoConfig()
    tokens: TokensConfigType = empty(dict)
    completions_options: CompletionsOptionsConfig = CompletionsOptionsConfig()
```

Configuration classes can contain dictionaries of other configuration classes. For example `hosts` property in `DirectoryConfig` is a dictionary of `EndpointConfig` instances:

```python

@config()
class DirectoryConfig:
    hosts: dict[str, EndpointConfig] = empty(dict)

```

Every top-level (not nested by some other `*Config` class) `*Config` class needs  an `id`. This `id` will be used to locate the config within the store by the `*ConfigStore`. For example, `DirectoryConfig` has an `id` of `directory`:

```python

@config(id='directory')
class DirectoryConfig:
    hosts: dict[str, EndpointConfig] = empty(dict)

```

When used with `JSONConfigStore`, this will result in the `JSONConfigStore` looking for a file named `directory.SECRET.json`. The `directory` part of the filename comes from the `id`.

## Configuration stores
You should not need to edit configuration stores, other than to fix bugs in them. There will be bugs.

## Using configuration system

Depending on where you'd like to request configuration from, pick the right store. For example, to load from a JSON file, use the `JSONConfigStore`:

```python
from polymath.config.json import JSONConfigStore
from polymath.config.types import HostConfig

host_config = JSONConfigStore().get(HostConfig)
```

The resulting `host_config` will be an instance of `HostConfig` with all the fields populated.

## Automatic documentation

The `*Config` classes come with automatically generated documentation that can be used for to create UI for editing configuration. There are two components to making this work.

First, document your `*Config` class using a well-established convention. I recommend using [Google-docstring](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html) style. For example:

```python

@config
class EnvironmentConfig:
    '''
    General environment configuration

    Used for configuring the environment in which this Polymath instance is running.

    Attributes:
        openai_api_key: The OpenAI API key to use
        library_filename: The filename of the Polymath library to use
    '''
    openai_api_key: str
    library_filename: str = None

```

Second, use the `polymath.config.dataclasses.create_doc` function to create the documentation. For example:

```python

from polymath.config.dataclasses import create_doc

doc = create_doc(EnvironmentConfig)

```

The doc will contain a `ConfigDoc` instance that has the following properties:

* `description`: The description of the configuration class (first line of the docstring)
* `attributes`: A list of `AttrDoc` instances, one for each attribute in the configuration class

The `AttrDoc` instances have the following properties:

* `name`: The name of the attribute (pulled from the class definition)
* `type`: The type of the attribute (pulled from the type annotation)
* `description`: The description of the attribute (pulled from the docstring)
* `doc`: If the attribute is a `*Config` class, this will be a `ConfigDoc` instance for that class.