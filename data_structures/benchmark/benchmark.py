"""Експерименти до задачі І. Запуск з кореня репозиторію (де лежить students.csv):

  python experiments.py compare            # операцій за 10 с для трьох варіантів
  python experiments.py scaling            # час операцій і пам'ять для 10 розмірів бази
  python experiments.py scaling --variant 3

Результати: results_compare.csv, results_scaling_v<N>.csv (далі їх обробляє analyze.py).
"""
import argparse
import copy
import csv
import gc
import random
import statistics
import sys
import tracemalloc
from time import perf_counter, perf_counter_ns
from pathlib import Path


from data_structures.database.loader import load_students
from data_structures.hash_scan import HashScanDB
from data_structures.sorted_array import SortedArrayDB
from data_structures.buckets_heap import BucketsHeapDB

OUT_DIR = Path(__file__).resolve().parent     # data_structures/benchmark

VARIANTS = {1: HashScanDB, 2: SortedArrayDB, 3: BucketsHeapDB}
SIZES = [100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000, 100000]
OP_WEIGHTS = (50, 1, 10)       # співвідношення операцій 1 : 2 : 3


def fresh(students):
    """Нові об'єкти Student: операція 2 змінює дані, тому кожен запуск має власну копію."""
    return [copy.copy(s) for s in students]


def random_rating(rng):
    return round(rng.uniform(0, 100), 2)


def make_ops(students, count, rng):
    """Заздалегідь підготовлена послідовність операцій (код, email, рейтинг)."""
    emails = [s.m_email for s in students]
    op1, op3 = (1, None, None), (3, None, None)
    codes = rng.choices((1, 2, 3), weights=OP_WEIGHTS, k=count)
    return [op1 if c == 1 else op3 if c == 3
            else (2, rng.choice(emails), random_rating(rng)) for c in codes]


# ---------------------------------------------------------------- compare
def count_ops(db, ops, seconds):
    """Скільки операцій з готової послідовності виконується за `seconds` секунд."""
    top, setr, best = db.top_100, db.set_rating, db.best_groups
    now = perf_counter
    done = 0
    gc.collect()
    gc.disable()
    deadline = now() + seconds
    try:
        while True:                       # послідовність проходиться по колу
            for code, email, rating in ops:
                if code == 1:
                    top()
                elif code == 3:
                    best()
                else:
                    setr(email, rating)
                done += 1
                if now() >= deadline:
                    return done
    finally:
        gc.enable()


def cmd_compare(a):
    students = load_students(a.csv)
    ops = make_ops(students, a.ops, random.Random(a.seed))
    rows = []
    for v, cls in VARIANTS.items():
        for run in range(1, a.runs + 1):
            db = cls(fresh(students))
            done = count_ops(db, ops, a.seconds)
            rows.append((v, run, done))
            print(f"варіант {v}, запуск {run}: {done} операцій", flush=True)
            del db
    with open(OUT_DIR / "results_compare.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["variant", "run", "ops_done"])
        w.writerows(rows)
    print(f"\nСередня кількість операцій за {a.seconds} с (n = {len(students)}):")
    for v in VARIANTS:
        counts = [r[2] for r in rows if r[0] == v]
        sd = statistics.stdev(counts) if len(counts) > 1 else 0.0
        print(f"  варіант {v}: {statistics.mean(counts):.0f} ± {sd:.0f}")


# ---------------------------------------------------------------- scaling
def resolve_variant(arg):
    if arg != "auto":
        return int(arg)
    try:
        with open(OUT_DIR / "results_compare.csv", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except FileNotFoundError:
        sys.exit("Немає results_compare.csv: спершу запустіть compare або вкажіть --variant.")
    means = {v: statistics.mean(int(r["ops_done"]) for r in rows if int(r["variant"]) == v)
             for v in VARIANTS}
    best = max(means, key=means.get)
    print(f"Найкращий за results_compare.csv: варіант {best}")
    return best


def measure_memory(cls, students):
    """Додаткова пам'ять структури (без самих об'єктів Student), байти: (залишок, пік)."""
    gc.collect()
    tracemalloc.start()
    before = tracemalloc.get_traced_memory()[0]
    db = cls(students)
    after, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    del db
    return after - before, peak - before


def time_batch(fn, calls, budget):
    """Середній час виклику fn() без аргументів, с."""
    t0 = perf_counter()
    done = 0
    for _ in range(calls):
        fn()
        done += 1
        if done >= 10 and perf_counter() - t0 > budget:
            break
    return (perf_counter() - t0) / done


def time_mixed(db, emails, rng, calls, budget):
    """Операції 3 і 2 у реальному співвідношенні 10 : 1; кожен виклик вимірюється окремо.
    Повертає (середній час операції 2, середній час операції 3), с."""
    best, setr = db.best_groups, db.set_rating
    ns = perf_counter_ns
    t2 = t3 = n2 = n3 = 0
    start = perf_counter()
    for i in range(calls):
        if i % 10 == 0:
            email, rating = rng.choice(emails), random_rating(rng)
            a = ns()
            setr(email, rating)
            t2 += ns() - a
            n2 += 1
        a = ns()
        best()
        t3 += ns() - a
        n3 += 1
        if n3 >= 20 and perf_counter() - start > budget:
            break
    return t2 / n2 / 1e9, t3 / n3 / 1e9


def cmd_scaling(a):
    variant = resolve_variant(a.variant)
    cls = VARIANTS[variant]
    all_students = load_students(a.csv)
    sizes = [n for n in SIZES if n <= len(all_students)]
    if len(sizes) < len(SIZES):
        print(f"Увага: у файлі лише {len(all_students)} студентів, частину розмірів пропущено.")
    out = OUT_DIR / f"results_scaling_v{variant}.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["n", "rep", "t_op1", "t_op2", "t_op3", "build_time", "mem_struct", "mem_peak"])
        for n in sizes:
            for rep in range(1, a.reps + 1):
                rng = random.Random(a.seed * 1_000_003 + n * 101 + rep)
                sample = rng.sample(all_students, n)
                emails = [s.m_email for s in sample]

                mem, peak = measure_memory(cls, fresh(sample))      # окремий прохід

                students = fresh(sample)
                gc.collect()
                gc.disable()
                t0 = perf_counter()
                db = cls(students)
                build = perf_counter() - t0
                t1 = time_batch(db.top_100, a.calls, a.budget)
                t2, t3 = time_mixed(db, emails, rng, a.calls, a.budget)
                gc.enable()
                del db

                w.writerow([n, rep, t1, t2, t3, build, mem, peak])
                f.flush()
                print(f"n={n:>6} rep={rep}: op1={t1*1e6:9.1f} мкс  op2={t2*1e6:9.1f} мкс  "
                      f"op3={t3*1e6:9.1f} мкс  пам'ять={mem/1024:9.1f} КіБ", flush=True)
    print(f"\nЗбережено {out}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("compare")
    c.add_argument("--csv", default="students.csv")
    c.add_argument("--seconds", type=float, default=10)
    c.add_argument("--runs", type=int, default=3)
    c.add_argument("--ops", type=int, default=2_000_000, help="довжина підготовленої послідовності")
    c.add_argument("--seed", type=int, default=1)
    c.set_defaults(func=cmd_compare)

    s = sub.add_parser("scaling")
    s.add_argument("--csv", default="students.csv")
    s.add_argument("--variant", choices=["auto", "1", "2", "3"], default="auto")
    s.add_argument("--reps", type=int, default=5, help="кількість запусків на точку (>= 5)")
    s.add_argument("--calls", type=int, default=2000, help="викликів кожної операції на запуск")
    s.add_argument("--budget", type=float, default=1.0, help="ліміт часу на одне вимірювання, с")
    s.add_argument("--seed", type=int, default=1)
    s.set_defaults(func=cmd_scaling)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()