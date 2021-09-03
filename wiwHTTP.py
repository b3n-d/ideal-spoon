import requests 
import json 
from datetime import datetime 
import argparse 

#args
helpMsg = 'This script executes limited WhenIWork functions through web requests'
parser = argparse.ArgumentParser(description=helpMsg)
parser.add_argument("-ls", "--lunchstart", help="begin lunch", action="store_true")
parser.add_argument("-le", "--lunchend", help="end lunch", action="store_true")
parser.add_argument("-ci", "--clockin", help="clock in to work", action="store_true")
parser.add_argument("-co", "--clockout", help="clock out of work", action="store_true")
parser.add_argument("-s", "--status", help="check status", action="store_true")
args = parser.parse_args()

# start the process by logging in with creds 
login_url = 'https://api.login.wheniwork.com/login'
with open('wiw_creds.json') as json_creds:
    creds = json.load(json_creds) 
login = requests.post(login_url, json=creds).text
login = json.loads(login)

# establish w_token, will be used for rest of script 
w_token = login['token']

# show_pending login to get ids for future use 
showpending_url = "https://api.wheniwork.com/2/login"
showpending_params = {'show_pending': 'true'}
showpending_headers = {'w-token': w_token} 
showpending = requests.get(showpending_url, params=showpending_params, headers=showpending_headers).text
showpending_json = json.loads(showpending)

# need to be str for header use 
account_id = str(showpending_json['users'][0]['account_id'])
w_user_id = str(showpending_json['users'][0]['id'])
user_id = str(showpending_json['login']['id'])


#def stateCheck(): # state check to see if I can clock in 
state_url = "https://api.wheniwork.com/2/punch/state"
state_params = {'deviceType': 'web'}
state_headers = {'w-token': w_token ,'w-userid': w_user_id }
state_check_text = requests.get(state_url, params=state_params, headers=state_headers).text
state_check = json.loads(state_check_text)
       
# header to be used for most requests 
wIdTokenIso_header = {'w-token': w_token ,'w-userid': w_user_id, 'w-date-format': 'iso'}

# collect state check info 
can_clock = state_check['canClockIn'] # bool 
can_lunch = state_check['canStartBreak'] # bool
can_endlunch = state_check['canEndBreak'] # bool
can_clockOut = state_check['canClockOut'] # bool
location_id = str(state_check['schedules']) # idk why 'schedules' in the state response is location_id for clockin
position_id = str(state_check['positions'])

# the following three vars aren't always included in state check output
if "shift" in state_check:
    global shift_id
    shift_id = str(state_check['shift'])
if "punchTimeID" in state_check:
    global time_id
    time_id = str(state_check['punchTimeId']) 
if "break" in state_check:
    global lunch_id
    lunch_id = str(state_check['break']['id'])

def clockIn(): 
    if can_clock: 
        clockin_url = "https://api.wheniwork.com/2/times/clockin"
        clockin_dict = {
            "id": w_user_id,
            "notes": "", 
            "location_id" : location_id,
            "position_id" : position_id,
            "shift_id" : shift_id 
        }
        json_dict = json.dumps(clockin_dict)
        clockin = requests.post(clockin_url, headers=wIdTokenIso_header, data=json_dict).text
        clockin = json.loads(clockin)
        if "time" in clockin: 
            timestamp = clockin['time']['start_time']
            print('Clocked in at ' +  timestamp)
        else: 
            print('Could not clock in')
    else:
        print('Unable to clock in')

def clockOut(): 
    if can_clockOut:
        clockOut_url = "https://api.wheniwork.com/2/times/clockout"
        clockOut_dict = {
            "id": w_user_id,
            "notes": "" 
        }
        clockOut_json = json.dumps(clockOut_dict)
        clockOut = requests.post(clockOut_url, headers=wIdTokenIso_header, data=clockOut_json).text
        clockOut = json.loads(clockOut) 
        if "time" in clockOut: 
            timestamp = clockOut['time']['end_time']
            print('Clocked out at ' +  timestamp)
        else: 
            print('Could not clock in')

    else: 
        print('Unable to clock out')

def takeLunch(): 
    if can_lunch:  
        lunch_url = "https://api.wheniwork.com/v3/shift-breaks"
        time_id = str(state_check['punchTimeId']) 
        lunch_start = datetime.utcnow().isoformat()[:-3]+'Z' # fuckery to create a JS ISO timestamp
        lunch_dict = {
            "start": lunch_start,
            "timeId": time_id
            }
        lunch_json = json.dumps(lunch_dict)
        lunch_start = requests.post(lunch_url, headers=wIdTokenIso_header, data=lunch_json).text 
        if "data" in lunch_start:
            timestamp = lunch_start['data']['start']
            print('Lunch started at ' + timestamp)
        else:
            print('Could not start lunch')
    else:
        print('Unable to start lunch')

def endLunch(): 
    if can_endlunch:
        lunch_id = str(state_check['break']['id'])
        lunch_url = "https://api.wheniwork.com/v3/shift-breaks/" + lunch_id # lunch end url must have lunch id 
        lunch_end = datetime.utcnow().isoformat()[:-3]+'Z' 
        lunch_dict = {
            "id": lunch_id,
            "end": lunch_end
            }
        lunch_json = json.dumps(lunch_dict) 
        lunch_end = requests.patch(lunch_url, headers=wIdTokenIso_header, data=lunch_json).text 
        lunch_end = json.loads(lunch_end) 
        if "data" in lunch_end:
            timestamp = lunch_end['data']['end']
            print('Lunch ended at ' + timestamp)
        else:
            print('Could not end lunch')
    else:
        print('Unable to end lunch')

if args.clockin:
    clockIn()
elif args.clockout:
    clockOut()
elif args.lunchstart:
    takeLunch()
elif args.lunchend:
    endLunch()
elif args.status:
    print(state_check)
