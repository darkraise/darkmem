# T2.54 authoring batch 3

Protocol: read `.superpowers/sdd/T2.54-entailment-gold-labelling/authoring-protocol.md` first, then LABELLING.md in full.

Worktree: /root/repositories/darkmem/.worktrees/e2-lane-t

Output file: /tmp/claude-0/-root-repositories-darkmem/8be3da95-78a0-427b-a2ed-b0d158efc5b4/scratchpad/step4/batch3-output.json

Your assigned slots (ids are final; l2-fact slots carry premise + fact_key to copy byte-for-byte; "premise": null means hand-authored premise):

```json
[
  {
    "id": "eg-0142",
    "slot": 100,
    "slice": "value-swap",
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
    "id": "eg-0143",
    "slot": 101,
    "slice": "verbatim",
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
    "id": "eg-0144",
    "slot": 102,
    "slice": "overreach",
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
    "id": "eg-0145",
    "slot": 103,
    "slice": "value-swap",
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
    "id": "eg-0146",
    "slot": 104,
    "slice": "value-swap",
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
    "id": "eg-0147",
    "slot": 105,
    "slice": "weakening",
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
    "id": "eg-0148",
    "slot": 106,
    "slice": "unrelated",
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
    "id": "eg-0149",
    "slot": 107,
    "slice": "value-swap",
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
    "id": "eg-0150",
    "slot": 108,
    "slice": "direction",
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
    "id": "eg-0151",
    "slot": 109,
    "slice": "verbatim",
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
    "id": "eg-0152",
    "slot": 110,
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
    "id": "eg-0153",
    "slot": 111,
    "slice": "verbatim",
    "premise": "redis deployed on queue-01",
    "fact_key": {
      "triple_key": "dea1fc2d-868a-5755-baa3-dea5ae8c184d",
      "subject_name": "redis",
      "rel_type": "DEPLOYED_ON",
      "object_name": "queue-01",
      "project": "default"
    }
  },
  {
    "id": "eg-0154",
    "slot": 112,
    "slice": "value-swap",
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
    "id": "eg-0155",
    "slot": 113,
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
    "id": "eg-0156",
    "slot": 114,
    "slice": "unrelated",
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
    "id": "eg-0157",
    "slot": 115,
    "slice": "paraphrase",
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
    "id": "eg-0158",
    "slot": 116,
    "slice": "unrelated",
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
    "id": "eg-0159",
    "slot": 117,
    "slice": "overreach",
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
    "id": "eg-0160",
    "slot": 118,
    "slice": "unrelated",
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
    "id": "eg-0161",
    "slot": 119,
    "slice": "overreach",
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
    "id": "eg-0162",
    "slot": 120,
    "slice": "direction",
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
    "id": "eg-0163",
    "slot": 121,
    "slice": "direction",
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
    "id": "eg-0164",
    "slot": 122,
    "slice": "value-swap",
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
    "id": "eg-0165",
    "slot": 123,
    "slice": "overreach",
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
    "id": "eg-0166",
    "slot": 124,
    "slice": "unrelated",
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
    "id": "eg-0167",
    "slot": 125,
    "slice": "verbatim",
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
    "id": "eg-0168",
    "slot": 126,
    "slice": "verbatim",
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
    "id": "eg-0169",
    "slot": 127,
    "slice": "weakening",
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
    "id": "eg-0170",
    "slot": 128,
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
    "id": "eg-0171",
    "slot": 129,
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
    "id": "eg-0172",
    "slot": 130,
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
    "id": "eg-0173",
    "slot": 131,
    "slice": "weakening",
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
    "id": "eg-0174",
    "slot": 132,
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
    "id": "eg-0175",
    "slot": 133,
    "slice": "value-swap",
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
    "id": "eg-0176",
    "slot": 134,
    "slice": "value-swap",
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
    "id": "eg-0177",
    "slot": 135,
    "slice": "direction",
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
    "id": "eg-0178",
    "slot": 136,
    "slice": "unrelated",
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
    "id": "eg-0179",
    "slot": 137,
    "slice": "direction",
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
    "id": "eg-0180",
    "slot": 138,
    "slice": "paraphrase",
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
    "id": "eg-0181",
    "slot": 139,
    "slice": "value-swap",
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
    "id": "eg-0182",
    "slot": 140,
    "slice": "overreach",
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
    "id": "eg-0183",
    "slot": 141,
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
    "id": "eg-0184",
    "slot": 142,
    "slice": "unrelated",
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
    "id": "eg-0185",
    "slot": 143,
    "slice": "verbatim",
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
    "id": "eg-0186",
    "slot": 144,
    "slice": "paraphrase",
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
    "id": "eg-0187",
    "slot": 145,
    "slice": "overreach",
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
    "id": "eg-0188",
    "slot": 146,
    "slice": "overreach",
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
    "id": "eg-0189",
    "slot": 147,
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
    "id": "eg-0190",
    "slot": 148,
    "slice": "paraphrase",
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
    "id": "eg-0191",
    "slot": 149,
    "slice": "unrelated",
    "premise": "nightly integration suite uses artifacts bucket",
    "fact_key": {
      "triple_key": "8a0cb86b-70de-555e-b834-80ef8a8a6323",
      "subject_name": "nightly integration suite",
      "rel_type": "USES",
      "object_name": "artifacts bucket",
      "project": "default"
    }
  }
]```
