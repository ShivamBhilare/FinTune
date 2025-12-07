import difflib

def are_similar(name1, name2):
    n1 = name1.lower()
    n2 = name2.lower()
    
    # Simple clean: remove non-alphanumeric (except spaces)
    n1_clean = ''.join(c for c in n1 if c.isalnum() or c.isspace())
    n2_clean = ''.join(c for c in n2 if c.isalnum() or c.isspace())
    
    if n1_clean == n2_clean and n1_clean != "":
        return True

    ratio = difflib.SequenceMatcher(None, n1, n2).ratio()
    return ratio > 0.80

transactions = [
    {'vendor': 'D*mart', 'amount': 500},
    {'vendor': 'Dmart', 'amount': 500},
    {'vendor': 'Walmart', 'amount': 500},
    {'vendor': 'Netflix', 'amount': 199},
    {'vendor': 'Netflix.com', 'amount': 199},
    {'vendor': 'Uber', 'amount': 300},
    {'vendor': 'Uber Rides', 'amount': 300},
]

grouped = []
processed_indices = set()

for i in range(len(transactions)):
    if i in processed_indices:
        continue
        
    current = transactions[i]
    group = [current]
    processed_indices.add(i)
    
    for j in range(i + 1, len(transactions)):
        if j in processed_indices:
            continue
            
        other = transactions[j]
        
        if current['amount'] == other['amount']:
            if are_similar(current['vendor'], other['vendor']):
                group.append(other)
                processed_indices.add(j)
                
    if len(group) > 1:
        print(f"Found recurring group: {[t['vendor'] for t in group]} - Amount: {current['amount']}")
    else:
        print(f"Single item: {current['vendor']}")
