# T2.54 authoring batch 4

Protocol: read `.superpowers/sdd/T2.54-entailment-gold-labelling/authoring-protocol.md` first, then LABELLING.md in full.

Worktree: /root/repositories/darkmem/.worktrees/e2-lane-t

Output file: /tmp/claude-0/-root-repositories-darkmem/8be3da95-78a0-427b-a2ed-b0d158efc5b4/scratchpad/step4/batch4-output.json

Your assigned slots (ids are final; l2-fact slots carry premise + fact_key to copy byte-for-byte; "premise": null means hand-authored premise):

```json
[
  {
    "id": "eg-0192",
    "slot": 150,
    "slice": "paraphrase",
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
    "id": "eg-0193",
    "slot": 151,
    "slice": "value-swap",
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
    "id": "eg-0194",
    "slot": 152,
    "slice": "direction",
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
    "id": "eg-0195",
    "slot": 153,
    "slice": "overreach",
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
    "id": "eg-0196",
    "slot": 154,
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
    "id": "eg-0197",
    "slot": 155,
    "slice": "weakening",
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
    "id": "eg-0198",
    "slot": 156,
    "slice": "overreach",
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
    "id": "eg-0199",
    "slot": 157,
    "slice": "verbatim",
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
    "id": "eg-0200",
    "slot": 158,
    "slice": "paraphrase",
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
    "id": "eg-0201",
    "slot": 159,
    "slice": "value-swap",
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
    "id": "eg-0202",
    "slot": 160,
    "slice": "value-swap",
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
    "id": "eg-0203",
    "slot": 161,
    "slice": "paraphrase",
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
    "id": "eg-0204",
    "slot": 162,
    "slice": "weakening",
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
    "id": "eg-0205",
    "slot": 163,
    "slice": "unrelated",
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
    "id": "eg-0206",
    "slot": 164,
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
    "id": "eg-0207",
    "slot": 165,
    "slice": "unrelated",
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
    "id": "eg-0208",
    "slot": 166,
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
    "id": "eg-0209",
    "slot": 167,
    "slice": "overreach",
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
    "id": "eg-0210",
    "slot": 168,
    "slice": "overreach",
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
    "id": "eg-0211",
    "slot": 169,
    "slice": "unrelated",
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
    "id": "eg-0212",
    "slot": 170,
    "slice": "overreach",
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
    "id": "eg-0213",
    "slot": null,
    "slice": "temporal",
    "premise": null,
    "fact_key": null
  },
  {
    "id": "eg-0214",
    "slot": null,
    "slice": "temporal",
    "premise": null,
    "fact_key": null
  },
  {
    "id": "eg-0215",
    "slot": null,
    "slice": "temporal",
    "premise": null,
    "fact_key": null
  },
  {
    "id": "eg-0216",
    "slot": null,
    "slice": "temporal",
    "premise": null,
    "fact_key": null
  },
  {
    "id": "eg-0217",
    "slot": null,
    "slice": "temporal",
    "premise": null,
    "fact_key": null
  },
  {
    "id": "eg-0218",
    "slot": null,
    "slice": "temporal",
    "premise": null,
    "fact_key": null
  },
  {
    "id": "eg-0219",
    "slot": null,
    "slice": "temporal",
    "premise": null,
    "fact_key": null
  },
  {
    "id": "eg-0220",
    "slot": null,
    "slice": "temporal",
    "premise": null,
    "fact_key": null
  },
  {
    "id": "eg-0221",
    "slot": null,
    "slice": "temporal",
    "premise": null,
    "fact_key": null
  },
  {
    "id": "eg-0222",
    "slot": null,
    "slice": "temporal",
    "premise": null,
    "fact_key": null
  },
  {
    "id": "eg-0223",
    "slot": null,
    "slice": "temporal",
    "premise": null,
    "fact_key": null
  },
  {
    "id": "eg-0224",
    "slot": null,
    "slice": "temporal",
    "premise": null,
    "fact_key": null
  },
  {
    "id": "eg-0225",
    "slot": null,
    "slice": "temporal",
    "premise": null,
    "fact_key": null
  },
  {
    "id": "eg-0226",
    "slot": null,
    "slice": "temporal",
    "premise": null,
    "fact_key": null
  },
  {
    "id": "eg-0227",
    "slot": null,
    "slice": "temporal",
    "premise": null,
    "fact_key": null
  },
  {
    "id": "eg-0228",
    "slot": null,
    "slice": "temporal",
    "premise": null,
    "fact_key": null
  },
  {
    "id": "eg-0229",
    "slot": null,
    "slice": "temporal",
    "premise": null,
    "fact_key": null
  },
  {
    "id": "eg-0230",
    "slot": null,
    "slice": "temporal",
    "premise": null,
    "fact_key": null
  },
  {
    "id": "eg-0231",
    "slot": null,
    "slice": "temporal",
    "premise": null,
    "fact_key": null
  },
  {
    "id": "eg-0232",
    "slot": null,
    "slice": "temporal",
    "premise": null,
    "fact_key": null
  },
  {
    "id": "eg-0233",
    "slot": null,
    "slice": "temporal",
    "premise": null,
    "fact_key": null
  },
  {
    "id": "eg-0234",
    "slot": null,
    "slice": "temporal",
    "premise": null,
    "fact_key": null
  },
  {
    "id": "eg-0235",
    "slot": null,
    "slice": "temporal",
    "premise": null,
    "fact_key": null
  },
  {
    "id": "eg-0236",
    "slot": null,
    "slice": "temporal",
    "premise": null,
    "fact_key": null
  },
  {
    "id": "eg-0237",
    "slot": null,
    "slice": "temporal",
    "premise": null,
    "fact_key": null
  },
  {
    "id": "eg-0238",
    "slot": null,
    "slice": "temporal",
    "premise": null,
    "fact_key": null
  },
  {
    "id": "eg-0239",
    "slot": null,
    "slice": "temporal",
    "premise": null,
    "fact_key": null
  },
  {
    "id": "eg-0240",
    "slot": null,
    "slice": "temporal",
    "premise": null,
    "fact_key": null
  },
  {
    "id": "eg-0241",
    "slot": null,
    "slice": "temporal",
    "premise": null,
    "fact_key": null
  }
]```
