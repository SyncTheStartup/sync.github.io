from flask import Flask, render_template, redirect, url_for, request, jsonify, session, g
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from datetime import datetime, timedelta, timezone
import sqlite3
import re
import logging
from dateutil.parser import parse as parse_date


app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

processed_events = set()

# Define the flow globally
flow = InstalledAppFlow.from_client_secrets_file(
    'client_secret_131606957380-u4ikuhues6u5s60dtueah3mgncn9u2u1.apps.googleusercontent.com.json', 
    scopes=['https://www.googleapis.com/auth/calendar.readonly'],
    redirect_uri='http://localhost:5000/login'  # Redirect to login after Google authorization
)

# Function to get Google Calendar URL
def get_google_calendar_url(credentials):
    service = build('calendar', 'v3', credentials=credentials)
    calendar_list = service.calendarList().list().execute()
    primary_calendar_id = next((item['id'] for item in calendar_list['items'] if item.get('primary')), None)
    return f"https://calendar.google.com/calendar/embed?src={primary_calendar_id}&mode=WEEK"

# Function to calculate weight based on event duration
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

@app.route('/')
def index():
    # Redirect to Google authentication
    authorization_url, state = flow.authorization_url(
        access_type='offline', prompt='select_account'
    )
    return redirect(authorization_url)

@app.route('/login')
def login():
    # Fetch the access code from the request parameters
    access_code = request.args.get('code')
    if not access_code:
        return redirect(url_for('index'))  # Redirect to index if no access code

    # Exchange the access code for credentials
    flow.fetch_token(code=access_code)

    # Redirect to onboarding
    return redirect(url_for('onboarding'))

@app.route('/onboarding', methods=['GET', 'POST'])
def onboarding():
    if request.method =='POST':
        return redirect(url_for('dashboard'))
    return render_template('onboarding.html')

@app.route('/dashboard')
def dashboard():
    # Get credentials
    credentials = flow.credentials
    
    # Get Google Calendar events for the current week
    service = build('calendar', 'v3', credentials=credentials)
    calendar_list = service.calendarList().list().execute()
    primary_calendar_id = next((item['id'] for item in calendar_list['items'] if item.get('primary')), None)
    
    # Get events for the current week
    start_of_week = datetime.now().date() - timedelta(days=datetime.now().weekday())
    end_of_week = start_of_week + timedelta(days=7)
    events_result = service.events().list(
        calendarId=primary_calendar_id,
        timeMin=start_of_week.isoformat() + 'T00:00:00Z',
        timeMax=end_of_week.isoformat() + 'T23:59:59Z',
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])

    # Calculate the average score for events in the current week
    average_score = calculate_average_score(events)

    # Get Google Calendar URL
    google_calendar_url = get_google_calendar_url(credentials)

    return render_template('dashboard.html', google_calendar_url=google_calendar_url, average_score=average_score)
@app.route('/batterypage') 
def batterypage():
    return render_template('batteryDisplay.html')
# Database connection functions
#def get_db():
 #   if 'db' not in g:
  #      g.db = sqlite3.connect('data.db')
   # return g.db

#@app.teardown_appcontext
#def close_db(exception):
   # db = g.pop('db', None)
   # if db is not None:
    #    db.close()


def categorize_event(event_name):
    categories = {
        "large_events": {
            "tags": ["Party", "Mixer", "Rager", "Banquet", "Networking Event", "Lecture", "Class", "Concert"],
            "value": 10
        },
        "mid_sized_events": {
            "tags": ["Lunch", "Dinner", "Movie", "Group meeting", "Section", "Seminar", "Study Group", "Networking", "Zoom"],
            "value": 7
        },
        "one_on_one_events": {
            "tags": ["Coffee", "Coffee Chat", "Date", "Hang out", "Meeting", "Meet", "Meet with", "Meet w/", "with"],
            "value": 4
        },
        "solo_events": {
            "tags": ["Read", "Workout", "Exercise", "Run", "Watch TV", "Study", "Nap", "Sleep"],
            "value": 2
        }
    }

    if not event_name:
        return 0

    event_name_lower = event_name.lower()

    for category in categories.values():
        for tag in category["tags"]:
            if re.search(r'\b' + re.escape(tag.lower()) + r'\b', event_name_lower):
                logging.debug(f"Matched '{tag}' in category with value {category['value']}")
                return category["value"]

    return 0

def categorize_event_into_12(event_name):
    categories = {
        "partyNum": ["Party", "Mixer", "Rager", "Celebration", "Festivity", "Bash", "Gathering", "Rave"],
        "networking": ["Networking Event", "Networking", "Professional Event", "Career Fair", "Industry Meetup"],
        "friend": ["Friend", "Dinner", "Hang out", "Meet with", "Meet w/", "with", "Catch up", "Chill", "Buddy"],
        "newPeople": ["Banquet", "Lecture", "Class", "Concert", "Conference", "Symposium", "Panel", "Expo"],
        "zoomVirtual": ["Zoom", "Virtual Meeting", "Online Meeting", "Webinar", "Remote Meeting", "Video Call"],
        "inPerson": ["In-Person Meeting", "Meeting", "Face-to-Face Meeting", "Appointment", "Interview"],
        "lectures": ["Lecture", "Class", "Course", "Presentation", "Talk", "Speech"],
        "seminarClasses": ["Seminar", "Section", "Study Group", "Workshop", "Training", "Session", "Discussion Group"],
        "homework": ["Homework", "Assignment", "Project", "Task", "Paper", "Report"],
        "extraCurriculars": ["Club", "Extracurricular Activity", "Society", "Organization", "Team", "Group Activity"],
        "workingOut": ["Workout", "Exercise", "Run", "Gym", "Training", "Fitness", "Jog", "Yoga"],
        "procrastinating": ["Procrastinate", "Slack off", "Waste time", "Delay", "Postpone", "Put off", "Dawdle"]
    }

    if not event_name:
        return "Uncategorized"

    event_name_lower = event_name.lower()

    for category_name, tags in categories.items():
        for tag in tags:
            if re.search(r'\b' + re.escape(tag.lower()) + r'\b', event_name_lower):
                logging.debug(f"Event '{event_name}' matched with tag '{tag}' in category '{category_name}'")
                return category_name

    return "Uncategorized"

@app.route('/initialbattery')
def initialBattery():
    sleepNeeded = 8
    sleepRegular = 7

    if (sleepNeeded - sleepRegular) <= 0:
        batteryLevel = 100
    elif (sleepNeeded - sleepRegular) == 1:
        batteryLevel = 95
    elif (sleepNeeded - sleepRegular) == 2:
        batteryLevel = 85
    elif (sleepNeeded - sleepRegular) == 3:
        batteryLevel = 75
    elif (sleepNeeded - sleepRegular) == 4:
        batteryLevel = 65
    else:
        batteryLevel = 60
    return jsonify(level=batteryLevel)
@app.route('/battery', methods=['POST'])
def battery():
    global processed_events  # Use the global set to keep track of processed events
    data = request.get_json()
    batteryLevel = data.get('battery', 100)

    credentials = flow.credentials  # Assuming credentials are available here
    service = build('calendar', 'v3', credentials=credentials)
    
    now = datetime.now(timezone.utc)  # Get current time as timezone-aware UTC
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    events_result = service.events().list(
        calendarId='primary', 
        timeMin=start_of_day.isoformat(), 
        timeMax=end_of_day.isoformat(), 
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])

    if not events:
        logging.debug('No events found for today.')
        return jsonify(level=batteryLevel)

    for event in events:
        event_id = event['id']
        if event_id in processed_events:
            continue  

        start = event['start'].get('dateTime')
        end = event['end'].get('dateTime')
        if start and end:
            start_time = parse_date(start)
            end_time = parse_date(end)
            
            if end_time <= now:  
                event_duration_hours = (end_time - start_time).seconds / 3600

                googleCalEvent = event.get('summary', '')

                event_value = categorize_event(googleCalEvent)
                category_name = categorize_event_into_12(googleCalEvent)

                logging.debug(f"Categorized event '{googleCalEvent}' into '{category_name}' with value {event_value}")

                category_map = {
                    "partyNum": 2,
                    "networking": 2,
                    "friend": 4,
                    "newPeople": 4,
                    "zoomVirtual": 5,
                    "inPerson": 1,
                    "lectures": 5,
                    "seminarClasses": 4,
                    "homework": 4,
                    "extraCurriculars": 2,
                    "workingOut": 2,
                    "procrastinating": 4
                }

                multipliers = {
                    1: 4,
                    2: 2,
                    3: 0,
                    4: -2,
                    5: -4
                }

                category_value = category_map.get(category_name, 0)
                multiplier = multipliers.get(category_value, 0)

                logging.debug(f"Category value: {category_value}, Multiplier: {multiplier}")

                eventDrain = multiplier * event_value * event_duration_hours

                logging.debug(f"Event drain: {eventDrain}")
                if(batteryLevel+eventDrain>100):
                    batteryLevel = 100
                else:
                    batteryLevel = max(0, batteryLevel + eventDrain)

                logging.debug(f"Updated battery level: {batteryLevel}")

                processed_events.add(event_id)

    return jsonify(level=batteryLevel)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)