#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright © 2015 Warren Turner
# Licensed under the LGPL version 2.1 or later
# Tundra's Tracker for Twitch
# Version 0.8.2

import os
# import easygui
import requests
import json
import psycopg2
import sys
import ConfigParser
import re
import logging
import gtk
import time
import gobject
import glib
import threading
import urllib2
import pango
import traceback
# import easygui

## Set Global Variables ##

don_old_record = 0
sub_old_record = 0
don_clear_status = 0
sub_clear_status = 0
update_running = 0
sub_cur_running = 0
follow_cur_running = 0
viewers_cur_running = 0
top_donator_running = 0


## Load Congfig File ##
try:
    ## Find location of file based on OS ##
    
    workingdir = os.getcwd()

    if os.name == "nt":
        configFilePath = r'' + workingdir + '\\twitch_tracker.conf'
    elif os.name == "posix":
        configFilePath = r'' + workingdir + '/twitch_tracker.conf'

    configParser = ConfigParser.RawConfigParser() 

    try:
        configParser.read(configFilePath)
    except:
        logging.exception('\nCould not find Config File.  Make sure that it is named twitch_tracker.conf and located in the same folder as the application.\n\n\n')
        # easygui.msgbox("Could not find Config File.  Make sure that it is named twitch_tracker.conf and located in the same folder as the application.")
        sys.exit(2)

    ## Set Logging ##
    log_file = configParser.get('logging', 'log_file')
    log_level = configParser.get('logging', 'log_level')
    logging.basicConfig(format='\n\n%(asctime)s\n---------------------- %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', filename=log_file, level=log_level)

    ## Output Path for OBS Text Files ##
    output_path = configParser.get('output_path', 'output_path')


    ## Enable/Disable Full Load Button ##
    reload_sub_btn_status = configParser.get('reload_sub', 'allow')

    # Change to Boolean
    if reload_sub_btn_status == "True":
        reload_sub_btn_status = True

    if reload_sub_btn_status == "False":
        reload_sub_btn_status = False

    ## Refresh Rate ##
    update_interval = configParser.get('update_interval', 'update_interval')
    stat_update_interval = configParser.get('update_interval', 'stat_update_interval')

    # Turn milliseconds to seconds
    update_interval = int(update_interval) * 1000
    stat_update_interval = int(stat_update_interval) * 1000

    ## Subscriber Count Max ##
    sub_offset = configParser.get('sub_offset', 'sub_offset')

    ## StreamTip Access Tokens ##
    streamtip_client_id = configParser.get('streamtip', 'streamtip_client_id')
    streamtip_access_token = configParser.get('streamtip', 'streamtip_access_token')

    ## Get OAuth Token and Twitch Username from the Config File ##
    twitch_username = configParser.get('twitch', 'twitch_username')
    twitch_oauth_token = configParser.get('twitch', 'twitch_oauth_token')

    ## Get Database Information ##
    db_name = configParser.get('database', 'db_name')
    db_user = configParser.get('database', 'db_user')
    db_server = configParser.get('database', 'db_server')
    db_password = configParser.get('database', 'db_password')

except:
    logging.basicConfig(filename='error.log',level='DEBUG')
    logging.exception('\nMissing a section in the config file.  Read the below error to figure out which one.\n\n\n')
    sys.exit(2)


## Connect to the DB ##
try:
    con = None
    con = psycopg2.connect("dbname='%s' user='%s' host='%s' password='%s'" % (db_name, db_user, db_server, db_password))
    cur = con.cursor()

except:
    logging.exception('\nCould not connect to the database specified\n\n\n')



## Check if all Necessary Tables Exist ##
try:        

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
        cur.execute("CREATE TABLE total_donations(Username varchar(100), Subscriber_Status varchar(30), Amount REAL)")
        con.commit()
    except:
        ## Rollback if create table command fails ##
        print "Total Donations Table Already Exists"
        con.rollback()

    try:
        cur.execute("CREATE TABLE session_stats(Type varchar(30), Info varchar(100), Amount REAL)")
        con.commit()
    except:
        ## Rollback if create table command fails ##
        print "Session Stats Table Already Exists"
        con.rollback()

    try:
        cur.execute("CREATE TABLE lost_subscribers(Username varchar(100), Date_Subscribed date DEFAULT CURRENT_DATE NOT NULL, Date_Lost date DEFAULT CURRENT_DATE NOT NULL, Time time DEFAULT CURRENT_TIME NOT NULL)")
        con.commit()
    except:
        ## Rollback if create table command fails ##
        print "Lost Subscribers Table Already Exists"
        con.rollback()

    con.close()

except:
    logging.exception('\nError Making the needed tables in the DB\n\n\n')



## Begin the Main Loop ##
try:

    ############### GUI ###############

    ## Set the sizes for each OS ##
    if os.name == "nt":
        main_window_length = 1050
        frame_label_size_large = "15000"
        frame_label_size_medium = "12000"
        frame_label_size_small = "11000"
        stats_vbox_spacing_size = 10
        don10_list_width = 364
        don_vbox_spacing_size = 25
        topdon_label_size = "13500"
        stats_box_position_y = 140
        topdon_box_position_y = 415
        data_insights_box_position_y = 570
        twitch_sad_text = 11000
        not_streaming_text = 11000

        # The below positions/text sizes are used instead if you want the "Recalculate Dononation Totals" Button
        # stats_box_position_y = 177
        # topdon_box_position_y = 445
        # data_insights_box_position_y = 600
        # twitch_sad_text = "11000"
        # not_streaming_text = "11000"

    elif os.name == "posix":
        main_window_length = 1300
        frame_label_size_large = "20000"
        frame_label_size_medium = "15000"
        frame_label_size_small = "13500"
        stats_vbox_spacing_size = 20
        don10_list_width = 350
        don_vbox_spacing_size = 40
        topdon_label_size = "18000"
        stats_box_position_y = 148
        topdon_box_position_y = 410
        data_insights_box_position_y = 560
        twitch_sad_text = 15000
        not_streaming_text = 14000

        # The below positions/text sizes are used instead if you want the "Recalculate Dononation Totals" Button
        # stats_box_position_y = 185
        # topdon_box_position_y = 440
        # data_insights_box_position_y = 590
        # twitch_sad_text = "15000"
        # not_streaming_text = "14000"


    class Tundras_Tracker():
        def __init__(self):
            

    ###### Main Window ######

            ## Set Title, Size, and Window Postion ##
            main_window = gtk.Window(gtk.WINDOW_TOPLEVEL)
            main_window.set_title("Tundra's Tracker")
            main_window.set_size_request(main_window_length, 680)
            main_window.set_position(gtk.WIN_POS_MOUSE)
            main_window.set_border_width(0)
            # main_window.modify_font(pango.FontDescription('Sans Bold Not-Rotated'))
            main_window.connect("destroy", gtk.main_quit)



    ###### Load Section ######

        ## Refresh Button (Refresh) ##
            refresh_btn = gtk.Button("Refresh")
            refresh_btn.set_size_request(120,25)
            refresh_btn.set_tooltip_text("Check for new Subscriptions and Donations")

            refresh_btn.connect("clicked", self.check_for_updates_thread)
            refresh_btn.connect("clicked", self.listfill_run)
            refresh_btn.connect("clicked", self.stats_thread)


        ## Reload all Subscribers Button ##
            self.reload_sub_btn = gtk.Button("Reload Subscribers")
            self.reload_sub_btn.set_size_request(120,25)
            self.reload_sub_btn.set_tooltip_text("Perform a full load of all records.  Must be enabled in the config file.")
            self.reload_sub_btn.set_sensitive(reload_sub_btn_status)

            self.reload_sub_btn.connect("clicked", self.reload_subs)
            self.reload_sub_btn.connect("clicked", self.listfill_run)
            self.reload_sub_btn.connect("clicked", self.get_current_sub_count)


        ## Recalculatione Donation Totals on Startup ##
            self.reload_don_totals()


        ## Recalculate Donation Totals Button ##
        ## I'm not sure it is actually useful to have a button that recalculates the donation totals because it would only need to be done in rare occurences so I'm disabling it.
        ## (like when there were rows in the donations table before the total donations table was being updated)
            # self.reload_don_totals_btn = gtk.Button("Recalculate Totals")
            # self.reload_don_totals_btn.set_size_request(120,25)
            # self.reload_don_totals_btn.set_tooltip_text("Recalculate donation totals for each username.")

            # self.reload_don_totals_btn.connect("clicked", self.reload_don_totals)
            # self.reload_don_totals_btn.connect("clicked", self.listfill_run)


        ## Load Section Frame ##

            # Frame Label #
            load_label = gtk.Label()
            load_label.set_markup('<span size="' + frame_label_size_large + '"><b>Load</b></span>')
            load_label.set_use_markup(True)

            # Create Frame #
            load_frame = gtk.Frame()
            load_frame.set_label_widget(load_label)
            load_frame.set_label_align(0.5, 0.5)
            load_vbox = gtk.VButtonBox()
            load_vbox.set_border_width(10)
            load_frame.add(load_vbox)

            # Set the Appearance of the Button Box #
            load_vbox.set_layout(gtk.BUTTONBOX_START)
            load_vbox.set_spacing(20)

            # Add the Buttons #
            load_vbox.add(refresh_btn)
            # load_vbox.add(self.reload_don_totals_btn)
            load_vbox.add(self.reload_sub_btn)
            
            # Horizontal Box inside Vertical Box for Sizing Purposes #
            load_hbox = gtk.HBox(False, 0)
            load_hbox.set_border_width(0)
            load_hbox.pack_start(load_frame, True, True, 0)
            
     

    ###### Stats Section ######

        ## Current Number of Subscribers ##

            # Make Label #
            self.sub_current = gtk.Label()
            self.sub_current.set_text("Loading...")

            sub_cur_label = gtk.Label()
            sub_cur_label.set_markup('<span size="' + frame_label_size_small + '"><b>Total Subscribers</b></span>')
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


        ## Current Number of Followers ##

            # Make Label #
            self.follow_cur = gtk.Label()
            self.follow_cur.set_text("Loading...")

            follow_cur_label = gtk.Label()
            follow_cur_label.set_markup('<span size="' + frame_label_size_small + '"><b>Total Followers</b></span>')
            follow_cur_label.set_use_markup(True)

            follow_cur_frame = gtk.Frame()
            follow_cur_frame.set_label_widget(follow_cur_label)
            follow_cur_frame.set_label_align(0.1, 0.5)
            follow_cur_vbox = gtk.VBox(False, 8)
            follow_cur_vbox.set_border_width(10)
            follow_cur_frame.add(follow_cur_vbox)
            follow_cur_vbox.add(self.follow_cur)
            

            follow_cur_hbox = gtk.HBox(False, 8)
            follow_cur_hbox.set_border_width(0)
            follow_cur_hbox.pack_start(follow_cur_frame, True, True, 0)


        ## Current Number of Viewers ##

            # Make Label #
            self.viewers_cur = gtk.Label()
            self.viewers_cur.set_text("Loading...")

            viewers_cur_label = gtk.Label()
            viewers_cur_label.set_markup('<span size="' + frame_label_size_small + '"><b>Viewer Count</b></span>')
            viewers_cur_label.set_use_markup(True)

            # Make Frame #
            viewers_cur_frame = gtk.Frame()
            viewers_cur_frame.set_label_widget(viewers_cur_label)
            viewers_cur_frame.set_label_align(0.1, 0.5)
            viewers_cur_vbox = gtk.VBox(False, 8)
            viewers_cur_vbox.set_border_width(10)
            viewers_cur_frame.add(viewers_cur_vbox)
            viewers_cur_vbox.add(self.viewers_cur)
            

            viewers_cur_hbox = gtk.HBox(False, 8)
            viewers_cur_hbox.set_border_width(0)
            viewers_cur_hbox.pack_start(viewers_cur_frame, True, True, 0)


        ## Top Donator ##

            # Make Label # 
            top_don_label = gtk.Label()
            top_don_label.set_markup('<span size="' + frame_label_size_small + '"><b>Top Donator</b></span>')
            top_don_label.set_use_markup(True)
            
            top_donator = "Loading..."
            top_donation_amount = ""
            self.top_don = gtk.Label()
            self.top_don.set_text(top_donator + '\n' + top_donation_amount)


            # Make Frame #
            top_don_frame = gtk.Frame()
            top_don_frame.set_label_widget(top_don_label)
            top_don_frame.set_label_align(0.1, 0.5)
            top_don_vbox = gtk.VBox(False, 8)
            top_don_vbox.set_border_width(10)
            top_don_frame.add(top_don_vbox)
            top_don_vbox.add(self.top_don)
            

            top_don_hbox = gtk.HBox(False, 8)
            top_don_hbox.set_border_width(0)
            top_don_hbox.pack_start(top_don_frame, True, True, 0)


        ## Stats Section Frame ##

            # Frame Label #
            stats_label = gtk.Label()
            stats_label.set_markup('<span size="' + frame_label_size_large + '"><b>Stats</b></span>')
            stats_label.set_use_markup(True)

            # Create Frame #
            stats_frame = gtk.Frame()
            stats_frame.set_label_widget(stats_label)
            stats_frame.set_label_align(0.5, 0.5)
            stats_vbox = gtk.VButtonBox()
            stats_vbox.set_border_width(10)
            stats_frame.add(stats_vbox)

            # Set the Appearance of the Button Box #
            stats_vbox.set_layout(gtk.BUTTONBOX_START)
            stats_vbox.set_spacing(stats_vbox_spacing_size)

            # Add the Buttons #
            stats_vbox.add(sub_cur_hbox)
            stats_vbox.add(follow_cur_hbox)
            stats_vbox.add(viewers_cur_hbox)
            
            # Horizontal Box inside Vertical Box for Sizing Purposes #
            stats_hbox = gtk.HBox(False, 0)
            stats_hbox.set_border_width(0)
            stats_hbox.pack_start(stats_frame, True, True, 0)



    ###### Data Insights Section ######

        ## Lost Subscribers Button ##
            lost_subs_btn = gtk.Button("Lost Subscribers")
            lost_subs_btn.set_size_request(120,25)
            lost_subs_btn.set_tooltip_text("Show Subscribers that have not renewed")

            lost_subs_btn.connect("clicked", self.lost_subs_window)


        ## Data Insights Section Frame ##

            # Frame Label #
            data_insights_label = gtk.Label()
            data_insights_label.set_markup('<span size="' + frame_label_size_large + '"><b>DI</b></span>')
            data_insights_label.set_use_markup(True)

            # Create Frame #
            data_insights_frame = gtk.Frame()
            data_insights_frame.set_label_widget(data_insights_label)
            data_insights_frame.set_label_align(0.5, 0.5)
            data_insights_vbox = gtk.VButtonBox()
            data_insights_vbox.set_border_width(10)
            data_insights_frame.add(data_insights_vbox)

            # Set the Appearance of the Button Box #
            data_insights_vbox.set_layout(gtk.BUTTONBOX_START)
            data_insights_vbox.set_spacing(20)

            # Add the Buttons #
            data_insights_vbox.add(lost_subs_btn)
            
            # Horizontal Box inside Vertical Box for Sizing Purposes #
            data_insights_hbox = gtk.HBox(False, 0)
            data_insights_hbox.set_border_width(0)
            data_insights_hbox.pack_start(data_insights_frame, True, True, 0)



    ###### Donation Section ######

        ## Clear Recent Donor Button ##
            self.don1_clear_btn = gtk.Button('Clear')
            self.don1_clear_btn.connect("clicked", self.clear_recent_donor_list)
            self.don1_clear_btn.connect("clicked", self.donor_uncolor)
            

        ## Most Recent Donor List ##

            # Make scrolling window 
            don1_list = gtk.ScrolledWindow()
            don1_list.set_size_request(490,80)
            don1_list.set_shadow_type(gtk.SHADOW_ETCHED_IN)
            don1_list.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

            self.donlist1 = self.create_recent_donor_list()
            self.fill_recent_donor_list()

            # Make a TreeView
            don1_tree = gtk.TreeView(self.donlist1)
            don1_tree.set_rules_hint(True)
            don1_tree.columns_autosize()
            don1_tree.set_grid_lines(gtk.TREE_VIEW_GRID_LINES_VERTICAL)
            self.create_donation_columns(don1_tree)

            # Add don1_tree to the Scrolling Window
            don1_list.add(don1_tree)


        ## Most Recent Donor Frame ##

            # Frame Label
            don1_label = gtk.Label()
            don1_label.set_markup('<span size="' + frame_label_size_medium + '"><b>Most Recent Donor</b></span>')
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




        ## Last 10 Donors List ##

            # Make scrolling window #
            don10_list = gtk.ScrolledWindow()
            don10_list.set_size_request(490,don10_list_width)
            don10_list.set_shadow_type(gtk.SHADOW_ETCHED_IN)
            don10_list.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

            self.donlist10 = self.create_last_10_donor_list()
            self.fill_last_10_donor_list()

            # Make a TreeView #
            don10_tree = gtk.TreeView(self.donlist10)
            don10_tree.set_rules_hint(True)
            don10_tree.columns_autosize()
            don10_tree.set_grid_lines(gtk.TREE_VIEW_GRID_LINES_BOTH)
            self.create_donation_columns(don10_tree)

            # Add don_tree to the Scrolling Window #
            don10_list.add(don10_tree)


        ## Last 10 Donors Frame ##

            # Frame Label #
            don10_label = gtk.Label()
            don10_label.set_markup('<span size="' + frame_label_size_medium + '"><b>Last 10 Donors</b></span>')
            don10_label.set_use_markup(True)

            # Create Frame #
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
            don_label.set_markup('<span size="' + frame_label_size_large + '"><b>Donations</b></span>')
            don_label.set_use_markup(True)

            # Create Frame
            don_frame = gtk.Frame()
            don_frame.set_label_widget(don_label)
            don_frame.set_label_align(0.5, 0.5)
            don_vbox = gtk.VBox(False, 8)
            don_vbox.set_border_width(10)
            don_frame.add(don_vbox)

            # Set Spacking between widgets
            don_vbox.set_spacing(don_vbox_spacing_size)
            
            # Add Clear Button and TreeLists to Box
            don_vbox.add(don1_hbox)
            don_vbox.add(don10_hbox)


            # Horizontal Box inside Vertical Box for Sizing Purposes #
            don_hbox = gtk.HBox(False, 8)
            don_hbox.set_border_width(0)
            don_hbox.pack_start(don_frame, True, True, 0)



    ###### Subscriber Section ######

        ## Clear Recent Donor Button ##
            self.sub1_clear_btn = gtk.Button('Clear')
            self.sub1_clear_btn.connect("clicked", self.clear_recent_sub_list)
            self.sub1_clear_btn.connect("clicked", self.sub_uncolor)

        ## Most Recent Subscriber List ##

            # Make scrolling window #
            sub1_list = gtk.ScrolledWindow()
            sub1_list.set_size_request(220,80)
            sub1_list.set_shadow_type(gtk.SHADOW_ETCHED_IN)
            sub1_list.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

            self.sublist1 = self.create_recent_sub_list()
            self.fill_recent_sub_list()

            # Make a TreeView #
            sub1_tree = gtk.TreeView(self.sublist1)
            sub1_tree.set_rules_hint(True)
            sub1_tree.columns_autosize()
            sub1_tree.set_grid_lines(gtk.TREE_VIEW_GRID_LINES_VERTICAL)
            self.create_subscriber_columns(sub1_tree)

            # Add sub1_tree to the Scrolling Window #
            sub1_list.add(sub1_tree)


        ## Most Recent Subscriber Frame ##

            # Format Label
            sub1_label = gtk.Label()
            sub1_label.set_markup('<span size="' + frame_label_size_medium + '"><b>Most Recent Subscriber</b></span>')
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




        ## Last 10 Subscribers List ##

            # Make scrolling window #
            sub10_list = gtk.ScrolledWindow()
            sub10_list.set_size_request(225,235)
            sub10_list.set_shadow_type(gtk.SHADOW_ETCHED_IN)
            sub10_list.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

            self.sublist10 = self.create_last_10_sub_list()
            self.fill_last_10_sub_list()

            # Make a TreeView #
            sub10_tree = gtk.TreeView(self.sublist10)
            sub10_tree.set_rules_hint(True)
            sub10_tree.columns_autosize()
            sub10_tree.set_grid_lines(gtk.TREE_VIEW_GRID_LINES_BOTH)
            self.create_subscriber_columns(sub10_tree)

            # Add don_tree to the Scrolling Window #
            sub10_list.add(sub10_tree)

        ## Last 10 Subscribers Frame ##

            # Format Label #
            sub10_label = gtk.Label()
            sub10_label.set_markup('<span size="' + frame_label_size_medium + '"><b>Last 10 Subscribers</b></span>')
            sub10_label.set_use_markup(True)

            # Create Frame #
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



        ## Subscription Goal Objective Set Button ##
            sub_goal_set_btn = gtk.Button("Set")
            sub_goal_set_btn.set_size_request(30,25)
            sub_goal_set_btn.set_tooltip_text("Set Subscription Goal")
            sub_goal_set_btn.connect("clicked", self.set_sub_goal)



        ## Subscription Goal Clear Button ##
            sub_goal_clear_btn = gtk.Button("Clear")
            sub_goal_clear_btn.set_size_request(30,25)
            sub_goal_clear_btn.set_tooltip_text("Clear Subscription Goal")
            sub_goal_clear_btn.connect("clicked", self.reset_sub_goal)



        ## Subscriber Goal Entry Box ##

            # Make Label # 
            sub_goal_label = gtk.Label()
            sub_goal_label.set_markup('<span size="' + frame_label_size_medium + '"><b>Sub Goal</b></span>')
            sub_goal_label.set_use_markup(True)


            self.sub_goal_entry = gtk.Entry()
            self.sub_goal_entry.set_size_request(30,25)
            self.sub_goal_entry.set_alignment(1.0)

            self.sub_goal_display = gtk.Label()

            self.populate_sub_goal()


            # Subscriber Goal Frame #
            sub_goal_frame = gtk.Frame()
            sub_goal_frame.set_label_widget(sub_goal_label)
            sub_goal_frame.set_label_align(0.1, 0.5)
            sub_goal_vbox1 = gtk.VBox(False, 8)
            sub_goal_vbox1.set_border_width(10)
            sub_goal_vbox2 = gtk.VBox(False, 8)
            sub_goal_vbox2.set_border_width(10)
            sub_goal_vbox1.add(self.sub_goal_entry)
            sub_goal_vbox1.add(sub_goal_set_btn)
            sub_goal_vbox2.add(self.sub_goal_display)
            sub_goal_vbox2.add(sub_goal_clear_btn)

            sub_goal_hbox2 = gtk.HBox(False, 8)
            

            sub_goal_hbox2.pack_start(sub_goal_vbox1, True, True, 0)
            sub_goal_hbox2.pack_start(sub_goal_vbox2, True, True, 0)
            
            sub_goal_frame.add(sub_goal_hbox2)

            sub_goal_hbox = gtk.HBox(False, 8)
            sub_goal_hbox.set_border_width(0)
            sub_goal_hbox.pack_start(sub_goal_frame, True, True, 0)



        ## Combined Subscriber Frame ##
            
            # Format Label #
            sub_label = gtk.Label()
            sub_label.set_markup('<span size="' + frame_label_size_large + '"><b>Subscribers</b></span>')
            sub_label.set_use_markup(True)

            # Create Frame #
            sub_frame = gtk.Frame()
            sub_frame.set_label_widget(sub_label)
            sub_frame.set_label_align(0.5, 0.5)
            sub_vbox = gtk.VBox(False, 8)
            sub_vbox.set_border_width(10)
            sub_frame.add(sub_vbox)

            # Set Spacking between widgets #
            sub_vbox.set_spacing(don_vbox_spacing_size)
            
            # Add Clear Button and TreeLists to Box #
            sub_vbox.add(sub1_hbox)
            sub_vbox.add(sub10_hbox)
            sub_vbox.add(sub_goal_hbox)

            # Horizontal Box inside Vertical Box for Sizing Purposes #
            sub_hbox = gtk.HBox(False, 8)
            sub_hbox.set_border_width(0)
            sub_hbox.pack_start(sub_frame, True, True, 0)



    ###### Top Donator Section ######

        ## Clear Top Donator Button ##
            self.top_don_clear_btn = gtk.Button('Reset Top Donator')
            self.top_don_clear_btn.connect("clicked", self.clear_top_don_list)

        ## Top Donator List ##

            # Make scrolling window #
            top_don_list = gtk.ScrolledWindow()
            top_don_list.set_size_request(160,65)
            top_don_list.set_shadow_type(gtk.SHADOW_ETCHED_IN)
            top_don_list.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

            self.top_don_list = self.create_top_don_list()
            self.fill_top_don_list()

            # Make a TreeView #
            top_don_tree = gtk.TreeView(self.top_don_list)
            top_don_tree.set_rules_hint(True)
            top_don_tree.columns_autosize()
            top_don_tree.set_grid_lines(gtk.TREE_VIEW_GRID_LINES_VERTICAL)
            self.create_top_don_columns(top_don_tree)

            # Add top_don_tree to the Scrolling Window #
            top_don_list.add(top_don_tree)


        ## Top Donator Frame ##

            # Format Label
            top_don_label = gtk.Label()
            top_don_label.set_markup('<span size="' + topdon_label_size + '"><b>Top Donator</b></span>')
            top_don_label.set_use_markup(True)

            # Create Frame
            top_don_frame = gtk.Frame()
            top_don_frame.set_label_widget(top_don_label)
            top_don_frame.set_label_align(0.5, 0.5)
            top_don_vbox = gtk.VBox(False, 8)
            top_don_vbox.set_border_width(10)
            top_don_frame.add(top_don_vbox)
            top_don_vbox.add(self.top_don_clear_btn)
            top_don_vbox.add(top_don_list)


            top_don_hbox = gtk.HBox(False, 8)
            top_don_hbox.set_border_width(0)
            top_don_hbox.pack_start(top_don_frame, True, True, 0)



    ###### Create Fixed Container so you can position all the frames where you want them ######
            fixed = gtk.Fixed()
            fixed.put(load_hbox, 25, 10)
            fixed.put(stats_hbox, 25, stats_box_position_y)
            fixed.put(top_don_hbox, 10, topdon_box_position_y)
            fixed.put(data_insights_hbox, 25, data_insights_box_position_y)
            fixed.put(don_hbox, 200, 10)
            fixed.put(sub_hbox, 750, 10)



    ###### Add everything to the main window ######

            # refresh_btn.grab_default()
            main_window.add(fixed)
            main_window.show_all()



    ###### Enable Auto Updating ######
        ## Refresh Updates (Interval Set in Config File) ###
            gtk.timeout_add(update_interval, self.check_for_updates_thread, self)
            gtk.timeout_add(update_interval, self.listfill_run, self)

        ## Refresh Current Stats (Interval Set in Config File)##
            gtk.timeout_add(stat_update_interval, self.stats_thread, self)








    ############### FUNCTIONS ###############


    ###### Threads ######
        def check_for_updates_thread(self, widget):
            check_for_updates_thread = threading.Thread(target=self.check_for_updates)
            check_for_updates_thread.daemon = True
            check_for_updates_thread.start()
            return True


        def stats_thread(self, widget):
            substat_thread = threading.Thread(target=self.stats_run)
            substat_thread.daemon = True
            substat_thread.start()
            return True


    # ###### Don't use this, it just crashes (I have no idea why) ######
    #     def listfill_thread(self, widget):
    #         listfill_thread = threading.Thread(target=self.listfill_run)
    #         listfill_thread.daemon = True
    #         listfill_thread.start()
    #         return True


    ###### Run Commands ######
        def listfill_run(self, widget):
            self.fill_recent_donor_list()
            self.fill_last_10_donor_list()
            self.fill_recent_sub_list()
            self.fill_last_10_sub_list()
            self.fill_top_don_list()
            return True


        def stats_run(self):
            self.get_current_sub_count(self)
            self.get_current_follow_count()
            self.get_current_viewers_count()



    ###### Functions that actually do things ######



    ###### Update Stats ######

        ## Update Current Sub Count ##
        def get_current_sub_count(self, widget):
            global sub_cur_running
            
            # Make sure that the get_current_sub_count function isn't already running #
            if sub_cur_running == 1:
                print "current sub count already running"
                return False
            sub_cur_running = 1
            try:
                twitch_sub_count_api_url = 'https://api.twitch.tv/kraken/channels/' + twitch_username + '/subscriptions?direction=desc&limit=1&offset=0&oauth_token=' + twitch_oauth_token
                twitch_sub_count = requests.get(twitch_sub_count_api_url, timeout=5).json()
                self.sub_current.set_markup('<span size="' + topdon_label_size + '">' + str(twitch_sub_count['_total']) + '</span>')
            except:
                logging.exception('\nCant Connect to Twitch to get current Sub Count\n\n\n')
                self.sub_current.set_markup('<span size="' + twitch_sad_text + '">Twitch :(</span>')

            self.sub_current.set_use_markup(True)
            print "Sub Stats Updated"
            sub_cur_running = 0


        ## Update Current Followers Count ##
        def get_current_follow_count(self):
            global follow_cur_running
            
            # Make sure that the get_current_sub_count function isn't already running #
            if follow_cur_running == 1:
                print "current followers already running"
                return False
            follow_cur_running = 1
            try:
                twitch_follow_count_api_url = 'https://api.twitch.tv/kraken/channels/' + twitch_username + '/follows?limit=1&offset=0'
                twitch_follow_count = requests.get(twitch_follow_count_api_url, timeout=5).json()
                if int(twitch_follow_count['_total']) == 0:
                    return True    
                else:
                    self.follow_cur.set_text('<span size="' + topdon_label_size + '">' + str(twitch_follow_count['_total']) + '</span>')
            except:
                logging.exception('\nCant Connect to Twitch to get current Follower Count\n\n\n')
                self.follow_cur.set_markup('<span size="' + twitch_sad_text + '">Twitch :(</span>')

            self.follow_cur.set_use_markup(True)
            print "Followers Updated"
            follow_cur_running = 0


        ## Update Current Viewer Count ##
        def get_current_viewers_count(self):
            global viewers_cur_running
            
            # Make sure that the get_current_sub_count function isn't already running #
            if viewers_cur_running == 1:
                print "current viewers already running"
                return False
            viewers_cur_running = 1
            try:
                twitch_viewers_count_api_url = 'https://api.twitch.tv/kraken/streams/' + twitch_username
                # twitch_viewers_count = json.load(urllib2.urlopen(twitch_viewers_count_api_url))
                twitch_viewers_count = requests.get(twitch_viewers_count_api_url, timeout=5).json()
                self.viewers_cur.set_markup('<span size="' + topdon_label_size + '">' + str(twitch_viewers_count['stream']['viewers']) + '</span>')
            except:
                #logging.exception('I dont understand?')
                self.viewers_cur.set_markup('<span size="'+ not_streaming_text + '">Not Streaming</span>')

            self.viewers_cur.set_use_markup(True)
            print "Viewers Updated"
            viewers_cur_running = 0



    ###### Check For Updates (Refresh Button) ######
        def check_for_updates(self):
            global update_running
            
        ## Make sure that the check_for_updates function isn't already running ##
            if update_running == 1:
                print "check for updates already running"
                return False
            update_running = 1

        ## Make a Big Try Block to avoid the "update_running" variable from getting stuck on when an error happens ##
            try:
            ## Open Connection to DB ##
                check_for_updates_con = None
                check_for_updates_con = psycopg2.connect("dbname='%s' user='%s' host='%s' password='%s'" % (db_name, db_user, db_server, db_password))
                check_for_updates_cur = check_for_updates_con.cursor()


            ## Update Donations ##
                offset = 0
                global don_on 
                don_on = 1

                # Pull Donation Info from StreamTip #

                try:
                    streamtip_api_url = 'https://streamtip.com/api/tips?direction=desc&sort_by=date&limit=100&offset=' + str(offset) + '&client_id=' + streamtip_client_id + '&access_token=' + streamtip_access_token
                    streamtip_donations = requests.get(streamtip_api_url, timeout=5).json()
                except:
                    logging.exception('\nError connecting to StreamTip\n\n\n')
                    update_running = 0
                    return True

                check_for_updates_cur.execute("SELECT Transaction_Id FROM donations ORDER BY date desc, time desc limit 1")
                rows = check_for_updates_cur.fetchall()
                try:
                    don_old_record = rows[0][0]
                except IndexError:
                    print "There are no existing donation records. Populating..."
                    don_old_record = ''

                while (streamtip_donations['_count'] > 0) and (don_on == 1):
                    try:
                        streamtip_api_url = 'https://streamtip.com/api/tips?direction=desc&sort_by=date&limit=100&offset=' + str(offset) + '&client_id=' + streamtip_client_id + '&access_token=' + streamtip_access_token
                        streamtip_donations = requests.get(streamtip_api_url, timeout=5).json()
                    except:
                        logging.exception('\nError connecting to StreamTip\n\n\n')
                        update_running = 0
                        check_for_updates_con.rollback()
                        check_for_updates_con.close()
                        return True

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
                            check_for_updates_cur.execute("INSERT INTO donations (Username, Amount, Message, Transaction_Id, Date, Time) VALUES ('%s',%f,'%s','%s','%s','%s')" % (item['username'], float(item['amount']), note, item['transactionId'], date, time))
                            check_for_updates_cur.execute("DELETE FROM total_donations WHERE LOWER(username) = LOWER('%s')" % (item['username']))
                            check_for_updates_cur.execute("INSERT INTO total_donations (username, amount) SELECT LOWER(username), SUM(amount) FROM donations WHERE username = '%s' GROUP BY LOWER(username)" % (item['username']))
                        except UnicodeDecodeError:
                            logging.exception('\nUnicode Exception (This transaction was loaded into the DB but the note was removed)\n\n')
                            error_info = '\n\nTransaction Info\nUsername: ' + item['username'] + '\nAmount: ' + item['amount'] + '\nNote: ' + item['note'] + '\nTransation_Id: ' + item['transactionId'] + '\nDate: ' + date + '\nTime: ' + time + '\n'
                            logging.error(error_info)
                            note = 'Sorry something about the message caused an error so it couldnt be saved :(  But Carci still loves you!'
                            check_for_updates_cur.execute("INSERT INTO donations (Username, Amount, Message, Transaction_Id, Date, Time) VALUES ('%s',%f,'%s','%s','%s','%s')" % (item['username'], float(item['amount']), note, item['transactionId'], date, time))
                        except:
                            # Need to write to a log file here
                            logging.exception('\nUnknown Exception (This transaction was not loaded into the DB)\n\n')
                            error_info = '\n\nTransaction Info\nUsername: ' + item['username'] + '\nAmount: ' + item['amount'] + '\nNote: ' + item['note'] + '\nTransation_Id: ' + item['transactionId'] + '\nDate: ' + date + '\nTime: ' + time + '\n'
                            logging.error(error_info)

                        try:
                            check_for_updates_cur.execute("SELECT Amount FROM session_stats WHERE Type='top_donator'")
                            top_donor_row = check_for_updates_cur.fetchall()

                            if float(item['amount']) > float(top_donor_row[0][0]):
                                check_for_updates_cur.execute("UPDATE session_stats SET Info = '%s', Amount = '%f' WHERE Type = 'top_donator'" % (item['username'], float(item['amount'])))
                        except IndexError:
                            print "The Top Donator Spot is empty. Populating..."
                            check_for_updates_cur.execute("INSERT INTO session_stats (type, info, amount) VALUES ('top_donator', '%s', '%f')" % (item['username'], float(item['amount'])))
                    offset = offset + 100

                # Pushes Changes to DB #
                check_for_updates_con.commit()


            ## Update Subscribers ##

                # Find the username of the last subscriber already entered into the DB #
                check_for_updates_cur.execute("SELECT Username FROM subscribers ORDER BY Date_Subscribed desc, time desc limit 1")
                rows = check_for_updates_cur.fetchall()
                try:
                    sub_old_record = rows[0][0]
                except IndexError:
                    print "There are no existing subscriber records.  Populating..."
                    sub_old_record = ''

                offset = 0
                global sub_on 
                sub_on = 1
                while sub_on == 1:
                    try:
                        twitch_subscribers_api_url = 'https://api.twitch.tv/kraken/channels/' + twitch_username + '/subscriptions?direction=desc&limit=100&offset=' + str(offset) + '&oauth_token=' + twitch_oauth_token
                        twitch_subscribers = requests.get(twitch_subscribers_api_url, timeout=5).json()                   
                    except:
                        logging.exception('\nError connecting to Twitch to Update Subscribers\n\n\n')
                        update_running = 0
                        check_for_updates_con.rollback()
                        check_for_updates_con.close()
                        return False
                    for item in twitch_subscribers['subscriptions']:
                        if item['user']['display_name'] == sub_old_record:
                            print 'Subscribers Are Up To Date'
                            sub_on = 0
                            break 
                    # Parse the date string that twitch gives you #
                        date = item['created_at'][0:10]
                        time = item['created_at'][12:18]
                        try:
                            check_for_updates_cur.execute("INSERT INTO subscribers (Username, Date_Subscribed, Time) VALUES ('%s','%s','%s')" % (item['user']['display_name'], date, time))
                            check_for_updates_cur.execute("UPDATE session_stats SET Amount=Amount+1 WHERE Type='sub_goal'")
                        except:
                            # Need to write to a log file here
                            logging.exception('\nUnknown Exception (This subscription was not loaded into the DB)\n\n')
                            error_info = '\n\nTransaction Info\nUsername: ' + item['user']['display_name'] + '\nDate: ' + date + '\n' + time + '\n'
                            logging.error(error_info)

                    offset = offset + 100
                    if offset > int(sub_offset):
                        sub_on = 0

                # Pushes Changes to DB #
                check_for_updates_con.commit()
                check_for_updates_con.close()
                # Update Sub Goal Progress
                self.populate_sub_goal()
                update_running = 0

            except:
                logging.exception('\nSome sort of exception occurred while checking for updates\n')
                update_running = 0



    ###### Reload All Subscribers Button ######
        def reload_subs(self, widget):
            reload_subs_con = None
            reload_subs_con = psycopg2.connect("dbname='%s' user='%s' host='%s' password='%s'" % (db_name, db_user, db_server, db_password))
            reload_subs_cur = reload_subs_con.cursor()
            global update_running
            if update_running == 1:
                print "reload all subscribers already running"
                return False

            print "Reloading All Subscribers"
            self.reload_sub_btn.set_label("Reloading...")
            self.sublist1.clear()
            self.sublist10.clear()
            while gtk.events_pending():
                gtk.main_iteration()  
            # Move existing data to new table #
            try:
                reload_subs_cur.execute("DROP TABLE previous_subscribers")
            except:
                reload_subs_con.rollback()

            reload_subs_cur.execute("ALTER TABLE subscribers RENAME TO previous_subscribers")
            reload_subs_cur.execute("CREATE TABLE subscribers(Username varchar(30), Date_Subscribed date DEFAULT CURRENT_DATE NOT NULL, Time time DEFAULT CURRENT_TIME NOT NULL)")
            
            offset = 0
            global sub_on
            sub_on = 1
            while sub_on == 1:
                try:
                    twitch_subscribers_api_url = 'https://api.twitch.tv/kraken/channels/' + twitch_username + '/subscriptions?direction=desc&limit=100&offset=' + str(offset) + '&oauth_token=' + twitch_oauth_token
                    twitch_subscribers = requests.get(twitch_subscribers_api_url, timeout=5).json()
                except:
                    logging.exception('\nError connecting to Twitch to Update Subscribers\n\n\n')
                    update_running = 0
                    return True
                for item in twitch_subscribers['subscriptions']:
                    date = item['created_at'][0:10]
                    time = item['created_at'][12:18]
                    try:
                        reload_subs_cur.execute("INSERT INTO subscribers (Username, Date_Subscribed, Time) VALUES ('%s','%s','%s')" % (item['user']['display_name'], date, time))
                    except:
                        logging.exception('\nUnknown Exception (This subscription was not loaded into the DB)\n\n')
                        error_info = '\n\nTransaction Info\nUsername: ' + item['user']['display_name'] + '\nDate: ' + date + '\n' + time + '\n'
                        logging.error(error_info)
                offset = offset + 100
                if offset > int(sub_offset):
                    sub_on = 0
            ## Pushes Changes to DB ##
            reload_subs_cur.execute("INSERT INTO lost_subscribers SELECT username, date_subscribed FROM subscribers where username not in (SELECT username FROM previous_subscribers)")
            reload_subs_cur.execute("DROP TABLE previous_subscribers")
            reload_subs_con.commit()
            reload_subs_con.close()
            update_running = 0
            self.reload_sub_btn.set_label("Reload Subscribers")



    ###### Recalculate Donation Totals Button ######
        def reload_don_totals(self):
            reload_don_totals_con = None
            reload_don_totals_con = psycopg2.connect("dbname='%s' user='%s' host='%s' password='%s'" % (db_name, db_user, db_server, db_password))
            reload_don_totals_cur = reload_don_totals_con.cursor()
            global update_running

            if update_running == 1:
                print "Recalculating Donation Totals is already running"
                return False

            print "Recalculating all Donation Totals"
            # self.reload_don_totals_btn.set_label("Recalculating...")

            while gtk.events_pending():
                gtk.main_iteration()  
            # Move existing data to new table #
            try:
                reload_don_totals_cur.execute("DROP TABLE total_donations")
            except:
                reload_don_totals_con.rollback()

            reload_don_totals_cur.execute("CREATE TABLE total_donations(Username varchar(100), Subscriber_Status varchar(30), Amount REAL)")
            reload_don_totals_cur.execute("INSERT INTO total_donations (username, amount) SELECT LOWER(username), SUM(amount) FROM donations GROUP BY LOWER(username)")

            ## Pushes Changes to DB ##
            reload_don_totals_con.commit()
            reload_don_totals_con.close()
            update_running = 0
            # self.reload_don_totals_btn.set_label("Recalculate Totals")



    ###### Donation Lists ######

        # Clear Most Recent Donor Button
        def clear_recent_donor_list(self, widget):
            self.donlist1.clear()
            global don_clear_status
            don_clear_status = 1
            return self.donlist1


        def create_recent_donor_list(self):
            self.donlist1 = gtk.ListStore(str, str, str, str)
            return self.donlist1


        def fill_recent_donor_list(self):
            don1_con = None
            don1_con = psycopg2.connect("dbname='%s' user='%s' host='%s' password='%s'" % (db_name, db_user, db_server, db_password))
            don1_cur = don1_con.cursor()

            total_don_con = None
            total_don_con = psycopg2.connect("dbname='%s' user='%s' host='%s' password='%s'" % (db_name, db_user, db_server, db_password))
            total_don_cur = total_don_con.cursor()

            self.donlist1.clear()
            global don_old_record
            global don_clear_status

            try:
                don1_cur.execute("SELECT * FROM donations ORDER BY date desc, time desc limit 1")
                rows = don1_cur.fetchall()

                amount = rows[0][2]
                amount = '%.2f' % amount
                transactionid = rows[0][4]

                # Get total donated by that username #
                total_don_cur.execute("SELECT amount FROM total_donations WHERE username = LOWER('%s')" % (rows[0][0]))
                total_don_rows = total_don_cur.fetchall()
                
                try:
                    total_don_amount = total_don_rows[0][0]
                    total_don_amount = '%.2f' % total_don_amount
                except:
                    total_don_amount = 'Unknown (Restart the App to Fix This)'

                if transactionid != don_old_record:
                    self.donlist1.append([rows[0][0], amount, rows[0][3], total_don_amount])
                    don_old_record = rows[0][4]
                    don_clear_status = 0
                    self.donor_color()
                    don1_con.close()
                    total_don_con.close()
                    return self.donlist1

                elif don_clear_status == 0:
                    self.donlist1.append([rows[0][0], amount, rows[0][3], total_don_amount])
                    don1_con.close()
                    total_don_con.close()
                    return self.donlist1

                else:
                    don1_con.close()
                    total_don_con.close()
                    return False
                         
            except IndexError:
                logging.exception('\nException while filling recent donor list (There is probably no data in the donations DB, filling it with "Loading")\n\n')
                self.donlist1.append(['Loading', 'Loading', 'Loading', 'Loading'])
                don1_con.close()
                total_don_con.close()
                return self.donlist1

            except:
                logging.exception('\nException while filling recent donor list\n\n')
                self.donlist1.append(['Loading', 'Loading', 'Loading', 'Loading'])
                don1_con.close()
                total_don_con.close()
                return self.donlist1


        def create_last_10_donor_list(self):
            self.donlist10 = gtk.ListStore(str, str, str, str)
            return self.donlist10


        def fill_last_10_donor_list(self):
            don10_con = None
            don10_con = psycopg2.connect("dbname='%s' user='%s' host='%s' password='%s'" % (db_name, db_user, db_server, db_password))
            don10_cur = don10_con.cursor()
            self.donlist10.clear()

            total_don10_con = None
            total_don10_con = psycopg2.connect("dbname='%s' user='%s' host='%s' password='%s'" % (db_name, db_user, db_server, db_password))
            total_don10_cur = total_don10_con.cursor()

            try:
                don10_cur.execute("SELECT * FROM donations ORDER BY date desc, time desc limit 10")
                rows = don10_cur.fetchall()
                rownumber = 0

                while rownumber != 10:
                    # Get total donated by that username #
                    total_don10_cur.execute("SELECT amount FROM total_donations WHERE username = LOWER('%s')" % (rows[rownumber][0]))
                    total_don10_rows = total_don10_cur.fetchall()
                
                    try:
                        total_don10_amount = total_don10_rows[0][0]
                        total_don10_amount = '%.2f' % total_don10_amount
                    except:
                        total_don10_amount = 'Unknown (Restart the App to Fix This)'

                    # Populate the List #
                    amount = rows[rownumber][2]
                    amount = '%.2f' % amount
                    self.donlist10.append([rows[rownumber][0], amount, rows[rownumber][3], total_don10_amount])
                    rownumber = rownumber + 1
            
            except IndexError:
                logging.exception('\nException while filling last 10 donors list (There is probably no data in the donations DB, filling it with "Loading")\n\n')
                self.donlist10.append(['Loading', 'Loading', 'Loading', 'Loading'])

            don10_con.close()
            total_don10_con.close()
            return self.donlist10

            
        def create_donation_columns(self, don_treeView):
        
            rendererText = gtk.CellRendererText()
            column = gtk.TreeViewColumn("User Name", rendererText, text=0)
            column.set_sort_column_id(0)    
            don_treeView.append_column(column)
            
            rendererText = gtk.CellRendererText()
            column = gtk.TreeViewColumn("Amount", rendererText, text=1)
            rendererText.set_property('xalign', 1.0)
            column.set_sort_column_id(1)
            don_treeView.append_column(column)

            rendererText = gtk.CellRendererText()
            rendererText.props.wrap_width = 260
            rendererText.props.wrap_mode = gtk.WRAP_WORD
            column = gtk.TreeViewColumn("Donation Comment", rendererText, text=2)
            column.set_sort_column_id(2)
            column.set_min_width(260)
            don_treeView.append_column(column)

            rendererText = gtk.CellRendererText()
            column = gtk.TreeViewColumn("Total", rendererText, text=3)
            rendererText.set_property('xalign', 1.0)
            column.set_sort_column_id(3)
            column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
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



    ###### Subscriber Lists ######

        ## Clear Most Recent Subscriber Button ##
        def clear_recent_sub_list(self, widget):
            self.sublist1.clear()
            global sub_clear_status
            sub_clear_status = 1
            return self.sublist1


        ## Create Recent Subscriber List ##
        def create_recent_sub_list(self):
            self.sublist1 = gtk.ListStore(str, str)
            return self.sublist1


        ## Fill Recent Subscriber List ##
        def fill_recent_sub_list(self):
            sub1_con = None
            sub1_con = psycopg2.connect("dbname='%s' user='%s' host='%s' password='%s'" % (db_name, db_user, db_server, db_password))
            sub1_cur = sub1_con.cursor()

            self.sublist1.clear()
            global sub_old_record
            global sub_clear_status

            try:
                sub1_cur.execute("SELECT * FROM subscribers ORDER BY Date_Subscribed desc, time desc limit 1")
                rows = sub1_cur.fetchall()

                if rows[0][0] != sub_old_record:
                    self.sublist1.append([rows[0][0], str(rows[0][1])])
                    sub_old_record = rows[0][0]
                    sub_clear_status = 0
                    self.sub_color()
                    sub1_con.close()

                    # Write to output text file for OBS #
                    recent_sub_file = open(output_path + 'recent_sub.txt', "w")
                    recent_sub_file.write(sub_old_record)
                    recent_sub_file.close()
                    return self.sublist1

                elif sub_clear_status == 0:
                    self.sublist1.append([rows[0][0], str(rows[0][1])])
                    sub1_con.close()
                    return self.sublist1

                else:
                    sub1_con.close()
                    return False
                         
            except IndexError:
                logging.exception('\nException while filling recent subscriber list (There is probably no data in the subscribers DB, filling it with "Loading")\n\n')
                self.sublist1.append(['Loading', 'Loading'])
                sub1_con.close()
                return self.sublist1

            except UnboundLocalError:
                logging.exception('\nException while filling recent subscriber list\n\n')
                self.sublist1.append(['Loading', 'Loading'])
                sub1_con.close()
                return self.sublist1
            


        ## Create Last 10 Subscribers List ##            
        def create_last_10_sub_list(self):
            self.sublist10 = gtk.ListStore(str, str)
            return self.sublist10


        ## Fill Last 10 Subscribers List ## 
        def fill_last_10_sub_list(self):
            sub10_con = None
            sub10_con = psycopg2.connect("dbname='%s' user='%s' host='%s' password='%s'" % (db_name, db_user, db_server, db_password))
            sub10_cur = sub10_con.cursor()

            self.sublist10.clear()

            try:
                sub10_cur.execute("SELECT * FROM subscribers ORDER BY Date_Subscribed desc, time desc limit 10")
                rows = sub10_cur.fetchall()

                rownumber = 0

                while rownumber != 10:
                    self.sublist10.append([rows[rownumber][0], str(rows[rownumber][1])])
                    rownumber = rownumber + 1
            
            except IndexError:
                logging.exception('\nException while filling last 10 subscribers list (There is probably no data in the subscribers DB, filling it with "Loading")\n\n')
                self.sublist10.append(['Loading', 'Loading'])

            except UnboundLocalError:
                logging.exception('\nException while filling last 10 subscribers list\n\n')
                self.sublist1.append(['Loading', 'Loading'])
                sub1_con.close()
                return self.sublist10

            sub10_con.close()
            return self.sublist10
            

        ## Create Subscribers TreeView ## 
        def create_subscriber_columns(self, sub_treeView):
        
            rendererText = gtk.CellRendererText()
            column = gtk.TreeViewColumn("User Name", rendererText, text=0)
            column.set_sort_column_id(0)    
            sub_treeView.append_column(column)
            
            rendererText = gtk.CellRendererText()
            column = gtk.TreeViewColumn("Date Subscribed", rendererText, text=1)
            rendererText.set_property('xalign', .5)
            column.set_sort_column_id(1)
            sub_treeView.append_column(column)


        ## Change Subscriber Clear Button Color ##
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

        

    ###### Subscriber Goal ######

        ## Clear Sub Goal Button ##
        def reset_sub_goal(self, widget):
            sub_goal_con = None
            sub_goal_con = psycopg2.connect("dbname='%s' user='%s' host='%s' password='%s'" % (db_name, db_user, db_server, db_password))
            sub_goal_cur = sub_goal_con.cursor()
            
            try:
                sub_goal_cur.execute("DELETE FROM session_stats WHERE Type='sub_goal'")
                sub_goal_con.commit()
                sub_goal_con.close()   
            except:
                logging.exception('\nException while reseting the subscriber goal (There is probably no data in the session_stats DB)\n\n')
                sub_goal_con.close()
            
            self.sub_goal_current = "0"
            self.sub_goal_objective = "0"
            self.sub_goal_display.set_markup('<span size="15000">' + self.sub_goal_current + '/' + self.sub_goal_objective + '</span>')
            self.sub_goal_display.set_use_markup(True)

            # Write to output text file for OBS #
            sub_goal_file = open(output_path + 'sub_goal.txt', "w")
            sub_goal_file.write('Sub Goal: ' + self.sub_goal_current + '/' + self.sub_goal_objective)
            sub_goal_file.close()



        ## Set Sub Goal ##
        def set_sub_goal(self, widget):
            sub_goal_con = None
            sub_goal_con = psycopg2.connect("dbname='%s' user='%s' host='%s' password='%s'" % (db_name, db_user, db_server, db_password))
            sub_goal_cur = sub_goal_con.cursor()

            self.sub_goal_objective = self.sub_goal_entry.get_text()

            if self.sub_goal_objective == "":
                return False

            try:
                sub_goal_cur.execute("SELECT Amount FROM session_stats WHERE Type='sub_goal'")
                sub_goal_row = sub_goal_cur.fetchall()

                if sub_goal_row[0][0] >= 0:
                    sub_goal_cur.execute("UPDATE session_stats SET Amount = '0', Info = '%s' WHERE Type = 'sub_goal'" % (self.sub_goal_objective))
                    sub_goal_con.commit()
                    sub_goal_con.close()

            except IndexError:
                print "The Sub Goal is empty. Populating..."
                sub_goal_cur.execute("INSERT INTO session_stats (type, amount, info) VALUES ('sub_goal', '0', '%s')" % (self.sub_goal_objective))
                sub_goal_con.commit()
                sub_goal_con.close()
            self.populate_sub_goal()
            self.sub_goal_entry.set_text("")

            # Write to output text file for OBS #
            sub_goal_file = open(output_path + 'sub_goal.txt', "w")
            sub_goal_file.write('Sub Goal: 0/' + self.sub_goal_objective)
            sub_goal_file.close()



        ## Populate Sub Goal Labels ##
        def populate_sub_goal(self):
            sub_goal_con = None
            sub_goal_con = psycopg2.connect("dbname='%s' user='%s' host='%s' password='%s'" % (db_name, db_user, db_server, db_password))
            sub_goal_cur = sub_goal_con.cursor()


            try:
                sub_goal_cur.execute("SELECT Amount, Info FROM session_stats WHERE Type='sub_goal'")
                rows = sub_goal_cur.fetchall()
      
                self.sub_goal_current = str(rows[0][0])
                self.sub_goal_objective = str(rows[0][1])
                # Remove last 2 characters from sub current output to remove the ".0" at the end
                self.sub_goal_current = self.sub_goal_current[:-2]

                self.sub_goal_display.set_markup('<span size="15000">' + self.sub_goal_current + '/' + self.sub_goal_objective + '</span>')
                self.sub_goal_display.set_use_markup(True)
                         
            except IndexError:
                # Disabling this log line because it will log an error everytime the list is empty and the refresh button is pushed #
                # logging.exception('\nException while reseting the subscriber goal (There is probably no data in the session_stats DB, filling it with "None")\n\n')
                self.sub_goal_current = "0"
                self.sub_goal_objective = "0"
                sub_goal_con.close()

            except:
                logging.exception('\nException while filling the top donor list\n\n')
                self.sub_goal_current = "0"
                self.sub_goal_objective = "0"
                sub_goal_con.close()
                

            self.sub_goal_display.set_markup('<span size="15000">' + self.sub_goal_current + '/' + self.sub_goal_objective + '</span>')
            self.sub_goal_display.set_use_markup(True)

            # Write to output text file for OBS #
            sub_goal_file = open(output_path + 'sub_goal.txt', "w")
            sub_goal_file.write('Sub Goal: ' + self.sub_goal_current + '/' + self.sub_goal_objective)
            sub_goal_file.close()



    ###### Top Donator List ######

        ## Clear Top Donator Button ##
        def clear_top_don_list(self, widget):
            top_don_con = None
            top_don_con = psycopg2.connect("dbname='%s' user='%s' host='%s' password='%s'" % (db_name, db_user, db_server, db_password))
            top_don_cur = top_don_con.cursor()

            self.top_don_list.clear()
            
            try:
                top_don_cur.execute("DELETE FROM session_stats WHERE Type='top_donator'")
                top_don_con.commit()
                top_don_con.close()   
            except:
                logging.exception('\nException while reseting the top donor list (There is probably no data in the session_stats DB)\n\n')
                top_don_con.close()
            
            return self.top_don_list


        ## Create Top Donator List ##
        def create_top_don_list(self):
            self.top_don_list = gtk.ListStore(str, str)
            return self.top_don_list


        ## Fill Top Donator List ##
        def fill_top_don_list(self):
            top_don_con = None
            top_don_con = psycopg2.connect("dbname='%s' user='%s' host='%s' password='%s'" % (db_name, db_user, db_server, db_password))
            top_don_cur = top_don_con.cursor()

            self.top_don_list.clear()

            try:
                top_don_cur.execute("SELECT Info, Amount FROM session_stats WHERE Type='top_donator'")
                rows = top_don_cur.fetchall()

                top_donator = rows[0][0]
                top_donation_amount = rows[0][1]
                top_donation_amount = '%.2f' % top_donation_amount

                self.top_don_list.append([top_donator, top_donation_amount])
                top_don_con.close()

                # Write to output text file for OBS #
                top_donator_file = open(output_path + 'top_donator.txt', "w")
                top_donator_file.write(top_donator + ': ' + top_donation_amount)
                top_donator_file.close()

                return self.top_don_list
                         
            except IndexError:
                # Disabling this log line because it will log an error everytime the list is empty and the refresh button is pushed #
                # logging.exception('\nException while filling the top donor list (There is probably no data in the session_stats DB, filling it with "None")\n\n')
                self.top_don_list.append(['None', 'None'])
                top_don_con.close()

                # Write to output text file for OBS #
                top_donator_file = open(output_path + 'top_donator.txt', "w")
                top_donator_file.write("")
                top_donator_file.close()
                
                return self.top_don_list

            except:
                logging.exception('\nException while filling the top donor list\n\n')
                self.top_don_list.append(['None', 'None'])
                top_don_con.close()

                # Write to output text file for OBS #
                top_donator_file = open(output_path + 'top_donator.txt', "w")
                top_donator_file.write("")
                top_donator_file.close()

                return self.top_don_list


        ## Create Top Donator TreeView ## 
        def create_top_don_columns(self, top_don_treeView):
        
            rendererText = gtk.CellRendererText()
            column = gtk.TreeViewColumn("User Name", rendererText, text=0)
            column.set_sort_column_id(0)    
            top_don_treeView.append_column(column)
            
            rendererText = gtk.CellRendererText()
            column = gtk.TreeViewColumn("Amount", rendererText, text=1)
            rendererText.set_property('xalign', 1.0)
            column.set_sort_column_id(1)
            top_don_treeView.append_column(column)



    ###### Lost Subscribers Window ######

        ## Clear Lost Subscribers List ##
        def clear_lost_subs_list(self, widget):
            lost_subs_con = None
            lost_subs_con = psycopg2.connect("dbname='%s' user='%s' host='%s' password='%s'" % (db_name, db_user, db_server, db_password))
            lost_subs_cur = lost_subs_con.cursor()

            
            try:
                lost_subs_cur.execute("DELETE FROM lost_subscribers")
                lost_subs_con.commit()
                lost_subs_con.close()   
            except:
                logging.exception('\nException while reseting the lost donor list (There is probably no data in the session_stats DB)\n\n')
                lost_subs_con.close()
            
            return self.lost_subs_list.clear()


        def lost_subs_window(self, widget):

            ## Set Title, Size, and Window Postion ##
            lost_sub_window = gtk.Window()
            lost_sub_window.set_destroy_with_parent(True)
            lost_sub_window.set_title("Lost Subscribers")
            lost_sub_window.set_size_request(350, 360)
            lost_sub_window.set_position(gtk.WIN_POS_MOUSE)
            lost_sub_window.set_border_width(0)


        ## Clear Lost Subscribers Button ##
            lost_subs_clear_btn = gtk.Button('Clear')
            lost_subs_clear_btn.connect("clicked", self.clear_lost_subs_list)
            

        ## Lost Subscriber List ##

            # Make scrolling window 
            lost_subs_list = gtk.ScrolledWindow()
            lost_subs_list.set_size_request(400,300)
            lost_subs_list.set_shadow_type(gtk.SHADOW_ETCHED_IN)
            lost_subs_list.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

            self.lost_subs_list = self.create_lost_subs_list()
            self.fill_lost_subs_list()

            # Make a TreeView
            lost_subs_tree = gtk.TreeView(self.lost_subs_list)
            lost_subs_tree.set_rules_hint(True)
            lost_subs_tree.columns_autosize()
            lost_subs_tree.set_grid_lines(gtk.TREE_VIEW_GRID_LINES_BOTH)
            self.create_lost_subs_columns(lost_subs_tree)

            # Add lost_subs_tree to the Scrolling Window
            lost_subs_list.add(lost_subs_tree)


        ## Lost Subscriber Frame ##
            

            # Create Frame
            lost_subs_frame = gtk.Frame()
            lost_subs_frame.set_label_align(0.5, 0.5)
            lost_subs_vbox = gtk.VBox(False, 8)
            lost_subs_vbox.set_border_width(10)
            lost_subs_frame.add(lost_subs_vbox)

            # Set Spacking between widgets
            lost_subs_vbox.set_spacing(10)
            
            # Add Clear Button and TreeLists to Box
            lost_subs_vbox.add(lost_subs_list)
            lost_subs_vbox.add(lost_subs_clear_btn)
            

            # Horizontal Box inside Vertical Box for Sizing Purposes #
            lost_subs_hbox = gtk.HBox(False, 8)
            lost_subs_hbox.set_border_width(0)
            lost_subs_hbox.pack_start(lost_subs_frame, True, True, 0)

            lost_sub_window.add(lost_subs_hbox)
            lost_sub_window.show_all()


        def create_lost_subs_list(self):
            self.lost_subs_list = gtk.ListStore(str, str, str)
            return self.lost_subs_list


        def fill_lost_subs_list(self):
            lost_subs_con = None
            lost_subs_con = psycopg2.connect("dbname='%s' user='%s' host='%s' password='%s'" % (db_name, db_user, db_server, db_password))
            lost_subs_cur = lost_subs_con.cursor()
            self.lost_subs_list.clear()

            try:
                lost_subs_cur.execute("SELECT username, date_subscribed, date_lost FROM lost_subscribers ORDER BY date_lost desc, time desc")
                rows = lost_subs_cur.fetchall()

                for item in rows:
                    self.lost_subs_list.append([item[0], str(item[1]), str(item[2])])
            
            except IndexError:
                logging.exception('\nException while filling lost Subscribers list (There is probably no data in the lost subscribers DB, filling it with "Loading")\n\n')
                self.lost_subs_list.append(['Loading', 'Loading', 'Loading'])

            lost_subs_con.close()
            return self.lost_subs_list

            

        def create_lost_subs_columns(self, lost_subs_treeView):
        
            rendererText = gtk.CellRendererText()
            column = gtk.TreeViewColumn("User Name", rendererText, text=0)
            column.set_sort_column_id(0)    
            lost_subs_treeView.append_column(column)
            
            rendererText = gtk.CellRendererText()
            column = gtk.TreeViewColumn("Date Subscribed", rendererText, text=1)
            column.set_sort_column_id(1)
            lost_subs_treeView.append_column(column)

            rendererText = gtk.CellRendererText()
            rendererText.props.wrap_width = 240
            column = gtk.TreeViewColumn("Date Lost", rendererText, text=2)
            column.set_sort_column_id(2)
            lost_subs_treeView.append_column(column)



    gobject.threads_init()
    Tundras_Tracker()
    gtk.main()

except:
    logging.exception('\n Everything went horribly wrong :( \n\n')
