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


actresses = [('jessica alba', 'pomona', '1981', '1981'), ('sigourney weaver', 'new york', '1949jsdhf;dskjf;lkdsjf;lkdsjfl;ksdjf;lkdsjf;lsdkjf;lkdsj;lkdjf', '1981'), ('jessica alba', 'pomona', '1981', '1981')]


## GUI Start ##

class Tundras_Tracker():
    def __init__(self):
        # super(Tundras_Tracker, self).__init__()
        
    ### Main Windows ###

        # Set Title, Size, and Window Postion
        main_window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        main_window.set_title("Tundra's Tracker")
        main_window.set_size_request(1000, 600)
        main_window.set_position(gtk.WIN_POS_MOUSE)
        main_window.set_border_width(0)

        main_window.connect("destroy", gtk.main_quit)




    ### Load Section ###

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


        # Load Button Frame #

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
        load_vbox.set_spacing(450)

        # Add the Buttons #
        load_vbox.add(refresh_btn)
        load_vbox.add(full_load_btn)
        
        # Horizontal Box inside Vertical Box for Sizing Purposes #
        load_hbox = gtk.HBox(False, 0)
        load_hbox.set_border_width(0)

        load_hbox.pack_start(load_frame, True, True, 0)
        



    ### Donation Section ###

        # Clear Recent Donor Button
        don1_clear_btn = gtk.Button('Clear')


        # Most Recent Donor List #

        # Make scrolling window 
        don1_list = gtk.ScrolledWindow()
        don1_list.set_size_request(490,100)
        don1_list.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        don1_list.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)

        store = self.create_model()

        # Make a TreeView
        don1_tree = gtk.TreeView(store)
        don1_tree.set_rules_hint(True)
        don1_tree.columns_autosize()
        # don_tree.set_grid_lines(gtk.TREE_VIEW_GRID_LINES_BOTH)
        self.create_columns(don1_tree)

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
        don1_vbox.add(don1_clear_btn)
        don1_vbox.add(don1_list)


        don1_hbox = gtk.HBox(False, 8)
        don1_hbox.set_border_width(0)
        don1_hbox.pack_start(don1_frame, True, True, 0)




        # Last 10 Donors List

        # Make scrolling window 
        don10_list = gtk.ScrolledWindow()
        don10_list.set_size_request(490,300)
        don10_list.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        don10_list.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)

        store = self.create_model()

        # Make a TreeView
        don10_tree = gtk.TreeView(store)
        don10_tree.set_rules_hint(True)
        don10_tree.columns_autosize()
        # don_tree.set_grid_lines(gtk.TREE_VIEW_GRID_LINES_BOTH)
        self.create_columns(don10_tree)

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
        don_vbox.set_spacing(50)
        
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






        # Create a colored border
        # button = gtk.Button("Click me")
        # button.set_border_width(50)
        # eb = gtk.EventBox()
        # eb.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("gray"))
        # eb.add(button)

        # Create Fixed Container so you can position all the frames where you want them #
        fixed = gtk.Fixed()
        fixed.put(load_hbox, 25, 10)
        fixed.put(don_hbox, 200, 10)

        # Add everything to the main window

        refresh_btn.grab_default()
        main_window.add(fixed)
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



    ## Donation Lists ##
    def create_model(self):
        cur.execute("SELECT * FROM donations ORDER BY date desc, time desc limit 10")
        rows = cur.fetchall()

        store = gtk.ListStore(str, str, str, str)

        rownumber = 0

        while rownumber != 10:
            amount = rows[rownumber][2]
            amount = '%.2f' % amount
            store.append([rows[rownumber][0], amount, rows[rownumber][3], rows[rownumber][0]])
            rownumber = rownumber + 1
        
        return store


    def create_columns(self, treeView):
    
        rendererText = gtk.CellRendererText()
        column = gtk.TreeViewColumn("User Name", rendererText, text=0)
        column.set_sort_column_id(0)    
        treeView.append_column(column)
        
        rendererText = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Amount", rendererText, text=1)
        column.set_sort_column_id(1)
        treeView.append_column(column)

        rendererText = gtk.CellRendererText()
        rendererText.props.wrap_width = 240
        rendererText.props.wrap_mode = gtk.WRAP_WORD
        column = gtk.TreeViewColumn("Donation Comment", rendererText, text=2)
        column.set_sort_column_id(2)
        treeView.append_column(column)

        rendererText = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Total", rendererText, text=3)
        column.set_sort_column_id(3)
        treeView.append_column(column)


Tundras_Tracker()
gtk.main()