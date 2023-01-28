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
  //If provided, will be used as the seed to sort.random to yield a deterministic order. May be omitted.
  seed: 'abc',
  //Sorts are descending by default. If true, will reverse the sort. May be omitted if 'false'
  reversed: true
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
