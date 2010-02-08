# Copyright (C) 2010 Samuel Abels.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2, as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
from lxml import etree

def _escape(arg):
    return str(arg).replace(r"'", r"''")

def _replacetags(string, **kwargs):
    for key, value in kwargs.iteritems():
        string = string.replace('%{' + key + '}', _escape(value))
    return string

class XQuery(object):
    """
    Represents a query. You normally don't want to create an XQuery instance
    directly, try using ExistDB.query() instead.
    
    Query evaluation is lazy, so the query is not executed before the result
    is requested using either the slice notation (such as query[0], or
    query[1:20]) or calling one of the count() or length methods.
    """
    def __init__(self, db, query, **kwargs):
        """
        Use ExistDB.query() instead of creating a query directly.

        @type  db: ExistDB
        @param db: The parent database instance.
        @type  query: string
        @param query: The xquery as a string.
        @type  kwargs: dict
        @param kwargs: Parameters to pass into the query.
        """
        self.db    = db
        self.query = _replacetags(query, **kwargs)
        self.len   = None

    @staticmethod
    def fromfile(db, filename, **kwargs):
        """
        Like the constructor, but reads the query from the file with the given
        name instead.

        @type  db: ExistDB
        @param db: The parent database instance.
        @type  filename: string
        @param filename: The name of a file containing an xquery statement.
        @type  kwargs: dict
        @param kwargs: Parameters to pass into the query.
        """
        return XQuery(db, open(file).read(), **kwargs)

    def __iter__(self):
        """
        Iterate over all results.

        @rtype:  iterator
        @return: An iterable the walks over all results.
        """
        return self[:].__iter__()

    def __len__(self):
        """
        Returns the number of matches that the query produces.

        @rtype:  long
        @return: The number of rows returned by the query.
        """
        return self.count()

    def count(self):
        """
        Equivalent to len().

        @rtype:  long
        @return: The number of rows returned by the query.
        """
        if self.len is None:
            # Execute the query with minimal results to see the count.
            tree     = self[0:1]
            self.len = int(tree.get('{' + self.db.RESULT_NS + '}hits'))
        return self.len

    def __getitem__(self, key):
        """
        Returns the range of matching items.

        @rtype:  lxml.etree._Element
        @return: The XML tree that is produced by the query.
        """
        # Parse the slice argument.
        if isinstance(key, int):
            start = int(key) + 1
            max   = 1
        elif isinstance(key, slice):
            # Try not to use key.indices(self.count()), as that would require
            # an extra query for counting the items.
            start = key.start is not None and key.start or 0
            step  = key.step or 1
            if step != 1:
                raise TypeError('slice step %d is not supported' % step)
            if key.stop is None:
                max = None
            else:
                max = key.stop - start
            start = start + 1
        else:
            raise TypeError('invalid key argument ' + repr(key))

        # Execute the query and parse the response.
        result = self.db._post(self.query, start = start, max = max)
        tree   = etree.fromstring(result)

        # Catch errors.
        if tree.tag == 'exception':
            try:
                error = tree.find('message').text
            except AttributeError:
                error = etree.tounicode(tree)
            raise self.db.Error('server said: ' + error)

        self.len = int(tree.get('{' + self.db.RESULT_NS + '}hits'))
        return tree
