The format of the library files is as follows:
```{
  version: 0,
  embedding_model: 'text-embedding-ada-002',
  content: {
    //A chunk_id is any string unique within this index to address your content. It could be a post's slug, a URL, or a monotonically-increasing integer formatted as a string.
    <chunk_id>: {
      text: <text>,
      embedding: <embedding>,
      token_count: <tokens_count>,
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

The file may be represented as either a Python pickle (with extension `.pkl`) or as JSON (with extension `.json`)