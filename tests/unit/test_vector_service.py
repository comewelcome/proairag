"""Unit tests for VectorService helper methods."""

import pytest

from src.services.vector_service import VectorService


class TestEmbeddingToString:
    """Tests pour la conversion d'embedding en string SQL."""

    def test_embedding_to_string_single_value(self):
        """Conversion d'un embedding avec une seule valeur."""
        embedding = [0.5]
        result = VectorService._embedding_to_string(embedding)

        assert result == "[0.5]"

    def test_embedding_to_string_multiple_values(self):
        """Conversion d'un embedding avec plusieurs valeurs."""
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        result = VectorService._embedding_to_string(embedding)

        assert result == "[0.1,0.2,0.3,0.4,0.5]"

    def test_embedding_to_string_negative_values(self):
        """Conversion avec des valeurs negatives."""
        embedding = [-0.5, 0.0, 0.5]
        result = VectorService._embedding_to_string(embedding)

        assert result == "[-0.5,0.0,0.5]"

    def test_embedding_to_string_very_small_values(self):
        """Conversion avec des valeurs tres petites."""
        embedding = [1e-10, 2.5e-5, -3.14e-8]
        result = VectorService._embedding_to_string(embedding)

        # Should handle scientific notation or decimal representation
        assert result.startswith("[")
        assert result.endswith("]")
        assert "e-" in result.lower() or "0.00" in result

    def test_embedding_to_string_large_values(self):
        """Conversion avec des valeurs grandes."""
        embedding = [999.99, -1000.0, 0.001]
        result = VectorService._embedding_to_string(embedding)

        assert result == "[999.99,-1000.0,0.001]"

    def test_embedding_to_string_384_dimensions(self):
        """Conversion d'un embedding 384 dimensions (taille standard)."""
        embedding = [0.1] * 384
        result = VectorService._embedding_to_string(embedding)

        # Should produce a valid SQL vector string
        assert result.startswith("[")
        assert result.endswith("]")
        # Count commas (should be 383 for 384 values)
        assert result.count(",") == 383

    def test_embedding_to_string_empty_list(self):
        """Conversion d'une liste vide."""
        embedding = []
        result = VectorService._embedding_to_string(embedding)

        assert result == "[]"

    def test_embedding_to_string_preserves_order(self):
        """L'ordre des valeurs est preserve."""
        embedding = [0.3, 0.1, 0.2, 0.4]
        result = VectorService._embedding_to_string(embedding)

        # Should maintain the original order
        assert result == "[0.3,0.1,0.2,0.4]"

    def test_embedding_to_string_integer_values(self):
        """Conversion avec des valeurs entieres (converties en float)."""
        embedding = [1, 2, 3]
        result = VectorService._embedding_to_string(embedding)

        # Python will convert to string as "1", "2", "3"
        assert result == "[1,2,3]"
