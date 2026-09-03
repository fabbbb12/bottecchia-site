"""Relações matemáticas entre mercados relacionados — Seção 8.

Só implementa relações que podem ser formalizadas sem interpretação
subjetiva: a relação em si (A implica B, A é subconjunto de B, etc.)
precisa ser declarada explicitamente por quem monta o experimento —
este módulo NUNCA infere relações a partir do texto da pergunta
(nada de NLP nesta fase, por definição da Seção 8).
"""

from dataclasses import dataclass
from enum import Enum


class RelationType(Enum):
    IMPLIES = "implies"                    # A -> B: P(A) <= P(B)
    SUBSET = "subset"                       # A subconjunto de B: P(A) <= P(B) (mesma restrição que IMPLIES)
    MUTUALLY_EXCLUSIVE = "mutually_exclusive"  # P(A) + P(B) <= 1
    EXHAUSTIVE = "exhaustive"               # P(A) + P(B) >= 1 (juntos cobrem todo o espaço)


@dataclass
class Relation:
    """Uma relação declarada manualmente entre dois tokens/mercados,
    com a justificativa registrada — nunca inferida."""

    token_a: str
    token_b: str
    relation_type: RelationType
    justification: str


@dataclass
class RelationViolation:
    relation: Relation
    price_a: float
    price_b: float
    violation_amount: float  # o quanto a restrição foi violada (sempre >= 0 quando há violação)


def check_relation(relation: Relation, price_a: float, price_b: float) -> RelationViolation | None:
    """Verifica se a restrição matemática da relação foi violada nos
    preços atuais. Devolve None se a restrição está sendo respeitada."""
    if relation.relation_type in (RelationType.IMPLIES, RelationType.SUBSET):
        # P(A) <= P(B) — violação se P(A) > P(B)
        violation_amount = price_a - price_b
        if violation_amount > 0:
            return RelationViolation(relation, price_a, price_b, violation_amount)
        return None

    if relation.relation_type == RelationType.MUTUALLY_EXCLUSIVE:
        # P(A) + P(B) <= 1 — violação se a soma passar de 1
        violation_amount = (price_a + price_b) - 1
        if violation_amount > 0:
            return RelationViolation(relation, price_a, price_b, violation_amount)
        return None

    if relation.relation_type == RelationType.EXHAUSTIVE:
        # P(A) + P(B) >= 1 — violação se a soma ficar abaixo de 1
        violation_amount = 1 - (price_a + price_b)
        if violation_amount > 0:
            return RelationViolation(relation, price_a, price_b, violation_amount)
        return None

    raise ValueError(f"Tipo de relação desconhecido: {relation.relation_type}")
