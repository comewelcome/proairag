import re
import uuid
from dataclasses import dataclass


@dataclass
class Entity:
    id: str
    name: str
    type: str
    confidence: float = 0.8


# Noise words to exclude from concept extraction
NOISE_WORDS = {
    "The", "And", "For", "Not", "Are", "Was", "But", "All", "Any", "Can",
    "Had", "Has", "His", "How", "Its", "May", "New", "One", "Our", "She",
    "They", "This", "That", "With", "From", "Have", "Will", "Their", "What",
    "About", "Which", "Other", "When", "Do", "If", "Out", "Up", "So", "He",
    "It", "Be", "An", "As", "Or", "My", "No", "At", "By", "On", "To", "Of",
    "In", "Is", "A", "I", "You", "We", "They",
    "DOCTYPE", "HTML", "HEAD", "META", "BODY", "DIV", "SPAN", "CLASS",
    "STYLE", "LINK", "SCRIPT", "SECTION", "HEADER", "FOOTER", "TITLE",
    "H1", "H2", "H3", "H4", "H5", "H6", "P", "BR", "HR", "UL", "OL", "LI",
    "IMG", "SRC", "ALT", "HREF", "ID", "LANG", "UTF",
}

MAX_CONCEPTS = 50


class EntityExtractor:
    PATTERNS = {
        "EMAIL": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "PHONE": r"\+?[1-9]\d{1,14}",
        "DATE": r"\b(?:\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})\b",
        "URL": r"https?://[^\s]+",
        "MONEY": r"\$?\d+(?:,\d{3})*(?:\.\d{2})?",
    }

    def extract(self, text: str) -> list[Entity]:
        entities = []
        seen = set()

        for etype, pattern in self.PATTERNS.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                name = match.group().strip()
                entity_key = (name, etype)
                if entity_key not in seen:
                    seen.add(entity_key)
                    entities.append(
                        Entity(
                            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, name)),
                            name=name,
                            type=etype,
                            confidence=0.9,
                        )
                    )

        concepts = self._extract_concepts(text)
        for concept in concepts:
            entity_key = (concept, "CONCEPT")
            if entity_key not in seen:
                seen.add(entity_key)
                entities.append(
                    Entity(
                        id=str(uuid.uuid5(uuid.NAMESPACE_DNS, concept)),
                        name=concept,
                        type="CONCEPT",
                        confidence=0.7,
                    )
                )

        return entities

    def _extract_concepts(self, text: str) -> list[str]:
        # Mixed case proper nouns: "Mohammed Haouach", "Data Engineer"
        proper_nouns = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}\b", text)
        # All-caps names (2+ words): "MOHAMMED HAOUACH", "JEAN DUPONT"
        all_caps = re.findall(r"\b[A-Z]{2,}(?:\s+[A-Z]{2,})+\b", text)
        # Mixed + caps combo: "Mohammed HAOUACH", "Jean DUPONT"
        mixed_caps = re.findall(r"\b[A-Z][a-z]+\s+[A-Z]{2,}\b", text)
        filtered = [
            n for n in proper_nouns + all_caps + mixed_caps
            if n not in NOISE_WORDS and len(n) > 3
        ]
        return list(set(filtered))[:MAX_CONCEPTS]

    async def extract_with_llm(self, text: str) -> list[Entity]:
        return self.extract(text)


def get_entity_extractor() -> EntityExtractor:
    return EntityExtractor()
