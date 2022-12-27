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

### Developing

It's recommended to use `virtualenv` to manage your python environment for this project.

If you don't have `virtualenv`, install it with `pip install virtualenv`.

After checking out the repo, create a virtualenv:

`virtualenv env`

Every time you open a new terminal, activate the environment with `source env/bin/activate`.

After checking out the repo and activating your environment install dependencies: `pip install -r requirements.txt`

Every time you add a new depenency, update the dependency list with `pip freeze > requirements.txt`
