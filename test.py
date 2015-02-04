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
import time


## Set Global Variables ##

don_old_record = 0
sub_old_record = 0
don_clear_status = 0
sub_clear_status = 0

## Congfig File ##
configParser = ConfigParser.RawConfigParser()   
configFilePath = r'/Users/wturner/Documents/git/tundras_tracker/twitch_tracker.conf'
configParser.read(configFilePath)

## Set Logging ##
log_file = configParser.get('logging', 'log_file')
log_level = configParser.get('logging', 'log_level')
logging.basicConfig(filename=log_file,level=log_level)


## Enable/Disable Full Load Button ##
reload_sub_btn_status = configParser.get('reload_sub', 'allow')

# Change to Boolean
if reload_sub_btn_status == "True":
    reload_sub_btn_status = True
if reload_sub_btn_status == "False":
    reload_sub_btn_status = False

## Refresh Rate ##
update_interval = configParser.get('update_interval', 'update_interval')

# Turn milliseconds to seconds
update_interval = int(update_interval) * 1000

## Subscriber Count Max ##
sub_offset = configParser.get('sub_offset', 'sub_offset')

## StreamTip Access Tokens ##
streamtip_client_id = configParser.get('streamtip', 'streamtip_client_id')
streamtip_access_token = configParser.get('streamtip', 'streamtip_access_token')

## Get OAuth Token and Twitch Username from the Config File ##
twitch_username = configParser.get('twitch', 'twitch_username')
twitch_oauth_token = configParser.get('twitch', 'twitch_oauth_token')




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
    cur.execute("CREATE TABLE donations(Username varchar(100), Subscriber_Status varchar(30), Amount REAL, Message varchar, Transaction_Id varchar(100), Date date DEFAULT CURRENT_DATE NOT NULL, Time time DEFAULT CURRENT_TIME NOT NULL)")
    con.commit()
except:
    ## Rollback if create table command fails ##
    print "Donations Table Already Exists"
    con.rollback()

try:
    cur.execute("CREATE TABLE subscribers(Username varchar(100), Date_Subscribed date DEFAULT CURRENT_DATE NOT NULL, Time time DEFAULT CURRENT_TIME NOT NULL)")
    con.commit()
except:
    ## Rollback if create table command fails ##
    print "Subscribers Table Already Exists"
    con.rollback()

try:
    cur.execute("CREATE TABLE total_donations(Username varchar(100), Subscriber_Status varchar(30), Amount INT)")
    con.commit()
except:
    ## Rollback if create table command fails ##
    print "Total Donations Table Already Exists"
    con.rollback()

try:
    cur.execute("CREATE TABLE session_stats(Type varchar(30), Info varchar(100), Amount INT)")
    con.commit()
except:
    ## Rollback if create table command fails ##
    print "Session Stats Table Already Exists"
    con.rollback()


# f = open('workfile', 'w')

## GUI Start ##

class Tundras_Tracker():
    def __init__(self):
        # super(Tundras_Tracker, self).__init__()
        
    ### Main Windows ###

        # Set Title, Size, and Window Postion
        main_window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        main_window.set_title("Tundra's Tracker")
        main_window.set_size_request(1300, 650)
        main_window.set_position(gtk.WIN_POS_MOUSE)
        main_window.set_border_width(0)

        main_window.connect("destroy", gtk.main_quit)





    ### Load Section ###

        # Load Button (Refresh)
        refresh_btn = gtk.Button("Refresh")
        refresh_btn.set_size_request(90,25)
        refresh_btn.set_tooltip_text("Check for new Subscriptions and Donations")

        refresh_btn.connect("clicked", self.refresh_btn)
        refresh_btn.connect("clicked", self.on_refresh)
        refresh_btn.connect("clicked", self.get_current_sub_count)
        refresh_btn.connect("clicked", self.get_current_follow_count)
        refresh_btn.connect("clicked", self.get_current_viewers_count)

        # Reload all Subscribers Button
        reload_sub_btn = gtk.Button("Reload Subscribers")
        reload_sub_btn.set_size_request(120,25)
        reload_sub_btn.set_tooltip_text("Perform a full load of all records.  Must be enabled in the config file.")
        reload_sub_btn.set_sensitive(reload_sub_btn_status)

        reload_sub_btn.connect("clicked", self.reload_sub_btn)
        reload_sub_btn.connect("clicked", self.on_refresh)
        reload_sub_btn.connect("clicked", self.get_current_sub_count)


        # Load Section Frame #

        # Format Label
        load_label = gtk.Label()
        load_label.set_markup('<span size="20000"><b>Load</b></span>')
        load_label.set_use_markup(True)

        # Create Frame
        load_frame = gtk.Frame()
        load_frame.set_label_widget(load_label)
        load_frame.set_label_align(0.5, 0.5)
        load_vbox = gtk.VButtonBox()
        load_vbox.set_border_width(10)
        load_frame.add(load_vbox)


        # Set the Appearance of the Button Box
        load_vbox.set_layout(gtk.BUTTONBOX_START)
        load_vbox.set_spacing(20)

        # Add the Buttons #
        load_vbox.add(refresh_btn)
        load_vbox.add(reload_sub_btn)
        
        # Horizontal Box inside Vertical Box for Sizing Purposes #
        load_hbox = gtk.HBox(False, 0)
        load_hbox.set_border_width(0)

        load_hbox.pack_start(load_frame, True, True, 0)
        
 


        ### Stats Section ###

        # Current Number of Subscribers

        # Make Label
        self.sub_current = gtk.Label()
        self.sub_current.set_text("Loading...")

        sub_cur_label = gtk.Label()
        sub_cur_label.set_markup('<span size="13500"><b>Total Subscribers</b></span>')
        sub_cur_label.set_use_markup(True)

        sub_cur_frame = gtk.Frame()
        sub_cur_frame.set_label_widget(sub_cur_label)
        sub_cur_frame.set_label_align(0.1, 0.5)
        sub_cur_vbox = gtk.VBox(False, 8)
        sub_cur_vbox.set_border_width(10)
        sub_cur_frame.add(sub_cur_vbox)
        sub_cur_vbox.add(self.sub_current)
        

        sub_cur_hbox = gtk.HBox(False, 8)
        sub_cur_hbox.set_border_width(0)
        sub_cur_hbox.pack_start(sub_cur_frame, True, True, 0)


        # Current Number of Followers

        # Make Label 
        self.follow_current = gtk.Label()
        self.follow_current.set_text("Loading...")

        follow_cur_label = gtk.Label()
        follow_cur_label.set_markup('<span size="13500"><b>Total Followers</b></span>')
        follow_cur_label.set_use_markup(True)

        follow_cur_frame = gtk.Frame()
        follow_cur_frame.set_label_widget(follow_cur_label)
        follow_cur_frame.set_label_align(0.1, 0.5)
        follow_cur_vbox = gtk.VBox(False, 8)
        follow_cur_vbox.set_border_width(10)
        follow_cur_frame.add(follow_cur_vbox)
        follow_cur_vbox.add(self.follow_current)
        

        follow_cur_hbox = gtk.HBox(False, 8)
        follow_cur_hbox.set_border_width(0)
        follow_cur_hbox.pack_start(follow_cur_frame, True, True, 0)


        # Current Number of Viewers

        # Make Label 
        self.viewers_current = gtk.Label()
        self.viewers_current.set_text("Loading...")

        viewers_cur_label = gtk.Label()
        viewers_cur_label.set_markup('<span size="13500"><b>Viewer Count</b></span>')
        viewers_cur_label.set_use_markup(True)

        viewers_cur_frame = gtk.Frame()
        viewers_cur_frame.set_label_widget(viewers_cur_label)
        viewers_cur_frame.set_label_align(0.1, 0.5)
        viewers_cur_vbox = gtk.VBox(False, 8)
        viewers_cur_vbox.set_border_width(10)
        viewers_cur_frame.add(viewers_cur_vbox)
        viewers_cur_vbox.add(self.viewers_current)
        

        viewers_cur_hbox = gtk.HBox(False, 8)
        viewers_cur_hbox.set_border_width(0)
        viewers_cur_hbox.pack_start(viewers_cur_frame, True, True, 0)


        # Stats Section Frame #

        # Format Label
        stats_label = gtk.Label()
        stats_label.set_markup('<span size="20000"><b>Stats</b></span>')
        stats_label.set_use_markup(True)

        # Create Frame
        stats_frame = gtk.Frame()
        stats_frame.set_label_widget(stats_label)
        stats_frame.set_label_align(0.5, 0.5)
        stats_vbox = gtk.VButtonBox()
        stats_vbox.set_border_width(10)
        stats_frame.add(stats_vbox)


        # Set the Appearance of the Button Box
        stats_vbox.set_layout(gtk.BUTTONBOX_START)
        stats_vbox.set_spacing(20)

        # Add the Buttons #
        stats_vbox.add(sub_cur_hbox)
        stats_vbox.add(follow_cur_hbox)
        stats_vbox.add(viewers_cur_hbox)
        
        # Horizontal Box inside Vertical Box for Sizing Purposes #
        stats_hbox = gtk.HBox(False, 0)
        stats_hbox.set_border_width(0)

        stats_hbox.pack_start(stats_frame, True, True, 0)




    ### Donation Section ###

        # Clear Recent Donor Button
        self.don1_clear_btn = gtk.Button('Clear')
        self.don1_clear_btn.connect("clicked", self.clear_recent_donor_list)
        self.don1_clear_btn.connect("clicked", self.donor_uncolor)
        

        # Most Recent Donor List #

        # Make scrolling window 
        don1_list = gtk.ScrolledWindow()
        don1_list.set_size_request(490,80)
        don1_list.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        don1_list.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

        self.donstore1 = self.create_recent_donor_list()
        self.fill_recent_donor_store()

        # Make a TreeView
        don1_tree = gtk.TreeView(self.donstore1)
        don1_tree.set_rules_hint(True)
        don1_tree.columns_autosize()
        don1_tree.set_grid_lines(gtk.TREE_VIEW_GRID_LINES_VERTICAL)
        self.create_donation_columns(don1_tree)

        # Add don1_tree to the Scrolling Window
        don1_list.add(don1_tree)


        # Most Recent Donor Frame #

        # Format Label
        don1_label = gtk.Label()
        don1_label.set_markup('<span size="15000"><b>Most Recent Donor</b></span>')
        don1_label.set_use_markup(True)

        # Create Frame
        don1_frame = gtk.Frame()
        don1_frame.set_label_widget(don1_label)
        don1_frame.set_label_align(0.1, 0.5)
        don1_vbox = gtk.VBox(False, 8)
        don1_vbox.set_border_width(10)
        don1_frame.add(don1_vbox)
        don1_vbox.add(self.don1_clear_btn)
        don1_vbox.add(don1_list)


        don1_hbox = gtk.HBox(False, 8)
        don1_hbox.set_border_width(0)
        don1_hbox.pack_start(don1_frame, True, True, 0)




        # Last 10 Donors List

        # Make scrolling window 
        don10_list = gtk.ScrolledWindow()
        don10_list.set_size_request(490,350)
        don10_list.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        don10_list.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

        self.donstore10 = self.create_last_10_donor_list()
        self.fill_last_10_donor_store()

        # Make a TreeView
        don10_tree = gtk.TreeView(self.donstore10)
        don10_tree.set_rules_hint(True)
        don10_tree.columns_autosize()
        don10_tree.set_grid_lines(gtk.TREE_VIEW_GRID_LINES_VERTICAL)
        self.create_donation_columns(don10_tree)

        # Add don_tree to the Scrolling Window
        don10_list.add(don10_tree)

        # Last 10 Donors Frame #

        # Format Label
        don10_label = gtk.Label()
        don10_label.set_markup('<span size="15000"><b>Last 10 Donors</b></span>')
        don10_label.set_use_markup(True)

        # Create Frame
        don10_frame = gtk.Frame()
        don10_frame.set_label_widget(don10_label)
        don10_frame.set_label_align(0.1, 0.5)
        don10_vbox = gtk.VBox(False, 8)
        don10_vbox.set_border_width(10)
        don10_frame.add(don10_vbox)
        don10_vbox.add(don10_list)
        

        don10_hbox = gtk.HBox(False, 8)
        don10_hbox.set_border_width(0)
        don10_hbox.pack_start(don10_frame, True, True, 0)



        # Donation Frame # 
        
        # Format Label
        don_label = gtk.Label()
        don_label.set_markup('<span size="20000"><b>Donations</b></span>')
        don_label.set_use_markup(True)

        # Create Frame
        don_frame = gtk.Frame()
        don_frame.set_label_widget(don_label)
        don_frame.set_label_align(0.5, 0.5)
        don_vbox = gtk.VBox(False, 8)
        don_vbox.set_border_width(10)
        don_frame.add(don_vbox)

        # Set Spacking between widgets
        don_vbox.set_spacing(40)
        
        # Add Clear Button and TreeLists to Box
        don_vbox.add(don1_hbox)
        don_vbox.add(don10_hbox)
        

        # # We add a status bar that doesn't show up to prevent the list from being highlighted by default (No idea why this works)
        # self.statusbar = gtk.Statusbar()
        # don_vbox.add(self.statusbar)


        # Horizontal Box inside Vertical Box for Sizing Purposes #
        don_hbox = gtk.HBox(False, 8)
        don_hbox.set_border_width(0)
        don_hbox.pack_start(don_frame, True, True, 0)





### Subscriber Section ###

        # Clear Recent Donor Button
        self.sub1_clear_btn = gtk.Button('Clear')
        self.sub1_clear_btn.connect("clicked", self.clear_recent_sub_list)
        self.sub1_clear_btn.connect("clicked", self.sub_uncolor)

        # Most Recent Subscriber List #

        # Make scrolling window 
        sub1_list = gtk.ScrolledWindow()
        sub1_list.set_size_request(220,80)
        sub1_list.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        sub1_list.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

        self.substore1 = self.create_recent_sub_list()
        self.fill_recent_sub_store()

        # Make a TreeView
        sub1_tree = gtk.TreeView(self.substore1)
        sub1_tree.set_rules_hint(True)
        sub1_tree.columns_autosize()
        sub1_tree.set_grid_lines(gtk.TREE_VIEW_GRID_LINES_VERTICAL)
        self.create_subscriber_columns(sub1_tree)

        # Add sub1_tree to the Scrolling Window
        sub1_list.add(sub1_tree)


        # Most Recent Subscriber Frame #

        # Format Label
        sub1_label = gtk.Label()
        sub1_label.set_markup('<span size="15000"><b>Most Recent Subscriber</b></span>')
        sub1_label.set_use_markup(True)

        # Create Frame
        sub1_frame = gtk.Frame()
        sub1_frame.set_label_widget(sub1_label)
        sub1_frame.set_label_align(0.1, 0.5)
        sub1_vbox = gtk.VBox(False, 8)
        sub1_vbox.set_border_width(10)
        sub1_frame.add(sub1_vbox)
        sub1_vbox.add(self.sub1_clear_btn)
        sub1_vbox.add(sub1_list)


        sub1_hbox = gtk.HBox(False, 8)
        sub1_hbox.set_border_width(0)
        sub1_hbox.pack_start(sub1_frame, True, True, 0)




        # Last 10 Subscribers List

        # Make scrolling window 
        sub10_list = gtk.ScrolledWindow()
        sub10_list.set_size_request(220,225)
        sub10_list.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        sub10_list.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

        self.substore10 = self.create_last_10_sub_list()
        self.fill_last_10_sub_store()

        # Make a TreeView
        sub10_tree = gtk.TreeView(self.substore10)
        sub10_tree.set_rules_hint(True)
        sub10_tree.columns_autosize()
        sub10_tree.set_grid_lines(gtk.TREE_VIEW_GRID_LINES_VERTICAL)
        self.create_subscriber_columns(sub10_tree)

        # Add don_tree to the Scrolling Window
        sub10_list.add(sub10_tree)

        # Last 10 Subscribers Frame #

        # Format Label
        sub10_label = gtk.Label()
        sub10_label.set_markup('<span size="15000"><b>Last 10 Subscribers</b></span>')
        sub10_label.set_use_markup(True)

        # Create Frame
        sub10_frame = gtk.Frame()
        sub10_frame.set_label_widget(sub10_label)
        sub10_frame.set_label_align(0.1, 0.5)
        sub10_vbox = gtk.VBox(False, 8)
        sub10_vbox.set_border_width(10)
        sub10_frame.add(sub10_vbox)
        sub10_vbox.add(sub10_list)
        

        sub10_hbox = gtk.HBox(False, 8)
        sub10_hbox.set_border_width(0)
        sub10_hbox.pack_start(sub10_frame, True, True, 0)








        # Subscriber Frame # 
        
        # Format Label
        sub_label = gtk.Label()
        sub_label.set_markup('<span size="20000"><b>Subscribers</b></span>')
        sub_label.set_use_markup(True)

        # Create Frame
        sub_frame = gtk.Frame()
        sub_frame.set_label_widget(sub_label)
        sub_frame.set_label_align(0.5, 0.5)
        sub_vbox = gtk.VBox(False, 8)
        sub_vbox.set_border_width(10)
        sub_frame.add(sub_vbox)

        # Set Spacking between widgets
        sub_vbox.set_spacing(40)
        
        # Add Clear Button and TreeLists to Box
        sub_vbox.add(sub1_hbox)
        sub_vbox.add(sub10_hbox)
        

        # # We add a status bar that doesn't show up to prevent the list from being highlighted by default (No idea why this works)
        # self.statusbar = gtk.Statusbar()
        # sub_vbox.add(self.statusbar)


        # Horizontal Box inside Vertical Box for Sizing Purposes #
        sub_hbox = gtk.HBox(False, 8)
        sub_hbox.set_border_width(0)
        sub_hbox.pack_start(sub_frame, True, True, 0)




        # Create a colored border
        # button = gtk.Button("Click me")
        # button.set_border_width(50)
        # eb = gtk.EventBox()
        # eb.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("gray"))
        # eb.add(button)

        # Create Fixed Container so you can position all the frames where you want them #
        fixed = gtk.Fixed()
        fixed.put(load_hbox, 25, 10)
        fixed.put(stats_hbox, 25, 150)
        fixed.put(don_hbox, 200, 10)
        fixed.put(sub_hbox, 750, 10)

        # Add everything to the main window

        refresh_btn.grab_default()
        main_window.add(fixed)
        main_window.show_all()

        ## Refresh Every X Seconds (Set in Config File) ###
        gtk.timeout_add(update_interval, self.refresh_btn, self)
        gtk.timeout_add(update_interval, self.on_refresh, self)

        ## Refresh Current Subscription Value Every 10 Minutes ##
        gtk.timeout_add(600000, self.get_current_sub_count, self)
        gtk.timeout_add(update_interval, self.get_current_follow_count, self)
        gtk.timeout_add(update_interval, self.get_current_viewers_count, self)





   




## Functions ##

    ## Refresh Button ##
    def refresh_btn(self, widget):

        # Update Donations #
        offset = 0
        global don_on 
        don_on = 1

        streamtip_api_url = 'https://streamtip.com/api/tips?direction=desc&sort_by=date&limit=100&offset=' + str(offset) + '&client_id=' + streamtip_client_id + '&access_token=' + streamtip_access_token
        streamtip_donations = json.load(urllib2.urlopen(streamtip_api_url))

        cur.execute("SELECT Transaction_Id FROM donations ORDER BY date desc, time desc limit 1")
        rows = cur.fetchall()
        try:
            don_old_record = rows[0][0]
        except IndexError:
            print "There are no existing donation records. Populating..."
            don_old_record = ''

        while (streamtip_donations['_count'] > 0) and (don_on == 1):
            streamtip_api_url = 'https://streamtip.com/api/tips?direction=desc&sort_by=date&limit=100&offset=' + str(offset) + '&client_id=' + streamtip_client_id + '&access_token=' + streamtip_access_token
            streamtip_donations = json.load(urllib2.urlopen(streamtip_api_url)) 
            for item in streamtip_donations['tips']:
                if item['transactionId'] == don_old_record:
                    print 'Donations Are Up To Date'
                    don_on = 0
                    break 
                # Parse the date string that streamtip gives you #
                date = item['date'][0:10]
                time = item['date'][12:18]
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
            offset = offset + 100

        ## Pushes Changes to DB ##
        con.commit()


        # Update Subscribers #

        # Find the username of the last subscriber already entered into the DB #
        cur.execute("SELECT Username FROM subscribers ORDER BY Date_Subscribed desc limit 1")
        rows = cur.fetchall()
        try:
            sub_old_record = rows[0][0]
        except IndexError:
            print "There are no existing subscriber records.  Populating..."
            sub_old_record = ''

        offset = 0
        global sub_on 
        sub_on = 1
        while sub_on == 1:
            twitch_subscribers_api_url = 'https://api.twitch.tv/kraken/channels/' + twitch_username + '/subscriptions?direction=desc&limit=100&offset=' + str(offset) + '&oauth_token=' + twitch_oauth_token
            twitch_subscribers = json.load(urllib2.urlopen(twitch_subscribers_api_url))
            ## Pull Payment Info from StreamTip and insert new records ##
            for item in twitch_subscribers['subscriptions']:
                if item['user']['display_name'] == sub_old_record:
                    print 'Subscribers Are Up To Date'
                    sub_on = 0
                    break 
            # Parse the date string that streamtip gives you #
                date = item['created_at'][0:10]
                time = item['created_at'][12:18]
                try:
                    cur.execute("INSERT INTO subscribers (Username, Date_Subscribed, Time) VALUES ('%s','%s','%s')" % (item['user']['display_name'], date, time))
                except:
                    # Need to write to a log file here
                    logging.exception('\n\nUnknown Exception (This subscription was not loaded into the DB):\n')
                    error_info = '\n\nTransaction Info\nUsername: ' + item['user']['display_name'] + '\nDate: ' + date + '\n'
                    logging.error(error_info)
            offset = offset + 100
            if offset > int(sub_offset):
                sub_on = 0

        ## Pushes Changes to DB ##
        con.commit()

        return True



    ## Refresh Donations and Subscribers ##
    def on_refresh(self, widget):
        self.fill_recent_donor_store()
        self.fill_last_10_donor_store()
        self.fill_recent_sub_store()
        self.fill_last_10_sub_store()
        return True



    ## Update Current Sub Count ##
    def get_current_sub_count(self, widget):
        twitch_sub_count_api_url = 'https://api.twitch.tv/kraken/channels/' + twitch_username + '/subscriptions?direction=desc&limit=1&offset=0&oauth_token=' + twitch_oauth_token
        twitch_sub_count = json.load(urllib2.urlopen(twitch_sub_count_api_url))
        self.sub_current.set_markup('<span size="18000">' + str(twitch_sub_count['_total']) + '</span>')
        self.sub_current.set_use_markup(True)
        print "Sub Stats Updated"
        return True


    ## Update Current Followers Count ##
    def get_current_follow_count(self, widget):
        twitch_follow_count_api_url = 'https://api.twitch.tv/kraken/channels/' + twitch_username + '/follows?limit=1&offset=0'
        twitch_follow_count = json.load(urllib2.urlopen(twitch_follow_count_api_url))

        if int(twitch_follow_count['_total']) == 0:
            return True    
        else:
            self.follow_current.set_text('<span size="18000">' + str(twitch_follow_count['_total']) + '</span>')
            self.follow_current.set_use_markup(True)
            print "Followers Updated"
            return True


    ## Update Current Viewer Count ##
    def get_current_viewers_count(self, widget):
        twitch_viewers_count_api_url = 'https://api.twitch.tv/kraken/streams/' + twitch_username
        twitch_viewers_count = json.load(urllib2.urlopen(twitch_viewers_count_api_url))
        try:
            self.viewers_current.set_markup('<span size="18000">' + str(twitch_viewers_count['stream']['viewers']) + '</span>')
        except:
            self.viewers_current.set_markup('<span size="14000">Not Streaming</span>')

        self.viewers_current.set_use_markup(True)
        print "Viewers Updated"
        return True



    ## Reload All Subscribers Button ##
    def reload_sub_btn(self, widget):

        # Recreate Subscribers Table to Clear It #
        cur.execute("DROP table Subscribers")
        cur.execute("CREATE TABLE subscribers(Username varchar(30), Date_Subscribed date DEFAULT CURRENT_DATE NOT NULL, Time time DEFAULT CURRENT_TIME NOT NULL)")
        con.commit()
        
        offset = 0
        global sub_on 
        sub_on = 1
        while sub_on == 1:
            twitch_subscribers_api_url = 'https://api.twitch.tv/kraken/channels/' + twitch_username + '/subscriptions?direction=desc&limit=100&offset=' + str(offset) + '&oauth_token=' + twitch_oauth_token
            twitch_subscribers = json.load(urllib2.urlopen(twitch_subscribers_api_url))
            ## Pull Payment Info from StreamTip and insert new records ##
            for item in twitch_subscribers['subscriptions']:
                if item['user']['display_name'] == sub_old_record:
                    print 'Subscribers Are Up To Date'
                    sub_on = 0
                    break 
            # Parse the date string that streamtip gives you #
                date = item['created_at'][0:10]
                try:
                    cur.execute("INSERT INTO subscribers (Username, Date_Subscribed) VALUES ('%s','%s')" % (item['user']['display_name'], date))
                except:
                    # Need to write to a log file here
                    logging.exception('\n\nUnknown Exception (This subscription was not loaded into the DB):\n')
                    error_info = '\n\nTransaction Info\nUsername: ' + item['user']['display_name'] + '\nDate: ' + date + '\n'
                    logging.error(error_info)
            offset = offset + 100
            if offset > int(sub_offset):
                sub_on = 0

        ## Pushes Changes to DB ##
        con.commit()

        return True



    ## Donation Lists ##

    # Clear Most Recent Donor Button
    def clear_recent_donor_list(self, widget):
        self.donstore1.clear()
        global don_clear_status
        don_clear_status = 1
        return self.donstore1


    def create_recent_donor_list(self):
        self.donstore1 = gtk.ListStore(str, str, str, str)
        return self.donstore1


    def fill_recent_donor_store(self):
        self.donstore1.clear()
        global don_old_record
        global don_clear_status

        try:
            cur.execute("SELECT * FROM donations ORDER BY date desc, time desc limit 1")
            rows = cur.fetchall()

            amount = rows[0][2]
            amount = '%.2f' % amount
            transactionid = rows[0][4]

            if transactionid != don_old_record:
                self.donstore1.append([rows[0][0], amount, rows[0][3], rows[0][0]])
                don_old_record = rows[0][4]
                don_clear_status = 0
                self.donor_color()
                return self.donstore1

            elif don_clear_status == 0:
                self.donstore1.append([rows[0][0], amount, rows[0][3], rows[0][0]])
                return self.donstore1

            else:
                return False
                     
        except IndexError:
            print "indexerror"
            logging.exception('Exception:')
            self.donstore1.append(['None', 'None', 'None', 'None'])
            return self.donstore1

        except UnboundLocalError:
            print "unbounderror"
            logging.exception('Exception:')
            self.donstore1.append(['None', 'None', 'None', 'None'])
            return self.donstore1




    def create_last_10_donor_list(self):
        self.donstore10 = gtk.ListStore(str, str, str, str)
        return self.donstore10

    def fill_last_10_donor_store(self):
        self.donstore10.clear()

        try:
            cur.execute("SELECT * FROM donations ORDER BY date desc, time desc limit 10")
            rows = cur.fetchall()

            rownumber = 0

            while rownumber != 10:
                amount = rows[rownumber][2]
                amount = '%.2f' % amount
                self.donstore10.append([rows[rownumber][0], amount, rows[rownumber][3], rows[rownumber][0]])
                rownumber = rownumber + 1
        
        except IndexError:
            logging.exception('Exception:')
            self.donstore10.append(['None', 'None', 'None', 'None'])

        return self.donstore10

        

    def create_donation_columns(self, don_treeView):
    
        rendererText = gtk.CellRendererText()
        column = gtk.TreeViewColumn("User Name", rendererText, text=0)
        column.set_sort_column_id(0)    
        don_treeView.append_column(column)
        
        rendererText = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Amount", rendererText, text=1)
        column.set_sort_column_id(1)
        don_treeView.append_column(column)

        rendererText = gtk.CellRendererText()
        rendererText.props.wrap_width = 240
        rendererText.props.wrap_mode = gtk.WRAP_WORD
        column = gtk.TreeViewColumn("Donation Comment", rendererText, text=2)
        column.set_sort_column_id(2)
        don_treeView.append_column(column)

        rendererText = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Total", rendererText, text=3)
        column.set_sort_column_id(3)
        don_treeView.append_column(column)



    def donor_color(self):
        map = self.don1_clear_btn.get_colormap() 
        color = map.alloc_color("yellow")
        style = self.don1_clear_btn.modify_bg(gtk.STATE_NORMAL, color)
        self.don1_clear_btn.set_style(style)
        self.don1_clear_btn.set_label('NEW DONATION! (Click to Clear)')            


    def donor_uncolor(self, widget):
        style = self.don1_clear_btn.modify_bg(gtk.STATE_NORMAL, None)
        self.don1_clear_btn.set_style(style)
        self.don1_clear_btn.set_label('Clear')




    ## Subscriber Lists ##

    # Clear Most Recent Subscriber Button
    def clear_recent_sub_list(self, widget):
        self.substore1.clear()
        global sub_clear_status
        sub_clear_status = 1
        return self.substore1


    def create_recent_sub_list(self):
        self.substore1 = gtk.ListStore(str, str)
        return self.substore1


    def fill_recent_sub_store(self):
        self.substore1.clear()
        global sub_old_record
        global sub_clear_status

        try:
            cur.execute("SELECT * FROM subscribers ORDER BY Date_Subscribed desc, time desc limit 1")
            rows = cur.fetchall()

            if rows[0][0] != sub_old_record:
                self.substore1.append([rows[0][0], str(rows[0][1])])
                sub_old_record = rows[0][0]
                sub_clear_status = 0
                self.sub_color()
                return self.substore1

            elif sub_clear_status == 0:
                self.substore1.append([rows[0][0], str(rows[0][1])])
                return self.substore1

            else:
                return False
                     
        except IndexError:
            print "indexerror"
            logging.exception('Exception:')
            self.substore1.append(['None', 'None'])
            return self.substore1

        except UnboundLocalError:
            print "unbounderror"
            logging.exception('Exception:')
            self.substore1.append(['None', 'None'])
            return self.substore1
        



    def create_last_10_sub_list(self):
        self.substore10 = gtk.ListStore(str, str)
        return self.substore10

    def fill_last_10_sub_store(self):
        self.substore10.clear()

        try:
            cur.execute("SELECT * FROM subscribers ORDER BY Date_Subscribed desc, time desc limit 10")
            rows = cur.fetchall()

            rownumber = 0

            while rownumber != 10:
                self.substore10.append([rows[rownumber][0], str(rows[rownumber][1])])
                rownumber = rownumber + 1
        
        except IndexError:
            logging.exception('Exception:')
            self.substore10.append(['None', 'None'])

        return self.substore10
        

    def create_subscriber_columns(self, sub_treeView):
    
        rendererText = gtk.CellRendererText()
        column = gtk.TreeViewColumn("User Name", rendererText, text=0)
        column.set_sort_column_id(0)    
        sub_treeView.append_column(column)
        
        rendererText = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Date Subscribed", rendererText, text=1)
        column.set_sort_column_id(1)
        sub_treeView.append_column(column)


    def sub_color(self):
        map = self.sub1_clear_btn.get_colormap() 
        color = map.alloc_color("orange")
        style = self.sub1_clear_btn.modify_bg(gtk.STATE_NORMAL, color)
        self.sub1_clear_btn.set_style(style)
        self.sub1_clear_btn.set_label('NEW SUBSCRIBER! (Click to Clear)')            


    def sub_uncolor(self, widget):
        style = self.sub1_clear_btn.modify_bg(gtk.STATE_NORMAL, None)
        self.sub1_clear_btn.set_style(style)
        self.sub1_clear_btn.set_label('Clear')




Tundras_Tracker()
gtk.main()