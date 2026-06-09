"""Unit tests for EntityExtractor (no DB needed - pure regex)."""

import pytest

from src.graph.entity_extractor import Entity, EntityExtractor, get_entity_extractor


class TestEmailExtraction:
    """Tests pour l'extraction d'emails."""

    @pytest.fixture
    def extractor(self):
        return get_entity_extractor()

    def test_extract_single_email(self, extractor):
        """Extraction d'un email simple."""
        entities = extractor.extract("Contactez nous a john.doe@example.com pour plus d'infos")

        email_entities = [e for e in entities if e.type == "EMAIL"]
        assert len(email_entities) == 1
        assert email_entities[0].name == "john.doe@example.com"
        assert email_entities[0].confidence == 0.9

    def test_extract_multiple_emails(self, extractor):
        """Extraction de plusieurs emails."""
        text = "Joindre john@example.com et jane@example.com pour la reunion"
        entities = extractor.extract(text)

        email_entities = [e for e in entities if e.type == "EMAIL"]
        assert len(email_entities) == 2

    def test_no_duplicate_emails(self, extractor):
        """Pas de doublons si le meme email apparait plusieurs fois."""
        text = "Contact john@example.com, john@example.com, john@example.com"
        entities = extractor.extract(text)

        email_entities = [e for e in entities if e.type == "EMAIL"]
        assert len(email_entities) == 1


class TestPhoneExtraction:
    """Tests pour l'extraction de numeros de telephone."""

    @pytest.fixture
    def extractor(self):
        return get_entity_extractor()

    def test_extract_phone_with_plus(self, extractor):
        """Extraction d'un numero avec '+'."""
        text = "Appelez le +33123456789 maintenant"
        entities = extractor.extract(text)

        phone_entities = [e for e in entities if e.type == "PHONE"]
        assert len(phone_entities) == 1
        assert phone_entities[0].name == "+33123456789"

    def test_extract_phone_without_plus(self, extractor):
        """Extraction d'un numero sans '+'."""
        text = "Numero: 33123456789"
        entities = extractor.extract(text)

        phone_entities = [e for e in entities if e.type == "PHONE"]
        assert len(phone_entities) >= 1  # May also match MONEY pattern


class TestDateExtraction:
    """Tests pour l'extraction de dates."""

    @pytest.fixture
    def extractor(self):
        return get_entity_extractor()

    def test_extract_date_dd_mm_yyyy(self, extractor):
        """Extraction d'une date au format JJ/MM/AAAA."""
        text = "La reunion est le 15/03/2024"
        entities = extractor.extract(text)

        date_entities = [e for e in entities if e.type == "DATE"]
        assert len(date_entities) == 1
        assert date_entities[0].name == "15/03/2024"

    def test_extract_date_dd_mm_yy(self, extractor):
        """Extraction d'une date au format JJ/MM/AA."""
        text = "Date: 15/03/24"
        entities = extractor.extract(text)

        date_entities = [e for e in entities if e.type == "DATE"]
        assert len(date_entities) == 1

    def test_extract_month_name_date(self, extractor):
        """Extraction d'une date avec nom de mois."""
        text = "La reunion est le March 15, 2024"
        entities = extractor.extract(text)

        date_entities = [e for e in entities if e.type == "DATE"]
        assert len(date_entities) >= 1


class TestUrlExtraction:
    """Tests pour l'extraction d'URLs."""

    @pytest.fixture
    def extractor(self):
        return get_entity_extractor()

    def test_extract_http_url(self, extractor):
        """Extraction d'une URL http."""
        text = "Voir http://example.com pour plus d'infos"
        entities = extractor.extract(text)

        url_entities = [e for e in entities if e.type == "URL"]
        assert len(url_entities) == 1
        assert url_entities[0].name == "http://example.com"

    def test_extract_https_url(self, extractor):
        """Extraction d'une URL https."""
        text = "Voir https://example.com/path?query=1 pour plus d'infos"
        entities = extractor.extract(text)

        url_entities = [e for e in entities if e.type == "URL"]
        assert len(url_entities) == 1
        assert url_entities[0].name == "https://example.com/path?query=1"


class TestMoneyExtraction:
    """Tests pour l'extraction de montants financiers."""

    @pytest.fixture
    def extractor(self):
        return get_entity_extractor()

    def test_extract_money_with_dollar(self, extractor):
        """Extraction d'un montant avec '$'."""
        text = "Le budget est de $5000.00 ce mois-ci"
        entities = extractor.extract(text)

        money_entities = [e for e in entities if e.type == "MONEY"]
        assert len(money_entities) == 1
        assert money_entities[0].name == "$5000.00"

    def test_extract_money_without_dollar(self, extractor):
        """Extraction d'un montant sans '$'."""
        text = "Le budget est de 5000.00 euros"
        entities = extractor.extract(text)

        money_entities = [e for e in entities if e.type == "MONEY"]
        assert len(money_entities) >= 1


class TestConceptExtraction:
    """Tests pour l'extraction de concepts (noms propres et acronymes)."""

    @pytest.fixture
    def extractor(self):
        return get_entity_extractor()

    def test_extract_proper_nouns(self, extractor):
        """Extraction de noms propres."""
        text = "Jean Dupont et Marie Curie travaillent a Paris"
        entities = extractor.extract(text)

        concept_entities = [e for e in entities if e.type == "CONCEPT"]
        concept_names = [e.name for e in concept_entities]

        # Should extract proper nouns (may vary based on regex)
        assert any("Jean" in name or "Dupont" in name for name in concept_names)

    def test_extract_acronyms(self, extractor):
        """Extraction d'acronymes."""
        text = "L'API utilise le protocole HTTP et HTTPS"
        entities = extractor.extract(text)

        concept_entities = [e for e in entities if e.type == "CONCEPT"]
        concept_names = [e.name for e in concept_entities]

        assert "API" in concept_names
        assert "HTTP" in concept_names
        assert "HTTPS" in concept_names


class TestEntityProperties:
    """Tests pour les proprietes des entites."""

    @pytest.fixture
    def extractor(self):
        return get_entity_extractor()

    def test_entity_has_uuid(self, extractor):
        """Les entites ont un UUID deterministe."""
        text = "Contact john@example.com"
        entities = extractor.extract(text)

        email_entities = [e for e in entities if e.type == "EMAIL"]
        assert len(email_entities) == 1

        # UUID should be deterministic (same input -> same UUID)
        entities2 = extractor.extract("Contact john@example.com")
        assert entities[0].id == entities2[0].id

    def test_entity_confidence(self, extractor):
        """Les entites ont un niveau de confiance."""
        text = "Contact john@example.com et appelez +33123456789"
        entities = extractor.extract(text)

        for entity in entities:
            if entity.type in ("EMAIL", "PHONE", "DATE", "URL", "MONEY"):
                assert entity.confidence == 0.9
            elif entity.type == "CONCEPT":
                assert entity.confidence == 0.7


class TestMixedExtraction:
    """Tests pour l'extraction mixte (plusieurs types d'entites)."""

    @pytest.fixture
    def extractor(self):
        return get_entity_extractor()

    def test_extract_all_types(self, extractor):
        """Extraction de tous les types d'entites dans un seul texte."""
        text = """
        Jean Dupont travaille chez ACME Corp a Paris.
        Contact: jean@acme.com ou +33123456789
        Budget: $10000.00 pour le projet Q1 2024
        Plus d'infos sur https://acme.com/projects
        Reunion le 15/03/2024
        """

        entities = extractor.extract(text)

        types_found = {e.type for e in entities}

        assert "EMAIL" in types_found
        assert "PHONE" in types_found
        assert "MONEY" in types_found
        assert "URL" in types_found
        assert "DATE" in types_found
        assert "CONCEPT" in types_found

    def test_no_entities_in_empty_text(self, extractor):
        """Pas d'entites dans un texte vide."""
        entities = extractor.extract("")

        assert entities == []

    def test_no_entities_in_plain_text(self, extractor):
        """Pas d'entites structurees dans un texte simple."""
        text = "Bonjour tout le monde, comment allez-vous aujourd'hui?"
        entities = extractor.extract(text)

        # No structured entities (EMAIL, PHONE, etc.)
        structured_entities = [e for e in entities if e.type != "CONCEPT"]
        assert len(structured_entities) == 0
