# -*- coding: utf-8 -*-
"""RadioDJ control class

author: Robert Langmeier
date: 2019-08-11

The goal of this package is to be able to gather informations for a given instance
for one radio station

"""

__version__ = '0.9'
__author__ = 'Robert Langmeier'


# %%

import os, sys
import logging
import re
import time

import win32con
import win32gui
import win32process
import win32api


# %%

class RadioDjConst:
    
    def __init__(self, version=None, onair_text='CLOCK', song_text='Copyright:', cart_text=['S', 'V']):

        # Text strings to find parent handle
        # They must be unique to avoid false detection
        # version number may be usefull in the future if something change in controls
        
        self.ONAIR_HANDLE = onair_text
        self.ONAIR_REMAINING = 11

        self.SONG_HANDLE = song_text
        self.SONG_ARTIST = 16
        self.SONG_TITLE = 17

        if type(cart_text) is not list:
            raise ValueError("A list is required for cart_text")
        self.CART_HANDLE = cart_text
        
        self.CART_NUMBER = 9
        self.CART_STRTIME = 4
        self.CART_DURATION = 5
        self.CART_ARTIST = 7
        self.CART_TITLE = 10


# %%

class RadioDj:

    
    def __init__(self, name, slogan=None):
        self.name = name
        self.slogan = slogan
        self.with_slogan = slogan != None
        if self.with_slogan:
            self.title_rex = '^%(name)s - %(slogan)s - RadioDJ v(\d+\.\d+\.\d+\.\d+)' % vars(self)
        else:
            self.title_rex = '^%(name)s - ([^-]*)- RadioDJ v(\d+\.\d+\.\d+\.\d+)' % vars(self)
        self.version = None
        self.hwnd = None
        self.const = None

        
    def get_window_handle(self):
        """Iterate over all top windows and get the handle and version
        number for the desired RadioDJ instance or None if not found."""
        
        def windowEnumerationHandler(hwnd, top_windows):
            top_windows.append((hwnd, win32gui.GetWindowText(hwnd)))

        self.version = None
        self.hwnd = None

        top_windows = []
        win32gui.EnumWindows(windowEnumerationHandler, top_windows)
        for win in top_windows:
            m = re.match(self.title_rex, win[1], re.I)       
            if m != None:
                if self.with_slogan:
                    self.version = m.group(1)
                else:
                    self.slogan = m.group(1).strip()
                    self.version = m.group(2)
                self.hwnd = win[0]
                self.title = win[1]
                return self.hwnd
        return None

    
    def set_const(self, const):
        self.const = const


    def is_iconised(self):
        return win32gui.IsIconic(self.hwnd)


    def activate(self):
        
        # Works when the screen is locked
        win32gui.ShowWindow(self.hwnd, win32con.SW_NORMAL)


    def set_foreground_window(self):
        if win32gui.GetForegroundWindow() != self.hwnd:
            mtid, mpid = win32process.GetWindowThreadProcessId(win32gui.GetForegroundWindow())
            tid, pid = win32process.GetWindowThreadProcessId(self.hwnd)
            if mtid != tid:
                win32process.AttachThreadInput(mtid, tid, 1)
                win32gui.SetForegroundWindow(self.hwnd)
#            win32gui.SetFocus(hwnd)
#                win32process.AttachThreadInput(mtid, tid, FALSE)
            else:
                win32gui.SetForegroundWindow(self.hwnd)


    def get_handle_map(self):
    
        def EnumChildHandler(hwnd, lparam):

            # Parent
            hwndpar = win32gui.GetParent(hwnd)
            # Initial text (to serch for some known position)
            wintext = win32gui.GetWindowText(hwnd)

            # Handle level
            lvl = self.hwndlvl[hwndpar] + 1
            self.hwndlvl[hwnd] = self.hwndlvl.get(hwnd, lvl)

            # Put all together
            self.hwndmap[hwndpar] = self.hwndmap.get(hwndpar, list())
            self.hwndmap[hwndpar].append([hwnd, lvl, wintext])
            return True
    
        self.hwndmap = {self.hwnd: list()}
        self.hwndlvl = {self.hwnd: 0}
        
        win32gui.EnumChildWindows(self.hwnd, EnumChildHandler, 0)


    def init_handles(self):
        self.hwnd_onair = self.get_onair_handle()
        self.hwnd_song = self.get_song_handle()
        self.hwnd_next = self.get_next_handle()    


    def get_handle_by_text(self, text):
        
        for hwnd, recs in self.hwndmap.items():
            for rec in recs:
                if rec[2] == text:
                    # Text handle, parent handle, level
                    return rec[0], hwnd, rec[1]        
        return 0, None, None


    def get_onair_handle(self):
        hwnd, hwndpar, lvl = self.get_handle_by_text(self.const.ONAIR_HANDLE)   # 'CLOCK'
        return hwndpar


    def get_song_handle(self):
        hwnd, hwndpar, lvl = self.get_handle_by_text(self.const.SONG_HANDLE)    # 'Copyright:'
        return hwndpar


    def get_next_handle(self):
        hwnd_next = []
        for hwnd, recs in self.hwndmap.items():
            if len(recs) < 3:
                continue
            if recs[0][2] == self.const.CART_HANDLE[0] and \
               recs[1][2] == self.const.CART_HANDLE[1] and recs[2][2] == '':
                hwnd_next.append(hwnd)
        return hwnd_next

    def get_remainging_time(self):
        return win32gui.GetWindowText(self.hwndmap[self.hwnd_onair][self.const.ONAIR_REMAINING][0])


    def get_onair_song(self):
        artist = win32gui.GetWindowText(self.hwndmap[self.hwnd_song][self.const.SONG_ARTIST][0])
        title = win32gui.GetWindowText(self.hwndmap[self.hwnd_song][self.const.SONG_TITLE][0])
        return artist, title

 
    def get_next_songs(self):
        
        next_songs = []
        for hwnd in self.hwnd_next:
            hwnd_cart = self.hwndmap[hwnd]
            cart = win32gui.GetWindowText(hwnd_cart[self.const.CART_NUMBER][0])
            strtime = win32gui.GetWindowText(hwnd_cart[self.const.CART_STRTIME][0])
            duration = win32gui.GetWindowText(hwnd_cart[self.const.CART_DURATION][0])
            artist = win32gui.GetWindowText(hwnd_cart[self.const.CART_ARTIST][0])
            title = win32gui.GetWindowText(hwnd_cart[self.const.CART_TITLE][0])
            next_songs.append([cart, artist, title, strtime, duration])
        
        return next_songs

    
    def is_dead(self):
        
        r = []
        for i in range(4):
            r.append(self.get_remainging_time())
            win32api.Sleep(1100)
        return all(x == r[0] for x in r[1:])


    def click_play_next(self):
        if self.is_iconised():
            self.activate()
        self.set_foreground_window()
        win32api.Sleep(200)
        rect = win32gui.GetWindowRect(self.hwndmap[self.hwnd_onair][15][0])
        x = rect[0]
        y = rect[1]
        print(win32api.SetCursorPos((x, y)))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)

        
    def dump_handles(self):
        snod = '+-'
        slvl = '| ' 
        stck = [[self.hwnd, 0]]
        while len(stck):
        
            hcur, hpos = stck[-1]
            lvl = len(stck) - 1

            sdec = slvl * lvl + snod
            htit = win32gui.GetWindowText(hcur)
            htit = htit.split('\r\n')
            if not stck[-1][1]:
                print(sdec, hcur, htit)

            if hcur not in funky24.hwndmap:
                stck.pop()
                stck[-1][1] += 1
                continue
            hlst = funky24.hwndmap[hcur]
            if hpos + 1 > len(hlst):
                stck.pop()
                if len(stck):
                    stck[-1][1] += 1
                continue                
            hnxt = hlst[hpos][0]
            stck.append([hlst[hpos][0], 0])


# %% Simple test

if __name__ == "__main__":

    # Search RadioDJ instance for one radio
    funky24 = RadioDj('Funky24')
    if funky24.get_window_handle() is None:
        raise KeyError("RadioDJ instance not found for '{}' radio station".format(funky24.name))
    print("RadioDJ version {} is running for '{}' radio station".format(funky24.version, funky24.name))
    
    # Set constant used to find all handles
    funky24.set_const(RadioDjConst(funky24.version))

    funky24.get_handle_map()
    funky24.init_handles()

    for i in range(3):
        print(funky24.get_remainging_time())
        time.sleep(1)    

    print(funky24.get_onair_song())
    print(funky24.get_next_songs())
