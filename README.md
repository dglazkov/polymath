# polymath

`polymath` is a utility that uses AI to intelligently answer free-form questions
based on a particular library of content.

Although you can ask just a single library questions, the real power of polymath
comes from being able to ask *multiple* federated libraries questions,
generating answers based on the combined intelligence of all of the authors.

Anyone can easily create a library of their own personal bits of content, based
on a Medium account, a Substack, your Twitter profile, or a generic import, and
it's easy to add new importer types.

### Before you begin

Polymath uses OpenAI under the covers, so you'll need a personal OpenAI key in
order to ask questions of any library.

You can get one easily by visiting https://beta.openai.com/account/api-keys and
logging in with your existing Google Account. Hit `Create new secret key`. Copy
the key (OpenAI will never show it to you again!) and put it somewhere safe.
Anyone who has this key can perform queries on your behalf and use your budget.

Every question you ask of polymath will cost you a cent or two. OpenAI accounts
come with a free $15 of credit to start.

### Asking your first question

Polymath libraries are hosted at public endpoints. You can visit the endpoint
directly to ask questions via a simple webapp, or use a command-line interface
to interact with a library.

Try visiting any of these endpoints and giving them a spin:
- https://polymath.komoroske.com
- https://polymath.glazkov.com
- https://polymath.fluxcollective.org

On each of these webapps, you'll first need to paste in your OpenAI API key. The
webapp stores the key locally in your browser for that site, and never transmits
it directly to anywhere but OpenAI.com itself.

### How it works

OpenAI's completion API is trained on a massive corpus of public content, making
it have good general intelligence. However, it typically knows nothing about
your *specific* content. It's possible to fine-tune these models with your
specific content, but that's expensive and unnecessary. The completion APIs tha
generate free-form answers have only a small window (no more than a few pages of
text) of "working memory". The trick is that when you ask a question, you also
select the most relevant bits of content from your library and include those
directly in the prompt, so the completion API has high-quality context to base
its answer on.

When the content is imported, its *embedding* is calculated by applying a
particular embedding model. An embedding is a list of decimal numbers that
encodes the fuzzy semantics of that block of content. Think of it like a
semantic "fingerprint" of your content. The embeddings don't mean much on their
own--they're just a list of obscure numbers. The magic happens when you
calculate the embedding of multiple bits of content with the same embedding
model. Bits of content that are semantically similar will have embeddings that
are close to each other.

Each polymath library hosts a collection of 'bits' of content. Each bit of
content is a couple of paragraphs of text. When it is imported its embedding is
calculated and saved so it doesn't have to be recalculated (each embedding costs
a few fractions of a cent to compute). Each library endpoint provides an API for
selecting bits of content based on a query.

When the query is created, first, its embedding is calculated. Then, the library
is asked to return bits of content that are most similar to that query (whose
embeddings have the smallest dot product compared to the query). The most
similar bits of content are selected and injected into the prompt, and the
completion API generates a high-quality answer based on the selected context.
The asker of the query pays a cent or two to OpenAI for every question they ask;
the library host pays only a small fee at import and then the cost of hosting a
Google App Engine instance.

### Querying multiple endpoints

The real power of polymath is from mixing multiple people's perspectives into one answer.

The webapp is a convenient GUI to query a library directly, but if you want to
mix across multiple libraries you currently have to use a CLI tool.

First, clone this repo.

Next, install virtualenv if you don't already have it, by running `pip3 install virtualenv`.

Next, create your virtualenv environment by running `virtualenv env` and then `source env/bin/activate`.

Next, make sure your OPENAI_API_KEY is set as an environment variable by adding

```
OPENAI_API_KEY=<key goes here>
```

to your `.bash_profile`, `.env` or similar.

Now you are ready to query multiple endpoints. Run:

`python3 -m sample.client --server https://polymath.komoroske.com --server https://polymath.glazkov.com "What are some of the benefits and drawbacks of a platform?"`

## Sample

`sample/` includes a sample question answerer.

You'll need to install the requirements. We recommend using `virtualenv` (see guidance below in this guide).

Then run `pip3 install -r requirements.txt` to load all of the requirements.

To run it, ensure you have an environment variable set for `OPENAI_API_KEY`.

Alternatively, create a `.env` file with these contents:

```
OPENAI_API_KEY=<key goes here>
```

Any library files you have in `libraries/` will be used as the content. If none exist, the sample will use `sample-content.json`.

Then run `python3 -m sample.main "How does building a platform differ from building a product?"`

You can run it with production libraries that others host with `python3 -m sample.client --server https://polymath.komoroske.com "What are best practices for managing platforms?"`

You can also use `--server` multiple times to use multiple end points.

A few public content servers you can try:
  - https://polymath.komoroske.com
  - https://polymath.glazkov.com
  - https://polymath.fluxcollective.org
  - https://polymath.almaer.com

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
  bits: [
    {
      text: '<raw text>',
      info: {
        url: '<URL>',
        //All of the following are optional
        image_url: '<IMAGE_URL>',
        title: '<TITLE>',
        description: '<DESCRIPTION>',
      }
    },
    //...
  ]
}
```

This format is effectively the library format but missing a version, embedding_model, and each bit missing embedding and token_count.

Then run `python3 -m convert.main --importer library <FILENAME>`. It will create a new file with the same name but a `.json` extension in the `libraries/` directory.

### `medium` : An import of a medium snapshot

First, generate a snapshot of your medium account by going to `https://medium.com/me/settings/security` and choosing `Download your information`. This will generate a snapshot and email you a link when it's ready.

When you have the snapshot, download it and unzip it. Then run:

`python3 -m convert.main --importer medium path/to/medium/root/`

Drafts will be excluded by default. If you want to include them, add `--medium-include-drafts` to the command.

### `substack` : An import of a substack snapshot

First, generate a snapshot of your substack account by going to the Exports part of your substack settings and choosing `Create new export`.

Download and unzip your snapshot. 
In the root of the snapshot, create a `config.json` file, formatted as:
```
{
        "substack_url": <url of the Substack site>,
        "exclude": [
            Optional, list of strings to exclude from the import. 
            Each string is a substring of the text to exclude from the import.
        ]
    }

```

Then run:

`python3 -m convert.main --importer substack path/to/substack/root/`

### `twitter` : An import of a Twitter archive

[How to get your archive](https://help.twitter.com/en/managing-your-account/how-to-download-your-twitter-archive)

There is a JSON structure that contains your tweets, but it is wrapped 
in a JavaScript object: window.YTD.tweets.part0

So, for the hackiest of hacks, after you unzip you data, do the following:

- cp archivedirectory/data/tweet.js archivedirectory/data/tweet.json
- take out the "window.YTD.tweets.part0 =" piece so it's just an array "[" on the first line.

#### Usage

% python3 -m convert.main --importer twitter --twitter-include regular path/to/twitter-archive/data/tweets.json


First, generate a snapshot of your Twitter account by following `https://help.twitter.com/en/managing-your-account/how-to-download-your-twitter-archive`. This will result in an email and notification in your Twitter client with a link to the archive.

When you have the snapshot, download it and unzip it. Then run:

`python3 -m convert.main --importer twitter --twitter-include regular --twitter-include $your_twitter_username path/to/twitter-archive/data/tweets.json`

You can choose if you want all tweets to be used, retweets, replies, or all but those types via `--twitter-include [all, regular, retweets, replies]`.

To see how many of the different type of tweets you have, there is a helper tool that you run:

`python3 twitter-scanner.py path/to/twitter-archive/data/tweets.json`

### `googledocs` : An import of a Google Document

This is a barebone import of one doc as a library. Great for large docs, such as books or journals.

Follow Google Cloud [instructions](https://developers.google.com/docs/api/quickstart/python#set_up_your_environment) to enable the Google Docs API and authorize credentials.

The instructions above omit the process of creating a consent screen, where you will need to enter the following information:

> Name: `Polymath Document Export` (or anything you would like)

> Email: `<your email>`

> Developer Contact Information: `<your email>`

Save the downloaded file as `credentials.SECRET.json` in the root of the repository.

Find the id of the document in its URL. It will be a long sequence of characters, separated by slashes:

`https://docs.google.com/document/d/<document_id>/edit`

Then run:

```shell
python3 -m convert.main --importer googledocs <document_id>
```

### RSS: import an RSS feed

This is a simple implementation of an RSS feed importer. Simply point it at your RSS feed and it will parse the content, title and link.

```shell
python3 -m convert.main --importer rss https://paul.kinlan.me/index.xml
```

Will result in a library created in the format of `rss-[origin]-[path (escaped)].json`.

## Running the server

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

If you have a file named `directory.SECRET.json` in the root of your directory, it
will automatically be used for configuration.

The config file should be formatted like this:

```
{
  "hosts": {
    //The name of the server can be whatever you want it to be, it's just a distinctive shortname for your own use.
    "wdl": {
      "endpoint": "https://polymath.wdl.com",
      //Optional. If set, and `--dev` is passed, then it will use this endpoint instead.
      "dev_endpoint": "http://127.0.0.1:8080",
      //Optional. If provided, it will be passed as the access_token when querying this server. It should be an access_token this host has in their `access.SECRET.json`.
      "token": <access_token>
    }
  }
}
```

You can also use the convenience script to set any proeprties and work with this file, like so:

`python3 -m config.directory set wdl endpoint https://polymath.wdl.com`

### Standing up a polymath endpoint

This project can be used to stand up your own polymath endpoint on Google App Engine.

1) Follow [these instructions](https://cloud.google.com/appengine/docs/standard/python3/building-app/creating-gcp-project) to set up a Google App Engine (GAE) instance. If you already have a GAE instance elsewhere on your machine, don't forget to change the name of the project before running `gcloud app create`. You can change the name of the project by invoking `gcloud config set project <gae-project-name>` first.

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

`python3 -m config.directory set wdl token sk_seret_key_123`

(If they haven't also run 
`python3 -m config.directory set wdl endpoint https://polymath.wdl.com` then they should also)

Then they run their client like: `python3 -m sample.client "query"`.

You'll also want to generate a token for yourself too so you have access to your private libraries.

You might chose to have your own `directory.SECRET.json` that looks like this:

```
{
  "hosts": {
    "your_server_vanity_id": {
      "endpoint": "https://polymath.yourserver.com",
      //Including this will switch to the local endpoint and provide the same token if `--dev` is passed to sample.client
      "dev_endpoint": "http://127.0.0.1:8080",
      "token": "<token_you_generated>"
    }
  }
}
```


#### How it works in more detail

polymath supports this use case with `access_tag`s. Each bit of content in a library may have an `access_tag` set on it. (Bits default to having no `access_tag`.). `access_tag` can be any string, but is typically `unpublished`. `Library.query()` will only return bits of content that have a non-missing `access_tag` if an `access_token` is provided that grants access to items with that tag.

`access_token` is typically not actually stored directly in the library.json file, but instead added at load time. The easiest way to do that is to put your library in a subdirectory like this: `libraries/access/unpublished/library.json`. In that case, it will automatically have the `access_tag` of `unpublished` added to all content in that library file, and that will flow with the bits if they're merged in with libraries with public bits. You can use this mechanism to add any access_tag; any part of the filename that includes `access/foo/` will add an `access_tag` of `foo`.

The mapping of `asset_token` to `access_tag` they give access to is configured in the `host.SECRET.json` file that you should keep at the root of the repo. It has a format like:

```
{
  //This defaults to "unpublished" if not explicitly set, and may be omitted
  "default_private_access_tag": "unpublished",
  //An optional configuration
  "restricted": {
    //Optional. If provided and set to true, then Library.query() will return count_restricted in its result. This will reveal to any queriers that there are private results.
    "count": true,
    //Optional. If provided, then Library.query() will output a message field of this message if at least one bit was filtered out due to being access restricted. This reveals that there are private results. The message will be prepended with 'Restricted results were omitted. '
    "message": "Contact alex@komoroske.com for an access_token."
  },
  "twitter": {
    "handle": "dalmaer"
  },

  "webclient": {
    "headername": "Dion's",
    "placeholder": "What is the best side effect of using an AI assistant?"
    "fun_queries": [
      "What is the best side effect of using an AI assistant?",
      "Tell me a story about OrderedJSON",
      "What is an Ajaxian?",
      "What happened to webOS?"
    ],
    "source_prefixes": {
      "https://remix.run/": "Remix: ",
      "https://reactrouter.com/": "React Router: "
    }
  },

  "tokens": {
      //user_vanity_id can be any user-understable name, typically an email address like 'alex@komoroske.com'
      <user_vanity_id>: {
        //A cryptographically secure string that is treated as a secret. It should be given to the user so they can put it in their "token" field in their `directory.SECRET.json` associated with this endpoint.
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

## Developing

It's recommended to use `virtualenv` to manage your python environment for this project.

If you don't have `virtualenv`, install it with `pip3 install virtualenv`.

After checking out the repo, create a virtualenv:

`virtualenv env`

Every time you open a new terminal, activate the environment with `source env/bin/activate`.

After checking out the repo and activating your environment install dependencies: `pip3 install -r requirements.txt`

Every time you add a new dependency, update the dependency list with `pip3 freeze > requirements.txt`

### Optimizing Tailwind

When using new Tailwind classes, you will want to create an updated `output.css` file by running:

`npx tailwindcss -i templates/input.css -o static/output.css`

from the `host` directory.

## Commmunity

If you would ike to participate in development or host a polymath endpoint, consider joining the [Polymath Discord](https://discord.gg/8mbSq5vA). It's not much, but should give you a better sense of what's happening, like when formats are changing or new interesting capabilities are available. 
