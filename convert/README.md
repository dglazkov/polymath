# polymath importers, exporters, and libraries

`polymath` is a utility that uses AI to intelligently answer free-form questions based on a particular library of content.

You will want to create libraries for your Polymath, and may want to
export them into a vector store such as `pinecone`.

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

```shell
python3 -m convert.main --importer twitter --twitter-include regular path/to/twitter-archive/data/tweets.json
```

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

### `RSS` : An import an RSS feed

This is a simple implementation of an RSS feed importer. Simply point it at your RSS feed and it will parse the content, title and link.

```shell
python3 -m convert.main --importer rss https://paul.kinlan.me/index.xml
```

Will result in a library created in the format of `rss-[origin]-[path (escaped)].json`.

### `markdown` : An import of a Markdown file

An importer that goes through a folder and looks for markdown files.

```shell
python -m convert.main --importer markdown --markdown-base-url https://paul.kinlan.me/ ../paul.kinlan.me/content/
```

Note: The `--markdown-base-url` combined with `slug` frontmatter is used to generate the URL for the markdown file.

### `OCR` : Import an image and run OCR on it

This is an experimental implementation of an OCR importer. Simply point it at an image and it will run OCR on it and create a library.

```shell
python3 -m convert.main --importer ocr fancyimage.png
```

### `wordpress` : An import of a WordPress exported archive

An importer that goes through your downloaded WordPress archive.

[How to get your archive](https://wordpress.com/support/export/)

#### Usage

```shell
python3 -m convert.main --importer wordpress ~/Downloads/exports/dionalmaer.WordPress.2023-01-14.xml
```

### `htmlscraper` : Import a web page based on the given URL

This importer will download the web page and import it

```shell
% python3 -m convert.main --importer htmlscraper https://almaer.com/dion/cv/
```

### `sitemap` : Import a sitemap and all the pages it links to

This importer will go through a sitemap and import all the pages it links to.

```shell
python3 -m convert.main --importer sitemap https://paul.kinlan.me/sitemap.xml
```

Note: This importer subclasses the `HTMLScraperImporter`.

### `knowledge` : Import some arbitary knowledge for your Polymath

Sometimes you have the knowledge and you want to simply tell your Polymath

```shell
% python3 -m convert.main --importer knowledge info.txt
```

The format of the knowledge is some key/value metadata (optional) and then the chunk of information. E.g.

```
url: https://hydrogen.shopify.dev
title: Hydrogen uses Remix!
description: Hydrogen uses Remix for the best online store development

Question: What is the best way to build an online store with Remix?

Answer: We recommend Hydrogen, Shopify's solution that uses the Remix you love at it's core, and then gives you all of the commerce helpers you need.
----------
url: https://remix.run/blog/remixing-react-router

Question: How is Remix related to React Router?

Answer: They are from the same team and they work great together!
```

## Exporting content

WARNING: This section is basically unbaked cookies.

To export a library to [pinecone](https://www.pinecone.io/), follow these steps:

Put `PINECONE_API_KEY=<key>` entry into your `.env` file.

Collect the following information:

* `index_name` -- name of the Pinecone index to use
* `path/to/library` -- path to the library to export to Pinecone
* `namespace_name` -- namespace in the Pinecone index.

Run
```shell
python3 -m convert.out \
  --exporter pinecone \
  --library path/to/library \
  --index index_name \
  --namespace namespace_name
```