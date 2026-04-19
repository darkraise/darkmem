---
library_name: sentence-transformers
pipeline_tag: sentence-similarity
base_model: BAAI/bge-base-en-v1.5
language:
- en
tags:
- sentence-similarity
- memory
- darkmem
- bge
- feature-extraction
---

# darkmem-retriever-v1

Contrastively fine-tuned bge-base encoder for darkmem semantic search. Query prefix: "Represent this sentence for searching relevant passages: ".

## Metrics

MRR@10 0.884 / R@1 0.872 / R@5 0.904 / R@10 0.910 on 500-pair test.

## Base model

[BAAI/bge-base-en-v1.5](https://huggingface.co/BAAI/bge-base-en-v1.5)

## Usage

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("darkraise/darkmem-retriever-v1")
emb = model.encode(
    "Represent this sentence for searching relevant passages: " + "your query",
    normalize_embeddings=True,
)
```

## License

Inherits the license of the base model. Fine-tuned weights published under the
same terms unless noted otherwise in the repo.

## Provenance

Fine-tuned as part of [darkmem](https://github.com/) — a centralized memory
system for AI agents. Training recipe and evaluation scripts are in the
`fine-tuning/` subtree of the darkmem repository.
