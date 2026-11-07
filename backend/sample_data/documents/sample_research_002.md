# Information Retrieval and Search Engine Architecture

## Introduction

Information retrieval (IR) is the discipline concerned with finding material — usually documents — of an unstructured nature that satisfies an information need from within large collections. Modern search engines are the most visible application of IR research, processing billions of queries per day across web-scale corpora. This document examines the core components of search engine architecture and the ranking models that power modern retrieval systems.

## The Inverted Index

The foundational data structure in information retrieval is the **inverted index**. Unlike a forward index that maps each document to its constituent terms, an inverted index maps each unique term to a **postings list** — a sorted list of document identifiers in which that term appears. Each entry in the postings list may also store the term frequency within the document, positional offsets (enabling phrase queries), and payload data such as per-position formatting flags.

Building an inverted index requires several preprocessing steps. The raw document text is first **tokenized** into individual terms. **Normalization** operations such as lowercasing, accent removal, and Unicode folding ensure that surface-level variants map to the same index term. A **stemmer** (e.g., Porter or Snowball) or **lemmatizer** reduces inflected forms to a common base. Finally, high-frequency but low-information **stop words** (e.g., "the", "is", "at") may be removed to reduce index size, although modern engines increasingly retain them to support phrase and proximity queries.

## Scoring and Ranking Models

### TF-IDF

**Term Frequency–Inverse Document Frequency (TF-IDF)** is a classical scoring model that assigns each query-document pair a relevance score. The term frequency component measures how often a term appears in a document — raw counts, log-scaled, or boolean. The inverse document frequency component penalizes terms that appear in many documents, assigning higher weight to rare, discriminative terms. The product of TF and IDF produces a score reflecting both local importance and global rarity.

### BM25

**BM25** (Best Match 25) refines TF-IDF in two important ways. First, it introduces **term frequency saturation** through a parameter *k₁*: as a term appears more frequently in a document, the marginal contribution to the score diminishes, following a non-linear curve. This prevents pathologically long documents from dominating results simply through repetition. Second, BM25 normalizes document scores by **document length** via parameter *b*, penalizing documents that are longer than the collection average. Together, these refinements produce substantially more robust rankings than raw TF-IDF, and BM25 remains the default scoring model in systems like Elasticsearch and Apache Lucene.

### Learned Ranking Models

Modern search engines supplement lexical models with **learned ranking** approaches. **Learning to Rank (LTR)** methods train a machine learning model — typically a gradient-boosted decision tree or a neural network — on feature vectors derived from query-document pairs. Features include BM25 scores, PageRank, click-through rates, document freshness, and embedding similarity. LTR models are trained on human relevance judgments or click logs to produce a final ranking that balances many relevance signals.

## Semantic and Dense Retrieval

Traditional lexical retrieval suffers from the **vocabulary mismatch problem**: a user searching for "automobile repair" will not match documents containing only "car maintenance." **Dense retrieval** addresses this by encoding both queries and documents as dense embedding vectors using pre-trained language models (e.g., BERT, sentence-transformers). Relevance is measured by the cosine similarity or inner product between the query vector and each document vector. Approximate nearest neighbor (ANN) indexes such as HNSW and IVF-PQ enable sub-linear search over millions of vectors.

## Hybrid Retrieval and Reciprocal Rank Fusion

In practice, the best results come from **hybrid retrieval** — combining lexical and semantic signals. **Reciprocal Rank Fusion (RRF)** is a simple but effective fusion technique: for each candidate document appearing in any result list, it computes a fused score as the sum of 1/(k + rank) across all lists, where *k* is a constant (typically 60). RRF is rank-based, requiring no score calibration between disparate retrieval systems, making it robust and easy to implement.

## Query Processing Pipeline

A complete search engine processes each query through several stages: parsing and tokenization, query expansion or rewriting, retrieval from one or more indexes, score fusion, re-ranking (often using a cross-encoder model for high precision), and result presentation with snippet generation and highlighting.

## Conclusion

Search engine architecture is a mature yet rapidly evolving field. The convergence of classical IR techniques like BM25 with neural dense retrieval and learned re-ranking has produced systems of remarkable accuracy and scale. Understanding these components is essential for building effective retrieval-augmented generation pipelines and enterprise search solutions.
