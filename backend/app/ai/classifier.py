"""
Request classification logic.

Plan:
- Load a sentence-transformers model for embeddings
- Either a simple rule-based classifier to start, or a small trained
  classifier (scikit-learn) on top of embeddings
- Expose a single function: classify(text: str) -> dict with category + confidence
"""
