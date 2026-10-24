"""Варіант 3: хеш-кошики за рейтингом + ліниве max-купа середніх по групах."""
import heapq
from bisect import bisect_left, insort
from heapq import heapify, heappop, heappush

from database.student import Student


def to_cents(rating: float) -> int:
    return round(rating * 100)


def bucket_of(rating: float) -> int:
    """Номер кошика (соті частки). Монотонна функція від рейтингу."""
    return int(rating * 100)


class BucketsHeapDB:
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
        self.buckets: dict[int, set[str]] = {}   # номер кошика -> множина email
        for s in self.by_email.values():
            self.buckets.setdefault(bucket_of(s.m_rating), set()).add(s.m_email)
        self.idx = sorted(self.buckets)          # відсортовані номери непорожніх кошиків
        self.gver = {g: 0 for g in self.group_stats}   # поточна версія запису групи
        self._rebuild_heap()

    def _rebuild_heap(self) -> None:
        self.heap = [(-t / c, g, self.gver[g]) for g, (t, c) in self.group_stats.items()]
        heapify(self.heap)

    # ---- операція 1: від найвищого кошика вниз, поки не назбирано 100 ----
    def top_100(self) -> list[Student]:
        got: list[str] = []
        for i in reversed(self.idx):
            got.extend(self.buckets[i])
            if len(got) >= 100:
                break
        studs = [self.by_email[e] for e in got]
        return heapq.nlargest(100, studs, key=lambda s: s.m_rating)

    # ---- операція 2: перенести студента між кошиками, дописати запис у купу ----
    def set_rating(self, email: str, new_rating: float) -> bool:
        s = self.by_email.get(email)
        if s is None:
            return False
        old = s.m_rating
        g = s.m_group
        stat = self.group_stats[g]
        stat[0] += to_cents(new_rating) - to_cents(old)

        i_old, i_new = bucket_of(old), bucket_of(new_rating)
        if i_old != i_new:
            bucket = self.buckets[i_old]
            bucket.remove(email)
            if not bucket:
                del self.buckets[i_old]
                del self.idx[bisect_left(self.idx, i_old)]
            bucket = self.buckets.get(i_new)
            if bucket is None:
                self.buckets[i_new] = {email}
                insort(self.idx, i_new)
            else:
                bucket.add(email)

        self.gver[g] += 1
        heappush(self.heap, (-stat[0] / stat[1], g, self.gver[g]))
        if len(self.heap) > 4 * len(self.gver) + 100:   # прибрати застарілі записи
            self._rebuild_heap()
        s.m_rating = new_rating
        return True

    # ---- операція 3: вершина купи без застарілих записів ----
    def best_groups(self) -> tuple[float, list[str]]:
        if not self.group_stats:
            return 0.0, []
        heap, gver = self.heap, self.gver
        while heap[0][2] != gver[heap[0][1]]:    # застарілий запис -- викинути
            heappop(heap)
        top_key = heap[0][0]
        keep = []
        while heap and heap[0][0] == top_key:    # усі групи з тим самим середнім
            item = heappop(heap)
            if item[2] == gver[item[1]]:
                keep.append(item)
        for item in keep:                        # актуальні записи повернути
            heappush(heap, item)
        return -top_key / 100, sorted(item[1] for item in keep)