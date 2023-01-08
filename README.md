# polymath

`polymath` is a utility that can answer free-form questions based on a corpus of federated content.

Each `polymath` instance defines a set of endpoints of federated content it
wants to be able to use, each with a short name e.g. 'Dimitri' or 'Alex'.

The federated endpoints contain pre-computed embeddings of chunks of content.

When `polymath` receives a question, it first computes an embedding for the
query. Then it hits each federated endpoint to select chunks of content most
relevant to the question. Then it injects as many chunks of content into a
prompt as will fit, appends the question, and uses the OpenAI completions API to
answer the question.

## Sample

`sample/` includes a sample question answerer.

You'll need to install the requirements. We recommend using `virtualenv` (see guidance below in this guide).

Then run `pip3 install -r requirements.txt` to load all of the requirements.

To run it, ensure you have an environment variable set for `OPENAI_API_KEY`.

Alternatively, create a `.env` file with these contents:

```
OPENAI_API_KEY=<key goes here>
TRANSFORMERS_VERBOSITY=error
```

(The last line will suppress the `None of PyTorch, TensorFlow >= 2.0, or Flax have been found` warning you may get when running the code)

Any library files you have in `libraries/` will be used as the content. If none exist, the sample will use `sample-content.json`.

Then run `python3 -m sample.main "How does building a platform differ from building a product?"`

You can run it with production libraries that others host with `python3 -m sample.client --server https://polymath.komoroske.com "What are best practices for managing platforms?"`

You can also use `--server` multiple times to use multiple end points.

A few public content servers you can try:
  - https://polymath.komoroske.com
  - https://polymath.glazkov.com
  - https://polymath.fluxcollective.org

If someone who runs a polymath server sent you a private token, see the section below on `Private Content` and its own getting started guide.

## Creating a new library

Libraries are files that are a `.json` and conform to the format defined in `format.md`.

You can create a library from many different input sources using the `python3 -m convert.main` script.

It comes with a number of different importers, specified with `--importer TYPE`

### `library`: A raw library

You can create a naked library (only containing some parts of the required object) to import

To create a new library file for a source, first, create a json object like this:

```
{
  content: {
    <chunk_id>: {
      text: '<raw text>',
      info: {
        url: '<URL>',
        //All of the following are optional
        image_url: '<IMAGE_URL>',
        title: '<TITLE>',
        description: '<DESCRIPTION>',
      }
    }
  }
}
```

This format is effectively the library format but missing a version, embedding_model, and each chunk missing embedding and token_count.

Then run `python3 -m convert.main --importer library <FILENAME>`. It will create a new file with the same name but a `.json` extension in the `libraries/` directory.

### `medium` : An import of a medium snapshot

First, generate a snapshot of your medium account by going to `https://medium.com/me/settings/security` and choosing `Download your information`. This will generate a snapshot and email you a link when it's ready.

When you have the snapshot, download it and unzip it. Then run:

`python3 -m convert.main --importer medium path/to/medium/root/`

Drafts will be excluded by default. If you want to include them, add `--medium-include-drafts` to the command.

### `substack` : An import of a substack snapshot

First, generate a snapshot of your substack account by going to the Exports part of your substack settings and choosing `Create new export`.

Download and unzip your snapshot. Then run:

`python3 -m convert.main --importer substack --substack-url=https://read.fluxcollective.org path/to/substack/root/`

Replacing the url with your base url.

### Running the server

To start the host server, run `python3 -m host.server`. It will start a Flask app as a local server. Go to `http://127.0.0.1:8080/api/query` to see the API endpoint.

It will automatically load up all libaries in `libraries/` and its subdirectories.

Sometimes it's nice to have libraries from other people in your development
server but don't want to upload those to production. To do that, create a
directory called `third_party` and put the third party libraries in it. During
development those libraries will be loaded up by the host by default, but they
will not be uploaded to the production instance because they are in
`.gcloudignore`.

### Server/Client experiment

To experiment with client/server setup, you will need multiple terminal instances: one for each server and one the client.

In each server terminal instance, start the server:

`LIBRARY_FILENAME=<path/to/library> python3 -m host.server --port <port_number>`

You can also omit the `LIBRARY_FILENAME`, and it will load all libraries in
`libraries/` and its subdirectories.

Now, run the client, specifying the query and servers that you just started. For example:

`python3 -m sample.client "tell me about miracles" --server 127.0.0.1:8080 --server 127.0.0.1:8090`

The output should be a completion on the combined context of both servers.

You can also specify client configuration in a config file like this: `--config client.SECRET.json`.

The config file should be formatted like this:

```
{
  "servers": {
    "wdl": {
      "endpoint": "https://polymath.wdl.com",
      //Optional. If provided, it will be passed as the access_token when querying this server. It should be an access_token this host has in their `access.SECRET.json`.
      "token": <access_token>
    }
  }
}
```

You might want to also create a `client.dev.SECRET.json` that includes the endpoints and tokens for your local setup, too, where your endpoints would be urls like `http://127.0.0.1:8080` and pass the tokens in use to protect unpublished library data.

### Standing up a polymath endpoint

This project can be used to stand up your own polymath endpoint on Google App Engine.

1) Follow [these instrustions](https://cloud.google.com/appengine/docs/standard/python3/building-app/creating-gcp-project) to set up a Google App Engine (GAE) instance. If you already have a GAE instance elsewhere on your machine, don't forget to change the name of the project before running `gcloud app create`. You can change the name of the project by invoking `gcloud config set project <gae-project-name>` first.

2) Place the libraries you want to use in the `libraries/` directory (anything in `libraries/third_party/` will not be uploaded to the production server). If you have multiple libraries in that directory but only want to serve one, you can add a line like `LIBRARY_FILENAME=libraries/my-substack-posts.json` to your `.env` file.

3) Run `gcloud app deploy` to deploy the app.

You can configure a subdomain of one of your domains to point to your polymath app engine instance. Follow [these instructions](https://cloud.google.com/appengine/docs/standard/mapping-custom-domains). If you manage the domain with Google Domains, a summary of steps:

1) Run `gcloud app domain-mappings create 'polymath.example.com' --certificate-management=AUTOMATIC`, replacing 'example.com' with your domain.

2) Go to `https://domains.google.com/registrar/example.com/dns` (replacing `example.com` with your domain) and click `Manage Custom Records`. Then click `Create new record`, choose type `CNAME`, host of `polymath`, and `data` of `ghs.googlehosted.com.` (or whatever the command above told you the data should be). Save your changes.

It might take a few minutes for your cert to be issued and DNS to update. Your automatically issued cert is ready when `gcloud app domain-mappings list` will show a number for SSL_CERTIFICATE_ID and no number for PENDING_AUTO_CERT.

### Private content

In many cases the content hosted in a library is published and viewable to anyone. But sometimes you have content that is unpublished (e.g. draft notes) but you still want some subset of clients to be able to query it.

#### Getting started quickly

Put the libraries you want everyone to have access to in the root of `libraries/`. Put libraries you only want people you have distributed tokens to into `libraries/access/unpublished`.

Run `python3 -m config.host access grant <email_address>` to generate a token. Copy/paste it and send it to that person in a secure channel. Note that you must redeploy to production with `gcloud app deploy`.

They then add their token to their `client.SECRET.config` like this:

```
{
  "servers": {
    "their_server_vanity_id": {
      "endpoint": "https://polymath.theirserver.com",
      "token": "<token_you_sent_them>"
    }
  }
}
```

Then they run their client like: `python3 -m sample.client --config client.SECRET.cong "query"`.

You'll also want to generate a token for yourself too so you have access to your private libraries.

You might chose to have your own `client.SECRET.json` that looks like this:

```
{
  "servers": {
    "your_server_vanity_id": {
      "endpoint": "https://polymath.yourserver.com",
      "token": "<token_you_generated>"
    }
  }
}
```

and a `client.dev.SECRET.json` that looks like this (for when you query your local development host)

```
{
  "servers": {
    "your_server_vanity_id": {
      "endpoint": "http://127.0.0.1:8080",
      "token": "<token_you_generated>"
    }
  }
}
```


#### How it works in more detail

polymath supports this use case with `access_tag`s. Each chunk of content in a library may have an `access_tag` set on it. (Chunks default to having no `access_tag`.). `access_tag` can be any string, but is typically `unpublished`. `Library.query()` will only return chunks of content that have a non-missing `access_tag` if an `access_token` is provided that grants access to items with that tag.

`access_token` is typically not actually stored directly in the library.json file, but instead added at load time. The easiest way to do that is to put your library in a subdirectory like this: `libraries/access/unpublished/library.json`. In that case, it will automatically have the `access_tag` of `unpublished` added to all content in that library file, and that will flow with the chunks if they're merged in with libraries with public chunks. You can use this mechanism to add any access_tag; any part of the filename that includes `access/foo/` will add an `access_tag` of `foo`.

The mapping of `asset_token` to `access_tag` they give access to is configured in the `host.SECRET.json` file that you should keep at the root of the repo. It has a format like:

```
{
  //This defaults to "unpublished" if not explicitly set, and may be omitted
  "default_private_access_tag": "unpublished",
  //An optional configuration
  "restricted": {
    //Optional. If provided and set to true, then Library.query() will return count_restricted in its result. This will reveal to any queriers that there are private results.
    "count": true,
    //Optional. If provided, then Library.query() will output a message field of this message if at least one chunk was filtered out due to being access restricted. This reveals that there are private results. A typical message might 
    "message": "Restricted results omitted. Contact alex@komoroske.com for an access_token."
  }
  "tokens": {
      //user_vanity_id can be any user-understable name, typically an email address like 'alex@komoroske.com'
      <user_vanity_id>: {
        //A cryptographically secure string that is treated as a secret. It should be given to the user so they can put it in their "token" field in their `client.SECRET.json` associated with this endpoint.
        "token": <access_token>,
        //An optional stirng where you can store notes about this user or record.
        "description": ""
        //The access_tags this token is allowed to access in this library. If it is omitted it defaults to `["unpublished"]`
        "access_tags": ["unpublished"]
    }
  }
}
```

Instead of generating keys yourself and modifying the file, you can use the following command:

`python3 -m config.host access grant <user_vanity_id>`

This will generate a new key, store it in `host.SECRET.json` and print it.

You can also revoke a key with `python3 -m config.host access revoke <user_vanity_id>`

### Developing

It's recommended to use `virtualenv` to manage your python environment for this project.

If you don't have `virtualenv`, install it with `pip install virtualenv`.

After checking out the repo, create a virtualenv:

`virtualenv env`

Every time you open a new terminal, activate the environment with `source env/bin/activate`.

After checking out the repo and activating your environment install dependencies: `pip install -r requirements.txt`

Every time you add a new depenency, update the dependency list with `pip freeze > requirements.txt`
