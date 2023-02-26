from argparse import ArgumentParser, Namespace

from overrides import override

from .base import BaseImporter, GetChunksResult

import json

"""
An importer that goes through your downloaded Twitter Archive.

[How to get your archive](https://help.twitter.com/en/managing-your-account/how-to-download-your-twitter-archive)

There is a JSON structure that contains your tweets, but it is wrapped 
in a JavaScript object: window.YTD.tweets.part0

So, for the hackiest of hacks, after you unzip you data, do the following:

- cp archivedirectory/data/tweet.js archivedirectory/data/tweet.json
- take out the "window.YTD.tweets.part0 =" piece so it's just an array "[" on the first line.

## Usage

% python3 -m convert.main --importer twitter --twitter-include regular ~/Downloads/exports/twitter-archive/data/tweets.json

The command line has the following options:

- --twitter-include:
  . all: everything is going in (default)
  . regular: only put in tweets that are NOT retweets, nor replies
  . retweets: put in retweets
  . replies: put in replies
- --twitter-username:
  . if you don't put in your username, it will use "twitter" which still works!
- Pass in the path to the actual JSON file

## Future tasks

[] - handle the JS object automatically
[] - tie together your threads to get chunks across them
"""
class TwitterArchiveImporter(BaseImporter):

    def __init__(self):
        self._include = 'all'
        self._username = 'twitter'

    @override
    def install_arguments(self, parser: ArgumentParser):
        """
        An opportunity to install arguments on the parser.

        Arguments should be in a new group, start with a `--{importer_name}-`
        and have a default.

        Soon will implement the ability to import subsets of your tweets,
        e.g. don't import your retweets
        """
        twitter_group = parser.add_argument_group('twitter')
        twitter_group.add_argument('--twitter-include', help='If provided and the importer is twitter, which tweets to include',
                                  choices=['all', 'regular', 'retweets', 'replies'], default='all')
        twitter_group.add_argument('--twitter-username', help='If provided and the importer is twitter, which @username to put into the URL')

    @override
    def retrieve_arguments(self, args: Namespace):
        """
        An opportunity to retrieve arguments configured via install_arguments.
        """
        self._include = args.twitter_include
        self._username = args.twitter_username

    @override
    def output_base_filename(self, filename) -> str:
        return 'twitterarchive-' + self._include

    @override
    def get_chunks(self, filename) -> GetChunksResult:
        print(filename)

        with open(filename, "r") as json_file:
            tweets_json = json.load(json_file)

            for tweet in tweets_json:
                if "tweet" in tweet:
                    realTweet = tweet["tweet"]
                    text = realTweet["full_text"]

                    if text.startswith("RT"):
                        if self._include != 'retweets' and self._include != 'all':
                            print("Skipping this retweet as the option '" + self._include + "' was passed in to the CLI.")
                            continue

                    elif text.startswith("@"):
                        if self._include != 'replies' and self._include != 'all':
                            print("Skipping this reply as the option '" + self._include + "' was passed in to the CLI.")
                            continue

                    else:
                        if self._include != 'regular' and self._include != 'all':
                            print("Skipping this regular tweet as the option '" + self._include + "' was passed in to the CLI.")
                            continue

                    id = realTweet["id_str"] 
                    print(id + ": " + text)

                    info = {
                        'url': "https://twitter.com/" + self._username + "/status/" + id,
                        'description': text
                    }

                    yield {
                        "text": text,
                        "info": info
                    }
