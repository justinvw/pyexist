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
from __future__ import with_statement
import os, httplib, urlparse, base64, threading
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

#_update_tmpl = '''
#<xupdate:modifications version="1.0" xmlns:xupdate="http://www.xmldb.org/xupdate">
#	%s
#</xupdate:modifications>
#'''

_modifications_tmpl = '''
<modifications version="1.0" xmlns="http://www.xmldb.org/xupdate">
	%s
</modifications>
'''
_update_tmpl = '''<update select="doc('%s')%s">%s</update>'''
_remove_tmpl = '''<remove select="doc('%s')%s">%s</remove>'''
_rename_tmpl = '''<rename select="doc('%s')%s">%s</rename>'''
_append_tmpl = '''<append select="doc('%s')%s">%s</append>'''
_insert_before_tmpl = '''<insert-before select="doc('%s')%s">%s</insert-before>'''
_insert_after_tmpl = '''<insert-after select="doc('%s')%s">%s</insert-after>'''

class ExistDB(object):
    """
    The eXist-db connection object.
    """
    RESULT_NS = 'http://exist.sourceforge.net/NS/exist'

    class Error(Exception):
        pass

    def __init__(self, host_uri, collection = '', query_cls = XQuery):
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
        self.username = auth.split(':', 1)[0]
        self.password = auth[len(self.username) + 1:]
        self.lock     = threading.Lock()
        self.conn     = httplib.HTTP(netloc)
        self.path     = ''
        if uri.path:
            self.path += '/' + uri.path.strip('/')
        if collection:
            self.path += '/' + collection.strip('/')
        self.query_cls = query_cls

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
        with self.lock:
            self.conn.putrequest('PUT', self.path + '/' + doc)
            self._authenticate()
            self.conn.putheader('Content-Type',   'text/xml')
            self.conn.putheader('Content-Length', str(len(xml)))
            self.conn.endheaders()
            self.conn.send(xml)

            errcode, errmsg, headers = self.conn.getreply()
            if errcode != 201:
                raise ExistDB.Error('Error %d: %s' % (errcode, errmsg))
            self.conn.close()

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
        with self.lock:
            self.conn.putrequest('DELETE', self.path + '/' + doc)
            self._authenticate()
            self.conn.endheaders()

            errcode, errmsg, headers = self.conn.getreply()
            if errcode != 200:
                raise ExistDB.Error('Error %d: %s' % (errcode, errmsg))
            self.conn.close()

    def xupdate(self, doc, modification='update', select='', value=None):
        """
        Use the XUpdate (http://xmldb-org.sourceforge.net/xupdate/) methods to
        apply modifications to documents.
        
        @type   doc: string
        @param  doc: A document name.
        @type   modification: string
        @param  modification: The modification you wish to apply (update, remove, rename, append, insert-before, insert-after)
        @type   select: string
        @param  select: The XQuery Expression used to select the nodes you wish to modify
        @type   value: string
        @param  value: The contents of the modification (can be empty, e.g. in case of a removal)
        """
        if modification is 'append':
            thequery = _modifications_tmpl %(_append_tmpl %('/db' + self.path \
                + '/' + doc, select, value))
        elif modification is 'remove':
            thequery = _modifications_tmpl %(_remove_tmpl %('/db' + self.path \
                + '/' + doc, select, value))
        elif modification is 'rename':
            thequery = _modifications_tmpl %(_rename_tmpl %('/db' + self.path \
                + '/' + doc, select, value))
        elif modification is 'insert-before':
            thequery = _modifications_tmpl %(_insert_before_tmpl %('/db' + self.path \
                + '/' + doc, select, value))
        elif modification is 'insert-after':
            thequery = _modifications_tmpl %(_insert_after_tmpl %('/db' + self.path \
                + '/' + doc, select, value))
        else:
            thequery = _modifications_tmpl %(_update_tmpl %('/db' + self.path \
                + '/' + doc, select, value))
        
        with self.lock:
            self.conn.putrequest('POST', self.path + '/' + doc)
            self._authenticate()
            self.conn.putheader('Content-Type', 'text/xml')
            self.conn.putheader('Content-Length', str(len(thequery)))
            self.conn.endheaders()
            self.conn.send(thequery)
            
            errcode, errmsg, headers = self.conn.getreply()
            if errcode not in (200, 202):
                raise ExistDB.Error('Error %d: %s' % (errcode, errmsg))

            response = self.conn.getfile().read()
            self.conn.close()
        return response

    def _post(self, thequery, start = 1, max = None):
        args = ''
        if start is not None:
            args += ' start="%d"' % start
        if max is None:
            args += ' max="-1"'
        else:
            args += ' max="%d"' % max
        thequery = _query_tmpl % (args, thequery)

        with self.lock:
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
            self.conn.close()
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
        return self.query_cls(self, thequery, **kwargs)

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
