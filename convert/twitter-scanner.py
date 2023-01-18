"""
## Usage

% python3 twitter-scanner.py ~/Downloads/twitter-archive/data/tweets.json

## Description

Load up a twitter archive JSON file and split out the number of various types of tweets:

[How to get your archive](https://help.twitter.com/en/managing-your-account/how-to-download-your-twitter-archive)

There is a JSON structure that contains your tweets, but it is wrapped 
in a JavaScript object: window.YTD.tweets.part0

So, for the hackiest of hacks, after you unzip you data, do the following:

- cp archivedirectory/data/tweet.js archivedirectory/data/tweet.json
- take out the "window.YTD.tweets.part0 =" piece so it's just an array "[" on the first line.
"""
import json
import sys

filename = sys.argv[1]

retweet_counter = 0
reply_counter = 0
regular_counter = 0

try:
    with open(filename, "r") as json_file:
        tweets_json = json.load(json_file)

        for tweet in tweets_json:
            if "tweet" in tweet:
                realTweet = tweet["tweet"]
                text = realTweet["full_text"]

                if text.startswith("RT"):
                        retweet_counter += 1
                        continue

                if text.startswith("@"):
                        reply_counter += 1
                        continue

                regular_counter += 1
        
        print(f"Regular tweets: {regular_counter}")
        print(f"Retweets: {retweet_counter}")
        print(f"Replies: {reply_counter}")
        print("----------------------")
        print(f"TOTAL: {regular_counter + retweet_counter + reply_counter}")
except FileNotFoundError:
    print(f"Error: {filename} not found.")
except Exception as e:
    print(f"Error: {filename} cannot be opened. {e}")
