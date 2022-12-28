Some noodlings on the format. The current pickle format for embeddings for [wanderer](https://github.com/dglazkov/wanderer) is this:

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