try:
    from debug_toolbar.panels import Panel
except ImportError:
    Panel = None

import time
from django.dispatch import Signal
from django.template.loader import render_to_string

import eulexistdb
from eulexistdb import db


# implementation based on django-debug-toolbar cache panel


xquery_called = Signal(providing_args=[
    "time_taken", "name", "return_value", "args", "kwargs"])


class ExistDBTracker(db.ExistDB):
    # subclass ExistDB in order to track query calls

    def query(self, *args, **kwargs):
        start = time.time()
        value = super(ExistDBTracker, self).query(*args, **kwargs)
        total_time = time.time() - start
        xquery_called.send(sender=self.__class__, time_taken=total_time,
                           name='query', return_value=value,
                           args=args, kwargs=kwargs)
        return value


class ExistDBPanel(Panel):

    name = 'ExistDB'
    has_content = True

    template = 'eulexistdb/debug_panel.html'

    def __init__(self, *args, **kwargs):
        super(ExistDBPanel, self).__init__(*args, **kwargs)
        self.total_time = 0
        self.queries = []

        xquery_called.connect(self._store_xquery_info)

    def _store_xquery_info(self, sender, name=None, time_taken=0,
                          return_value=None, args=None, kwargs=None,
                          trace=None, **kw):
        # process xquery signal and store information for display
        if name != 'query':
            return

        # if xml result has a serialize method (i.e., is an xmlobject)
        # use that for display
        if hasattr(return_value, 'serialize'):
            return_value = return_value.serialize()

        time_taken *= 1000
        self.total_time += time_taken
        self.queries.append({
            'time': time_taken,
            'args': args,
            'kwargs': kwargs,
            'return_value': return_value
        })

    @property
    def nav_title(self):
        return self.name

    def url(self):
        return ''

    def title(self):
        return self.name

    def nav_subtitle(self):
        return "%(xqueries)d queries in %(time).2fms" % \
               {'xqueries': len(self.queries), 'time': self.total_time}

    def enable_instrumentation(self):
        # patch tracking existdb subclass in for the real one
        db.RealExistDB = db.ExistDB
        eulexistdb.db.ExistDB = ExistDBTracker
        # also patch into the manager module (already imported)
        eulexistdb.manager.ExistDB = db.ExistDB

    def disable_instrumentation(self):
        db.ExistDB = db.RealExistDB
        eulexistdb.manager.ExistDB = db.ExistDB

    def generate_stats(self, request, response):
        # statistics for display in the template
        self.record_stats({
            'total_queries': len(self.queries),
            'queries': self.queries,
            'total_time': self.total_time,
        })
