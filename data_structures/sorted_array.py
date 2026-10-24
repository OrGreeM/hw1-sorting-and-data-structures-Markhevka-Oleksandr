"""Варіант 2: відсортований масив (рейтинг, email) + бінарний пошук."""
from bisect import bisect_left, insort

from data_structures.database.student import Student


def to_cents(rating: float) -> int:
    return round(rating * 100)


class SortedArrayDB:
    def __init__(self, students: list[Student]):
        self.by_email: dict[str, Student] = {}   # email -> студент
        self.group_stats: dict[str, list] = {}   # група -> [сума_сотих, кількість]
        for s in students:
            self.by_email[s.m_email] = s
            stat = self.group_stats.get(s.m_group)
            if stat is None:
                self.group_stats[s.m_group] = [to_cents(s.m_rating), 1]
            else:
                stat[0] += to_cents(s.m_rating)
                stat[1] += 1
        # за зростанням: найкращі студенти -- в кінці масиву
        self.keys = sorted((s.m_rating, s.m_email) for s in self.by_email.values())

    def top_100(self) -> list[Student]:          # O(100)
        by_email = self.by_email
        return [by_email[email] for _, email in reversed(self.keys[-100:])]

    def set_rating(self, email: str, new_rating: float) -> bool:   # O(log n) + зсув
        s = self.by_email.get(email)
        if s is None:
            return False
        old = s.m_rating
        stat = self.group_stats[s.m_group]
        stat[0] += to_cents(new_rating) - to_cents(old)
        keys = self.keys
        del keys[bisect_left(keys, (old, email))]
        insort(keys, (new_rating, email))
        s.m_rating = new_rating
        return True

    def best_groups(self) -> tuple[float, list[str]]:             # O(G)
        best = -1.0
        result: list[str] = []
        for group, (total, count) in self.group_stats.items():
            avg = total / count
            if avg > best:
                best, result = avg, [group]
            elif avg == best:
                result.append(group)
        return best / 100, sorted(result)