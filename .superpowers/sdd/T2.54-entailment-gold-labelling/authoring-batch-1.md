# T2.54 authoring batch 1

Protocol: read `.superpowers/sdd/T2.54-entailment-gold-labelling/authoring-protocol.md` first, then LABELLING.md in full.

Worktree: /root/repositories/darkmem/.worktrees/e2-lane-t

Output file: /tmp/claude-0/-root-repositories-darkmem/8be3da95-78a0-427b-a2ed-b0d158efc5b4/scratchpad/step4/batch1-output.json

Your assigned slots (ids are final; l2-fact slots carry premise + fact_key to copy byte-for-byte; "premise": null means hand-authored premise):

```json
[
  {
    "id": "eg-0042",
    "slot": 0,
    "slice": "direction",
    "premise": "door-badge uses directory replica",
    "fact_key": {
      "triple_key": "6f06fed4-2f25-5d7e-a363-f24002c62128",
      "subject_name": "door-badge",
      "rel_type": "USES",
      "object_name": "directory replica",
      "project": "default"
    }
  },
  {
    "id": "eg-0043",
    "slot": 1,
    "slice": "paraphrase",
    "premise": "ocr worker deployed on gpu-01",
    "fact_key": {
      "triple_key": "420e13ba-2f7d-5b8d-bd57-5fb1834d0667",
      "subject_name": "ocr worker",
      "rel_type": "DEPLOYED_ON",
      "object_name": "gpu-01",
      "project": "default"
    }
  },
  {
    "id": "eg-0044",
    "slot": 2,
    "slice": "paraphrase",
    "premise": "acs-01 depends on ntp",
    "fact_key": {
      "triple_key": "cbb3f9de-ea07-5b45-8a09-214a2cb41319",
      "subject_name": "acs-01",
      "rel_type": "DEPENDS_ON",
      "object_name": "ntp",
      "project": "default"
    }
  },
  {
    "id": "eg-0045",
    "slot": 3,
    "slice": "verbatim",
    "premise": "analytics etl depends on orders database",
    "fact_key": {
      "triple_key": "e6b5497a-9611-5b9e-92bb-69a6a3fd41e3",
      "subject_name": "analytics etl",
      "rel_type": "DEPENDS_ON",
      "object_name": "orders database",
      "project": "default"
    }
  },
  {
    "id": "eg-0046",
    "slot": 4,
    "slice": "paraphrase",
    "premise": "nginx uses client certificates",
    "fact_key": {
      "triple_key": "e759f6f2-d05a-552e-bf7e-0e0cc4dbe640",
      "subject_name": "nginx",
      "rel_type": "USES",
      "object_name": "client certificates",
      "project": "default"
    }
  },
  {
    "id": "eg-0047",
    "slot": 5,
    "slice": "overreach",
    "premise": "team wiki deployed on lab-vm-3",
    "fact_key": {
      "triple_key": "b41579f0-3b76-5b77-b8d9-dd6267c51416",
      "subject_name": "team wiki",
      "rel_type": "DEPLOYED_ON",
      "object_name": "lab-vm-3",
      "project": "default"
    }
  },
  {
    "id": "eg-0048",
    "slot": 6,
    "slice": "value-swap",
    "premise": "wireguard deployed on udp",
    "fact_key": {
      "triple_key": "3822925d-685c-596b-adba-ee726a6bdf10",
      "subject_name": "wireguard",
      "rel_type": "DEPLOYED_ON",
      "object_name": "udp",
      "project": "default"
    }
  },
  {
    "id": "eg-0049",
    "slot": 7,
    "slice": "overreach",
    "premise": "prometheus uses node exporters",
    "fact_key": {
      "triple_key": "3d8b8266-237f-5431-8f58-691ff67c4f73",
      "subject_name": "prometheus",
      "rel_type": "USES",
      "object_name": "node exporters",
      "project": "default"
    }
  },
  {
    "id": "eg-0050",
    "slot": 8,
    "slice": "unrelated",
    "premise": "terraform uses tf-state",
    "fact_key": {
      "triple_key": "2b8fd40f-418b-5234-9981-030377289c8e",
      "subject_name": "terraform",
      "rel_type": "USES",
      "object_name": "tf-state",
      "project": "default"
    }
  },
  {
    "id": "eg-0051",
    "slot": 9,
    "slice": "verbatim",
    "premise": "license-report depends on internal package mirror",
    "fact_key": {
      "triple_key": "6c47ab46-8bdd-5d7d-92d2-62fa1af14d2f",
      "subject_name": "license-report",
      "rel_type": "DEPENDS_ON",
      "object_name": "internal package mirror",
      "project": "default"
    }
  },
  {
    "id": "eg-0052",
    "slot": 10,
    "slice": "direction",
    "premise": "vector related to telegraf",
    "fact_key": {
      "triple_key": "11606722-ee98-5a68-a01f-3f2b5f1e49e7",
      "subject_name": "vector",
      "rel_type": "RELATED_TO",
      "object_name": "telegraf",
      "project": "default"
    }
  },
  {
    "id": "eg-0053",
    "slot": 11,
    "slice": "unrelated",
    "premise": "unleash uses oidc",
    "fact_key": {
      "triple_key": "cf0723ca-43de-5212-983c-2799f5c28902",
      "subject_name": "unleash",
      "rel_type": "USES",
      "object_name": "oidc",
      "project": "default"
    }
  },
  {
    "id": "eg-0054",
    "slot": 12,
    "slice": "verbatim",
    "premise": "nightly integration suite uses junit",
    "fact_key": {
      "triple_key": "32a364bc-cf4d-525c-9376-816541ebbeb5",
      "subject_name": "nightly integration suite",
      "rel_type": "USES",
      "object_name": "junit",
      "project": "default"
    }
  },
  {
    "id": "eg-0055",
    "slot": 13,
    "slice": "weakening",
    "premise": "kibana has part elk",
    "fact_key": {
      "triple_key": "0d272cc9-159e-5368-a6bb-9c7d33f4a9a4",
      "subject_name": "kibana",
      "rel_type": "HAS_PART",
      "object_name": "elk",
      "project": "default"
    }
  },
  {
    "id": "eg-0056",
    "slot": 14,
    "slice": "weakening",
    "premise": "terraform uses minio",
    "fact_key": {
      "triple_key": "519cf15a-5746-54cb-ba07-9055d074cdb4",
      "subject_name": "terraform",
      "rel_type": "USES",
      "object_name": "minio",
      "project": "default"
    }
  },
  {
    "id": "eg-0057",
    "slot": 15,
    "slice": "overreach",
    "premise": "redis deployed on cache-01",
    "fact_key": {
      "triple_key": "a02af11e-49a4-56de-aa61-b3f11d9bf66d",
      "subject_name": "redis",
      "rel_type": "DEPLOYED_ON",
      "object_name": "cache-01",
      "project": "default"
    }
  },
  {
    "id": "eg-0058",
    "slot": 16,
    "slice": "direction",
    "premise": "caddy improves on nginx",
    "fact_key": {
      "triple_key": "60a400b1-1d0c-58f3-ac90-f5e3c2831d44",
      "subject_name": "caddy",
      "rel_type": "IMPROVES_ON",
      "object_name": "nginx",
      "project": "default"
    }
  },
  {
    "id": "eg-0059",
    "slot": 17,
    "slice": "paraphrase",
    "premise": "rooftop weather station uses iot-gw-1",
    "fact_key": {
      "triple_key": "77567f40-e068-57b7-b8c3-14cae1b8b01e",
      "subject_name": "rooftop weather station",
      "rel_type": "USES",
      "object_name": "iot-gw-1",
      "project": "default"
    }
  },
  {
    "id": "eg-0060",
    "slot": 18,
    "slice": "paraphrase",
    "premise": "telegraf uses influxdb",
    "fact_key": {
      "triple_key": "b2cf933e-d858-53f4-a542-39c4abba5441",
      "subject_name": "telegraf",
      "rel_type": "USES",
      "object_name": "influxdb",
      "project": "default"
    }
  },
  {
    "id": "eg-0061",
    "slot": 19,
    "slice": "value-swap",
    "premise": "sftp-02 uses dns",
    "fact_key": {
      "triple_key": "7ff82019-0e6e-5ba1-a679-933ebecb9ac0",
      "subject_name": "sftp-02",
      "rel_type": "USES",
      "object_name": "dns",
      "project": "default"
    }
  },
  {
    "id": "eg-0062",
    "slot": 20,
    "slice": "direction",
    "premise": "apps-02 deployed on rack ups",
    "fact_key": {
      "triple_key": "66fd8c8e-86e1-51d2-98bd-0e4db22078e1",
      "subject_name": "apps-02",
      "rel_type": "DEPLOYED_ON",
      "object_name": "rack ups",
      "project": "default"
    }
  },
  {
    "id": "eg-0063",
    "slot": 21,
    "slice": "verbatim",
    "premise": "jenkins deployed on ci-01",
    "fact_key": {
      "triple_key": "1a1c7fc4-cd11-506a-8209-4a372ee02b5a",
      "subject_name": "jenkins",
      "rel_type": "DEPLOYED_ON",
      "object_name": "ci-01",
      "project": "default"
    }
  },
  {
    "id": "eg-0064",
    "slot": 22,
    "slice": "weakening",
    "premise": "restic uses wiki volume",
    "fact_key": {
      "triple_key": "e31a032d-dfbd-5123-9df0-420e8e07619b",
      "subject_name": "restic",
      "rel_type": "USES",
      "object_name": "wiki volume",
      "project": "default"
    }
  },
  {
    "id": "eg-0065",
    "slot": 23,
    "slice": "paraphrase",
    "premise": "mobile app uses edge-cdn-4",
    "fact_key": {
      "triple_key": "b7e6e07d-4135-5663-9acd-f3e4e1c12911",
      "subject_name": "mobile app",
      "rel_type": "USES",
      "object_name": "edge-cdn-4",
      "project": "default"
    }
  },
  {
    "id": "eg-0066",
    "slot": 24,
    "slice": "value-swap",
    "premise": "vault related to .env files",
    "fact_key": {
      "triple_key": "37a75f1f-b666-5ca3-9ae6-4cd8c8b8a2e5",
      "subject_name": "vault",
      "rel_type": "RELATED_TO",
      "object_name": ".env files",
      "project": "default"
    }
  },
  {
    "id": "eg-0067",
    "slot": 25,
    "slice": "weakening",
    "premise": "nightly integration suite uses artifacts bucket",
    "fact_key": {
      "triple_key": "8a0cb86b-70de-555e-b834-80ef8a8a6323",
      "subject_name": "nightly integration suite",
      "rel_type": "USES",
      "object_name": "artifacts bucket",
      "project": "default"
    }
  },
  {
    "id": "eg-0068",
    "slot": 26,
    "slice": "weakening",
    "premise": "typesense deployed on search-01",
    "fact_key": {
      "triple_key": "c84b1f53-c648-5e04-af0a-3289806947d4",
      "subject_name": "typesense",
      "rel_type": "DEPLOYED_ON",
      "object_name": "search-01",
      "project": "default"
    }
  },
  {
    "id": "eg-0069",
    "slot": 27,
    "slice": "overreach",
    "premise": "postgres deployed on stg-db-01",
    "fact_key": {
      "triple_key": "8b0af751-67c2-572d-adfc-db51d823ed3f",
      "subject_name": "postgres",
      "rel_type": "DEPLOYED_ON",
      "object_name": "stg-db-01",
      "project": "default"
    }
  },
  {
    "id": "eg-0070",
    "slot": 28,
    "slice": "verbatim",
    "premise": "github actions replaces jenkins",
    "fact_key": {
      "triple_key": "07025480-5ae2-5262-9214-97aa13ba990d",
      "subject_name": "github actions",
      "rel_type": "REPLACES",
      "object_name": "jenkins",
      "project": "default"
    }
  },
  {
    "id": "eg-0071",
    "slot": 29,
    "slice": "paraphrase",
    "premise": "internal package mirror uses client",
    "fact_key": {
      "triple_key": "0e91af7b-4b37-5ce2-afdd-0f6c1d0c751d",
      "subject_name": "internal package mirror",
      "rel_type": "USES",
      "object_name": "client",
      "project": "default"
    }
  },
  {
    "id": "eg-0072",
    "slot": 30,
    "slice": "paraphrase",
    "premise": "redis replaces memcached",
    "fact_key": {
      "triple_key": "76bdd776-8827-5d92-b736-1a2050a180fa",
      "subject_name": "redis",
      "rel_type": "REPLACES",
      "object_name": "memcached",
      "project": "default"
    }
  },
  {
    "id": "eg-0073",
    "slot": 31,
    "slice": "overreach",
    "premise": "expense uses ocr worker",
    "fact_key": {
      "triple_key": "af9706e3-0c61-5a4b-944a-29504a498035",
      "subject_name": "expense",
      "rel_type": "USES",
      "object_name": "ocr worker",
      "project": "default"
    }
  },
  {
    "id": "eg-0074",
    "slot": 32,
    "slice": "verbatim",
    "premise": "compactor uses loki",
    "fact_key": {
      "triple_key": "d3733844-d4ed-5316-84f2-c41bcef4401d",
      "subject_name": "compactor",
      "rel_type": "USES",
      "object_name": "loki",
      "project": "default"
    }
  },
  {
    "id": "eg-0075",
    "slot": 33,
    "slice": "direction",
    "premise": "ci runners uses docker-in-docker",
    "fact_key": {
      "triple_key": "f5074b56-a4c5-5004-bdf7-2c9470dce973",
      "subject_name": "ci runners",
      "rel_type": "USES",
      "object_name": "docker-in-docker",
      "project": "default"
    }
  },
  {
    "id": "eg-0076",
    "slot": 34,
    "slice": "weakening",
    "premise": "iot-gw-1 uses firmware check",
    "fact_key": {
      "triple_key": "49ae7c87-e610-5a39-b93b-7fcdf01bcedc",
      "subject_name": "iot-gw-1",
      "rel_type": "USES",
      "object_name": "firmware check",
      "project": "default"
    }
  },
  {
    "id": "eg-0077",
    "slot": 35,
    "slice": "verbatim",
    "premise": "thumbs queue deployed on queue-01",
    "fact_key": {
      "triple_key": "c51c06e3-a505-52c8-972d-d8abb6285c01",
      "subject_name": "thumbs queue",
      "rel_type": "DEPLOYED_ON",
      "object_name": "queue-01",
      "project": "default"
    }
  },
  {
    "id": "eg-0078",
    "slot": 36,
    "slice": "weakening",
    "premise": "apps/portal uses audit-log",
    "fact_key": {
      "triple_key": "a8abee19-e45b-5503-a90b-709107983352",
      "subject_name": "apps/portal",
      "rel_type": "USES",
      "object_name": "audit-log",
      "project": "default"
    }
  },
  {
    "id": "eg-0079",
    "slot": 37,
    "slice": "verbatim",
    "premise": "status dashboard uses vite",
    "fact_key": {
      "triple_key": "1a01b5f5-2533-5737-a884-89a789b27b65",
      "subject_name": "status dashboard",
      "rel_type": "USES",
      "object_name": "vite",
      "project": "default"
    }
  },
  {
    "id": "eg-0080",
    "slot": 38,
    "slice": "paraphrase",
    "premise": "glitchtip replaces sentry",
    "fact_key": {
      "triple_key": "9d16fe42-683a-5ffa-935e-c90096dfccdd",
      "subject_name": "glitchtip",
      "rel_type": "REPLACES",
      "object_name": "sentry",
      "project": "default"
    }
  },
  {
    "id": "eg-0081",
    "slot": 39,
    "slice": "overreach",
    "premise": "memcached deployed on cache-02",
    "fact_key": {
      "triple_key": "e5737d01-742c-5adf-acbc-d4694bbc849f",
      "subject_name": "memcached",
      "rel_type": "DEPLOYED_ON",
      "object_name": "cache-02",
      "project": "default"
    }
  },
  {
    "id": "eg-0082",
    "slot": 40,
    "slice": "direction",
    "premise": "grafana uses infra",
    "fact_key": {
      "triple_key": "505aabfc-86d4-548f-b9af-71c08d1ad7fb",
      "subject_name": "grafana",
      "rel_type": "USES",
      "object_name": "infra",
      "project": "default"
    }
  },
  {
    "id": "eg-0083",
    "slot": 41,
    "slice": "paraphrase",
    "premise": "config management agent causes lp-relay",
    "fact_key": {
      "triple_key": "ad6f7451-228c-5bfc-80c6-df1f9bb16702",
      "subject_name": "config management agent",
      "rel_type": "CAUSES",
      "object_name": "lp-relay",
      "project": "default"
    }
  },
  {
    "id": "eg-0084",
    "slot": 42,
    "slice": "paraphrase",
    "premise": "fleet-cfg related to booking schedule",
    "fact_key": {
      "triple_key": "702b3d82-86a3-5ce6-87af-1a869e21ad13",
      "subject_name": "fleet-cfg",
      "rel_type": "RELATED_TO",
      "object_name": "booking schedule",
      "project": "default"
    }
  },
  {
    "id": "eg-0085",
    "slot": 43,
    "slice": "verbatim",
    "premise": "restic uses nas",
    "fact_key": {
      "triple_key": "09ab4ffb-3316-56d5-baa9-58e750835481",
      "subject_name": "restic",
      "rel_type": "USES",
      "object_name": "nas",
      "project": "default"
    }
  },
  {
    "id": "eg-0086",
    "slot": 44,
    "slice": "weakening",
    "premise": "lp-relay uses office label printers",
    "fact_key": {
      "triple_key": "c03b1b8e-db87-5360-989d-07ee46a59ecc",
      "subject_name": "lp-relay",
      "rel_type": "USES",
      "object_name": "office label printers",
      "project": "default"
    }
  },
  {
    "id": "eg-0087",
    "slot": 45,
    "slice": "weakening",
    "premise": "grafana uses nginx",
    "fact_key": {
      "triple_key": "08cf924b-93e6-552d-a645-3064a950cba1",
      "subject_name": "grafana",
      "rel_type": "USES",
      "object_name": "nginx",
      "project": "default"
    }
  },
  {
    "id": "eg-0088",
    "slot": 46,
    "slice": "value-swap",
    "premise": "directory replica deployed on acs-01",
    "fact_key": {
      "triple_key": "0cb4c678-60b3-5302-a1d6-946382b61fe0",
      "subject_name": "directory replica",
      "rel_type": "DEPLOYED_ON",
      "object_name": "acs-01",
      "project": "default"
    }
  },
  {
    "id": "eg-0089",
    "slot": 47,
    "slice": "overreach",
    "premise": "monthly payroll export uses sftp-02",
    "fact_key": {
      "triple_key": "bcafb282-5cd6-5a77-9abd-5d578479b2f9",
      "subject_name": "monthly payroll export",
      "rel_type": "USES",
      "object_name": "sftp-02",
      "project": "default"
    }
  },
  {
    "id": "eg-0090",
    "slot": 48,
    "slice": "overreach",
    "premise": "search-01 is a typesense",
    "fact_key": {
      "triple_key": "04ebe769-fa68-5371-9467-f7a8c6aad887",
      "subject_name": "search-01",
      "rel_type": "IS_A",
      "object_name": "typesense",
      "project": "default"
    }
  },
  {
    "id": "eg-0091",
    "slot": 49,
    "slice": "direction",
    "premise": "redis deployed on queue-01",
    "fact_key": {
      "triple_key": "dea1fc2d-868a-5755-baa3-dea5ae8c184d",
      "subject_name": "redis",
      "rel_type": "DEPLOYED_ON",
      "object_name": "queue-01",
      "project": "default"
    }
  }
]```
