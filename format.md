The format of the library files is as follows:
```
{
  version: 0,
  //Currently the only supported model is 'openai.com:text-embedding-ada-002'. That might change in the future.
  embedding_model: 'openai.com:text-embedding-ada-002',
  //Omit is optional. If provided, it is a string or array of strings that specify which keys in chunks are expected to be missing. '' means nothing is supposed to be missing, and '*' means all chunks are totally gone, that is content: {}.
  omit: 'embedding'
  content: {
    //A chunk_id is any string unique within this index to address your content. It could be a post's slug, a URL, or a monotonically-increasing integer formatted as a string.
    <chunk_id>: {
      text: <text>,
      // The full vector of floats representing the embedding, as base64-encoded string. The number of floats will depend on which embedding_model is in use.
      embedding: <embedding>,
      token_count: <tokens_count>,
      //Similarity is included in libraries that were given a query_embedding.
      similarity: <float>,
      //An optional field. If it is set, then this chunk will only be returned from Library.query() if an access_token that grant
      //access to that tag is presented. These are typically not stored in files, but rather provided in the Library constructor.
      access_tag: <access_tag>,
      info: {
        url: <url>,
        //All of the following properties are optional
        image_url: <image_url>,
        title: <title>,
        description: <description>
      }
    }
  }
}
```

The file is represented as JSON (with extension `.json`).

The host API endpoint returns a library.
