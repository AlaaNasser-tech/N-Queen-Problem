import random

class NQueenHC:
    def __init__(self, n):
        self.n = n
    
    def randomState(self):
        return [random.randint(0, self.n-1) for _ in range(self.n)]
    
    def conflicts(self, state):
        count = 0

        for i in range(self.n):
            for j in range(i + 1, self.n):

                if state[i] == state[j]:
                    count += 1

                elif abs(state[i] - state[j]) == abs(i - j):
                    count += 1

        return count
    
    def nextMoves(self ,state):
        moves = []

        for col in range(self.n):
            for row in range(self.n):
                if state[col] != row:
                    newState = state.copy()
                    newState[col] = row
                    moves.append(newState)
        return moves
    
    def bestMove(self, state):
        moves = self.nextMoves(state)
        best = state
        bestConf = self.conflicts(state)

        for move in moves:
            c = self.conflicts(move)
            if c < bestConf:
                best = move
                bestConf = c
        
        return best, bestConf

    def HillClimbing(self):
        curr =  self.randomState()

        while True:
            currConf = self.conflicts(curr)

            if currConf == 0:
                return curr
            
            move , moveConf = self.bestMove(curr)

            if moveConf  >= currConf:
                return None
            
            curr = move

    def solve(self, maxAttempts = 100):
        for _ in range(maxAttempts):
            result = self.HillClimbing()

            if result is not None:
                return result
        
        return None
    


