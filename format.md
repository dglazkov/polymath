The format of the library files is as follows:
```{
  version: 0,
  embedding_model: 'text-embedding-ada-002',
  embeddings: [
    (
      <text>,
      <embedding>,
      <tokens_length>,
      <issue_id>
    )
  ],
  issue_info: {
    <issue_id>: (
      <url>
      <image_url>,
      <title>,
      <description>
    )
  }
}
```

The file may be represented as either a Python pickle (with extension `.pkl`) or as JSON (with extension `.json`)