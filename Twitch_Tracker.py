#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright © 2015 Warren Turner
# Licensed under the LGPL version 2.1 or later
# Tundra's Tracker for Twitch

import urllib2
import json
import psycopg2
import sys
import ConfigParser
import re
import logging

## Congfig File ##
configParser = ConfigParser.RawConfigParser()   
configFilePath = r'/Users/wturner/Documents/git/tundras_tracker/twitch_tracker.conf'
configParser.read(configFilePath)

## Set Logging ##
log_file = configParser.get('logging', 'log_file')
log_level = configParser.get('logging', 'log_level')
logging.basicConfig(filename=log_file,level=log_level)
logging.warning('Creating log file')

## Connect to the DB
db_name = configParser.get('database', 'db_name')
db_user = configParser.get('database', 'db_user')
db_server = configParser.get('database', 'db_server')
db_password = configParser.get('database', 'db_password')

con = None
con = psycopg2.connect("dbname='%s' user='%s' host='%s' password='%s'" % (db_name, db_user, db_server, db_password))
cur = con.cursor()


### Check if all Necessary Tables Exist ###

try:
    cur.execute("CREATE TABLE donations(Username varchar(30), Subscriber_Status varchar(30), Amount REAL, Message varchar, Transaction_Id varchar(100), Date date DEFAULT CURRENT_DATE NOT NULL, Time time DEFAULT CURRENT_TIME NOT NULL)")
    con.commit()
except:
    ## Rollback if create table command fails ##
    print "Donations Table Already Exists"
    con.rollback()

try:
    cur.execute("CREATE TABLE subscribers(Username varchar(30), Date_Subscribed date DEFAULT CURRENT_DATE NOT NULL)")
    con.commit()
except:
    ## Rollback if create table command fails ##
    print "Subscribers Table Already Exists"
    con.rollback()

try:
    cur.execute("CREATE TABLE total_donations(Username varchar(30), Subscriber_Status varchar(30), Amount INT)")
    con.commit()
except:
    ## Rollback if create table command fails ##
    print "Total Donations Table Already Exists"
    con.rollback()






### Payment Processing ###

# Get Credentials From Config File #
streamtip_client_id = configParser.get('streamtip', 'streamtip_client_id')
streamtip_access_token = configParser.get('streamtip', 'streamtip_access_token')

# Pull Information from StreamTip #
offset = 0
offset = str(offset)
streamtip_api_url = 'https://streamtip.com/api/tips?direction=desc&sort_by=date&limit=100&offset=' + offset + '&client_id=' + streamtip_client_id + '&access_token=' + streamtip_access_token

# Convert to JSON so we can read it #
streamtip_donations = json.load(urllib2.urlopen(streamtip_api_url))

# print json.dumps(streamtip_donations, sort_keys=True, indent=4)

####### Full Load Of All Donations Ever #######
# if initial_load:

while streamtip_donations['_count'] > 0:
    offset = str(offset)
    streamtip_api_url = 'https://streamtip.com/api/tips?direction=desc&sort_by=date&limit=100&offset=' + offset + '&client_id=' + streamtip_client_id + '&access_token=' + streamtip_access_token
    streamtip_donations = json.load(urllib2.urlopen(streamtip_api_url)) 
    for item in streamtip_donations['tips']:
        # Parse the date string that streamtip gives you #
        date = item['date'][0:10]
        time = item['date'][12:16]
        note = item['note']
        if note == None:
            note = 'No Message Left :('
        note = note.encode('utf-8')
        note = str(note)
        note = note.translate(None, '\'\\')
        # Replace none ASCI II Characters with a [?]
        note = re.sub(r'[^\x00-\x7F]+','[?]', note)
        try:
            cur.execute("INSERT INTO donations (Username, Amount, Message, Transaction_Id, Date, Time) VALUES ('%s',%f,'%s','%s','%s','%s')" % (item['username'], float(item['amount']), note, item['transactionId'], date, time))
        except UnicodeDecodeError:
            logging.exception('\n\nUnicode Exception (This transaction was loaded into the DB but the note was removed):\n')
            error_info = '\n\nTransaction Info\nUsername: ' + item['username'] + '\nAmount: ' + item['amount'] + '\nNote: ' + item['note'] + '\nTransation_Id: ' + item['transactionId'] + '\nDate: ' + date + '\nTime: ' + time + '\n'
            logging.error(error_info)
            note = 'Sorry something about the message caused an error so it couldnt be saved :(  But Carci still loves you!'
            cur.execute("INSERT INTO donations (Username, Amount, Message, Transaction_Id, Date, Time) VALUES ('%s',%f,'%s','%s','%s','%s')" % (item['username'], float(item['amount']), note, item['transactionId'], date, time))
        except:
            # Need to write to a log file here
            logging.exception('\n\nUnknown Exception (This transaction was not loaded into the DB):\n')
            error_info = '\n\nTransaction Info\nUsername: ' + item['username'] + '\nAmount: ' + item['amount'] + '\nNote: ' + item['note'] + '\nTransation_Id: ' + item['transactionId'] + '\nDate: ' + date + '\nTime: ' + time + '\n'
            logging.error(error_info)
    offset = int(offset)
    offset = offset + 100

## Pushes Changes to DB ##
con.commit()




####### Incremental Update of Donations (This can only get a maximum of 100 donations) #######

offset = 0
offset = str(offset)
streamtip_api_url = 'https://streamtip.com/api/tips?direction=desc&sort_by=date&limit=100&offset=' + offset + '&client_id=' + streamtip_client_id + '&access_token=' + streamtip_access_token
streamtip_donations = json.load(urllib2.urlopen(streamtip_api_url))

# Find the transaction ID of the last donation already entered into the DB #
cur.execute("SELECT Transaction_Id FROM donations ORDER BY date desc, time desc limit 1")
rows = cur.fetchall()
try:
    old_record = rows[0][0]
except IndexError:
    print "There are no existing records"
    old_record = ''

## Pull Payment Info from StreamTip and insert new records ##
for item in streamtip_donations['tips']:
    if item['transactionId'] == old_record:
        print 'Donations Are Up To Date'
        break     
# Parse the date string that streamtip gives you #
    date = item['date'][0:10]
    time = item['date'][12:16]
    note = item['note']
    if note == None:
        note = 'No Message Left :('
    note = note.encode('utf-8')
    note = str(note)
    note = note.translate(None, '\'\\')
    # Replace none ASCI II Characters with a [?]
    note = re.sub(r'[^\x00-\x7F]+','[?]', note)
    try:
        cur.execute("INSERT INTO donations (Username, Amount, Message, Transaction_Id, Date, Time) VALUES ('%s',%f,'%s','%s','%s','%s')" % (item['username'], float(item['amount']), note, item['transactionId'], date, time))
    except UnicodeDecodeError:
        logging.exception('\n\nUnicode Exception (This transaction was loaded into the DB but the note was removed):\n')
        error_info = '\n\nTransaction Info\nUsername: ' + item['username'] + '\nAmount: ' + item['amount'] + '\nNote: ' + item['note'] + '\nTransation_Id: ' + item['transactionId'] + '\nDate: ' + date + '\nTime: ' + time + '\n'
        logging.error(error_info)
        note = 'Sorry something about the message caused an error so it couldnt be saved :(  But Carci still loves you!'
        cur.execute("INSERT INTO donations (Username, Amount, Message, Transaction_Id, Date, Time) VALUES ('%s',%f,'%s','%s','%s','%s')" % (item['username'], float(item['amount']), note, item['transactionId'], date, time))
    except:
        # Need to write to a log file here
        logging.exception('\n\nUnknown Exception (This transaction was not loaded into the DB):\n')
        error_info = '\n\nTransaction Info\nUsername: ' + item['username'] + '\nAmount: ' + item['amount'] + '\nNote: ' + item['note'] + '\nTransation_Id: ' + item['transactionId'] + '\nDate: ' + date + '\nTime: ' + time + '\n'
        logging.error(error_info)

## Pushes Changes to DB ##
con.commit()



### Twitch ###

# Get OAuth Token and Twitch Username from the Config File
twitch_username = configParser.get('twitch', 'twitch_username')
twitch_oauth_token = configParser.get('twitch', 'twitch_oauth_token')


## Followers (This is not used in the tracker currently) ##
twitch_followers_api_url = 'https://api.twitch.tv/kraken/channels/' + twitch_username + '/follows?limit=10&offset=20550'
twitch_followers = json.load(urllib2.urlopen(twitch_followers_api_url))
print json.dumps(twitch_followers, sort_keys=True, indent=4) 


## Subscribers ##
twitch_subscribers_api_url = 'https://api.twitch.tv/kraken/channels/' + twitch_username + '/subscriptions?limit=10&offset=0&oauth_token=' + twitch_oauth_token
twitch_subscribers = json.load(urllib2.urlopen(twitch_subscribers_api_url))
print json.dumps(twitch_subscribers, sort_keys=True, indent=4) 






# ## PART ASA ADDED ##
# twitch_url = "https://api.twitch.tv/kraken/"+twitch_user

# send_headers = {
#    "Accept": "application/vnd.twitchtv.v2+json",
#    "Authorization": "OAuth "+twitch_access_token
# }

# request_data = urllib2.Request(url, None, send_headers)
# twitch_data = json.load(urllib2.urlopen(request_data))
# print json.dumps(twitch_data, sort_keys=True, indent=4) 

# ## END PART ASA ADDED ##








if con:
    con.close()