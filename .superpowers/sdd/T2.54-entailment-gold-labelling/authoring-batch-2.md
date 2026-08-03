# T2.54 authoring batch 2

Protocol: read `.superpowers/sdd/T2.54-entailment-gold-labelling/authoring-protocol.md` first, then LABELLING.md in full.

Worktree: /root/repositories/darkmem/.worktrees/e2-lane-t

Output file: /tmp/claude-0/-root-repositories-darkmem/8be3da95-78a0-427b-a2ed-b0d158efc5b4/scratchpad/step4/batch2-output.json

Your assigned slots (ids are final; l2-fact slots carry premise + fact_key to copy byte-for-byte; "premise": null means hand-authored premise):

```json
[
  {
    "id": "eg-0092",
    "slot": 50,
    "slice": "verbatim",
    "premise": "prod-db-01 deployed on postgres",
    "fact_key": {
      "triple_key": "8f37265e-35d6-5fa1-8fd7-7e0c764d818c",
      "subject_name": "prod-db-01",
      "rel_type": "DEPLOYED_ON",
      "object_name": "postgres",
      "project": "default"
    }
  },
  {
    "id": "eg-0093",
    "slot": 51,
    "slice": "direction",
    "premise": "hv-27 has part scratch partition",
    "fact_key": {
      "triple_key": "31c1a0ee-0bcb-555a-ab9b-86cd7d898f40",
      "subject_name": "hv-27",
      "rel_type": "HAS_PART",
      "object_name": "scratch partition",
      "project": "default"
    }
  },
  {
    "id": "eg-0094",
    "slot": 52,
    "slice": "verbatim",
    "premise": "billing-sync deployed on apps-02",
    "fact_key": {
      "triple_key": "be4e96f1-635c-5f36-8489-106bfbb63d7c",
      "subject_name": "billing-sync",
      "rel_type": "DEPLOYED_ON",
      "object_name": "apps-02",
      "project": "default"
    }
  },
  {
    "id": "eg-0095",
    "slot": 53,
    "slice": "overreach",
    "premise": "nightly dump related to orders database",
    "fact_key": {
      "triple_key": "f6970044-019e-5aba-b03e-5d8af25af9cf",
      "subject_name": "nightly dump",
      "rel_type": "RELATED_TO",
      "object_name": "orders database",
      "project": "default"
    }
  },
  {
    "id": "eg-0096",
    "slot": 54,
    "slice": "paraphrase",
    "premise": "artifacts-prod deployed on minio",
    "fact_key": {
      "triple_key": "3ed12383-bb50-5361-bd65-d5a56a7e04b8",
      "subject_name": "artifacts-prod",
      "rel_type": "DEPLOYED_ON",
      "object_name": "minio",
      "project": "default"
    }
  },
  {
    "id": "eg-0097",
    "slot": 55,
    "slice": "verbatim",
    "premise": "postfix deployed on mail-01",
    "fact_key": {
      "triple_key": "60502a4d-76a9-5004-8d26-c94a05c4557b",
      "subject_name": "postfix",
      "rel_type": "DEPLOYED_ON",
      "object_name": "mail-01",
      "project": "default"
    }
  },
  {
    "id": "eg-0098",
    "slot": 56,
    "slice": "value-swap",
    "premise": "arc-store deployed on minio",
    "fact_key": {
      "triple_key": "8eeb62a2-ef08-5622-904f-9b31b246d742",
      "subject_name": "arc-store",
      "rel_type": "DEPLOYED_ON",
      "object_name": "minio",
      "project": "default"
    }
  },
  {
    "id": "eg-0099",
    "slot": 57,
    "slice": "direction",
    "premise": "customer-portal uses vault",
    "fact_key": {
      "triple_key": "4e7f472b-5da4-545b-8f41-b30558cf9ba0",
      "subject_name": "customer-portal",
      "rel_type": "USES",
      "object_name": "vault",
      "project": "default"
    }
  },
  {
    "id": "eg-0100",
    "slot": 58,
    "slice": "weakening",
    "premise": "astro replaces mkdocs",
    "fact_key": {
      "triple_key": "d08a8d38-04c1-5631-a8e5-f870fdba3f8e",
      "subject_name": "astro",
      "rel_type": "REPLACES",
      "object_name": "mkdocs",
      "project": "default"
    }
  },
  {
    "id": "eg-0101",
    "slot": 59,
    "slice": "weakening",
    "premise": "cleanup cron job causes scratch partition",
    "fact_key": {
      "triple_key": "12894a6a-ea4c-5811-91e6-5f21705c7917",
      "subject_name": "cleanup cron job",
      "rel_type": "CAUSES",
      "object_name": "scratch partition",
      "project": "default"
    }
  },
  {
    "id": "eg-0102",
    "slot": 60,
    "slice": "paraphrase",
    "premise": "ntfy related to sms",
    "fact_key": {
      "triple_key": "c2cff8f6-025e-5129-9b47-4d87a3ba9346",
      "subject_name": "ntfy",
      "rel_type": "RELATED_TO",
      "object_name": "sms",
      "project": "default"
    }
  },
  {
    "id": "eg-0103",
    "slot": 61,
    "slice": "weakening",
    "premise": "vault uses apps/portal",
    "fact_key": {
      "triple_key": "3a8ffbdb-90d8-59d2-b478-6e99319fe38d",
      "subject_name": "vault",
      "rel_type": "USES",
      "object_name": "apps/portal",
      "project": "default"
    }
  },
  {
    "id": "eg-0104",
    "slot": 62,
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
    "id": "eg-0105",
    "slot": 63,
    "slice": "overreach",
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
    "id": "eg-0106",
    "slot": 64,
    "slice": "weakening",
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
    "id": "eg-0107",
    "slot": 65,
    "slice": "paraphrase",
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
    "id": "eg-0108",
    "slot": 66,
    "slice": "unrelated",
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
    "id": "eg-0109",
    "slot": 67,
    "slice": "value-swap",
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
    "id": "eg-0110",
    "slot": 68,
    "slice": "direction",
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
    "id": "eg-0111",
    "slot": 69,
    "slice": "value-swap",
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
    "id": "eg-0112",
    "slot": 70,
    "slice": "paraphrase",
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
    "id": "eg-0113",
    "slot": 71,
    "slice": "unrelated",
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
    "id": "eg-0114",
    "slot": 72,
    "slice": "paraphrase",
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
    "id": "eg-0115",
    "slot": 73,
    "slice": "overreach",
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
    "id": "eg-0116",
    "slot": 74,
    "slice": "paraphrase",
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
    "id": "eg-0117",
    "slot": 75,
    "slice": "value-swap",
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
    "id": "eg-0118",
    "slot": 76,
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
    "id": "eg-0119",
    "slot": 77,
    "slice": "direction",
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
    "id": "eg-0120",
    "slot": 78,
    "slice": "value-swap",
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
    "id": "eg-0121",
    "slot": 79,
    "slice": "overreach",
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
    "id": "eg-0122",
    "slot": 80,
    "slice": "direction",
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
    "id": "eg-0123",
    "slot": 81,
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
    "id": "eg-0124",
    "slot": 82,
    "slice": "overreach",
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
    "id": "eg-0125",
    "slot": 83,
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
    "id": "eg-0126",
    "slot": 84,
    "slice": "unrelated",
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
    "id": "eg-0127",
    "slot": 85,
    "slice": "direction",
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
    "id": "eg-0128",
    "slot": 86,
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
    "id": "eg-0129",
    "slot": 87,
    "slice": "unrelated",
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
    "id": "eg-0130",
    "slot": 88,
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
    "id": "eg-0131",
    "slot": 89,
    "slice": "weakening",
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
    "id": "eg-0132",
    "slot": 90,
    "slice": "weakening",
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
    "id": "eg-0133",
    "slot": 91,
    "slice": "direction",
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
    "id": "eg-0134",
    "slot": 92,
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
    "id": "eg-0135",
    "slot": 93,
    "slice": "unrelated",
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
    "id": "eg-0136",
    "slot": 94,
    "slice": "unrelated",
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
    "id": "eg-0137",
    "slot": 95,
    "slice": "overreach",
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
    "id": "eg-0138",
    "slot": 96,
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
    "id": "eg-0139",
    "slot": 97,
    "slice": "weakening",
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
    "id": "eg-0140",
    "slot": 98,
    "slice": "paraphrase",
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
    "id": "eg-0141",
    "slot": 99,
    "slice": "direction",
    "premise": "status dashboard uses vite",
    "fact_key": {
      "triple_key": "1a01b5f5-2533-5737-a884-89a789b27b65",
      "subject_name": "status dashboard",
      "rel_type": "USES",
      "object_name": "vite",
      "project": "default"
    }
  }
]```
