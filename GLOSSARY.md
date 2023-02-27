# The Polymath Glossary

There is a lot of terminology around a project, so here we have a simple
place to define some of the parts of Polymath:

- A `client` is an object that is able to ask one or more Polymath `endpoints` a question, hopefully getting back some useful `results`
- A `library` is the storage of knowledge in the [form of bits and metadata]('format.md')
- An `endpoint` is a Polymath host, something that is able to respond to questions, and has one or more libraries (it may even ask other endpoints for their results to aggregate with their own)
- `results` are the resulting bits of knowledge from a given client question
- A `query` is a string representing a question being asked
- A `queryEmbedding` is a vector embedding representing a question being asked
- A `bit` is a container for one URL/text pairing, including metadata and the embedding
- A `canonical id` for a bit is a hex digest SHA-256 hash of: url + "\n" + the text of the bit
