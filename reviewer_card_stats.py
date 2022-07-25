from anki.hooks import addHook
from aqt.qt import *
from aqt.webview import AnkiWebView
from aqt import mw
import math
from datetime import datetime, timedelta
from aqt import gui_hooks

config = mw.addonManager.getConfig(__name__)

show_debug = config['show_debug']
lrn_steps = config['lrn_steps']
tz = config['tz']  # GMT+ <CHANGE THIS TO YOUR GMT+_ (negative number if you're GMT-)>
no_days = config['no_days']  # how many days ago anki should use to calculate new, learn, relearn, and review weights


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
    global n_review_mature
    global n_review_super_mature
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
    n_review_mature = len(mw.col.find_cards("is:due -is:learn is:review prop:ivl>=21 prop:ivl<99"))
    n_review_super_mature = len(mw.col.find_cards("is:due -is:learn is:review prop:ivl>=100"))


gui_hooks.main_window_did_init.append(add_info)


class StatsSidebar(object):
    def __init__(self, mw):
        self.mw = mw
        self.shown = False
        addHook("showQuestion", self.show)
        addHook("deckClosing", self.show)
        addHook("reviewCleanup", self.show)

    def _add_dockable(self, w):
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

    @staticmethod
    def _rem_dockable(dock):
        mw.removeDockWidget(dock)

    def show(self):
        if not self.shown:
            class ThinAnkiWebView(AnkiWebView):
                @staticmethod
                def size_hint():
                    return QSize(200, 100)

            self.web = ThinAnkiWebView()
            self.shown = self._add_dockable(self.web)
            self.shown.closed.connect(self._on_closed)
        self._update()

    def hide(self):
        if self.shown:
            self._rem_dockable(self.shown)
            self.shown = None
            # actionself.mw.form.actionCstats.setChecked(False)

    def toggle(self):
        if self.shown:
            self.hide()
        else:
            self.show()

    def _on_closed(self):
        # schedule removal for after evt has finished
        self.mw.progress.timer(100, self.hide, False)

    # copy and paste from Browser
    # Added IntDate column

    def _update(self):
        add_info()
        x = (mw.col.sched.day_cutoff - 86400 * no_days) * 1000

        """Calculate progress using weights and card counts from the sched."""
        # Get studied cards  and true retention stats
        x_cards, y_the_time, x_failed, x_learn, x_learn_pass, x_review, x_re_learn, x_re_learn_pass, x_manual, x_flunked, x_passed, x_flunked2, x_passed2, x_flunked3, x_passed3, x_flunked4, x_passed4, x_flunked5, x_passed5, x_flunked6, x_passed6, x_flunked7, x_passed7, x_flunked8, x_passed8, x_passed_super_mature, x_flunked_super_mature = mw.col.db.first("""
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
        sum(case when ease = 1 and type == 1 and lastIvl == 1 then 1 else 0 end), /* x_flunked */
        sum(case when ease > 1 and type == 1 and lastIvl == 1 then 1 else 0 end), /* x_passed */
        sum(case when ease = 1 and type == 1 and lastIvl == 2 then 1 else 0 end), /* x_flunked2 */
        sum(case when ease > 1 and type == 1 and lastIvl == 2 then 1 else 0 end), /* x_passed2 */
        sum(case when ease = 1 and type == 1 and lastIvl == 3 then 1 else 0 end), /* x_flunked3 */
        sum(case when ease > 1 and type == 1 and lastIvl == 3 then 1 else 0 end), /* x_passed3 */
        sum(case when ease = 1 and type == 1 and lastIvl == 4 then 1 else 0 end), /* x_flunked4 */
        sum(case when ease > 1 and type == 1 and lastIvl == 4 then 1 else 0 end), /* x_passed4 */
        sum(case when ease = 1 and type == 1 and lastIvl == 5 then 1 else 0 end), /* x_flunked5 */
        sum(case when ease > 1 and type == 1 and lastIvl == 5 then 1 else 0 end), /* x_passed5 */
        sum(case when ease = 1 and type == 1 and lastIvl == 6 then 1 else 0 end), /* x_flunked6 */
        sum(case when ease > 1 and type == 1 and lastIvl == 6 then 1 else 0 end), /* x_passed6 */ 
        sum(case when ease = 1 and type == 1 and lastIvl between 7 and 21 then 1 else 0 end), /* x_flunked7 */
        sum(case when ease > 1 and type == 1 and lastIvl between 7 and 21 then 1 else 0 end), /* x_passed7 */ 
        sum(case when ease = 1 and type == 1 and lastIvl between 22 and 99 then 1 else 0 end), /* x_flunked8 */
        sum(case when ease > 1 and type == 1 and lastIvl between 22 and 99 then 1 else 0 end), /* x_passed8 */ 
        sum(case when ease > 1 and type == 1 and lastIvl >= 100 then 1 else 0 end), /* x_passed_super_mature */
        sum(case when ease = 1 and type == 1 and lastIvl >= 100 then 1 else 0 end) /* x_flunked_super_mature */
        from revlog where id > ?""", x)
        x_cards = x_cards or 0
        y_the_time = y_the_time or 0
        x_failed = x_failed or 0
        x_learn_pass = x_learn_pass or 0
        x_learn = x_learn or 0
        x_review = x_review or 0
        x_re_learn = x_re_learn or 0
        x_re_learn_pass = x_re_learn_pass or 0
        x_manual = x_manual or 0
        x_flunked = x_flunked or 0
        x_passed = x_passed or 0
        x_flunked2 = x_flunked2 or 0
        x_passed2 = x_passed2 or 0
        x_flunked3 = x_flunked3 or 0
        x_passed3 = x_passed3 or 0
        x_flunked4 = x_flunked4 or 0
        x_passed4 = x_passed4 or 0
        x_flunked5 = x_flunked5 or 0
        x_passed5 = x_passed5 or 0
        x_flunked6 = x_flunked6 or 0
        x_passed6 = x_passed6 or 0
        x_flunked7 = x_flunked7 or 0
        x_passed7 = x_passed7 or 0
        x_flunked8 = x_flunked8 or 0
        x_passed8 = x_passed8 or 0
        x_passed_super_mature = x_passed_super_mature or 0
        x_flunked_super_mature = x_flunked_super_mature or 0

        try:
            x_temp = "%0.2f%%" % (x_passed / float(x_passed + x_flunked) * 100)
        except ZeroDivisionError:
            x_temp = "N/A"
        try:
            x_temp_super_mature = "%0.2f%%" % (
                    x_passed_super_mature / float(x_passed_super_mature + x_flunked_super_mature) * 100)
        except ZeroDivisionError:
            x_temp_super_mature = "N/A"
        try:
            y_again = "%0.2f%%" % ((x_failed / x_cards) * 100)
        except ZeroDivisionError:
            y_again = "N/A"

        tr = (float(x_flunked / (float(max(1, x_passed + x_flunked)))))
        tr2 = (float(x_flunked2 / (float(max(1, x_passed2 + x_flunked2)))))
        tr3 = (float(x_flunked3 / (float(max(1, x_passed3 + x_flunked3)))))
        tr4 = (float(x_flunked4 / (float(max(1, x_passed4 + x_flunked4)))))
        tr5 = (float(x_flunked5 / (float(max(1, x_passed5 + x_flunked5)))))
        tr6 = (float(x_flunked6 / (float(max(1, x_passed6 + x_flunked6)))))
        tr7 = (float(x_flunked7 / (float(max(1, x_passed7 + x_flunked7)))))
        tr8 = (float(x_flunked8 / (float(max(1, x_passed8 + x_flunked8)))))
        tr9 = (float(x_flunked_super_mature / (float(max(1, x_passed_super_mature + x_flunked_super_mature)))))

        x_learn_agains = float(x_learn / max(1, (x_learn + x_learn_pass)))
        x_relearn_agains = float(x_re_learn / max(1, (x_re_learn + x_re_learn_pass)))
        x_again = float(x_failed / max(1, x_cards))
        lrn_weight = float((1 + (1 * x_learn_agains * lrn_steps)) / 1)
        re_lrn_weight = float((1 + (1 * x_relearn_agains * lrn_steps)) / 1)
        new_weight = float((1 + (1 * x_again * lrn_steps)) / 1)
        rev_weight = float((1 + (1 * tr * lrn_steps)) / 1)
        rev_weight2 = float((1 + (1 * tr2 * lrn_steps)) / 1)
        rev_weight3 = float((1 + (1 * tr3 * lrn_steps)) / 1)
        rev_weight4 = float((1 + (1 * tr4 * lrn_steps)) / 1)
        rev_weight5 = float((1 + (1 * tr5 * lrn_steps)) / 1)
        rev_weight6 = float((1 + (1 * tr6 * lrn_steps)) / 1)
        rev_weight7 = float((1 + (1 * tr7 * lrn_steps)) / 1)
        rev_weight8 = float((1 + (1 * tr8 * lrn_steps)) / 1)
        rev_weight9 = float((1 + (1 * tr9 * lrn_steps)) / 1)

        # Get studdied cards
        cards, the_time, failed, flunked, passed, passed_super_mature, flunked_super_mature = self.mw.col.db.first(
            """select 
                sum(case when ease >=1 then 1 else 0 end), /* cards */
                sum(time)/1000, /* thetime */
                sum(case when ease = 1 then 1 else 0 end), /* failed */
                sum(case when ease = 1 and type == 1 then 1 else 0 end), /* flunked */
                sum(case when ease > 1 and type == 1 then 1 else 0 end), /* passed */
                sum(case when ease > 1 and type == 1 and lastIvl >= 100 then 1 else 0 end), /* passed_super_mature */
                sum(case when ease = 1 and type == 1 and lastIvl >= 100 then 1 else 0 end) /* flunked_super_mature */
                from revlog where id > ?""",
            (self.mw.col.sched.day_cutoff - 86400) * 1000)

        cards = cards or 0
        the_time = the_time or 0
        failed = failed or 0
        flunked = flunked or 0
        passed = passed or 0
        passed_super_mature = passed_super_mature or 0
        flunked_super_mature = flunked_super_mature or 0

        # if CountTimesNew == 0: CountTimesNew = 2
        total = (new_weight * n_new) + (lrn_weight * n_learn) + (re_lrn_weight * n_relearn) + (
                rev_weight * n_review1) + (
                        rev_weight2 * n_review2) + (rev_weight3 * n_review3) + (rev_weight4 * n_review4) + (
                        rev_weight5 * n_review5) + (rev_weight6 * n_review6) + (rev_weight7 * n_review7) + (
                        rev_weight8 * n_review_mature) + (rev_weight9 * n_review_super_mature)

        total_display = round(total)
        # total = new + lrn + due

        try:
            temp = "%0.2f%%" % (passed / float(passed + flunked) * 100)
        except ZeroDivisionError:
            temp = "N/A"
        try:
            temp_super_mature = "%0.2f%%" % (
                    passed_super_mature / float(passed_super_mature + flunked_super_mature) * 100)
        except ZeroDivisionError:
            temp_super_mature = "N/A"
        try:
            again = "%0.2f%%" % ((failed / cards) * 100)
        except ZeroDivisionError:
            again = "N/A"

        total_total = cards + total_display
        percent_total = cards / max(1, total_total) * 100
        percent_total_rounded = round(cards / max(1, total_total) * 100, 2)
        percent_left = round(100 - percent_total, 2)

        speed = the_time / max(1, cards)
        y_speed = y_the_time / max(1, x_cards)
        speed = round(speed, 2)
        y_speed = round(y_speed, 2)
        minutes = (total * speed) / 3600
        minutes = round(minutes, 2)

        x = math.floor(the_time / 3600)
        y = math.floor((the_time - (x * 3600)) / 60)

        hrhr = math.floor(minutes)
        hr_min = math.floor(60 * (minutes - hrhr))
        hr_sec = ((minutes - hrhr) * 60 - hr_min) * 60

        dt = datetime.today()

        tz_sec = tz * 3600

        t = timedelta(hours=hrhr, minutes=hr_min, seconds=hr_sec)
        left = dt.timestamp() + tz_sec + t.total_seconds()

        date_time = datetime.utcfromtimestamp(left).strftime('%Y-%m-%d %H:%M:%S')
        date_time_24_h = datetime.strptime(date_time, "%Y-%m-%d %H:%M:%S")
        eta = date_time_24_h.strftime("%I:%M %p")

        if not self.shown:
            return

        if show_debug:
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
            </body></html>""".format(cards, percent_total_rounded, total_display, percent_left, speed, y_speed, again,
                                     y_again, temp, x_temp, temp_super_mature, x_temp_super_mature, x, y, hrhr, hr_min,
                                     eta,
                                     new_weight, lrn_weight, re_lrn_weight, n_learn, n_relearn, tr * 100, tr2 * 100,
                                     tr3 * 100, tr4 * 100, tr5 * 100, tr6 * 100, tr7 * 100, tr8 * 100, tr9 * 100,
                                     x_learn, x_review, x_re_learn, x_manual, x_failed + x_manual, rev_weight,
                                     rev_weight2,
                                     rev_weight3, rev_weight4, rev_weight5, rev_weight6, rev_weight7, rev_weight8,
                                     rev_weight9,
                                     n_review1, n_review2, n_review3, n_review4, n_review5, n_review6, n_review7,
                                     n_review_mature, n_review_super_mature))
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
            </body></html>""".format(cards, percent_total_rounded, total_display, percent_left, speed, y_speed, again,
                                     y_again, temp, x_temp, temp_super_mature, x_temp_super_mature, x, y, hrhr, hr_min,
                                     eta))

    @staticmethod
    def _style():
        from anki import version
        if version.startswith("2.0."):
            return ""
        return "td { font-size: 80%; }"


_cs = StatsSidebar(mw)


def card_stats(on):
    _cs.toggle()


action = QAction(mw)
action.setText("Review Stats")
action.setCheckable(True)
action.setShortcut(QKeySequence("Shift+C"))
mw.form.menuTools.addAction(action)
action.toggled.connect(card_stats)
