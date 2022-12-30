The format of the library files is as follows:
```
{
  version: 0,
  //Currently the only supported model is 'openai.com:text-embedding-ada-002'. That might change in the future.
  embedding_model: 'openai.com:text-embedding-ada-002',
  content: {
    //A chunk_id is any string unique within this index to address your content. It could be a post's slug, a URL, or a monotonically-increasing integer formatted as a string.
    <chunk_id>: {
      text: <text>,
      //The full vector of floats representing the embedding. The number of floats will depend on which embedding_model is in use.
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

The file may be represented as either a Python pickle (with extension `.pkl`) or as JSON (with extension `.json`). The json version is the default, since the files are easier to inspect and tweak by hand. However, the pkl format is still supported because they tend to be ~3x smaller in size than the equivalent json file.

The format of the API endpoint is currently:

```
{
  context: [ <text> ],
  chunks: [{
    url: <url>,
    image_url: <image_url>,
    title: <title>,
    description: <description>
  }]
}
```
