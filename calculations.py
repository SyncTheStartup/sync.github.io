from datetime import datetime, timedelta

def calculate_weight(duration):
    if duration >= timedelta(hours=2):
        return 40
    elif timedelta(hours=1) <= duration < timedelta(hours=2):
        return 25
    elif duration < timedelta(hours=1):
        return 10
    
# Function to calculate the average score for all events
def calculate_average_score(events):
    total_score = 0
    count = 0
    for event in events:
        start_time = event.get('start', {}).get('dateTime')
        end_time = event.get('end', {}).get('dateTime')
        if start_time and end_time:
            total_score += calculate_weight(datetime.fromisoformat(end_time) - datetime.fromisoformat(start_time))
            count += 1
    return total_score / count if count > 0 else 0