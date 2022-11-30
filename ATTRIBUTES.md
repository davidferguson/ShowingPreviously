# Showing JSON Attributes

Each showing entry in the database can have some JSON attributes. This is a JSON object with string keys and any values,
that add some extra information about that showing. All JSON attributes are optional, but it is best that if the cinema
exposes that information, they are used.

The following attributes are used:
- `ad-trailer-free`: bool, specifies if this showing has no adverts or trailers beforehand
- `audio-described`: string or bool, specifies if the film can be viewed with an audio description (usually through an
additional device provided by the cinema). If the language of the audio description is known, this is the string 
language (eg. `english`), and if not, this is simply `True`
- `carers-and-babies`: bool, specifies if this showing is for babies and their carers only
- `captioned`: string or bool, specifies if the film is captioned. If the language of the captioning is known, this is
the string language (eg. `english`), and if not, this is simply `True`
- `format`: list of str, specifies the format(s) the film was projected in
- `dog-friendly`: bool, specifies if this showing is dog friendly
- `language`: string, specifies the language(s) of the showing
- `senior`: bool, specifies if this showing is for senior citizens only
- `subtitled`: string or bool, specifies if the film is subtitled. If the language of the subtitling is known, this is
the string language (eg. `english`), and if not, this is simply `True`
- `kids`: this film is for kids, and adults must be accompanying a child
