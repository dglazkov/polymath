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

To run it, ensure you have an environment variable set for `OPENAI_API_KEY`.

Alternatively, create a `.env` file with these contents:

```
OPENAI_API_KEY=<key goes here>
TRANSFORMERS_VERBOSITY=error
```

(The last line will suppress the `None of PyTorch, TensorFlow >= 2.0, or Flax have been found` warning you may get when running the code)

Any embeddings pkl files you have in `libraries/` will be used as the content. If none exist, it will use the `sample-import-content.pkl`.

Then run `python3 -m sample.main "How does building a platform differ from building a product?"`

## Creating a new pkl

To create a new pkl file for a source, first, create a json object like this:

```
{
  content: {
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
```

This format is effectively the library format but missing a version, embedding_model, and each chunk missing embedding and token_count.

Then run `python3 -m import.main <FILENAME>`. It will create a new file with the same name but a `.pkl` extension in the `libraries/` directory.

### Running the server

To start the host server, run `python3 -m host.server`. It will start a Flask app as a local server. Go to `http://127.0.0.1:8080/api/query` to see the API endpoint.

### Server/Client experiment

To experiment with client/server setup, you will need multiple terminal instances: one for each server and one the client.

In each server terminal instance, start the server:

`python3 -m host.server <path/to/pickle/containing/embeddings> <port_number>`

Now, run the client, specifying the query and servers that you just started. For example:

`python3 -m sample.client "tell me about miracles" --server 127.0.0.1:8080 --server 127.0.0.1:8090`

The output should be a completion on the combined context of both servers.

### Standing up a polymath endpoint

This project can be used to stand up your own polymath endpoint on Google App Engine.

1) Follow [these instrustions](https://cloud.google.com/appengine/docs/standard/python3/building-app/creating-gcp-project) to set up a Google App Engine (GAE) instance. If you already have a GAE instance elsewhere on your machine, don't forget to change the name of the project before running `gcloud app create`. You can change the name of the project by invoking `gcloud config set project <gae-project-name>` first.

2) Place the libraries you want to use in the `libraries/` directory. If you have multiple libraries in that directory but only want to serve one, you can add a line like `LIBRARY_FILENAME=libraries/my-substack-posts.pkl` to your `.env` file.

3) Run `gcloud app deploy` to deploy the app.


### Developing

It's recommended to use `virtualenv` to manage your python environment for this project.

If you don't have `virtualenv`, install it with `pip install virtualenv`.

After checking out the repo, create a virtualenv:

`virtualenv env`

Every time you open a new terminal, activate the environment with `source env/bin/activate`.

After checking out the repo and activating your environment install dependencies: `pip install -r requirements.txt`

Every time you add a new depenency, update the dependency list with `pip freeze > requirements.txt`
