"""Звіряє кожен варіант із повільним, але очевидно правильним еталоном.
Запуск з кореня репозиторію: py -m data_structures.DS_tests"""
import copy
import random
from collections import defaultdict
from fractions import Fraction


from data_structures.database.student import Student
from data_structures.hash_scan import HashScanDB
from data_structures.sorted_array import SortedArrayDB
from data_structures.buckets_heap import BucketsHeapDB, bucket_of


def to_cents(rating):
    return round(rating * 100)


def make_students(n, n_groups, rng):
    return [
        Student("Імʼя", "Прізвище", f"user{i}@student.org", 2000, 1, 1,
                f"AAA-{rng.randrange(n_groups):02d}",
                round(rng.uniform(0, 100), 2), f"38(050)00-00-{i:03d}")
        for i in range(n)
    ]


def expected_groups(ratings, group_of):
    """Еталон: точні середні через Fraction."""
    sums, counts = defaultdict(int), defaultdict(int)
    for email, r in ratings.items():
        sums[group_of[email]] += to_cents(r)
        counts[group_of[email]] += 1
    avgs = {g: Fraction(sums[g], counts[g]) for g in sums}
    best = max(avgs.values())
    return float(best) / 100, sorted(g for g, a in avgs.items() if a == best)


def check_internal(db, ratings):
    """Перевірка внутрішніх інваріантів структур після змін."""
    if isinstance(db, SortedArrayDB):
        assert db.keys == sorted((r, e) for e, r in ratings.items())
    if isinstance(db, BucketsHeapDB):
        expected = defaultdict(set)
        for e, r in ratings.items():
            expected[bucket_of(r)].add(e)
        assert db.buckets == dict(expected)
        assert db.idx == sorted(expected)


def check(cls, n, n_groups, steps, seed):
    rng = random.Random(seed)
    students = make_students(n, n_groups, rng)
    db = cls(copy.deepcopy(students))          # кожному варіанту -- власні копії
    ratings = {s.m_email: s.m_rating for s in students}
    group_of = {s.m_email: s.m_group for s in students}
    emails = list(ratings)
    for _ in range(steps):
        op = rng.choice([1, 1, 2, 2, 2, 3])
        if op == 1:
            res = db.top_100()
            assert [s.m_rating for s in res] == sorted(ratings.values(), reverse=True)[:100]
            assert len({s.m_email for s in res}) == len(res)
            assert all(ratings[s.m_email] == s.m_rating for s in res)
        elif op == 2:
            email = rng.choice(emails)
            new = rng.choice([0.0, 100.0, 50.0, round(rng.uniform(0, 100), 2)])
            assert db.set_rating(email, new)
            ratings[email] = new
        else:
            avg, groups = db.best_groups()
            e_avg, e_groups = expected_groups(ratings, group_of)
            assert groups == e_groups, (groups, e_groups)
            assert abs(avg - e_avg) < 1e-9
    check_internal(db, ratings)
    assert db.set_rating("nobody@student.org", 1.0) is False


if __name__ == "__main__":
    cases = [(50, 5, 1), (300, 20, 2), (1000, 3, 3), (2000, 90, 4), (500, 1, 5)]
    for cls in (HashScanDB, SortedArrayDB, BucketsHeapDB):
        for n, groups, seed in cases:
            check(cls, n, groups, 3000, seed)
        print(f"{cls.__name__}: OK")