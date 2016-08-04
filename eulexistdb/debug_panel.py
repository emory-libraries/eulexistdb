'''
Panel for use with
`django-debug-toolbar <https://django-debug-toolbar.readthedocs.org/>`_.

To install, add:

    'eulexistdb.debug_panel.ExistDBPanel',

to your configured **DEBUG_TOOLBAR_PANELS**.

Reports on the Xqueries run to generate a page, including time to run
the query, arguments passed, and response returned.
'''

from debug_toolbar.panels import Panel

from eulexistdb import db

# implementation based on django-debug-toolbar cache panel


class ExistDBPanel(Panel):

    name = 'ExistDB'
    has_content = True

    template = 'eulexistdb/debug_panel.html'

    def __init__(self, *args, **kwargs):
        super(ExistDBPanel, self).__init__(*args, **kwargs)
        self.total_time = 0
        self.queries = []

        db.xquery_called.connect(self._store_xquery_info)

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

        # remove empty values from kwargs, to simplify display
        for k, val in list(kwargs.iteritems()):
            if val is None:
                del kwargs[k]

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
        return "%(xqueries)d quer%(plural)s in %(time).2fms" % \
               {'xqueries': len(self.queries),
                'plural': 'y' if (len(self.queries) == 1) else 'ies',
                'time': self.total_time}

    def generate_stats(self, request, response):
        # statistics for display in the template
        self.record_stats({
            'total_queries': len(self.queries),
            'queries': self.queries,
            'total_time': self.total_time,
        })
