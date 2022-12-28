The format of the library files is as follows:
```{
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