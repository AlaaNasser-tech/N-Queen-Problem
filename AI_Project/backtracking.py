def solve(n: int) -> list[int]:

    result = [-1] * n

    def safe(col, row):
        for c in range(col):
            r = result[c]

            if r == row:
                return False

            if abs(r - row) == abs(c - col):
                return False
            
        return True
    
    def backtrack(col):
        if col == n:
            return True
        
        for row in range(n):
            if safe(col, row):
                result[col] = row

                if backtrack(col + 1):
                    return True
                
                result[col] = -1

        return False
    
    if n <= 0:
        return []

    if backtrack(0):
        return result

    return []

