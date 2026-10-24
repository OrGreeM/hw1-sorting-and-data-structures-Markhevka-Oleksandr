"""Порівняння часу сортування за m_rating (S2) залежно від кількості записів. Запуск з кореня:

  py -m sorting.benchmark_sort
  py -m sorting.benchmark_sort --reps 10 --sizes 1000 10000 100000

Результати в папці скрипта: results_sort.csv (усі запуски), summary_sort.csv (середнє, σ),
sort_time.png (графік; потрібен matplotlib).

Методика: для кожного n і повтору береться нова випадкова підмножина з students.csv
(фіксований seed). Обидва методи сортують ОДНУ Й ТУ САМУ підмножину; порядок методів
міняється циклічно між повторами. Вимірюється весь виклик сортувальника, тобто з
побудовою ключів і кошиків. Збирач сміття вимкнено. Запис у CSV не вимірюється.
Коректність результату перевіряється поза виміром.
"""
import argparse
import csv
import gc
import random
import statistics
from collections import defaultdict
from pathlib import Path
from time import perf_counter

from data_structures.database.loader import load_students
from sorting.sorters import SORTERS

OUT_DIR = Path(__file__).resolve().parent
SIZES = [100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000, 100000]


def timed(fn, data, inner):
    """Мінімум-вільний вимір: середній час одного виклику за `inner` викликів, с."""
    gc.collect()
    gc.disable()
    try:
        t0 = perf_counter()
        for _ in range(inner):
            res = fn(data)
        dt = (perf_counter() - t0) / inner
    finally:
        gc.enable()
    return dt, res


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--csv", default="students.csv")
    p.add_argument("--reps", type=int, default=5, help="повторів на точку (>= 5)")
    p.add_argument("--sizes", type=int, nargs="+", default=SIZES)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--min-time", type=float, default=0.05,
                   help="мінімальна сумарна тривалість одного виміру, с (для малих n виклик повторюється)")
    a = p.parse_args()

    all_students = load_students(a.csv)
    sizes = [n for n in a.sizes if n <= len(all_students)]
    if len(sizes) < len(a.sizes):
        print(f"Увага: у файлі лише {len(all_students)} студентів, частину розмірів пропущено.")
    names = list(SORTERS)

    rows = []
    for n in sizes:
        for rep in range(1, a.reps + 1):
            rng = random.Random(a.seed * 1_000_003 + n * 101 + rep)
            sample = rng.sample(all_students, n)
            expected = sorted(s.m_rating for s in sample)
            shift = rep % len(names)
            for name in names[shift:] + names[:shift]:
                fn = SORTERS[name]
                once, res = timed(fn, sample, 1)                 # пробний виклик для оцінки тривалості
                inner = max(1, int(a.min_time / max(once, 1e-9)))
                t, res = timed(fn, sample, inner) if inner > 1 else (once, res)
                assert [s.m_rating for s in res] == expected, f"{name}: неправильний результат"
                rows.append((n, rep, name, t))
        line = "  ".join(f"{nm}={statistics.mean(r[3] for r in rows if r[0]==n and r[2]==nm)*1e3:8.3f} мс"
                         for nm in names)
        print(f"n={n:>6}: {line}", flush=True)

    with open(OUT_DIR / "results_sort.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["n", "rep", "method", "time_s"])
        w.writerows(rows)

    stat = defaultdict(list)
    for n, _, name, t in rows:
        stat[(name, n)].append(t)
    with open(OUT_DIR / "summary_sort.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["n"] + [f"{nm}_{k}_ms" for nm in names for k in ("mean", "std")] +
                   [f"speedup_{nm}" for nm in names if nm != "builtin"])
        for n in sizes:
            row, means = [n], {}
            for nm in names:
                v = stat[(nm, n)]
                means[nm] = statistics.mean(v)
                row += [f"{means[nm]*1e3:.4f}", f"{(statistics.stdev(v) if len(v) > 1 else 0)*1e3:.4f}"]
            row += [f"{means['builtin']/means[nm]:.2f}" for nm in names if nm != "builtin"]
            w.writerow(row)
    print("\nЗбережено results_sort.csv, summary_sort.csv")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib не встановлено: графік пропущено.")
        return
    fig, ax = plt.subplots(figsize=(8, 5))
    for nm in names:
        mu = [statistics.mean(stat[(nm, n)]) * 1e3 for n in sizes]
        sd = [(statistics.stdev(stat[(nm, n)]) if len(stat[(nm, n)]) > 1 else 0) * 1e3 for n in sizes]
        ax.errorbar(sizes, mu, yerr=sd, fmt="o-", capsize=3, label=nm)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("кількість студентів n")
    ax.set_ylabel("час сортування, мс")
    ax.set_title("S2: сортування за m_rating (середнє ± σ)")
    ax.grid(alpha=0.3, which="both")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT_DIR / "sort_time.png", dpi=150)
    print("Збережено sort_time.png")


if __name__ == "__main__":
    main()
