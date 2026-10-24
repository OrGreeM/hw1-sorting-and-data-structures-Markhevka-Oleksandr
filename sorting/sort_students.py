"""Сортує студентів за m_rating (S2) і зберігає результат у CSV. Запуск з кореня репозиторію:

  py -m sorting.sort_students --method counting --out sorted_by_rating.csv

Час вимірюється лише для сортування; запис у файл у нього не входить.
"""
import argparse
import csv
from dataclasses import fields
from time import perf_counter

from data_structures.database.loader import load_students
from data_structures.database.student import Student
from sorting.sorters import SORTERS

COLUMNS = [f.name for f in fields(Student)]


def write_csv(students: list[Student], path: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        for s in students:
            w.writerow([getattr(s, c) for c in COLUMNS])


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--csv", default="students.csv")
    p.add_argument("--method", choices=list(SORTERS), default="counting")
    p.add_argument("--out", default="sorted_by_rating.csv")
    a = p.parse_args()

    students = load_students(a.csv)
    t0 = perf_counter()
    result = SORTERS[a.method](students)
    dt = perf_counter() - t0
    write_csv(result, a.out)
    print(f"{a.method}: {len(result)} студентів відсортовано за {dt*1000:.2f} мс -> {a.out}")


if __name__ == "__main__":
    main()
