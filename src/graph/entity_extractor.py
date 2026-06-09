import re
import uuid
from dataclasses import dataclass


@dataclass
class Entity:
    id: str
    name: str
    type: str
    confidence: float = 0.8


class EntityExtractor:
    PATTERNS = {
        "EMAIL": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "PHONE": r"\+?[1-9]\d{1,14}",
        "DATE": r"\b(?:\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4})\b",
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
        proper_nouns = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", text)
        acronyms = re.findall(r"\b[A-Z]{2,}\b", text)
        return list(set(proper_nouns + acronyms))

    async def extract_with_llm(self, text: str) -> list[Entity]:
        return self.extract(text)


def get_entity_extractor() -> EntityExtractor:
    return EntityExtractor()
