job_schema = {
  "definitions": {},
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "http://example.com/root.json",
  "type": "object",
  "title": "Aves2 Job schema for PAI",
  "required": [
    "jobId",
    "username",
    "namespace",
    "engine",
    "image",
    "distributeType",
    "entryPoint",
    "envs",
    "codeSpec",
    "inputSpec",
    "outputSpec",
    "logDir",
    "resourceSpec",
    "storageMode"
  ],
  "properties": {
    "jobId": {
      "$id": "#/properties/jobId",
      "type": "string",
      "title": "The Jobid Schema",
      "description": "job id generated in pai system",
      "default": "",
      "examples": [
        "comp19680"
      ],
      "pattern": "^(.*)$"
    },
    "username": {
      "$id": "#/properties/username",
      "type": "string",
      "title": "The Username Schema",
      "default": "",
      "examples": [
        "pai"
      ],
      "pattern": "^(.*)$"
    },
    "namespace": {
      "$id": "#/properties/namespace",
      "type": "string",
      "title": "The Namespace Schema",
      "default": "",
      "examples": [
        "pai"
      ],
      "pattern": "^(.*)$"
    },
    "engine": {
      "$id": "#/properties/engine",
      "type": "string",
      "title": "The Engine Schema",
      "default": "",
      "examples": [
        "TensorFlow"
      ],
      "pattern": "^(.*)$"
    },
    "image": {
      "$id": "#/properties/image",
      "type": "string",
      "title": "The Image Schema",
      "default": "",
      "examples": [
        ""
      ],
      "pattern": "^(.*)$"
    },
    "distributeType": {
      "$id": "#/properties/distributeType",
      "type": "string",
      "title": "The Distributetype Schema",
      "default": "",
      "examples": [
        "", "HOROVOD", "TF-PS"
      ],
      "pattern": "^(.*)$"
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
    },
    "envs": {
      "$id": "#/properties/envs",
      "type": "object",
      "title": "The Envs Schema",
    },
    "codeSpec": {
      "$id": "#/properties/codeSpec",
      "type": "object",
      "title": "The Codespec Schema",
    },
    "inputSpec": {
      "$id": "#/properties/inputSpec",
      "type": "object",
      "title": "The Inputspec Schema",
    },
    "outputSpec": {
      "$id": "#/properties/outputSpec",
      "type": "object",
      "title": "The Outputspec Schema",
    },
    "logDir": {
      "$id": "#/properties/logDir",
      "type": "object",
      "title": "The Logdir Schema",
    },
    "resourceSpec": {
      "$id": "#/properties/resourceSpec",
      "type": "object",
      "title": "The Resourcespec Schema",
    },
    "storageMode": {
      "$id": "#/properties/storageMode",
      "type": "object",
      "title": "The Storagemode Schema",
      "required": [
        "mode",
        "config"
      ],
      "properties": {
        "mode": {
          "$id": "#/properties/storageMode/properties/mode",
          "type": "string",
          "title": "The Mode Schema",
          "default": "",
          "examples": [
            "OSSFile"
          ],
          "pattern": "^(.*)$"
        },
        "config": {
          "$id": "#/properties/storageMode/properties/config",
          "type": "object",
          "title": "The Config Schema",
          "required": [
            "S3Endpoint",
            "S3AccessKeyId",
            "S3SecretAccessKey"
          ],
          "properties": {
            "S3Endpoint": {
              "$id": "#/properties/storageMode/properties/config/properties/S3Endpoint",
              "type": "string",
              "title": "The S3endpoint Schema",
              "default": "",
              "examples": [
                "http://xxxx"
              ],
              "pattern": "^(.*)$"
            },
            "S3AccessKeyId": {
              "$id": "#/properties/storageMode/properties/config/properties/S3AccessKeyId",
              "type": "string",
              "title": "The S3accesskeyid Schema",
              "default": "",
              "examples": [
                ""
              ],
              "pattern": "^(.*)$"
            },
            "S3SecretAccessKey": {
              "$id": "#/properties/storageMode/properties/config/properties/S3SecretAccessKey",
              "type": "string",
              "title": "The S3secretaccesskey Schema",
              "default": "",
              "examples": [
                ""
              ],
              "pattern": "^(.*)$"
            }
          }
        }
      }
    }
  }
}
