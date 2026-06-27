"""
Clustering logic for grouping similar requests.

Plan:
- Generate embeddings for incoming requests (sentence-transformers)
- Compare against existing open requests using cosine similarity
- Assign to an existing cluster if similarity > threshold, else start a new one
- Periodic batch re-clustering option using scikit-learn (KMeans/HDBSCAN)
"""
