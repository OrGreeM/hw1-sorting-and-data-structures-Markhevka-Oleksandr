"""Обробка результатів scaling: таблиця, регресія для найповільнішої операції, графіки.

  python -m data_structures.benchmark.analyze                      # знайде results_scaling_v*.csv
  python -m data_structures.benchmark.analyze --file results_scaling_v3.csv
  python -m data_structures.benchmark.analyze --basis "n,log n,1"  # власні f1, f2, f3

Файли читаються з папки скрипта і записуються в неї ж:
summary.csv, regression.txt, fit.png, memory.png
"""
import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT_DIR = Path(__file__).resolve().parent     # папка зі скриптом

FUNCS = {
    "1": lambda n: np.ones_like(n),
    "log n": lambda n: np.log2(n),
    "n": lambda n: n,
    "n log n": lambda n: n * np.log2(n),
    "n^2": lambda n: n ** 2,
}

# Базис (f1, f2, f3) за теоретичною складністю: (варіант, операція) -> функції
THEORY = {
    (1, 1): ("n", "log n", "1"),   # nlargest: O(n)
    (1, 2): ("1", "log n", "n"),   # хеш: O(1)
    (1, 3): ("n", "log n", "1"),   # перебір груп: O(G), G ~ n
    (2, 1): ("1", "log n", "n"),   # зріз 100 елементів: O(1) відносно n
    (2, 2): ("log n", "n", "1"),   # бісекція O(log n) + зсув масиву O(n)
    (2, 3): ("n", "log n", "1"),   # перебір груп: O(G), G ~ n
    (3, 1): ("1", "log n", "n"),   # O(K + m)
    (3, 2): ("log n", "1", "n"),   # купа O(log G) + зсув списку номерів кошиків
    (3, 3): ("log n", "1", "n"),   # амортизовано O(log G)
}


def load(path):
    data = defaultdict(lambda: defaultdict(list))     # колонка -> n -> значення
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            n = int(r["n"])
            for col in ("t_op1", "t_op2", "t_op3", "mem_struct", "mem_peak", "build_time"):
                data[col][n].append(float(r[col]))
    return data


def mean_std(values):
    arr = np.array(values)
    return arr.mean(), (arr.std(ddof=1) if len(arr) > 1 else 0.0)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--file")
    p.add_argument("--basis", help='три функції через кому, напр. "n,log n,1"')
    a = p.parse_args()

    if a.file:
        path = Path(a.file)
        if not path.exists():
            path = OUT_DIR / path
    else:
        found = sorted(OUT_DIR.glob("results_scaling_v*.csv"))
        if len(found) != 1:
            sys.exit(f"Вкажіть --file (знайдено файлів: {len(found)}).")
        path = found[0]
    variant = int(re.search(r"_v(\d+)", path.name).group(1))
    data = load(path)
    sizes = sorted(data["t_op1"])

    # ---- таблиця
    lines = ["n,op1_mean_us,op1_std_us,op2_mean_us,op2_std_us,op3_mean_us,op3_std_us,"
             "mem_mean_KiB,mem_std_KiB,bytes_per_student"]
    print(f"{'n':>7} | {'op1, мкс':>18} | {'op2, мкс':>18} | {'op3, мкс':>18} | {'пам`ять, КіБ':>16}")
    for n in sizes:
        cells, row = [], [str(n)]
        for col in ("t_op1", "t_op2", "t_op3"):
            m, s = mean_std(data[col][n])
            cells.append(f"{m*1e6:9.2f} ± {s*1e6:7.2f}")
            row += [f"{m*1e6:.3f}", f"{s*1e6:.3f}"]
        m, s = mean_std(data["mem_struct"][n])
        cells.append(f"{m/1024:8.1f} ± {s/1024:5.1f}")
        row += [f"{m/1024:.2f}", f"{s/1024:.2f}", f"{m/n:.1f}"]
        print(f"{n:>7} | " + " | ".join(cells))
        lines.append(",".join(row))
    with open(OUT_DIR / "summary.csv", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    # ---- найповільніша операція (за середнім часом при найбільшому n)
    nmax = sizes[-1]
    means = {op: np.mean(data[f"t_op{op}"][nmax]) for op in (1, 2, 3)}
    slow = max(means, key=means.get)
    print(f"\nНайповільніша операція при n = {nmax}: операція {slow} "
          f"({means[slow]*1e6:.2f} мкс)")

    # ---- регресія
    names = [x.strip() for x in a.basis.split(",")] if a.basis else list(THEORY[(variant, slow)])
    if len(names) != 3 or any(x not in FUNCS for x in names):
        sys.exit(f"Базис має складатися з трьох функцій із {list(FUNCS)}.")
    xs, ys = [], []
    for n in sizes:
        for t in data[f"t_op{slow}"][n]:
            xs.append(n)
            ys.append(t * 1e6)                         # мікросекунди
    xs, ys = np.array(xs, float), np.array(ys)
    X = np.column_stack([FUNCS[nm](xs) for nm in names])
    coef, *_ = np.linalg.lstsq(X, ys, rcond=None)
    pred = X @ coef
    r2 = 1 - ((ys - pred) ** 2).sum() / ((ys - ys.mean()) ** 2).sum()
    label = " + ".join(f"({c:.4g})·{nm}" for c, nm in zip(coef, names))
    result = (f"Варіант {variant}, операція {slow}\n"
              f"Базис: f1 = {names[0]}, f2 = {names[1]}, f3 = {names[2]}\n"
              f"c1 = {coef[0]:.6g}, c2 = {coef[1]:.6g}, c3 = {coef[2]:.6g}\n"
              f"T(n) [мкс] = {label}\n"
              f"R^2 = {r2:.5f}\n")
    print("\n" + result)
    with open(OUT_DIR / "regression.txt", "w", encoding="utf-8") as f:
        f.write(result)

    # ---- графік регресії: середнє і середньоквадратичне відхилення
    mu = np.array([mean_std([t * 1e6 for t in data[f"t_op{slow}"][n]])[0] for n in sizes])
    sd = np.array([mean_std([t * 1e6 for t in data[f"t_op{slow}"][n]])[1] for n in sizes])
    grid = np.linspace(sizes[0], sizes[-1], 400)
    curve = np.column_stack([FUNCS[nm](grid) for nm in names]) @ coef
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.errorbar(sizes, mu, yerr=sd, fmt="o", capsize=4, label="експеримент (середнє ± σ)")
    ax.plot(grid, curve, label=f"T(n), R² = {r2:.4f}")
    ax.set_xlabel("кількість студентів n")
    ax.set_ylabel("час операції, мкс")
    ax.set_title(f"Варіант {variant}, операція {slow}")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT_DIR / "fit.png", dpi=150)

    # ---- графік пам'яті
    mm = np.array([mean_std(data["mem_struct"][n])[0] / 1024 for n in sizes])
    ms = np.array([mean_std(data["mem_struct"][n])[1] / 1024 for n in sizes])
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.errorbar(sizes, mm, yerr=ms, fmt="o-", capsize=4)
    ax.set_xlabel("кількість студентів n")
    ax.set_ylabel("пам'ять структури, КіБ")
    ax.set_title(f"Варіант {variant}: пам'ять допоміжних структур")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "memory.png", dpi=150)
    print("Збережено: summary.csv, regression.txt, fit.png, memory.png")


if __name__ == "__main__":
    main()