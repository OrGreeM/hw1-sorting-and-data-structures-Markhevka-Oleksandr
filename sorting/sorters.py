"""Задача II, варіант S2: сортування студентів за m_rating (за зростанням).

Усі функції повертають НОВИЙ список і не змінюють вхідний. Час побудови допоміжних
структур (ключі, кошики) входить у час сортування, бо вони створюються всередині функцій.

Ключ -- рейтинг у сотих: round(rating * 100), ціле число 0..10 000 (рейтинг 0..100
із двома знаками після коми). Це дозволяє сортувати без порівнянь:

  sort_builtin  -- стандартний sorted() (Timsort, O(n log n));
  sort_counting -- власне сортування підрахунком / кошиками: 1 прохід, 10 001 кошик, O(n + K).

Власний алгоритм стабільний. Порядок записів з однаковим рейтингом за умовою
завдання не визначений. Якщо рейтинг має більше двох знаків, студенти з однаковими
сотими можуть стояти не за точним рейтингом (як і в розділі 6 rationale.md).
"""
from itertools import chain

from data_structures.database.student import Student

MAX_KEY = 10_000          # 100.00 у сотих


def _keys(students: list[Student]) -> list[int]:
    """Ключі в сотих із перевіркою діапазону (від'ємний індекс мовчки зіпсував би кошики)."""
    keys = [round(s.m_rating * 100) for s in students]
    if keys and (min(keys) < 0 or max(keys) > MAX_KEY):
        raise ValueError("m_rating поза діапазоном 0..100")
    return keys


def sort_builtin(students: list[Student]) -> list[Student]:
    return sorted(students, key=lambda s: s.m_rating)


def sort_counting(students: list[Student]) -> list[Student]:
    keys = _keys(students)
    buckets: list[list[Student]] = [[] for _ in range(MAX_KEY + 1)]
    for k, s in zip(keys, students):
        buckets[k].append(s)
    return list(chain.from_iterable(buckets))


SORTERS = {"builtin": sort_builtin, "counting": sort_counting}