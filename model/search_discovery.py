"""
Search & Discovery Engine for HealthOS.
Provides full-text search, semantic similarity, and intelligent recommendations.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import math

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A search result."""
    id: str
    type: str  # meal, recipe, user, goal
    title: str
    description: str
    relevance_score: float
    metadata: Dict[str, Any]


class FullTextSearchEngine:
    """Full-text search using TF-IDF and inverted index.
    
    Production: Use PostgreSQL full-text search or Elasticsearch.
    """
    
    def __init__(self):
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.inverted_index: Dict[str, set] = {}  # word -> doc_ids
        self.doc_frequencies: Dict[str, int] = {}
    
    def index_document(self, doc_id: str, text: str, doc_type: str = "general", 
                      metadata: Optional[Dict[str, Any]] = None):
        """Index a document for full-text search.
        
        Args:
            doc_id: Unique document identifier
            text: Document text to index
            doc_type: Type of document (meal, recipe, user, etc)
            metadata: Additional metadata
        """
        self.documents[doc_id] = {
            "text": text,
            "type": doc_type,
            "metadata": metadata or {},
        }
        
        # Tokenize and build inverted index
        words = self._tokenize(text)
        seen = set()
        
        for word in words:
            if word not in seen:
                if word not in self.inverted_index:
                    self.inverted_index[word] = set()
                    self.doc_frequencies[word] = 0
                
                self.inverted_index[word].add(doc_id)
                seen.add(word)
                self.doc_frequencies[word] += 1
    
    def search(self, query: str, doc_type: Optional[str] = None, limit: int = 10) -> List[SearchResult]:
        """Search documents using TF-IDF.
        
        Args:
            query: Search query
            doc_type: Filter by document type
            limit: Max results to return
            
        Returns:
            List of search results ranked by relevance
        """
        query_words = self._tokenize(query)
        
        if not query_words:
            return []
        
        # Find candidate documents
        candidate_docs = set()
        for word in query_words:
            if word in self.inverted_index:
                candidate_docs.update(self.inverted_index[word])
        
        if not candidate_docs:
            return []
        
        # Calculate TF-IDF scores
        scores = {}
        for doc_id in candidate_docs:
            # Filter by doc type if specified
            if doc_type and self.documents[doc_id]["type"] != doc_type:
                continue
            
            score = 0
            doc_text = self.documents[doc_id]["text"].lower()
            
            for word in query_words:
                # Term frequency
                tf = doc_text.count(word) / len(doc_text.split())
                
                # Inverse document frequency
                total_docs = len(self.documents)
                doc_freq = self.doc_frequencies.get(word, 1)
                idf = math.log(total_docs / max(1, doc_freq))
                
                score += tf * idf
            
            scores[doc_id] = score
        
        # Sort by score and return
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        results = []
        for doc_id, score in ranked:
            doc = self.documents[doc_id]
            results.append(SearchResult(
                id=doc_id,
                type=doc["type"],
                title=doc["metadata"].get("title", doc_id),
                description=doc["text"][:200],
                relevance_score=round(score, 4),
                metadata=doc["metadata"],
            ))
        
        return results
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenizer.
        
        Production: Use NLTK, spaCy, or ES for better tokenization.
        """
        words = text.lower().split()
        # Remove punctuation and short words
        return [w.strip(".,!?;:") for w in words if len(w) > 2]


class SemanticSearchEngine:
    """Semantic search using vector embeddings.
    
    Uses ChromaDB for vector similarity.
    """
    
    def __init__(self):
        self.embeddings: Dict[str, List[float]] = {}
        self.documents: Dict[str, Dict[str, Any]] = {}
    
    def add_document(self, doc_id: str, text: str, embedding: List[float],
                    doc_type: str = "general", metadata: Optional[Dict[str, Any]] = None):
        """Add document with embedding.
        
        Args:
            doc_id: Document identifier
            text: Document text
            embedding: Vector embedding (from ChromaDB)
            doc_type: Type of document
            metadata: Additional metadata
        """
        self.documents[doc_id] = {
            "text": text,
            "type": doc_type,
            "metadata": metadata or {},
        }
        self.embeddings[doc_id] = embedding
    
    def search_similar(self, query_embedding: List[float], 
                      doc_type: Optional[str] = None, limit: int = 10) -> List[SearchResult]:
        """Find semantically similar documents.
        
        Args:
            query_embedding: Vector embedding of query
            doc_type: Filter by document type
            limit: Max results
            
        Returns:
            Similar documents ranked by cosine similarity
        """
        if not self.embeddings:
            return []
        
        similarities = {}
        for doc_id, embedding in self.embeddings.items():
            # Filter by type if specified
            if doc_type and self.documents[doc_id]["type"] != doc_type:
                continue
            
            # Cosine similarity
            similarity = self._cosine_similarity(query_embedding, embedding)
            similarities[doc_id] = similarity
        
        # Sort by similarity
        ranked = sorted(similarities.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        results = []
        for doc_id, similarity in ranked:
            doc = self.documents[doc_id]
            results.append(SearchResult(
                id=doc_id,
                type=doc["type"],
                title=doc["metadata"].get("title", doc_id),
                description=doc["text"][:200],
                relevance_score=round(similarity, 4),
                metadata=doc["metadata"],
            ))
        
        return results
    
    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a ** 2 for a in vec1))
        norm2 = math.sqrt(sum(b ** 2 for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)


class RecommendationEngine:
    """Intelligent meal and diet recommendations.
    
    Uses collaborative filtering, content-based filtering, and hybrid approaches.
    """
    
    def __init__(self):
        self.user_meal_interactions: Dict[str, Dict[str, int]] = {}  # user_id -> meal_id -> rating
        self.meal_features: Dict[str, Dict[str, Any]] = {}  # meal_id -> features
        self.user_preferences: Dict[str, Dict[str, Any]] = {}  # user_id -> preferences
    
    def record_interaction(self, user_id: str, meal_id: str, rating: int):
        """Record user-meal interaction.
        
        Args:
            user_id: User identifier
            meal_id: Meal identifier
            rating: Rating (1-5)
        """
        if user_id not in self.user_meal_interactions:
            self.user_meal_interactions[user_id] = {}
        
        self.user_meal_interactions[user_id][meal_id] = rating
    
    def add_meal_features(self, meal_id: str, features: Dict[str, Any]):
        """Add features for a meal.
        
        Args:
            meal_id: Meal identifier
            features: Meal features (calories, protein, carbs, cuisine, etc)
        """
        self.meal_features[meal_id] = features
    
    def get_collaborative_recommendations(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recommendations using collaborative filtering.
        
        Similar users liked these meals -> recommend to current user
        
        Args:
            user_id: User to recommend for
            limit: Number of recommendations
            
        Returns:
            List of recommended meals
        """
        if user_id not in self.user_meal_interactions:
            return []
        
        user_ratings = self.user_meal_interactions[user_id]
        
        # Find similar users (simplified: users who rated same meals)
        similar_users = []
        for other_user, other_ratings in self.user_meal_interactions.items():
            if other_user == user_id:
                continue
            
            # Overlap of rated meals
            overlap = set(user_ratings.keys()) & set(other_ratings.keys())
            if len(overlap) > 0:
                # Simple similarity: avg rating agreement
                avg_diff = sum(abs(user_ratings[m] - other_ratings[m]) for m in overlap) / len(overlap)
                similarity = 1 / (1 + avg_diff)
                similar_users.append((other_user, similarity))
        
        if not similar_users:
            return []
        
        # Get meals liked by similar users but not yet rated by current user
        recommendations = {}
        for similar_user, similarity in similar_users:
            for meal_id, rating in self.user_meal_interactions[similar_user].items():
                if meal_id not in user_ratings:
                    if meal_id not in recommendations:
                        recommendations[meal_id] = []
                    recommendations[meal_id].append(rating * similarity)
        
        # Average scores
        scored = [(meal_id, sum(scores) / len(scores)) for meal_id, scores in recommendations.items()]
        scored.sort(key=lambda x: x[1], reverse=True)
        
        return [
            {
                "meal_id": meal_id,
                "predicted_rating": round(score, 2),
                "features": self.meal_features.get(meal_id, {}),
            }
            for meal_id, score in scored[:limit]
        ]
    
    def get_content_based_recommendations(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recommendations based on meal content similarity.
        
        Args:
            user_id: User to recommend for
            limit: Number of recommendations
            
        Returns:
            List of recommended meals
        """
        if user_id not in self.user_meal_interactions:
            return []
        
        liked_meals = [m for m, r in self.user_meal_interactions[user_id].items() if r >= 4]
        if not liked_meals:
            return []
        
        # Find common features in liked meals
        liked_features = defaultdict(lambda: [])
        for meal_id in liked_meals:
            features = self.meal_features.get(meal_id, {})
            for feature, value in features.items():
                liked_features[feature].append(value)
        
        # Find meals with similar features
        recommendations = {}
        for meal_id, features in self.meal_features.items():
            if meal_id in self.user_meal_interactions[user_id]:
                continue  # Already rated
            
            # Calculate similarity based on shared features
            similarity_score = 0
            for feature, liked_values in liked_features.items():
                if feature in features:
                    # Simple feature matching
                    if features[feature] in liked_values:
                        similarity_score += 1
            
            if similarity_score > 0:
                recommendations[meal_id] = similarity_score
        
        # Sort and return
        sorted_recs = sorted(recommendations.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        return [
            {
                "meal_id": meal_id,
                "similarity_score": score,
                "features": self.meal_features.get(meal_id, {}),
            }
            for meal_id, score in sorted_recs
        ]


from collections import defaultdict

# Global instances
full_text_search = FullTextSearchEngine()
semantic_search = SemanticSearchEngine()
recommendation_engine = RecommendationEngine()
