# -*- coding: utf-8 -*-

"""
Anki Add-on: Card Stats

Displays stats in a sidebar while reviewing.

For the most part based on the following add-ons:

- Card Info During Review by Damien Elmes (https://ankiweb.net/shared/info/2179254157)
- reviewer_show_cardinfo by Steve AW (https://github.com/steveaw/anki_addons/)

This version of Card Stats combines the sidebar in Damien's add-on with the extra
review log info found in Steve AW's add-on.

Copyright: (c) Glutanimate 2016-2017 <https://glutanimate.com/>
License: GNU AGPLv3 or later <https://www.gnu.org/licenses/agpl.html>
"""

from anki.hooks import addHook
from aqt import mw
from aqt.qt import *
from aqt.webview import AnkiWebView
import aqt.stats

from anki.lang import _
from anki.utils import fmtTimeSpan
from anki.stats import CardStats

import anki
from anki.lang import _, ngettext
import aqt
from aqt import mw, theme
from aqt.utils import tooltip
from aqt.overview import Overview, OverviewContent, OverviewBottomBar

import math
from datetime import datetime, timezone, timedelta, date
import time

showDebug = 0

class StatsSidebar(object):
    def __init__(self, mw):
        self.mw = mw
        self.shown = False
        addHook("showQuestion", self.show)
        addHook("deckClosing", self._update)
        addHook("reviewCleanup", self._update)

    def _addDockable(self, w):
        class DockableWithClose(QDockWidget):
            closed = pyqtSignal()
            def closeEvent(self, evt):
                self.closed.emit()
                QDockWidget.closeEvent(self, evt)
        dock = DockableWithClose(mw)
        dock.setAllowedAreas(Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea)
        dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        dock.setWidget(w)
        mw.addDockWidget(Qt.TopDockWidgetArea, dock)
        return dock

    def _remDockable(self, dock):
        mw.removeDockWidget(dock)

    def show(self):
        if not self.shown:
            class ThinAnkiWebView(AnkiWebView):
                def sizeHint(self):
                    return QSize(200, 100)
            self.web = ThinAnkiWebView()
            self.shown = self._addDockable(self.web)
            self.shown.closed.connect(self._onClosed)
        self._update()

    def hide(self):
        if self.shown:
            self._remDockable(self.shown)
            self.shown = None
            #actionself.mw.form.actionCstats.setChecked(False)

    def toggle(self):
        if self.shown:
            self.hide()
        else:
            self.show()

    def _onClosed(self):
        # schedule removal for after evt has finished
        self.mw.progress.timer(100, self.hide, False)

    #copy and paste from Browser
    #Added IntDate column

    def _update(self):
        lrnSteps = 3
        x = (mw.col.sched.day_cutoff - 86400*7)*1000

        """Calculate progress using weights and card counts from the sched."""
        # Get studdied cards  and true retention stats
        xcards, xfailed, xdistinct, xflunked, xpassed = mw.col.db.first("""
        select
        sum(case when ease >=1 then 1 else 0 end), /* xcards */
        sum(case when ease = 1 then 1 else 0 end), /* xfailed */
        count(distinct cid), /* xdistinct */
        sum(case when ease = 1 and type == 1 then 1 else 0 end), /* xflunked */
        sum(case when ease > 1 and type == 1 then 1 else 0 end) /* xpassed */
        from revlog where id > ?""",x)
        xcards = xcards or 0
        xfailed = xfailed or 0
        xdistinct = xdistinct or 0
        xflunked = xflunked or 0
        xpassed = xpassed or 0

        TR = 1-float(xpassed/(float(max(1,xpassed+xflunked))))
        xagain = float((xfailed)/max(1,(xcards-xpassed)))
        lrnWeight = float((1+(1*xagain*lrnSteps))/1)
        newWeight = float((1+(1*xagain*lrnSteps))/1)
        revWeight = float((1+(1*TR*lrnSteps))/1)

        # Get due and new cards
        new = 0
        lrn = 0
        due = 0

        for tree in self.mw.col.sched.deckDueTree():
            new += tree[4]
            lrn += tree[3]
            due += tree[2]

        #if CountTimesNew == 0: CountTimesNew = 2
        total = (newWeight*new) + (lrnWeight*lrn) + (revWeight*due)
        totalDisplay = int((newWeight*new) + (lrnWeight*lrn) + (revWeight*due))
        #total = new + lrn + due

        # Get studdied cards
        cards, thetime = self.mw.col.db.first(
                """select count(), sum(time)/1000 from revlog where id > ?""",
                (self.mw.col.sched.dayCutoff - 86400) * 1000)

        cards   = cards or 0
        thetime = thetime or 0
        
        ycards, ythetime = self.mw.col.db.first(
                """select count(), sum(time)/1000 from revlog where id > ?""",
                (self.mw.col.sched.dayCutoff - 86400*7) * 1000)

        cards   = cards or 0
        thetime = thetime or 0
        
        totaltotal = cards+totalDisplay
        percenttotal = cards/max(1, totaltotal)*100
        percenttotalrounded = round(cards/max(1, totaltotal)*100,2)
        percentleft = round(100-percenttotal,2)
        
        speed   = thetime / max(1, cards)
        yspeed   = ythetime / max(1, ycards)
        speed = round(speed,2)
        yspeed = round(yspeed,2)
        minutes = (total*speed)/3600
        minutes = round(minutes,2)
        
        hr = (total / max(1, speed))/60

        x = math.floor(thetime/3600)
        y = math.floor((thetime-(x*3600))/60)
    
        hrhr = math.floor(minutes)
        hrmin = math.floor(60*(minutes-hrhr))
        hrsec = ((minutes-hrhr)*60-hrmin)*60

        dt=datetime.today()
        tz = 8 #GMT+ <CHANGE THIS TO YOUR GMT+_ (negative number if you're GMT-)>
        tzsec = tz*3600

        t = timedelta(hours = hrhr, minutes = hrmin, seconds = hrsec)
        left = dt.timestamp()+tzsec+t.total_seconds()

        date_time = datetime.utcfromtimestamp(left).strftime('%Y-%m-%d %H:%M:%S')
        date_time_24H = datetime.strptime(date_time, "%Y-%m-%d %H:%M:%S")
        ETA = date_time_24H.strftime("%I:%M %p")
        
        if not self.shown:
            return

        style = self._style()
        if showDebug:
            self.web.setHtml("""
            <html>
                <head>
                </head>
            <body style="color:white;font-family:Helvetica Neue;">
                <center> 
                {} ({}%) done&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{} ({}%) left&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{} ({}) s/card&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{:02d}:{:02d} spent&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{:02d}:{:02d} more&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;ETA: {}&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{:.2f} New/Lrn Weight&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{:.2f} Rev Weight
                </center>
            </body></html>""".format(cards, percenttotalrounded, totalDisplay, percentleft, speed, yspeed, x, y, hrhr, hrmin, ETA, lrnWeight, revWeight))
        else:
            self.web.setHtml("""
            <html>
                <head>
                </head>
            <body style="color:white;font-family:Helvetica Neue;">
                <center> 
                {} ({}%) done&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{} ({}%) left&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{} ({}) s/card&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{:02d}:{:02d} spent&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{:02d}:{:02d} more&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;ETA: {}
                </center>
            </body></html>""".format(cards, percenttotalrounded, totalDisplay, percentleft, speed, yspeed, x, y, hrhr, hrmin, ETA))
            
    def _style(self):
        from anki import version
        if version.startswith("2.0."):
            return ""
        return "td { font-size: 80%; }"

_cs = StatsSidebar(mw)

def cardStats(on):
    _cs.toggle()

action = QAction(mw)
action.setText("Card Stats")
action.setCheckable(True)
action.setShortcut(QKeySequence("Shift+C"))
mw.form.menuTools.addAction(action)
action.toggled.connect(cardStats)
