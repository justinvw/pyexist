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
from XQuery import XQuery

class XQueryMinidom(XQuery):
    """
    Like XQuery(), but uses xml.dom.minidom instead of lxml.etree.
    """
    def count(self):
        if self.len is None:
            # Execute the query with minimal results to see the count.
            tree     = self[0:1]
            self.len = int(tree.get('{' + self.db.RESULT_NS + '}hits'))
        return self.len

    def __getitem__(self, key):
        from xml.dom.minidom import parseString

        # Execute the query and parse the response.
        response = self._getitem_post(key)
        tree     = parseString(response)
        root     = tree.documentElement

        # Catch errors.
        if root.tagName == 'exception':
            try:
                element = root.getElementsByTagName('message')[0]
                error   = element.firstChild.data
            except AttributeError:
                error = result
            raise self.db.Error('server said: ' + error \
                              + 'in response to ' + self.query)

        self.len = int(root.getAttribute('exist:hits'))
        result   = root.getElementsByTagName('result')[0]
        return result
