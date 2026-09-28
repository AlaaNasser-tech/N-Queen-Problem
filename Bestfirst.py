import random
import heapq

def heuristic(state):
    conflicts = 0
    n = len(state)

    for i in range(n):
        for j in range(i + 1, n):
            if state[i] == state[j]:
                conflicts += 1
            elif abs(state[i] - state[j]) == abs(i - j):
                conflicts += 1

    return conflicts


def generate_neighbors(state):
    neighbors = []
    n = len(state)

    for col in range(n):
        current_row = state[col]

        for row in range(1, n + 1):
            if row != current_row:
                new_state = state.copy()
                new_state[col] = row
                neighbors.append(new_state)

    return neighbors

def random_state(n):
    return [random.randint(1, n) for _ in range(n)]


def best_first_search(n):

    start = random_state(n)

    pq = []
    heapq.heappush(pq, (heuristic(start), start))

    visited = set()

    while pq:
        h, current = heapq.heappop(pq)

        state_key = tuple(current)
        if state_key in visited:
            continue
        visited.add(state_key)

        if h == 0:
            return current

        for nb in generate_neighbors(current):
            heapq.heappush(pq, (heuristic(nb), nb))

    return None


