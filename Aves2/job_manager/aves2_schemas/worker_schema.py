worker_schema = {
  "definitions": {},
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "http://example.com/root.json",
  "type": "object",
  "title": "The Root Schema",
  "required": [
    "args",
    "memory",
    "port",
    "count",
    "cpu",
    "nvidia.com/gpu",
    "entryPoint"
  ],
  "properties": {
    "args": {
      "$id": "#/properties/args",
      "type": "array",
      "title": "The Args Schema"
    },
    "memory": {
      "$id": "#/properties/memory",
      "type": "string",
      "title": "The Memory Schema",
      "default": "",
      "examples": [
        "20Gi"
      ],
      "pattern": "^(.*)$"
    },
    "port": {
      "$id": "#/properties/port",
      "type": "integer",
      "title": "The Port Schema",
      "default": "",
      "examples": [
        ""
      ],
      "pattern": "^(.*)$"
    },
    "count": {
      "$id": "#/properties/count",
      "type": "integer",
      "title": "The Count Schema",
      "default": 1,
      "examples": [
        1
      ],
    },
    "cpu": {
      "$id": "#/properties/cpu",
      "type": "integer",
      "title": "The Cpu Schema",
      "default": 0,
      "examples": [
        10
      ]
    },
    "nvidia.com/gpu": {
      "$id": "#/properties/nvidia.com/gpu",
      "type": "integer",
      "title": "The Nvidia.com/gpu Schema",
      "default": 0,
      "examples": [
        1
      ]
    },
    "entryPoint": {
      "$id": "#/properties/entryPoint",
      "type": "string",
      "title": "The Entrypoint Schema",
      "default": "",
      "examples": [
        "bash run.sh"
      ],
      "pattern": "^(.*)$"
    }
  }
}
