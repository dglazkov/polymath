NOTE: Consider this document archived. Its contents are now maintained in the [polymath-ai/architecture](https://github.com/polymath-ai/architecture/blob/main/format.md) repository.

The format of the library files is as follows:

```
{
  version: 1,
  //Currently the only supported model is 'openai.com:text-embedding-ada-002'. That might change in the future.
  embedding_model: 'openai.com:text-embedding-ada-002',
  //Omit is optional. If provided, it is a string or array of strings that specify which keys in bits are expected to be missing. '' means nothing is supposed to be missing, and '*' means all bits are totally gone, that is content: {}.
  omit: 'embedding',
  //The type of the sort. May be omitted if type is 'any'. Legal values are 'any', 'similarity', 'manual', and 'random'.
  sort: 'random',
  //details is optional. It's typically only set for libraries generated from Library.query()
  details: {
    //Message is optional and will be displayed when
    message: "A message that will be displayed when Library() is called with this data"
    //Counts is optional. It can be retrieved or set by Library.counts.
    counts: {
      //bits is the number of bits that this file contains... even if they were all omitted with omit='*'. It can be retrieved or set with Library.count_bits
      bits: <int>,
      //restricted is how many bits would have been returned, but were filtered out because an access_token with permission to view them was not provided. By default hosts do not divulge this information, but if access.SECRET.json:restricted.count is true, it will be returned.
      restricted: <int>
    }
  }
  bits: [
    {
      text: <text>,
      // The full vector of floats representing the embedding, as base64-encoded string. The number of floats will depend on which embedding_model is in use.
      embedding: <embedding>,
      token_count: <tokens_count>,
      //Similarity is included in libraries that were given a query_embedding.
      similarity: <float>,
      //An optional field. If it is set, then this bit will only be returned from Library.query() if an access_token that grant
      //access to that tag is presented. These are typically not stored in files, but rather provided in the Library constructor.
      access_tag: <access_tag>,
      info: {
        url: <url>,
        //All of the following properties are optional
        image_url: <image_url>,
        title: <title>,
        description: <description>
      }
    },
    //...
  ]
}
```

The file is represented as JSON (with extension `.json`).

The host API endpoint returns a library.

The endpoint passes all of its arguments to Library.query() to return a new library. The arguments it accepts are:

- `version` - The version of library result that the client expects. This number must be greater than or equal to the host's current version.
- `query_embedding` - Optional. A base64 encoded embedding of the query. The returned chunks will be semantically similar to this. If one is not provided, a random embedding will be used, which will return a random but semantically similar set of results.
- `query_embedding_model` - The name of the embedding model in use. The embedding model provided must match the host's embedding model.
- `count` - An integer for how many bits of content to return. If `count_type` is `token` then it will return up to this many tokens total. If it is `bit` then it will return up to that many bits. If not provided, count will be set to a reasonable number.
- `count_type` - Optional. Whether `count` is of type `token` or `bit`
- `omit` - Optional. Fields to omit from the returned bits. e.g. 'embeddings,similarity'
- `access_token` - Optional. If provided then it will also include bits of content who have an `access_tag` that requires this access_token.
