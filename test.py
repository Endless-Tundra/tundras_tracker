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
import gtk

## Congfig File ##
configParser = ConfigParser.RawConfigParser()   
configFilePath = r'/Users/wturner/Documents/git/tundras_tracker/twitch_tracker.conf'
configParser.read(configFilePath)

## Set Logging ##
log_file = configParser.get('logging', 'log_file')
log_level = configParser.get('logging', 'log_level')
logging.basicConfig(filename=log_file,level=log_level)
logging.warning('Creating log file')

# Get Credentials From Config File #
streamtip_client_id = configParser.get('streamtip', 'streamtip_client_id')
streamtip_access_token = configParser.get('streamtip', 'streamtip_access_token')

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


actresses = [('jessica alba', 'pomona', '1981'), ('sigourney weaver', 'new york', '1949'), ('angelina jolie', 'los angeles', '1975'), ('natalie portman', 'jerusalem', '1981'), ('rachel weiss', 'london', '1971'), ('scarlett johansson', 'new york', '1984' )]


## GUI Start ##

class Tundras_Tracker():
    def __init__(self):
        # super(Tundras_Tracker, self).__init__()
        
        # Set Title, Size, and Window Postion
        main_window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        main_window.set_title("Tundra's Tracker")
        main_window.set_size_request(1000, 600)
        main_window.set_position(gtk.WIN_POS_MOUSE)
        main_window.set_border_width(0)

        main_window.connect("destroy", gtk.main_quit)




        # Full Load Button
        full_load_btn = gtk.Button("Full Load")
        full_load_btn.set_size_request(90,25)
        full_load_btn.set_tooltip_text("Perform a full load of all records.  Must be enabled in the config file.")
        full_load_btn.set_sensitive(False)

        full_load_btn.connect("clicked", self.full_load_btn)



        # Partial Load Button (Refresh)
        refresh_btn = gtk.Button("Refresh")
        refresh_btn.set_size_request(90,25)
        refresh_btn.set_tooltip_text("Check for new Subscriptions and Donations")


        refresh_btn.connect("clicked", self.refresh_btn)

        button6 = gtk.Button(label="Button 6")

        main_grid = gtk.Table(8, 8, False)

        main_grid.set_col_spacing(0, 20)

        main_grid.attach(refresh_btn, 0, 1, 0, 1)
        main_grid.attach(full_load_btn, 0, 1, 8, 9)
        



        # fixed = gtk.Fixed()

        # fixed.put(full_load_btn, 20, 520)
        # fixed.put(refresh_btn, 20, 20)

        main_window.add(main_grid)
        main_window.show_all()






   








## Funcations ##
    ## Full Load Button ##
    def full_load_btn(self, widget):
        ### Payment Processing ###

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




    ## Refresh Button ##
    def refresh_btn(self, widget):
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
                note = 'No Message was Left :('
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




Tundras_Tracker()
gtk.main()