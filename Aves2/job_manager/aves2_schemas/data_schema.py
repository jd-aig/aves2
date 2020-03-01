data_schema = {
  "definitions": {},
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "http://example.com/root.json",
  "type": "object",
  "title": "The Root Schema",
  "required": [
    "type",
    "pvc",
    "path",
    "filename"
  ],
  "properties": {
    "type": {
      "$id": "#/properties/type",
      "type": "string",
      "title": "The Type Schema",
      "default": "",
      "examples": [
        "OSSFile", "K8SPVC"
      ],
      "pattern": "^(.*)$"
    },
    "pvc": {
      "$id": "#/properties/pvc",
      "type": "string",
      "title": "The Pvc Schema",
      "default": "",
      "examples": [
        ""
      ],
      "pattern": "^(.*)$"
    },
    "path": {
      "$id": "#/properties/path",
      "type": "string",
      "title": "The Path Schema",
      "default": "",
      "examples": [
        "s3://xxxxx"
      ],
      "pattern": "^(.*)$"
    },
    "filename": {
      "$id": "#/properties/filename",
      "type": "string",
      "title": "The Filename Schema",
      "default": "",
      "examples": [
        ""
      ],
      "pattern": "^(.*)$"
    }
  }
}
