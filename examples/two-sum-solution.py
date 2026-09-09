"""Reference solution for the two-sum example.

Reads n, target, then n integers. Prints the indices of the two
numbers that add up to target, space-separated.
"""
import sys


def two_sum(nums, target):
    seen = {}
    for i, x in enumerate(nums):
        if target - x in seen:
            return seen[target - x], i
        seen[x] = i
    return None


def main():
    data = sys.stdin.read().split()
    n, target = int(data[0]), int(data[1])
    nums = [int(v) for v in data[2:2 + n]]
    i, j = two_sum(nums, target)
    print(i, j)


if __name__ == "__main__":
    main()
