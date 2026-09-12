# Multilingual PII Detection & RAG Retrieval-Quality Benchmark

## Why this project exists

Off-the-shelf PII detection tools (Microsoft Presidio, spaCy NER, multilingual embedding models) 
are built and benchmarked primarily on English and, to a lesser extent, French. Arabic — spoken 
by 400M+ people and the primary or co-official language across North Africa and the Middle East — 
is systematically underserved:

- spaCy has no official Arabic NER pipeline comparable to its French one
- Multilingual embedding models (BGE-M3, multilingual-E5) score measurably lower on Arabic 
  in MTEB benchmarks than on French or English
- Presidio's default recognizers and locale support are built around Latin-script, 
  English/French-first assumptions

This project tests a specific hypothesis: **if PII detection is weaker on Arabic, then any 
RAG system built on top of PII-scrubbed Arabic documents inherits that weakness twice — once 
in what gets incorrectly redacted or missed, and again in retrieval quality once the text has 
been altered.**

## What this project does

1. **Generates synthetic multilingual corpora** (French, Arabic, English control) — 
   custom generators for Moroccan CIN, French SIRET, and local phone/IBAN formats, 
   embedded in realistic sentence context rather than bare entity lists.

2. **Benchmarks PII detection** across all three languages using Presidio, zero-shot 
   transformer NER (XLM-RoBERTa, CamemBERT, AraBERT/MARBERT), and fine-tuned models — 
   measured with entity-level precision, recall, and F1 per language and per entity type, 
   with recall prioritized (a missed name is a privacy failure; a false positive is 
   only annoying).

3. **Measures RAG retrieval quality** with and without PII scrubbing, across all three 
   languages, using hybrid search (dense + BM25) and reranking — quantifying whether 
   redaction degrades retrieval more in Arabic than in French or English.

4. **Contributes findings back to Microsoft Presidio** as custom recognizers for 
   underrepresented entity types, backed by this benchmark's evidence.

## What this project does NOT do

- This is not built on, derived from, or dependent on any proprietary codebase. 
  All data
