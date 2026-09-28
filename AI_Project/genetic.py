import random

class NQueenGA:
   
    def __init__(self, n):
        self.n = n
        self.population_size = 60
        self.generations = 500
        self.mutation_rate = 0.2
        self.tournament_size = 3
        random.seed(42)

    def create_individual(self):
        return random.sample(range(self.n), self.n)

    def count_conflicts(self, board):
        conflicts = 0
        for c1 in range(self.n):
            for c2 in range(c1 + 1, self.n):
                r1, r2 = board[c1], board[c2]
                if abs(r1 - r2) == abs(c1 - c2):
                    conflicts += 1
        return conflicts

    def fitness(self, board):
        max_pairs = self.n * (self.n - 1) // 2
        return max_pairs - self.count_conflicts(board)

    def select_parent(self, population):
        candidates = random.sample(population, self.tournament_size)
        return max(candidates, key=self.fitness)

    def crossover(self, parent1, parent2):
        left, right = sorted(random.sample(range(self.n), 2))
        child = [-1] * self.n

        child[left:right + 1] = parent1[left:right + 1]

        remaining = [gene for gene in parent2 if gene not in child]
        idx = 0
        for i in range(self.n):
            if child[i] == -1:
                child[i] = remaining[idx]
                idx += 1

        return child

    def mutate(self, board):
        if random.random() < self.mutation_rate:
            i, j = random.sample(range(self.n), 2)
            board[i], board[j] = board[j], board[i]

    def solve(self):
        if self.n <= 0:
            return []
        if self.n == 1:
            return [1]
        if self.n in (2, 3):
            return []

        population = [self.create_individual() for _ in range(self.population_size)]

        for _ in range(self.generations):
            best = max(population, key=self.fitness)

            if self.count_conflicts(best) == 0:
                return [row + 1 for row in best]

            new_population = [best[:]]

            while len(new_population) < self.population_size:
                parent1 = self.select_parent(population)
                parent2 = self.select_parent(population)

                child1 = self.crossover(parent1, parent2)
                child2 = self.crossover(parent2, parent1)

                self.mutate(child1)
                self.mutate(child2)

                new_population.append(child1)
                if len(new_population) < self.population_size:
                    new_population.append(child2)

            population = new_population

        best = max(population, key=self.fitness)
        if self.count_conflicts(best) == 0:
            return [row + 1 for row in best]

        return []


def solve(n):
    solver = NQueenGA(n)
    return solver.solve()

