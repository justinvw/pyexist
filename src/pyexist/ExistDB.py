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
import os, httplib, urlparse, base64
from XQuery import XQuery

_query_tmpl = '''
<query xmlns="http://exist.sourceforge.net/NS/exist"%s>
  <text><![CDATA[ %s ]]></text>
  <properties>
    <property name="indent" value="yes"/>
    <property name="pretty-print" value="yes"/>
  </properties>
</query>
'''

class ExistDB(object):
    """
    The eXist-db connection object.
    """
    RESULT_NS = 'http://exist.sourceforge.net/NS/exist'

    class Error(Exception):
        pass

    def __init__(self, host_uri, collection):
        """
        Create a new database connection using the REST protocol.

        @type  host_uri: string
        @param host_uri: The host and port number, separated by a ':' character.
        @type  collection: string
        @param collection: A database (collection) name.
        """
        # Python's urlparse module is so bad it hurts.
        uri = urlparse.urlparse('http://' + host_uri)
        try:
            auth, netloc = uri.netloc.split('@', 1)
        except ValueError:
            auth   = ''
            netloc = uri.netloc
        self.username   = auth.split(':', 1)[0]
        self.password   = auth[len(self.username) + 1:]
        self.collection = collection
        self.conn       = httplib.HTTP(netloc)
        self.path       = collection

    def _authenticate(self):
        if not self.username:
            return
        if self.password:
            auth = self.username + ':' + self.password
        else:
            auth = self.username
        auth = base64.encodestring(auth).strip()
        self.conn.putheader('Authorization', 'Basic ' + auth)

    def store(self, doc, xml):
        """
        Imports the XML string into the document with the given name.

        @type  doc: string
        @param doc: A document name.
        @type  xml: string
        @param xml: The XML to import.
        """
        self.conn.putrequest('PUT', self.path + '/' + doc)
        self._authenticate()
        self.conn.putheader('Content-Type',   'text/xml')
        self.conn.putheader('Content-Length', str(len(xml)))
        self.conn.endheaders()
        self.conn.send(xml)

        errcode, errmsg, headers = self.conn.getreply()
        if errcode != 201:
            raise ExistDB.Error('Error %d: %s' % (errcode, errmsg))

    def store_file(self, filename, doc = None):
        """
        Like store(), but reads the XML from a file instead. If the document
        name is None, it defaults to the basename of the file, with the .xml
        extension removed.

        @type  filename: string
        @param filename: The name of an XML file.
        @type  doc: string
        @param doc: A document name.
        """
        if doc is None:
            doc = os.path.splitext(os.path.basename(filename))[0]
        xml = open(filename).read()
        self.store(doc, xml)

    def delete(self, doc):
        """
        Deletes the document with the given name. Raises an error if the
        document does not exist.

        @type  doc: string
        @param doc: A document name.
        """
        self.conn.putrequest('DELETE', self.path + '/' + doc)
        self._authenticate()
        self.conn.endheaders()

        errcode, errmsg, headers = self.conn.getreply()
        if errcode != 200:
            raise ExistDB.Error('Error %d: %s' % (errcode, errmsg))

    def _post(self, thequery, start = 1, max = None):
        args = ''
        if start is not None:
            args += ' start="%d"' % start
        if max is None:
            args += ' max="-1"'
        else:
            args += ' max="%d"' % max
        thequery = _query_tmpl % (args, thequery)
        self.conn.putrequest('POST', self.path)
        self._authenticate()
        self.conn.putheader('Content-Type',   'text/xml')
        self.conn.putheader('Content-Length', str(len(thequery)))
        self.conn.endheaders()
        self.conn.send(thequery)

        errcode, errmsg, headers = self.conn.getreply()
        if errcode not in (200, 202):
            raise ExistDB.Error('Error %d: %s' % (errcode, errmsg))

        response = self.conn.getfile().read()
        return response

    def query(self, thequery, **kwargs):
        """
        Creates a new query object from the given xquery statement.
        The given kwargs are parameters that are replaced in the query.
        The query may use the following syntax for such parameters::

            let myvar := '%{myparam}'

        Passing "myparam = 'foo'" will produce the following query::

            let myvar := 'foo'

        @type  thequery: string
        @param thequery: The xquery as a string.
        @type  kwargs: dict
        @param kwargs: Parameters to pass into the query.
        @rtype:  XQuery
        @return: An XQuery object.
        """
        return XQuery(self, thequery, **kwargs)

    def query_from_file(self, filename, **kwargs):
        """
        Like query(), but reads the xquery from the file with the given
        name instead.

        @type  filename: string
        @param filename: The name of a file containing the query.
        @type  kwargs: dict
        @param kwargs: Parameters to pass into the query.
        @rtype:  XQuery
        @return: An XQuery object.
        """
        thequery = open(filename, 'r').read()
        return self.query(thequery, **kwargs)
