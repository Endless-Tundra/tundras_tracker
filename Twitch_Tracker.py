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

## Congfig File ##
configParser = ConfigParser.RawConfigParser()   
configFilePath = r'/twitch_tracker.conf'
configParser.read(configFilePath)

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
    cur.execute("CREATE TABLE donations(Username varchar(30), Subscriber_Status varchar(30), Amount REAL, Transaction_Id varchar(100), Date date DEFAULT CURRENT_DATE NOT NULL, Time time DEFAULT CURRENT_TIME NOT NULL)")
except:
    ## Rollback if create table command fails ##
    print "Donations Table Already Exists"
    con.rollback()

try:
    cur.execute("CREATE TABLE subscribers(Username varchar(30), Date_Subscribed date DEFAULT CURRENT_DATE NOT NULL)")
except:
    ## Rollback if create table command fails ##
    print "Subscribers Table Already Exists"
    con.rollback()

try:
    cur.execute("CREATE TABLE total_donations(Username varchar(30), Subscriber_Status varchar(30), Amount INT)")
except:
    ## Rollback if create table command fails ##
    print "Total Donations Table Already Exists"
    con.rollback()

con.commit()




### Payment Processing ###

# Get Credentials From Config File #
streamtip_client_id = configParser.get('streamtip', 'streamtip_client_id')
streamtip_access_token = configParser.get('streamtip', 'streamtip_access_token')

# Pull Information from StreamTip #
streamtip_api_url = 'https://streamtip.com/api/tips?direction=desc&sort_by=date&limit=5&offset=0&client_id=' + streamtip_client_id + '&access_token=' + streamtip_access_token

# Convert to JSON so we can read it #
streamtip_donations = json.load(urllib2.urlopen(streamtip_api_url))

print json.dumps(streamtip_donations, sort_keys=True, indent=4)

####### Full Load Of All Donations Ever #######
if initial_load:

    offset = 0

    while streamtip_donations_full['_count'] > 0:
        offset = str(offset)
        streamtip_api_url_full = 'https://streamtip.com/api/tips?direction=desc&sort_by=date&limit=100&offset=' + offset + '&client_id=' + streamtip_client_id + '&access_token=' + streamtip_access_token
        streamtip_donations_full = json.load(urllib2.urlopen(streamtip_api_url_full)) 
        for item in streamtip_donations_full['tips']:
                # Parse the date string that streamtip gives you #
                date = item['date'][0:10]
                time = item['date'][12:16]
                cur.execute("INSERT INTO donations (Username, Amount, Transaction_Id, Date, Time) VALUES ('%s',%f,'%s','%s','%s')" % (item['username'], float(item['amount']), item['transactionId'], date, time))
        offset = int(offset)
        offset = offset + 100
    con.commit()




####### Incremental Update of Donations #######

# Find the transaction ID of the last donation already entered into the DB #
cur.execute("SELECT Transaction_Id FROM donations ORDER BY date desc, time desc limit 1")
rows = cur.fetchall()
old_record = rows[0][0]

## Pull Payment Info from StreamTip and insert new records ##
for item in streamtip_donations['tips']:
    if item['transactionId'] == old_record:
        print 'Donations Are Up To Date'
        break
    # Parse the date string that streamtip gives you #
    date = item['date'][0:10]
    time = item['date'][12:16]
    cur.execute("INSERT INTO donations (Username, Amount, Transaction_Id, Date, Time) VALUES ('%s',%f,'%s','%s','%s')" % (item['username'], float(item['amount']), item['transactionId'], date, time))

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






## PART ASA ADDED ##
twitch_url = "https://api.twitch.tv/kraken/"+twitch_user

send_headers = {
   "Accept": "application/vnd.twitchtv.v2+json",
   "Authorization": "OAuth "+twitch_access_token
}

request_data = urllib2.Request(url, None, send_headers)
twitch_data = json.load(urllib2.urlopen(request_data))
print json.dumps(twitch_data, sort_keys=True, indent=4) 

## END PART ASA ADDED ##








if con:
    con.close()