"""Перевірка сортувань. Запуск з кореня репозиторію: py -m sorting.SORT_tests"""
import copy
import csv
import os
import random
import tempfile

from data_structures.database.student import Student
from sorting.sorters import SORTERS
from sorting.sort_students import COLUMNS, write_csv


def make(n, rng, ratings=None):
    return [
        Student("Імʼя", "Прізвище", f"user{i}@student.org", 2000, 1, 1, "AAA-00",
                ratings[i] if ratings else round(rng.uniform(0, 100), 2),
                f"38(050)00-00-{i:03d}")
        for i in range(n)
    ]


def check(name, fn, students):
    before = copy.deepcopy(students)
    res = fn(students)
    assert students == before, "вхідний список змінено"
    assert [s.m_rating for s in res] == sorted(s.m_rating for s in students), "порядок"
    assert sorted(s.m_email for s in res) == sorted(s.m_email for s in students), "склад"
    assert all(a is b or a == b for a, b in zip(sorted(res, key=lambda s: s.m_email),
                                                sorted(students, key=lambda s: s.m_email)))


def main():
    rng = random.Random(7)
    cases = {
        "порожній": [],
        "один": make(1, rng),
        "випадкові 5000": make(5000, rng),
        "усі однакові": make(500, rng, [42.5] * 500),
        "межі 0 і 100": make(400, rng, [0.0, 100.0] * 200),
        "мало значень (багато дублікатів)": make(3000, rng, [rng.choice([0, 1, 2.5, 99.99, 100]) for _ in range(3000)]),
        "вже відсортований": make(1000, rng, sorted(round(i / 10, 2) for i in range(1000))),
        "зворотний порядок": make(1000, rng, sorted((round(i / 10, 2) for i in range(1000)), reverse=True)),
        "усі 10001 значень": make(10001, rng, [i / 100 for i in range(10001)]),
    }
    for name, fn in SORTERS.items():
        for label, data in cases.items():
            check(name, fn, data)
        # некоректні дані
        if name != "builtin":                  # стандартний sorted діапазон не перевіряє
            for bad in (-0.01, 100.01):
                try:
                    fn(make(3, rng, [1.0, bad, 2.0]))
                    raise AssertionError("очікувався ValueError")
                except ValueError:
                    pass
        # збереження в CSV: рядки відповідають відсортованим студентам
        data = make(200, rng)
        res = fn(data)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "out.csv")
            write_csv(res, path)
            with open(path, encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))
        assert list(rows[0]) == COLUMNS and len(rows) == len(data)
        assert [float(r["m_rating"]) for r in rows] == sorted(s.m_rating for s in data)
        assert [r["m_email"] for r in rows] == [s.m_email for s in res]
        print(f"{fn.__name__}: OK")


if __name__ == "__main__":
    main()
