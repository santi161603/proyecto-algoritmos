from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List


Sorter = Callable[[List[int]], List[int]]


# -----------------------------------------------------------------------------
# 1) TimSort (implementación manual simplificada)
# -----------------------------------------------------------------------------
def timsort(arr: List[int]) -> List[int]:
    a = arr[:]
    n = len(a)
    if n < 2:
        return a

    min_run = _calc_min_run(n)

    # 1) Ordenar pequeños runs con binary insertion sort local
    start = 0
    while start < n:
        end = start + min_run
        if end > n:
            end = n
        _binary_insertion_sort_range(a, start, end)
        start = end

    # 2) Mezclar runs duplicando tamaño
    size = min_run
    while size < n:
        left = 0
        while left < n:
            mid = left + size
            right = left + (2 * size)
            if mid > n:
                mid = n
            if right > n:
                right = n

            if mid < right:
                _merge_runs(a, left, mid, right)

            left = right
        size *= 2

    return a


def _calc_min_run(n: int) -> int:
    r = 0
    while n >= 64:
        r |= n & 1
        n >>= 1
    return n + r


def _binary_insertion_sort_range(a: List[int], lo: int, hi: int) -> None:
    i = lo + 1
    while i < hi:
        x = a[i]
        left = lo
        right = i
        while left < right:
            mid = (left + right) // 2
            if a[mid] <= x:
                left = mid + 1
            else:
                right = mid

        j = i
        while j > left:
            a[j] = a[j - 1]
            j -= 1
        a[left] = x
        i += 1


def _merge_runs(a: List[int], lo: int, mid: int, hi: int) -> None:
    left = a[lo:mid]
    right = a[mid:hi]

    i = 0
    j = 0
    k = lo

    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            a[k] = left[i]
            i += 1
        else:
            a[k] = right[j]
            j += 1
        k += 1

    while i < len(left):
        a[k] = left[i]
        i += 1
        k += 1

    while j < len(right):
        a[k] = right[j]
        j += 1
        k += 1


# -----------------------------------------------------------------------------
# 2) Comb Sort
# -----------------------------------------------------------------------------
def comb_sort(arr: List[int]) -> List[int]:
    a = arr[:]
    n = len(a)
    gap = n
    shrink = 1.3
    swapped = True

    while gap > 1 or swapped:
        gap = int(gap / shrink)
        if gap < 1:
            gap = 1

        swapped = False
        for i in range(0, n - gap):
            j = i + gap
            if a[i] > a[j]:
                a[i], a[j] = a[j], a[i]
                swapped = True

    return a


# -----------------------------------------------------------------------------
# 3) Selection Sort
# -----------------------------------------------------------------------------
def selection_sort(arr: List[int]) -> List[int]:
    a = arr[:]
    n = len(a)
    for i in range(n):
        min_idx = i
        for j in range(i + 1, n):
            if a[j] < a[min_idx]:
                min_idx = j
        if min_idx != i:
            a[i], a[min_idx] = a[min_idx], a[i]
    return a


# -----------------------------------------------------------------------------
# 4) Tree Sort
# -----------------------------------------------------------------------------
class _Node:
    __slots__ = ("value", "left", "right", "count")

    def __init__(self, value: int):
        self.value = value
        self.left = None
        self.right = None
        self.count = 1


def _tree_insert(root: _Node | None, value: int) -> _Node:
    if root is None:
        return _Node(value)
    if value < root.value:
        root.left = _tree_insert(root.left, value)
    elif value > root.value:
        root.right = _tree_insert(root.right, value)
    else:
        root.count += 1
    return root


def _tree_inorder(root: _Node | None, out: List[int]) -> None:
    if root is None:
        return
    _tree_inorder(root.left, out)
    out.extend([root.value] * root.count)
    _tree_inorder(root.right, out)


def tree_sort(arr: List[int]) -> List[int]:
    root = None
    for x in arr:
        root = _tree_insert(root, x)
    out: List[int] = []
    _tree_inorder(root, out)
    return out


# -----------------------------------------------------------------------------
# 5) Pigeonhole Sort (versión segura para rangos grandes con compresión)
# -----------------------------------------------------------------------------
def pigeonhole_sort(arr: List[int]) -> List[int]:
    if not arr:
        return []

    unique_map = {}
    for x in arr:
        unique_map[x] = True
    unique_sorted = quicksort(list(unique_map.keys()))
    rank = {v: i for i, v in enumerate(unique_sorted)}
    holes = [0] * len(unique_sorted)

    for x in arr:
        holes[rank[x]] += 1

    out: List[int] = []
    for i, c in enumerate(holes):
        if c:
            out.extend([unique_sorted[i]] * c)
    return out


# -----------------------------------------------------------------------------
# 6) Bucket Sort (integers)
# -----------------------------------------------------------------------------
def bucket_sort(arr: List[int]) -> List[int]:
    if not arr:
        return []

    a_min, a_max = min(arr), max(arr)
    if a_min == a_max:
        return arr[:]

    n = len(arr)
    bucket_count = int(n ** 0.5) + 1
    buckets: List[List[int]] = [[] for _ in range(bucket_count)]

    span = (a_max - a_min + 1)
    for x in arr:
        idx = int((x - a_min) * (bucket_count - 1) / (span - 1))
        buckets[idx].append(x)

    out: List[int] = []
    for b in buckets:
        if b:
            out.extend(binary_insertion_sort(b))
    return out


# -----------------------------------------------------------------------------
# 7) QuickSort
# -----------------------------------------------------------------------------
def quicksort(arr: List[int]) -> List[int]:
    a = arr[:]

    def _qs(lo: int, hi: int) -> None:
        if lo >= hi:
            return
        p = _partition(lo, hi)
        _qs(lo, p - 1)
        _qs(p + 1, hi)

    def _partition(lo: int, hi: int) -> int:
        pivot = a[hi]
        i = lo
        for j in range(lo, hi):
            if a[j] <= pivot:
                a[i], a[j] = a[j], a[i]
                i += 1
        a[i], a[hi] = a[hi], a[i]
        return i

    _qs(0, len(a) - 1)
    return a


# -----------------------------------------------------------------------------
# 8) HeapSort
# -----------------------------------------------------------------------------
def heap_sort(arr: List[int]) -> List[int]:
    a = arr[:]
    n = len(a)

    def heapify(size: int, i: int) -> None:
        largest = i
        l = 2 * i + 1
        r = 2 * i + 2

        if l < size and a[l] > a[largest]:
            largest = l
        if r < size and a[r] > a[largest]:
            largest = r

        if largest != i:
            a[i], a[largest] = a[largest], a[i]
            heapify(size, largest)

    for i in range(n // 2 - 1, -1, -1):
        heapify(n, i)

    for i in range(n - 1, 0, -1):
        a[i], a[0] = a[0], a[i]
        heapify(i, 0)

    return a


# -----------------------------------------------------------------------------
# 9) Bitonic Sort (padding al siguiente 2^k)
# -----------------------------------------------------------------------------
def bitonic_sort(arr: List[int]) -> List[int]:
    if not arr:
        return []

    n = len(arr)
    p2 = 1
    while p2 < n:
        p2 <<= 1

    sentinel = max(arr) + 1
    a = arr[:] + [sentinel] * (p2 - n)

    def compare_and_swap(i: int, j: int, ascending: bool) -> None:
        if (ascending and a[i] > a[j]) or ((not ascending) and a[i] < a[j]):
            a[i], a[j] = a[j], a[i]

    def bitonic_merge(lo: int, cnt: int, ascending: bool) -> None:
        if cnt > 1:
            k = cnt // 2
            for i in range(lo, lo + k):
                compare_and_swap(i, i + k, ascending)
            bitonic_merge(lo, k, ascending)
            bitonic_merge(lo + k, k, ascending)

    def bitonic_rec(lo: int, cnt: int, ascending: bool) -> None:
        if cnt > 1:
            k = cnt // 2
            bitonic_rec(lo, k, True)
            bitonic_rec(lo + k, k, False)
            bitonic_merge(lo, cnt, ascending)

    bitonic_rec(0, len(a), True)
    return [x for x in a if x != sentinel][:n]


# -----------------------------------------------------------------------------
# 10) Gnome Sort
# -----------------------------------------------------------------------------
def gnome_sort(arr: List[int]) -> List[int]:
    a = arr[:]
    i = 0
    n = len(a)
    while i < n:
        if i == 0 or a[i] >= a[i - 1]:
            i += 1
        else:
            a[i], a[i - 1] = a[i - 1], a[i]
            i -= 1
    return a


# -----------------------------------------------------------------------------
# 11) Binary Insertion Sort
# -----------------------------------------------------------------------------
def binary_insertion_sort(arr: List[int]) -> List[int]:
    a = arr[:]

    def binary_search(value: int, hi: int) -> int:
        lo = 0
        while lo < hi:
            mid = (lo + hi) // 2
            if a[mid] <= value:
                lo = mid + 1
            else:
                hi = mid
        return lo

    for i in range(1, len(a)):
        x = a[i]
        pos = binary_search(x, i)
        j = i
        while j > pos:
            a[j] = a[j - 1]
            j -= 1
        a[pos] = x

    return a


# -----------------------------------------------------------------------------
# 12) Radix Sort (base 10, no negativos)
# -----------------------------------------------------------------------------
def radix_sort(arr: List[int]) -> List[int]:
    if not arr:
        return []

    if min(arr) < 0:
        shift = -min(arr)
        shifted = [x + shift for x in arr]
        sorted_shifted = _radix_non_negative(shifted)
        return [x - shift for x in sorted_shifted]

    return _radix_non_negative(arr[:])


def _radix_non_negative(a: List[int]) -> List[int]:
    exp = 1
    m = max(a)
    while m // exp > 0:
        _counting_by_digit(a, exp)
        exp *= 10
    return a


def _counting_by_digit(a: List[int], exp: int) -> None:
    n = len(a)
    output = [0] * n
    count = [0] * 10

    for i in range(n):
        idx = (a[i] // exp) % 10
        count[idx] += 1

    for i in range(1, 10):
        count[i] += count[i - 1]

    for i in range(n - 1, -1, -1):
        idx = (a[i] // exp) % 10
        output[count[idx] - 1] = a[i]
        count[idx] -= 1

    for i in range(n):
        a[i] = output[i]


@dataclass(frozen=True)
class MetodoOrdenamiento:
    nombre: str
    complejidad: str
    funcion: Sorter


METODOS_ORDENAMIENTO = [
    MetodoOrdenamiento("TimSort", "O(n log n)", timsort),
    MetodoOrdenamiento("Comb Sort", "O(n^2)", comb_sort),
    MetodoOrdenamiento("Selection Sort", "O(n^2)", selection_sort),
    MetodoOrdenamiento("Tree Sort", "O(n log n) promedio", tree_sort),
    MetodoOrdenamiento("Pigeonhole Sort", "O(n + k)", pigeonhole_sort),
    MetodoOrdenamiento("Bucket Sort", "O(n + k)", bucket_sort),
    MetodoOrdenamiento("QuickSort", "O(n log n) promedio", quicksort),
    MetodoOrdenamiento("HeapSort", "O(n log n)", heap_sort),
    MetodoOrdenamiento("Bitonic Sort", "O(n log^2 n)", bitonic_sort),
    MetodoOrdenamiento("Gnome Sort", "O(n^2)", gnome_sort),
    MetodoOrdenamiento("Binary Insertion Sort", "O(n^2)", binary_insertion_sort),
    MetodoOrdenamiento("RadixSort", "O(d*(n+b))", radix_sort),
]
