"""
EmbeddingKNNClassifier — KNN-based intent classification using embeddings.

Replaces cosine-threshold nearest-centroid approach with scikit-learn KNeighborsClassifier
that votes on K nearest training examples for more robust classification.

Falls back to cosine similarity if scikit-learn is unavailable.
"""
import numpy as np
from typing import Optional, Dict, List, Tuple, Any

try:
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.preprocessing import LabelEncoder
    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False


class EmbeddingKNNClassifier:
    """KNN classifier over embedding vectors for intent classification.

    Advantages over cosine-threshold:
    - Considers K nearest neighbors (majority vote), not just closest centroid
    - Handles overlapping intents better via probability estimates
    - Distance-weighted voting reduces impact of outlier training examples
    """

    K_NEIGHBORS = 5
    MIN_TRAINING = 3  # minimum training examples to fit KNN

    def __init__(self):
        self._knn = None
        self._label_encoder = None
        self._labels = []       # list of (action, skill) tuples, aligned with vectors
        self._vectors = None    # numpy array of training vectors
        self._fitted = False

    @property
    def available(self) -> bool:
        return _HAS_SKLEARN and self._fitted

    def fit(self, training_data: List[Tuple[str, str]], vectors: np.ndarray):
        """Fit KNN on training vectors with (action, skill) labels.

        Args:
            training_data: list of (action, skill) tuples
            vectors: numpy array of shape (n_samples, n_features)
        """
        if not _HAS_SKLEARN or len(training_data) < self.MIN_TRAINING:
            self._fitted = False
            return

        self._labels = list(training_data)
        self._vectors = np.array(vectors)

        # Encode labels as strings "action:skill"
        label_strings = [f"{a}:{s}" for a, s in self._labels]
        self._label_encoder = LabelEncoder()
        y = self._label_encoder.fit_transform(label_strings)

        k = min(self.K_NEIGHBORS, len(training_data))
        self._knn = KNeighborsClassifier(
            n_neighbors=k,
            weights="distance",   # closer neighbors get more vote weight
            metric="cosine",
            algorithm="brute",    # cosine metric requires brute-force
        )
        self._knn.fit(self._vectors, y)
        self._fitted = True

    def predict(self, user_vec: np.ndarray) -> Optional[Dict[str, Any]]:
        """Predict intent for a user vector.

        Returns dict with keys:
            action, skill, confidence, all_scores
        or None if not fitted.
        """
        if not self._fitted or self._knn is None:
            return None

        user_vec = np.array(user_vec).reshape(1, -1)

        # Get probabilities for each class
        proba = self._knn.predict_proba(user_vec)[0]
        classes = self._label_encoder.classes_

        # Build scores dict and find top prediction
        scores = {}
        for i, cls in enumerate(classes):
            scores[cls] = float(proba[i])

        top_idx = np.argmax(proba)
        top_label = classes[top_idx]
        top_conf = float(proba[top_idx])

        action, skill = top_label.split(":", 1)

        return {
            "action": action,
            "skill": skill if action == "use" else "",
            "confidence": top_conf,
            "all_scores": {k: v for k, v in sorted(scores.items(),
                                                    key=lambda x: -x[1])[:5]},
        }

    def predict_with_distances(self, user_vec: np.ndarray) -> Optional[Dict[str, Any]]:
        """Like predict but also returns nearest neighbor distances for debugging."""
        result = self.predict(user_vec)
        if result is None:
            return None

        user_vec = np.array(user_vec).reshape(1, -1)
        distances, indices = self._knn.kneighbors(user_vec)

        neighbors = []
        for dist, idx in zip(distances[0], indices[0]):
            action, skill = self._labels[idx]
            neighbors.append({
                "action": action,
                "skill": skill,
                "distance": float(dist),
            })

        result["neighbors"] = neighbors
        return result
