from anki.hooks import addHook
from aqt import mw
from aqt.gui_hooks import deck_browser_will_render_content, profile_did_open

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

from aqt.gui_hooks import deck_browser_will_render_content, profile_did_open

from aqt import gui_hooks

config = mw.addonManager.getConfig(__name__)

showDebug = config['showDebug']
lrnSteps = config['lrnSteps']
tz = config['tz'] #GMT+ <CHANGE THIS TO YOUR GMT+_ (negative number if you're GMT-)>
nodays = config['nodays'] #how many days ago anki should use to calculate new, learn, relearn, and review weights

def add_info():
    global n_new
    global n_learn
    global n_review
    global n_learn
    global n_relearn
    global n_review1
    global n_review2
    global n_review3
    global n_review4
    global n_review5
    global n_review6
    global n_review7
    global n_reviewmature
    global n_reviewsupermature
    n_new = mw.col.sched.deck_due_tree().new_count
    n_learn = len(mw.col.find_cards("is:due is:learn -is:review prop:ivl=0"))
    n_relearn = len(mw.col.find_cards("is:due is:learn is:review prop:ivl>0"))
    n_review1 = len(mw.col.find_cards("is:due -is:learn is:review prop:ivl=1"))
    n_review2 = len(mw.col.find_cards("is:due -is:learn is:review prop:ivl=2"))
    n_review3 = len(mw.col.find_cards("is:due -is:learn is:review prop:ivl=3"))
    n_review4 = len(mw.col.find_cards("is:due -is:learn is:review prop:ivl=4"))
    n_review5 = len(mw.col.find_cards("is:due -is:learn is:review prop:ivl=5"))
    n_review6 = len(mw.col.find_cards("is:due -is:learn is:review prop:ivl=6"))
    n_review7 = len(mw.col.find_cards("is:due -is:learn is:review prop:ivl>=7 prop:ivl<21"))
    n_reviewmature = len(mw.col.find_cards("is:due -is:learn is:review prop:ivl>=21 prop:ivl<99"))
    n_reviewsupermature = len(mw.col.find_cards("is:due -is:learn is:review prop:ivl>=100"))
    
gui_hooks.main_window_did_init.append(add_info)

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
        x = (mw.col.sched.day_cutoff - 86400*nodays)*1000

        """Calculate progress using weights and card counts from the sched."""
        # Get studdied cards  and true retention stats
        xcards, ythetime, xfailed, xlearn, xlearnpass, xreview, xrelearn, xrelearnpass, xmanual, xflunked, xpassed, xflunked2, xpassed2, xflunked3, xpassed3, xflunked4, xpassed4, xflunked5, xpassed5, xflunked6, xpassed6, xflunked7, xpassed7, xflunked8, xpassed8, xpassed_supermature, xflunked_supermature = mw.col.db.first("""
        select
        sum(case when ease >=1 then 1 else 0 end), /* xcards */
        sum(time)/1000, /* ythetime */
        sum(case when ease = 1 then 1 else 0 end), /* xfailed */
        sum(case when ease = 1 and type == 0 then 1 else 0 end), /* xlearn agains */
        sum(case when ease > 1 and type == 0 then 1 else 0 end), /* xlearn pass */
        sum(case when ease = 1 and type == 1 then 1 else 0 end), /* xreview agains */
        sum(case when ease = 1 and type == 2 then 1 else 0 end), /* xrelearn agains */
        sum(case when ease > 1 and type == 2 then 1 else 0 end), /* xrelearn pass */
        sum(case when ease = 0 then 1 else 0 end), /* manual resched ease 0 */
        sum(case when ease = 1 and type == 1 and lastIvl == 1 then 1 else 0 end), /* xflunked */
        sum(case when ease > 1 and type == 1 and lastIvl == 1 then 1 else 0 end), /* xpassed */
        sum(case when ease = 1 and type == 1 and lastIvl == 2 then 1 else 0 end), /* xflunked2 */
        sum(case when ease > 1 and type == 1 and lastIvl == 2 then 1 else 0 end), /* xpassed2 */
        sum(case when ease = 1 and type == 1 and lastIvl == 3 then 1 else 0 end), /* xflunked3 */
        sum(case when ease > 1 and type == 1 and lastIvl == 3 then 1 else 0 end), /* xpassed3 */
        sum(case when ease = 1 and type == 1 and lastIvl == 4 then 1 else 0 end), /* xflunked4 */
        sum(case when ease > 1 and type == 1 and lastIvl == 4 then 1 else 0 end), /* xpassed4 */
        sum(case when ease = 1 and type == 1 and lastIvl == 5 then 1 else 0 end), /* xflunked5 */
        sum(case when ease > 1 and type == 1 and lastIvl == 5 then 1 else 0 end), /* xpassed5 */
        sum(case when ease = 1 and type == 1 and lastIvl == 6 then 1 else 0 end), /* xflunked6 */
        sum(case when ease > 1 and type == 1 and lastIvl == 6 then 1 else 0 end), /* xpassed6 */ 
        sum(case when ease = 1 and type == 1 and lastIvl between 7 and 21 then 1 else 0 end), /* xflunked7 */
        sum(case when ease > 1 and type == 1 and lastIvl between 7 and 21 then 1 else 0 end), /* xpassed7 */ 
        sum(case when ease = 1 and type == 1 and lastIvl between 22 and 99 then 1 else 0 end), /* xflunked8 */
        sum(case when ease > 1 and type == 1 and lastIvl between 22 and 99 then 1 else 0 end), /* xpassed8 */ 
        sum(case when ease > 1 and type == 1 and lastIvl >= 100 then 1 else 0 end), /* xpassed_supermature */
        sum(case when ease = 1 and type == 1 and lastIvl >= 100 then 1 else 0 end) /* xflunked_supermature */
        from revlog where id > ?""",x)
        xcards = xcards or 0
        ythetime =  ythetime or 0
        xfailed = xfailed or 0
        xlearnpass = xlearnpass or 0
        xlearn = xlearn or 0
        xreview = xreview or 0
        xrelearn = xrelearn or 0
        xrelearnpass = xrelearnpass or 0
        xmanual = xmanual or 0
        xflunked = xflunked or 0
        xpassed = xpassed or 0
        xflunked2 = xflunked2 or 0
        xpassed2 = xpassed2 or 0
        xflunked3 = xflunked3 or 0
        xpassed3 = xpassed3 or 0
        xflunked4 = xflunked4 or 0
        xpassed4 = xpassed4 or 0
        xflunked5 = xflunked5 or 0
        xpassed5 = xpassed5 or 0
        xflunked6 = xflunked6 or 0
        xpassed6 = xpassed6 or 0   
        xflunked7 = xflunked7 or 0
        xpassed7 = xpassed7 or 0 
        xflunked8 = xflunked8 or 0
        xpassed8 = xpassed8 or 0  
        xpassed_supermature = xpassed_supermature or 0
        xflunked_supermature = xflunked_supermature or 0
        
        try:
            xtemp = "%0.2f%%" %(xpassed/float(xpassed+xflunked)*100)
        except ZeroDivisionError:
            xtemp = "N/A"
        try:
            xtemp_supermature = "%0.2f%%" %(xpassed_supermature/float(xpassed_supermature+xflunked_supermature)*100)
        except ZeroDivisionError:
            xtemp_supermature = "N/A"
        try:
            yagain = "%0.2f%%" %(((xfailed)/(xcards))*100)
        except ZeroDivisionError:
            yagain = "N/A"
        
        TR = (float(xflunked/(float(max(1,xpassed+xflunked)))))
        TR2 = (float(xflunked2/(float(max(1,xpassed2+xflunked2)))))
        TR3 = (float(xflunked3/(float(max(1,xpassed3+xflunked3)))))
        TR4 = (float(xflunked4/(float(max(1,xpassed4+xflunked4)))))
        TR5 = (float(xflunked5/(float(max(1,xpassed5+xflunked5)))))
        TR6 = (float(xflunked6/(float(max(1,xpassed6+xflunked6)))))
        TR7 = (float(xflunked7/(float(max(1,xpassed7+xflunked7)))))
        TR8 = (float(xflunked8/(float(max(1,xpassed8+xflunked8)))))
        TR9 = (float(xflunked_supermature/(float(max(1,xpassed_supermature+xflunked_supermature)))))
        
        xlearnagains = float((xlearn)/max(1,(xlearn+xlearnpass)))
        xrelearnagains = float((xrelearn)/max(1,(xrelearn+xrelearnpass)))
        xagain = float((xfailed)/max(1,(xcards)))
        lrnWeight = float((1+(1*xlearnagains*lrnSteps))/1)
        relrnWeight = float((1+(1*xrelearnagains*lrnSteps))/1)
        newWeight = float((1+(1*xagain*lrnSteps))/1)
        revWeight = float((1+(1*TR*lrnSteps))/1)
        revWeight2 = float((1+(1*TR2*lrnSteps))/1)
        revWeight3 = float((1+(1*TR3*lrnSteps))/1)
        revWeight4 = float((1+(1*TR4*lrnSteps))/1)
        revWeight5 = float((1+(1*TR5*lrnSteps))/1)
        revWeight6 = float((1+(1*TR6*lrnSteps))/1)
        revWeight7 = float((1+(1*TR7*lrnSteps))/1)
        revWeight8 = float((1+(1*TR8*lrnSteps))/1)
        revWeight9 = float((1+(1*TR9*lrnSteps))/1)
        
        # Get studdied cards
        cards, thetime, failed, flunked, passed, passed_supermature, flunked_supermature = self.mw.col.db.first(
                """select 
                sum(case when ease >=1 then 1 else 0 end), /* cards */
                sum(time)/1000, /* thetime */
                sum(case when ease = 1 then 1 else 0 end), /* failed */
                sum(case when ease = 1 and type == 1 then 1 else 0 end), /* flunked */
                sum(case when ease > 1 and type == 1 then 1 else 0 end), /* passed */
                sum(case when ease > 1 and type == 1 and lastIvl >= 100 then 1 else 0 end), /* passed_supermature */
                sum(case when ease = 1 and type == 1 and lastIvl >= 100 then 1 else 0 end) /* flunked_supermature */
                from revlog where id > ?""",
                (self.mw.col.sched.day_cutoff - 86400) * 1000)

        cards   = cards or 0
        thetime = thetime or 0
        failed = failed or 0 
        flunked = flunked or 0
        passed = passed or 0
        passed_supermature = passed_supermature or 0
        flunked_supermature = flunked_supermature or 0
        
        #if CountTimesNew == 0: CountTimesNew = 2
        total = (newWeight*n_new) + (lrnWeight*n_learn) + (relrnWeight*n_relearn) + (revWeight*n_review1) + (revWeight2*n_review2) + (revWeight3*n_review3) + (revWeight4*n_review4) + (revWeight5*n_review5) + (revWeight6*n_review6) + (revWeight7*n_review7) + (revWeight8*n_reviewmature) + (revWeight9*n_reviewsupermature)
        
        totalDisplay = round(total)
        #total = new + lrn + due
        
        try:
            temp = "%0.2f%%" %(passed/float(passed+flunked)*100)
        except ZeroDivisionError:
            temp = "N/A"
        try:
            temp_supermature = "%0.2f%%" %(passed_supermature/float(passed_supermature+flunked_supermature)*100)
        except ZeroDivisionError:
            temp_supermature = "N/A"
        try:
            again = "%0.2f%%" %(((failed)/(cards))*100)
        except ZeroDivisionError:
            again = "N/A"
        
        totaltotal = cards+totalDisplay
        percenttotal = cards/max(1, totaltotal)*100
        percenttotalrounded = round(cards/max(1, totaltotal)*100,2)
        percentleft = round(100-percenttotal,2)
        
        speed   = thetime / max(1, cards)
        yspeed   = ythetime / max(1, xcards)
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
                {} ({:.2f}%) done
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                {} ({:.2f}%) left
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                {:.2f} ({:.2f}) s/card
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                {} ({}) AR
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                {} ({}) TR
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                {} ({}) SMTR
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                {:02d}:{:02d} spent
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                {:02d}:{:02d} more
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                ETA: {}<hr>
                
                {:.2f} New Weight 
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                {:.2f} Learn Weight
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                {:.2f} Relearn Weight
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                Learning Cards: {} 
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                Relearning Cards: {}<hr>
                
                1 day: {:.2f}%
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
                2 days: {:.2f}%
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
                3 days: {:.2f}%
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
                4 days: {:.2f}%
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
                5 days: {:.2f}%
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
                6 days: {:.2f}%
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
                Young: {:.2f}%
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
                Mature: {:.2f}%
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
                Super Mature: {:.2f}%<hr>
                
                Learn Agains: {}
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
                Review Agains: {}
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
                Relearn Agains: {}
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
                Manual Agains: {}
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
                Total Agains: {}<hr>
                
                1 day: {:.2f}
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                2 days: {:.2f}
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
                3 days: {:.2f}
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
                4 days: {:.2f}
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
                5 days: {:.2f}
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
                6 days: {:.2f}
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
                Young: {:.2f}
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
                Mature: {:.2f}
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
                Super Mature: {:.2f}<hr>
                1 day: {}
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                2 days: {}
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
                3 days: {}
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
                4 days: {}
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
                5 days: {}
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
                6 days: {}
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
                Young: {}
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
                Mature: {}
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
                Super Mature: {}
                </center>
            </body></html>""".format(cards, percenttotalrounded, totalDisplay, percentleft, speed, yspeed, again, yagain, temp, xtemp, temp_supermature, xtemp_supermature, x, y, hrhr, hrmin, ETA, newWeight, lrnWeight, relrnWeight, n_learn, n_relearn, TR*100, TR2*100, TR3*100, TR4*100, TR5*100, TR6*100, TR7*100, TR8*100, TR9*100, xlearn, xreview, xrelearn, xmanual, xfailed+xmanual, revWeight, revWeight2, revWeight3, revWeight4, revWeight5, revWeight6, revWeight7, revWeight8, revWeight9, n_review1, n_review2, n_review3, n_review4, n_review5, n_review6, n_review7, n_reviewmature, n_reviewsupermature))
        else:
            self.web.setHtml("""
            <html>
                <head>
                </head>
            <body style="color:white;font-family:Helvetica Neue;">
                <center> 
                {} ({:.2f}%) done
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                {} ({:.2f}%) left
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                {:.2f} ({:.2f}) s/card
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                {} ({}) AR
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                {} ({}) TR
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                {} ({}) SMTR
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                {:02d}:{:02d} spent
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                {:02d}:{:02d} more
                &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                ETA: {}
                </center>
            </body></html>""".format(cards, percenttotalrounded, totalDisplay, percentleft, speed, yspeed, again, yagain, temp, xtemp, temp_supermature, xtemp_supermature, x, y, hrhr, hrmin, ETA))
            
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
