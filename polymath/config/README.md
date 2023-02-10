# Configuring Polymath

This directory contains the configuration system for Polymath. It's a little hand-rolled ditty that is designed to accommodate multiple types of stores and allow expressing configuration flexibly and reliably.

## Lay of the land

There are three key groups of files:

* Files that end with `*Config` are the configuration classes. They are effectively [dataclasses](https://docs.python.org/3/library/dataclasses.html) with some extra features. They are used to define the configuration schema.

* Files that end with `*ConfigStore` are the configuration stores. They are responsible for loading (and hopefully soon, saving) configuration data. They are specific to the kind of store, but not to any particular configuration class. There are currently three stores):
  * `FilestoreConfigStore`
  * `EnvConfigStore`
  * `JSONConfigStore`
* Files that end with `*ConfigLoader` are the configuration loaders. They are responsible for loading configuration data from a specific configuration store into a specific configuration class. They are the link between `*Config` classes to `*ConfigStore` classes: a `*ConfigLoader` knows how to use a `*ConfigStore` to produce a `*Config`. There are currently three loaders:
  * `FilestoreConfigLoader`
  * `EnvConfigLoader`
  * `JSONConfigLoader`

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

Configuration classes can be nested. For example, `InfoConfig` is nested inside `HostConfig`. The nifty `@config` decorator will ensure that the configuration loader automatically creates the right instances and populates them.

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
    completions_options: PropertyBagConfigType = empty(dict)
```

## Configuration stores
You should not need to edit configuration stores, other than to fix bugs in them. There will be bugs.

## Configuration loaders
To load new kinds of configurations, add a new method to the respective loader. Look for other methods around, it should be fairly straightforward. For example, here's the `load_host_config` method for `FirestoreConfigLoader`:

```python
    def load_host_config(self, ref: firestore.DocumentReference = None) -> HostConfig:
        if ref is None:
            ref = self._client.document('sites/127')
        config = FirestoreConfigStore().load(ref)
        return HostConfig(config)

```

## Using configuration system

Depending on where you'd like to request configuration from, pick the right loader. For example, to load from a JSON file, use the `JSONConfigLoader`:

```python
from polymath.config.json import JSONConfigLoader

host_config = JSONConfigLoader().load_host_config()
```
The resulting `host_config` will be an instance of `HostConfig` with all the fields populated.