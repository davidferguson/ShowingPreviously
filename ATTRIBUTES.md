# Showing JSON Attributes

Each showing entry in the database can have some JSON attributes. This is a JSON object with string keys and any values,
that add some extra information about that showing. All JSON attributes are optional, but it is best that if the cinema
exposes that information, they are used.

The following attributes are used:
- `language`: string, specifies the language of the showing
- `captioned`: string or bool, specifies if the film is captioned. If the language of the captioning is known, this is 
the string language (eg. `english`), and if not, this is simply `True`
- `subtitled`: string or bool, specifies if the film is subtitled. If the language of the subtitling is known, this is 
the string language (eg. `english`), and if not, this is simply `True`
- `senior`: specifies if this showing is for senior citizens only