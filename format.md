Some noodlings on the format. The current pickle format for embeddings for [wanderer](https://github.com/dglazkov/wanderer) is this:

```{
  embeddings: [
    (
      <text>,
      <embedding>,
      <tokens>,
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
