from arbitrage.relationships import Relation, RelationType, check_relation


def test_implies_violation_when_a_more_expensive_than_b():
    rel = Relation("A", "B", RelationType.IMPLIES, "A implica B: candidato específico implica categoria geral")
    violation = check_relation(rel, price_a=0.60, price_b=0.50)
    assert violation is not None
    assert round(violation.violation_amount, 6) == 0.10


def test_implies_no_violation_when_constraint_respected():
    rel = Relation("A", "B", RelationType.IMPLIES, "A implica B")
    violation = check_relation(rel, price_a=0.40, price_b=0.50)
    assert violation is None


def test_mutually_exclusive_violation_when_sum_above_one():
    rel = Relation("A", "B", RelationType.MUTUALLY_EXCLUSIVE, "não podem ocorrer os dois")
    violation = check_relation(rel, price_a=0.60, price_b=0.55)
    assert violation is not None
    assert round(violation.violation_amount, 6) == 0.15


def test_exhaustive_violation_when_sum_below_one():
    rel = Relation("A", "B", RelationType.EXHAUSTIVE, "cobrem todo o espaço de resultados")
    violation = check_relation(rel, price_a=0.40, price_b=0.45)
    assert violation is not None
    assert round(violation.violation_amount, 6) == 0.15


def test_subset_behaves_like_implies():
    rel = Relation("A", "B", RelationType.SUBSET, "A é subconjunto de B")
    violation = check_relation(rel, price_a=0.70, price_b=0.60)
    assert violation is not None
