# file eulexistdb/management/commands/existdb.py
# 
#   Copyright 2010,2011 Emory University Libraries
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import time
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from eulexistdb.db import ExistDB

class Command(BaseCommand):    
    help = """Tasks for managing eXist-db index configuration file.

Available subcommands:
  load-index      - load index configuration file to eXist
  show-index      - show the contents of index configuration file currently in eXist
  index-info      - show information about index configuration file in eXist (owner, date modified, etc.)
  remove-index    - remove index configuration from eXist
  reindex         - reindex the configured eXist collection with the loaded index
  """

    arg_list = ['load-index', 'show-index', 'index-info', 'remove-index', 'reindex']

    args = ' | '. join(arg_list)

    # FIXME/TODO: possibly convert into a django LabelCommand 
    
    def handle(self, *args, **options):
        if not len(args) or args[0] == 'help':
            print self.help
            return

        cmd = args[0]
        if cmd not in self.arg_list:
            print "Command '%s' not recognized" % cmd
            print self.help
            return

        # check for required settings (used in all modes)
        if not hasattr(settings, 'EXISTDB_ROOT_COLLECTION') or not settings.EXISTDB_ROOT_COLLECTION:
            raise CommandError("EXISTDB_ROOT_COLLECTION setting is missing")
            return
        if not hasattr(settings, 'EXISTDB_INDEX_CONFIGFILE') or not settings.EXISTDB_INDEX_CONFIGFILE:
            raise CommandError("EXISTDB_INDEX_CONFIGFILE setting is missing")
            return

        collection = settings.EXISTDB_ROOT_COLLECTION
        index = settings.EXISTDB_INDEX_CONFIGFILE

        try:
            # Explicitly request no timeout (even if one is configured
            # in django settings), since some tasks (such as
            # reindexing) could take a while.
            self.db = ExistDB(timeout=None)

            # check there is already an index config
            hasindex = self.db.hasCollectionIndex(collection)

            # for all commands but load, nothing to do if config collection does not exist
            if not hasindex and cmd != 'load-index':
                raise CommandError("Collection %s has no index configuration" % collection)

            if cmd == 'load-index':
                # load collection index to eXist

                # no easy way to check if index is different, but give some info to user to help indicate
                if hasindex:
                    index_desc = self.db.describeDocument(self.db._collectionIndexPath(collection))
                    print "Collection already has an index configuration; last modified %s\n" % index_desc['modified']
                else:
                    print "This appears to be a new index configuration\n"

                message =  "eXist index configuration \n collection:\t%s\n index file:\t%s" % (collection, index)

                success = self.db.loadCollectionIndex(collection, open(index))
                if success:
                    print "Succesfully updated %s" % message
                    print """
If your collection already contains data and the index configuration
is new or has changed, you should reindex the collection.
            """
                else:
                    raise CommandError("Failed to update %s" % message)

            elif cmd == 'show-index':
                # show the contents of the the collection index config file in exist
                print self.db.getDoc(self.db._collectionIndexPath(collection))

            elif cmd == 'index-info':
                # show information about the collection index config file in exist
                index_desc = self.db.describeDocument(self.db._collectionIndexPath(collection))
                for field, val in index_desc.items():
                    print "%s:\t%s" % (field, val)

            elif cmd == 'remove-index':
                # remove any collection index in eXist
                if self.db.removeCollectionIndex(collection):
                    print "Removed collection index configuration for %s" % collection
                else:
                    raise CommandError("Failed to remove collection index configuration for %s" % collection)


            elif cmd == 'reindex':
                # reindex the collection
                if not self.db.hasCollection(collection):
                    raise CommandError("Collection %s does not exist" % collection)

                print "Reindexing collection %s" % collection
                print "-- If you have a large collection, this may take a while."
                start_time = time.time()
                success = self.db.reindexCollection(collection)
                end_time = time.time()
                if success:
                    print "Successfully reindexed collection %s" % collection
                    print "Reindexing took %.2f seconds" % (end_time - start_time)
                else:
                    print "Failed to reindexed collection %s" % collection
                    print "-- Check that the configured exist user is in the exist DBA group."


        except Exception as err:
            # better error messages would be nice...
            raise CommandError(err)

