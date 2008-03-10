# -*- coding: utf-8 -*-
## $Id$

## This file is part of CDS Invenio.
## Copyright (C) 2002, 2003, 2004, 2005, 2006, 2007, 2008 CERN.
##
## CDS Invenio is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 2 of the
## License, or (at your option) any later version.
##
## CDS Invenio is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with CDS Invenio; if not, write to the Free Software Foundation, Inc.,
## 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

# pylint: disable-msg=C0301

__revision__ = "$Id$"

import urllib
import time
import cgi
import gettext
import string
import locale

from invenio.config import \
     CFG_WEBSEARCH_ADVANCEDSEARCH_PATTERN_BOX_WIDTH, \
     CFG_WEBSEARCH_AUTHOR_ET_AL_THRESHOLD, \
     CFG_WEBSEARCH_USE_ALEPH_SYSNOS, \
     CFG_BIBRANK_SHOW_READING_STATS, \
     CFG_BIBRANK_SHOW_DOWNLOAD_STATS, \
     CFG_BIBRANK_SHOW_DOWNLOAD_GRAPHS, \
     CFG_BIBRANK_SHOW_CITATION_LINKS, \
     CFG_BIBRANK_SHOW_CITATION_STATS, \
     CFG_BIBRANK_SHOW_CITATION_GRAPHS, \
     CFG_WEBSEARCH_RSS_TTL, \
     cdslang, \
     cdsname, \
     cdsnameintl, \
     CFG_VERSION, \
     weburl, \
     supportemail
from invenio.dbquery import run_sql
from invenio.messages import gettext_set_language
#from invenio.search_engine_config import CFG_EXPERIMENTAL_FEATURES
from invenio.urlutils import make_canonical_urlargd, drop_default_urlargd, create_html_link, create_url
from invenio.htmlutils import nmtoken_from_string
from invenio.webinterface_handler import wash_urlargd

from invenio.websearch_external_collections import external_collection_get_state

def get_fieldvalues(recID, tag):
    """Return list of field values for field TAG inside record RECID.
       FIXME: should be imported commonly for search_engine too."""
    out = []
    if tag == "001___":
        # we have asked for recID that is not stored in bibXXx tables
        out.append(str(recID))
    else:
        # we are going to look inside bibXXx tables
        digit = tag[0:2]
        bx = "bib%sx" % digit
        bibx = "bibrec_bib%sx" % digit
        query = "SELECT bx.value FROM %s AS bx, %s AS bibx WHERE bibx.id_bibrec='%s' AND bx.id=bibx.id_bibxxx AND bx.tag LIKE '%s'" \
                "ORDER BY bibx.field_number, bx.tag ASC" % (bx, bibx, recID, tag)
        res = run_sql(query)
        for row in res:
            out.append(row[0])
    return out

class Template:

    # This dictionary maps CDS Invenio language code to locale codes (ISO 639)
    tmpl_localemap = {
        'bg': 'bg_BG',
        'ca': 'ca_ES',
        'de': 'de_DE',
        'el': 'el_GR',
        'en': 'en_US',
        'es': 'es_ES',
        'pt': 'pt_BR',
        'fr': 'fr_FR',
        'it': 'it_IT',
        'ru': 'ru_RU',
        'sk': 'sk_SK',
        'cs': 'cs_CZ',
        'no': 'no_NO',
        'sv': 'sv_SE',
        'uk': 'uk_UA',
        'ja': 'ja_JA',
        'pl': 'pl_PL',
        'hr': 'hr_HR',
        'zh_CN': 'zh_CN',
        'zh_TW': 'zh_TW',
        }
    tmpl_default_locale = "en_US" # which locale to use by default, useful in case of failure

    # Type of the allowed parameters for the web interface for search results
    search_results_default_urlargd = {
        'cc': (str, cdsname),
        'c': (list, []),
        'p': (str, ""), 'f': (str, ""),
        'rg': (int, 10),
        'sf': (str, ""),
        'so': (str, "d"),
        'sp': (str, ""),
        'rm': (str, ""),
        'of': (str, "hb"),
        'ot': (list, []),
        'as': (int, 0),
        'p1': (str, ""), 'f1': (str, ""), 'm1': (str, ""), 'op1':(str, ""),
        'p2': (str, ""), 'f2': (str, ""), 'm2': (str, ""), 'op2':(str, ""),
        'p3': (str, ""), 'f3': (str, ""), 'm3': (str, ""),
        'sc': (int, 0),
        'jrec': (int, 0),
        'recid': (int, -1), 'recidb': (int, -1), 'sysno': (str, ""),
        'id': (int, -1), 'idb': (int, -1), 'sysnb': (str, ""),
        'action': (str, "search"),
        'action_search': (str, ""),
        'action_browse': (str, ""),
        'd1': (str, ""),
        'd1y': (int, 0), 'd1m': (int, 0), 'd1d': (int, 0),
        'd2': (str, ""),
        'd2y': (int, 0), 'd2m': (int, 0), 'd2d': (int, 0),
        'dt': (str, ""),
        'ap': (int, 1),
        'verbose': (int, 0),
        'ec': (list, []),
        }

    # ...and for search interfaces
    search_interface_default_urlargd = {
        'as': (int, 0),
        'verbose': (int, 0)}

    # ...and for RSS feeds
    rss_default_urlargd = {'c'  : (list, []),
                           'cc' : (str, ""),
                           'p'  : (str, ""),
                           'f'  : (str, ""),
                           'p1' : (str, ""),
                           'f1' : (str, ""),
                           'm1' : (str, ""),
                           'op1': (str, ""),
                           'p2' : (str, ""),
                           'f2' : (str, ""),
                           'm2' : (str, ""),
                           'op2': (str, ""),
                           'p3' : (str, ""),
                           'f3' : (str, ""),
                           'm3' : (str, "")}

    tmpl_openurl_accepted_args = {
            'genre' : (str, ''),
            'aulast' : (str, ''),
            'aufirst' : (str, ''),
            'auinit' : (str, ''),
            'auinit1' : (str, ''),
            'auinitm' : (str, ''),
            'issn' : (str, ''),
            'eissn' : (str, ''),
            'coden' : (str, ''),
            'isbn' : (str, ''),
            'sici' : (str, ''),
            'bici' : (str, ''),
            'title' : (str, ''),
            'stitle' : (str, ''),
            'atitle' : (str, ''),
            'volume' : (str, ''),
            'part' : (str, ''),
            'issue' : (str, ''),
            'spage' : (str, ''),
            'epage' : (str, ''),
            'pages' : (str, ''),
            'artnum' : (str, ''),
            'date' : (str, ''),
            'ssn' : (str, ''),
            'quarter' : (str, ''),
            'url_ver' : (str, ''),
            'ctx_ver' : (str, ''),
            'rft_val_fmt' : (str, ''),
            'rfr_id' : (str, ''),
            'rft.atitle' : (str, ''),
            'rft.title' : (str, ''),
            'rft.jtitle' : (str, ''),
            'rft.stitle' : (str, ''),
            'rft.date' : (str, ''),
            'rft.volume' : (str, ''),
            'rft.issue' : (str, ''),
            'rft.spage' : (str, ''),
            'rft.epage' : (str, ''),
            'rft.pages' : (str, ''),
            'rft.artnumber' : (str, ''),
            'rft.issn' : (str, ''),
            'rft.eissn' : (str, ''),
            'rft.aulast' : (str, ''),
            'rft.aufirst' : (str, ''),
            'rft.auinit' : (str, ''),
            'rft.auinit1' : (str, ''),
            'rft.auinitm' : (str, ''),
            'rft.ausuffix' : (str, ''),
            'rft.au' : (list, []),
            'rft.aucorp' : (str, ''),
            'rft.isbn' : (str, ''),
            'rft.coden' : (str, ''),
            'rft.sici' : (str, ''),
            'rft.genre' : (str, 'unknown'),
            'rft.chron' : (str, ''),
            'rft.ssn' : (str, ''),
            'rft.quarter' : (int, ''),
            'rft.part' : (str, ''),
            'rft.btitle' : (str, ''),
            'rft.isbn' : (str, ''),
            'rft.atitle' : (str, ''),
            'rft.place' : (str, ''),
            'rft.pub' : (str, ''),
            'rft.edition' : (str, ''),
            'rft.tpages' : (str, ''),
            'rft.series' : (str, ''),
    }

    def tmpl_openurl2invenio(self, openurl_data):
        """ Return an Invenio url corresponding to a search with the data
        included in the openurl form map.
        """

        from invenio.search_engine import perform_request_search

        aulast = openurl_data['rft.aulast'] or openurl_data['aulast']
        aufirst = openurl_data['rft.aufirst'] or openurl_data['aufirst']
        auinit = openurl_data['rft.auinit'] or \
                 openurl_data['auinit'] or \
                 openurl_data['rft.auinit1'] + ' ' + openurl_data['rft.auinitm'] or \
                 openurl_data['auinit1'] + ' ' + openurl_data['auinitm'] or  aufirst[:1]
        auinit = auinit.upper()

        if aulast and aufirst:
            author_query = 'author:"%s, %s" or author:"%s, %s"' % (aulast, aufirst, aulast, auinit)
        elif aulast and auinit:
            author_query = 'author:"%s, %s"' % (aulast, auinit)
        else:
            author_query = ''

        title = openurl_data['rft.atitle'] or \
                openurl_data['atitle'] or \
                openurl_data['rft.btitle'] or \
                openurl_data['rft.title'] or \
                openurl_data['title']

        if title:
            title_query = 'title:"%s"' % title
        else:
            title_query = ''

        jtitle = openurl_data['rft.stitle'] or \
                 openurl_data['stitle'] or \
                 openurl_data['rft.jtitle'] or \
                 openurl_data['title']

        if jtitle:
            journal_query = 'journal:"%s"' % jtitle
        else:
            journal_query = ''

        isbn = openurl_data['rft.isbn'] or \
               openurl_data['isbn']

        if isbn:
            isbn_query = '020__a:"%s"' % isbn
        else:
            isbn_query = ''

        issn = openurl_data['rft.eissn'] or \
               openurl_data['eissn'] or \
               openurl_data['rft.issn'] or \
               openurl_data['issn']

        if issn:
            issn_query = '022__a:"%s"' % issn
        else:
            issn_query = ''

        coden = openurl_data['rft.coden'] or openurl_data['coden']

        if coden:
            coden_query = '030__a:"%s"' % coden
        else:
            coden_query = ''

        if openurl_data['rfr_id'].startswith('info:doi/'):
            doi_query = '773__a:"%s"' % openurl_data['rfr_id'][len('info:doi/'):]
        else:
            doi_query = ''

        if doi_query:
            if perform_request_search(p=doi_query):
                return '%s/search%s' % (weburl, make_canonical_urlargd({
                    'p' : doi_query,
                    'sc' : 1,
                    'of' : 'hd'}, {}))
        if isbn_query:
            if perform_request_search(p=isbn_query):
                return '%s/search%s' % (weburl, make_canonical_urlargd({
                    'p' : isbn_query,
                    'sc' : 1,
                    'of' : 'hd'}, {}))
        if coden_query:
            if perform_request_search(p=coden_query):
                return '%s/search%s' % (weburl, make_canonical_urlargd({
                    'p' : coden_query,
                    'sc' : 1,
                    'of' : 'hd'}, {}))
        if author_query and title_query:
            if perform_request_search(p='%s and %s' % (title_query, author_query)):
                return '%s/search%s' % (weburl, make_canonical_urlargd({
                    'p' : '%s and %s' % (title_query, author_query),
                    'sc' : 1,
                    'of' : 'hd'}, {}))
        if title_query:
            if perform_request_search(p=title_query):
                return '%s/search%s' % (weburl, make_canonical_urlargd({
                    'p' : title_query,
                    'sc' : 1,
                    'of' : 'hb'}, {}))
        if title:
            return '%s/search%s' % (weburl, make_canonical_urlargd({
                    'p' : title,
                    'sc' : 1,
                    'of' : 'hb'}, {}))
        return ''

    def build_search_url(self, known_parameters={}, **kargs):
        """ Helper for generating a canonical search
        url. 'known_parameters' is the list of query parameters you
        inherit from your current query. You can then pass keyword
        arguments to modify this query.

           build_search_url(known_parameters, of="xm")

        The generated URL is absolute.
        """

        parameters = {}
        parameters.update(known_parameters)
        parameters.update(kargs)

        # Now, we only have the arguments which have _not_ their default value
        parameters = drop_default_urlargd(parameters, self.search_results_default_urlargd)

        # Asking for a recid? Return a /record/<recid> URL
        if 'recid' in parameters:
            target = "%s/record/%d" % (weburl, parameters['recid'])
            del parameters['recid']
            target += make_canonical_urlargd(parameters, self.search_results_default_urlargd)
            return target

        return "%s/search%s" % (weburl, make_canonical_urlargd(parameters, self.search_results_default_urlargd))

    def build_search_interface_url(self, known_parameters={}, **kargs):
        """ Helper for generating a canonical search interface URL."""

        parameters = {}
        parameters.update(known_parameters)
        parameters.update(kargs)

        c = parameters['c']
        del parameters['c']

        # Now, we only have the arguments which have _not_ their default value
        if c and c != cdsname:
            base = weburl + '/collection/' + urllib.quote(c)
        else:
            base = weburl
        return create_url(base, drop_default_urlargd(parameters, self.search_results_default_urlargd))

    def build_rss_url(self, known_parameters,  **kargs):
        """Helper for generating a canonical RSS URL"""

        parameters = {}
        parameters.update(known_parameters)
        parameters.update(kargs)

        # Keep only interesting parameters
        argd = wash_urlargd(parameters, self.rss_default_urlargd)

        if argd:
            # Handle 'c' differently since it is a list
            c = argd.get('c', [])
            del argd['c']
            # Create query, and drop empty params
            args = make_canonical_urlargd(argd, self.rss_default_urlargd)
            if c != []:
                # Add collections
                c = [urllib.quote(coll) for coll in c]
                args += '&amp;c=' + '&amp;c='.join(c)

        return weburl + '/rss' + args

    def tmpl_record_page_header_content(self, req, recid, ln):
        """ Provide extra information in the header of /record pages """

        _ = gettext_set_language(ln)

        title = get_fieldvalues(recid, "245__a")

        if title:
            title = _("Record") + '#%d: %s' %(recid, cgi.escape(title[0]))
        else:
            title = _("Record") + ' #%d' % recid

        keywords = ', '.join(get_fieldvalues(recid, "6531_a"))
        description = ' '.join(get_fieldvalues(recid, "520__a"))
        description += "\n"
        description += '; '.join(get_fieldvalues(recid, "100__a") + get_fieldvalues(recid, "700__a"))

        return [cgi.escape(x, True) for x in (title, description, keywords)]

    def tmpl_navtrail_links(self, as, ln, dads):
        """
        Creates the navigation bar at top of each search page (*Home > Root collection > subcollection > ...*)

        Parameters:

          - 'as' *bool* - Should we display an advanced search box?

          - 'ln' *string* - The language to display

          - 'weburl' *string* - The base URL for the site

          - 'separator' *string* - The separator between two consecutive collections

          - 'dads' *list* - A list of parent links, eachone being a dictionary of ('name', 'longname')
        """
        out = []
        for url, name in dads:
            out.append(create_html_link(self.build_search_interface_url(c=url, as=as, ln=ln), {}, cgi.escape(name), {'class': 'navtrail'}))

        return ' &gt; '.join(out)

    def tmpl_webcoll_body(self, ln, collection, te_portalbox,
                          searchfor, np_portalbox, narrowsearch,
                          focuson, instantbrowse, ne_portalbox):

        """ Creates the body of the main search page.

        Parameters:

          - 'ln' *string* - language of the page being generated

          - 'collection' - collection id of the page being generated

          - 'te_portalbox' *string* - The HTML code for the portalbox on top of search

          - 'searchfor' *string* - The HTML code for the search options

          - 'np_portalbox' *string* - The HTML code for the portalbox on bottom of search

          - 'searchfor' *string* - The HTML code for the search categories (left bottom of page)

          - 'focuson' *string* - The HTML code for the "focuson" categories (right bottom of page)

          - 'ne_portalbox' *string* - The HTML code for the bottom of the page
        """

        if not narrowsearch:
            narrowsearch = instantbrowse

        body = '''
                <form name="search" action="%(weburl)s/search" method="get">
                %(searchfor)s
                %(np_portalbox)s
                <table cellspacing="0" cellpadding="0" border="0">
                  <tr>
                    <td valign="top">%(narrowsearch)s</td>
               ''' % {
                 'weburl' : weburl,
                 'searchfor' : searchfor,
                 'np_portalbox' : np_portalbox,
                 'narrowsearch' : narrowsearch
               }
        if focuson:
            body += """<td valign="top">""" + focuson + """</td>"""
        body += """</tr></table>
            %(ne_portalbox)s
               </form>""" % {'ne_portalbox' : ne_portalbox}
        return body

    def tmpl_portalbox(self, title, body):
        """Creates portalboxes based on the parameters
        Parameters:

          - 'title' *string* - The title of the box

          - 'body' *string* - The HTML code for the body of the box

        """
        out = """<div class="portalbox">
                    <div class="portalboxheader">%(title)s</div>
                    <div class="portalboxbody">%(body)s</div>
                 </div>""" % {'title' : cgi.escape(title), 'body' : body}

        return out

    def tmpl_searchfor_simple(self, ln, collection_id, collection_name, record_count, middle_option):
        """Produces simple *Search for* box for the current collection.

        Parameters:

          - 'ln' *string* - The language to display

          - 'header' *string* - header of search form

          - 'middle_option' *string* - HTML code for the options (any field, specific fields ...)
        """

        # load the right message language
        _ = gettext_set_language(ln)

        out = '''
        <!--create_searchfor_simple()-->
        '''

        argd = drop_default_urlargd({'ln': ln, 'cc': collection_id, 'sc': 1},
                                    self.search_results_default_urlargd)

        # Only add non-default hidden values
        for field, value in argd.items():
            out += self.tmpl_input_hidden(field, value)


        header = _("Search %s records for:") % \
                 self.tmpl_nbrecs_info(record_count, "","")
        asearchurl = self.build_search_interface_url(c=collection_id, as=1, ln=ln)

        # print commentary start:
        out += '''
        <table class="searchbox">
         <thead>
          <tr align="left">
           <th colspan="3" class="searchboxheader">%(header)s</th>
          </tr>
         </thead>
         <tbody>
          <tr valign="baseline">
           <td class="searchboxbody" align="left"><input type="text" name="p" size="40" value="" /></td>
           <td class="searchboxbody" align="left">%(middle_option)s</td>
           <td class="searchboxbody" align="left">
             <input class="formbutton" type="submit" name="action_search" value="%(msg_search)s" />
             <input class="formbutton" type="submit" name="action_browse" value="%(msg_browse)s" /></td>
          </tr>
          <tr valign="baseline">
           <td class="searchboxbody" colspan="3" align="right">
             <small>
               <a href="%(weburl)s/help/search-tips%(langlink)s">%(msg_search_tips)s</a> ::
               %(asearch)s
             </small>
           </td>
          </tr>
         </tbody>
        </table>
        <!--/create_searchfor_simple()-->
        ''' % {'ln' : ln,
               'langlink': ln != cdslang and '?ln=' + ln or '',
               'weburl' : weburl,
               'asearch' : create_html_link(asearchurl, {}, _('Advanced Search')),
               'header' : header,
               'middle_option' : middle_option,
               'msg_search' : _('Search'),
               'msg_browse' : _('Browse'),
               'msg_search_tips' : _('Search Tips')}

        return out

    def tmpl_searchfor_advanced(self,
                                ln,                  # current language
                                collection_id,
                                collection_name,
                                record_count,
                                middle_option_1, middle_option_2, middle_option_3,
                                searchoptions,
                                sortoptions,
                                rankoptions,
                                displayoptions,
                                formatoptions
                                ):
        """
          Produces advanced *Search for* box for the current collection.

          Parameters:

            - 'ln' *string* - The language to display

            - 'weburl' *string* - The base URL for the site

            - 'ssearchurl' *string* - The URL to simple search form

            - 'header' *string* - header of search form

            - 'middle_option_1' *string* - HTML code for the first row of options (any field, specific fields ...)

            - 'middle_option_2' *string* - HTML code for the second row of options (any field, specific fields ...)

            - 'middle_option_3' *string* - HTML code for the third row of options (any field, specific fields ...)

            - 'searchoptions' *string* - HTML code for the search options

            - 'sortoptions' *string* - HTML code for the sort options

            - 'rankoptions' *string* - HTML code for the rank options

            - 'displayoptions' *string* - HTML code for the display options

            - 'formatoptions' *string* - HTML code for the format options

        """

        # load the right message language
        _ = gettext_set_language(ln)

        out = '''
        <!--create_searchfor_advanced()-->
        '''

        argd = drop_default_urlargd({'ln': ln, 'as': 1, 'cc': collection_id, 'sc': 1},
                                    self.search_results_default_urlargd)

        # Only add non-default hidden values
        for field, value in argd.items():
            out += self.tmpl_input_hidden(field, value)


        header = _("Search %s records for") % \
                 self.tmpl_nbrecs_info(record_count, "","")
        header += ':'
        ssearchurl = self.build_search_interface_url(c=collection_id, as=0, ln=ln)

        out += '''
        <table class="searchbox">
         <thead>
          <tr>
           <th class="searchboxheader" colspan="3">%(header)s</th>
          </tr>
         </thead>
         <tbody>
          <tr valign="bottom">
            <td class="searchboxbody" style="white-space: nowrap;">
                %(matchbox_m1)s<input type="text" name="p1" size="40" value="" />
            </td>
            <td class="searchboxbody" style="white-space: nowrap;">%(middle_option_1)s</td>
            <td class="searchboxbody">%(andornot_op1)s</td>
          </tr>
          <tr valign="bottom">
            <td class="searchboxbody" style="white-space: nowrap;">
                %(matchbox_m2)s<input type="text" name="p2" size="40" value="" />
            </td>
            <td class="searchboxbody">%(middle_option_2)s</td>
            <td class="searchboxbody">%(andornot_op2)s</td>
          </tr>
          <tr valign="bottom">
            <td class="searchboxbody" style="white-space: nowrap;">
                %(matchbox_m3)s<input type="text" name="p3" size="40" value="" />
            </td>
            <td class="searchboxbody">%(middle_option_3)s</td>
            <td class="searchboxbody" style="white-space: nowrap;">
              <input class="formbutton" type="submit" name="action_search" value="%(msg_search)s" />
              <input class="formbutton" type="submit" name="action_browse" value="%(msg_browse)s" /></td>
          </tr>
          <tr valign="bottom">
            <td colspan="3" class="searchboxbody" align="right">
              <small>
                <a href="%(weburl)s/help/search-tips%(langlink)s">%(msg_search_tips)s</a> ::
                %(ssearch)s
              </small>
            </td>
          </tr>
         </tbody>
        </table>
        <!-- @todo - more imports -->
        ''' % {'ln' : ln,
               'langlink': ln != cdslang and '?ln=' + ln or '',
               'weburl' : weburl,
               'ssearch' : create_html_link(ssearchurl, {}, _("Simple Search")),
               'header' : header,

               'matchbox_m1' : self.tmpl_matchtype_box('m1', ln=ln),
               'middle_option_1' : middle_option_1,
               'andornot_op1' : self.tmpl_andornot_box('op1', ln=ln),

               'matchbox_m2' : self.tmpl_matchtype_box('m2', ln=ln),
               'middle_option_2' : middle_option_2,
               'andornot_op2' : self.tmpl_andornot_box('op2', ln=ln),

               'matchbox_m3' : self.tmpl_matchtype_box('m3', ln=ln),
               'middle_option_3' : middle_option_3,

               'msg_search' : _("Search"),
               'msg_browse' : _("Browse"),
               'msg_search_tips' : _("Search Tips")}

        if (searchoptions):
            out += """<table class="searchbox">
                      <thead>
                       <tr>
                         <th class="searchboxheader">
                           %(searchheader)s
                         </th>
                       </tr>
                      </thead>
                      <tbody>
                       <tr valign="bottom">
                        <td class="searchboxbody">%(searchoptions)s</td>
                       </tr>
                      </tbody>
                     </table>""" % {
                       'searchheader' : _("Search options:"),
                       'searchoptions' : searchoptions
                     }

        out += """<table class="searchbox">
                   <thead>
                    <tr>
                      <th class="searchboxheader">
                        %(added)s
                      </th>
                      <th class="searchboxheader">
                        %(until)s
                      </th>
                    </tr>
                   </thead>
                   <tbody>
                    <tr valign="bottom">
                      <td class="searchboxbody">%(added_or_modified)s %(date_added)s</td>
                      <td class="searchboxbody">%(date_until)s</td>
                    </tr>
                   </tbody>
                  </table>
                  <table class="searchbox">
                   <thead>
                    <tr>
                      <th class="searchboxheader">
                        %(msg_sort)s
                      </th>
                      <th class="searchboxheader">
                        %(msg_display)s
                      </th>
                      <th class="searchboxheader">
                        %(msg_format)s
                      </th>
                    </tr>
                   </thead>
                   <tbody>
                    <tr valign="bottom">
                      <td class="searchboxbody">%(sortoptions)s %(rankoptions)s</td>
                      <td class="searchboxbody">%(displayoptions)s</td>
                      <td class="searchboxbody">%(formatoptions)s</td>
                    </tr>
                   </tbody>
                  </table>
                  <!--/create_searchfor_advanced()-->
              """ % {

                    'added' : _("Added/modified since:"),
                    'until' : _("until:"),
                    'added_or_modified': self.tmpl_inputdatetype(ln=ln),
                    'date_added' : self.tmpl_inputdate("d1", ln=ln),
                    'date_until' : self.tmpl_inputdate("d2", ln=ln),

                    'msg_sort' : _("Sort by:"),
                    'msg_display' : _("Display results:"),
                    'msg_format' : _("Output format:"),
                    'sortoptions' : sortoptions,
                    'rankoptions' : rankoptions,
                    'displayoptions' : displayoptions,
                    'formatoptions' : formatoptions
                  }
        return out

    def tmpl_matchtype_box(self, name='m', value='', ln='en'):
        """Returns HTML code for the 'match type' selection box.

          Parameters:

            - 'name' *string* - The name of the produced select

            - 'value' *string* - The selected value (if any value is already selected)

            - 'ln' *string* - the language to display
        """

        # load the right message language
        _ = gettext_set_language(ln)

        out = """
        <select name="%(name)s">
        <option value="a"%(sela)s>%(opta)s</option>
        <option value="o"%(selo)s>%(opto)s</option>
        <option value="e"%(sele)s>%(opte)s</option>
        <option value="p"%(selp)s>%(optp)s</option>
        <option value="r"%(selr)s>%(optr)s</option>
        </select>
        """ % {'name' : name,
               'sela' : self.tmpl_is_selected('a', value),
                                                           'opta' : _("All of the words:"),
               'selo' : self.tmpl_is_selected('o', value),
                                                           'opto' : _("Any of the words:"),
               'sele' : self.tmpl_is_selected('e', value),
                                                           'opte' : _("Exact phrase:"),
               'selp' : self.tmpl_is_selected('p', value),
                                                           'optp' : _("Partial phrase:"),
               'selr' : self.tmpl_is_selected('r', value),
                                                           'optr' : _("Regular expression:")
              }
        return out

    def tmpl_is_selected(self, var, fld):
        """
          Checks if *var* and *fld* are equal, and if yes, returns ' selected="selected"'.  Useful for select boxes.

          Parameters:

          - 'var' *string* - First value to compare

          - 'fld' *string* - Second value to compare
        """
        if var == fld:
            return ' selected="selected"'
        else:
            return ""

    def tmpl_andornot_box(self, name='op', value='', ln='en'):
        """
          Returns HTML code for the AND/OR/NOT selection box.

          Parameters:

            - 'name' *string* - The name of the produced select

            - 'value' *string* - The selected value (if any value is already selected)

            - 'ln' *string* - the language to display
        """

        # load the right message language
        _ = gettext_set_language(ln)

        out = """
        <select name="%(name)s">
        <option value="a"%(sela)s>%(opta)s</option>
        <option value="o"%(selo)s>%(opto)s</option>
        <option value="n"%(seln)s>%(optn)s</option>
        </select>
        """ % {'name' : name,
               'sela' : self.tmpl_is_selected('a', value), 'opta' : _("AND"),
               'selo' : self.tmpl_is_selected('o', value), 'opto' : _("OR"),
               'seln' : self.tmpl_is_selected('n', value), 'optn' : _("AND NOT")
              }
        return out

    def tmpl_inputdate(self, name, ln, sy = 0, sm = 0, sd = 0):
        """
          Produces *From Date*, *Until Date* kind of selection box. Suitable for search options.

          Parameters:

            - 'name' *string* - The base name of the produced selects

            - 'ln' *string* - the language to display
        """
        # load the right message language
        _ = gettext_set_language(ln)

        box = """
               <select name="%(name)sd">
                 <option value=""%(sel)s>%(any)s</option>
              """ % {
                'name' : name,
                'any' : _("any day"),
                'sel' : self.tmpl_is_selected(sd, 0)
              }
        for day in range(1, 32):
            box += """<option value="%02d"%s>%02d</option>""" % (day, self.tmpl_is_selected(sd, day), day)
        box += """</select>"""
        # month
        box += """
                <select name="%(name)sm">
                  <option value=""%(sel)s>%(any)s</option>
               """ % {
                 'name' : name,
                 'any' : _("any month"),
                 'sel' : self.tmpl_is_selected(sm, 0)
               }
        for mm, month in [(1, _("January")), (2, _("February")), (3, _("March")), (4, _("April")), \
                          (5, _("May")), (6, _("June")), (7, _("July")), (8, _("August")), \
                          (9, _("September")), (10, _("October")), (11, _("November")), (12, _("December"))]:
            box += """<option value="%02d"%s>%s</option>""" % (mm, self.tmpl_is_selected(sm, mm), month)
        box += """</select>"""
        # year
        box += """
                <select name="%(name)sy">
                  <option value=""%(sel)s>%(any)s</option>
               """ % {
                 'name' : name,
                 'any' : _("any year"),
                 'sel' : self.tmpl_is_selected(sy, 0)
               }
        this_year = int(time.strftime("%Y", time.localtime()))
        for year in range(this_year-20, this_year+1):
            box += """<option value="%d"%s>%d</option>""" % (year, self.tmpl_is_selected(sy, year), year)
        box += """</select>"""
        return box

    def tmpl_inputdatetype(self, dt='', ln=cdslang):
        """
          Produces input date type selection box to choose
          added-or-modified date search option.

          Parameters:

            - 'dt' *string - date type (c=created, m=modified)

            - 'ln' *string* - the language to display
        """
        # load the right message language
        _ = gettext_set_language(ln)

        box = """<select name="dt">
                  <option value="">%(added)s </option>
                  <option value="m"%(sel)s>%(modified)s </option>
                 </select>
              """ % { 'added': _("Added since:"),
                      'modified': _("Modified since:"),
                      'sel': self.tmpl_is_selected(dt, 'm'),
                    }
        return box

    def tmpl_narrowsearch(self, as, ln, type, father,
                          has_grandchildren, sons, display_grandsons,
                          grandsons):

        """
        Creates list of collection descendants of type *type* under title *title*.
        If as==1, then links to Advanced Search interfaces; otherwise Simple Search.
        Suitable for 'Narrow search' and 'Focus on' boxes.

        Parameters:

          - 'as' *bool* - Should we display an advanced search box?

          - 'ln' *string* - The language to display

          - 'type' *string* - The type of the produced box (virtual collections or normal collections)

          - 'father' *collection* - The current collection

          - 'has_grandchildren' *bool* - If the current collection has grand children

          - 'sons' *list* - The list of the sub-collections (first level)

          - 'display_grandsons' *bool* - If the grand children collections should be displayed (2 level deep display)

          - 'grandsons' *list* - The list of sub-collections (second level)
        """

        # load the right message language
        _ = gettext_set_language(ln)

        title = {'r': _("Narrow by collection:"),
                 'v': _("Focus on:")}[type]


        if has_grandchildren:
            style_prolog = "<strong>"
            style_epilog = "</strong>"
        else:
            style_prolog = ""
            style_epilog = ""

        out = """<table class="%(narrowsearchbox)s">
                   <thead>
                    <tr>
                     <th colspan="2" align="left" class="%(narrowsearchbox)sheader">
                       %(title)s
                     </th>
                    </tr>
                   </thead>
                   <tbody>""" % {'title' : title,
                                 'narrowsearchbox': {'r': 'narrowsearchbox',
                                                     'v': 'focusonsearchbox'}[type]}
        # iterate through sons:
        i = 0
        for son in sons:
            out += """<tr><td class="%(narrowsearchbox)sbody" valign="top">""" % \
                   { 'narrowsearchbox': {'r': 'narrowsearchbox',
                                         'v': 'focusonsearchbox'}[type]}

            if type == 'r':
                if son.restricted_p() and son.restricted_p() != father.restricted_p():
                    out += """<input type="checkbox" name="c" value="%(name)s" />&nbsp;</td>""" % {'name' : cgi.escape(son.name) }
                else:
                    out += """<input type="checkbox" name="c" value="%(name)s" checked="checked" />&nbsp;</td>""" % {'name' : cgi.escape(son.name) }
            else:
                out += '</td>'
            out += """<td valign="top">%(link)s%(recs)s """ % {
                'link': create_html_link(self.build_search_interface_url(c=son.name, ln=ln, as=as),
                                         {}, style_prolog + cgi.escape(son.get_name(ln)) + style_epilog),
                'recs' : self.tmpl_nbrecs_info(son.nbrecs, ln=ln)}

            if son.restricted_p():
                out += """ <small class="warning">[%(msg)s]</small> """ % { 'msg' : _("restricted") }
            if display_grandsons and len(grandsons[i]):
                # iterate trough grandsons:
                out += """<br />"""
                for grandson in grandsons[i]:
                    out += """ <small>%(link)s%(nbrec)s</small> """ % {
                        'link': create_html_link(self.build_search_interface_url(c=grandson.name, ln=ln, as=as),
                                                 {},
                                                 cgi.escape(grandson.get_name(ln))),
                        'nbrec' : self.tmpl_nbrecs_info(grandson.nbrecs, ln=ln)}

            out += """</td></tr>"""
            i += 1
        out += "</tbody></table>"

        return out

    def tmpl_searchalso(self, ln, engines_list, collection_id):
        _ = gettext_set_language(ln)

        box_name = _("Search also:")

        html = """<table cellspacing="0" cellpadding="0" border="0">
            <tr><td valign="top"><table class="searchalsosearchbox">
            <thead><tr><th colspan="2" align="left" class="searchalsosearchboxheader">%(box_name)s
            </th></tr></thead><tbody>
        """ % locals()

        for engine in engines_list:
            internal_name = engine.name
            name = _(internal_name)
            base_url = engine.base_url
            if external_collection_get_state(engine, collection_id) == 3:
                checked = ' checked="checked"'
            else:
                checked = ''

            html += """<tr><td class="searchalsosearchboxbody" valign="top">
                <input type="checkbox" name="ec" id="%(id)s" value="%(internal_name)s" %(checked)s /></td>
                <td valign="top" class="searchalsosearchboxbody">
                <div style="white-space: nowrap"><label for="%(id)s">%(name)s</label>
                <a href="%(base_url)s">
                <img src="%(weburl)s/img/external-icon-light-8x8.gif" border="0" alt="%(name)s"/></a>
                </div></td></tr>""" % \
                                 { 'checked': checked,
                                   'base_url': base_url,
                                   'internal_name': internal_name,
                                   'name': cgi.escape(name),
                                   'id': "extSearch" + nmtoken_from_string(name),
                                   'weburl': weburl,}

        html += """</tbody></table></td></tr></table>"""
        return html

    def tmpl_nbrecs_info(self, number, prolog=None, epilog=None, ln=cdslang):
        """
        Return information on the number of records.

        Parameters:

        - 'number' *string* - The number of records

        - 'prolog' *string* (optional) - An HTML code to prefix the number (if **None**, will be
        '<small class="nbdoccoll">(')

        - 'epilog' *string* (optional) - An HTML code to append to the number (if **None**, will be
        ')</small>')
        """

        if number is None:
            number = 0
        if prolog is None:
            prolog = '''&nbsp;<small class="nbdoccoll">('''
        if epilog is None:
            epilog = ''')</small>'''

        return prolog + self.tmpl_nice_number(number, ln) + epilog

    def tmpl_box_restricted_content(self, ln):
        """
          Displays a box containing a *restricted content* message

        Parameters:

          - 'ln' *string* - The language to display

        """

        # load the right message language
        _ = gettext_set_language(ln)

        return _("The contents of this collection is restricted.")

    def tmpl_box_no_records(self, ln):
        """
          Displays a box containing a *no content* message

        Parameters:

          - 'ln' *string* - The language to display

        """

        # load the right message language
        _ = gettext_set_language(ln)

        return _("This collection does not contain any document yet.")


    def tmpl_instant_browse(self, as, ln, recids, more_link = None):
        """
          Formats a list of records (given in the recids list) from the database.

        Parameters:

          - 'as' *int* - Advanced Search interface or not (0 or 1)

          - 'ln' *string* - The language to display

          - 'recids' *list* - the list of records from the database

          - 'more_link' *string* - the "More..." link for the record. If not given, will not be displayed

        """

        # load the right message language
        _ = gettext_set_language(ln)

        body = '''<table class="latestadditionsbox">'''
        for recid in recids:
            body += '''
            <tr>
              <td class="latestadditionsboxtimebody">%(date)s</td>
              <td class="latestadditionsboxrecordbody">%(body)s</td>
            </tr>''' % {'date': recid['date'],
                        'body': recid['body']
                      }
        body += "</table>"
        if more_link:
            body += '<div align="right"><small>' + \
                    create_html_link(more_link, {}, '[&gt;&gt; %s]' % _("more")) + \
                    '</small></div>'

        return '''
        <table class="narrowsearchbox">
          <thead>
            <tr>
              <th class="narrowsearchboxheader">%(header)s</th>
            </tr>
          </thead>
          <tbody>
            <tr>
            <td class="narrowsearchboxbody">%(body)s</td>
            </tr>
          </tbody>
        </table>''' % {'header' : _("Latest additions:"),
                       'body' : body,
                       }


    def tmpl_searchwithin_select(self, ln, fieldname, selected, values):
        """
          Produces 'search within' selection box for the current collection.

        Parameters:

          - 'ln' *string* - The language to display

          - 'fieldname' *string* - the name of the select box produced

          - 'selected' *string* - which of the values is selected

          - 'values' *list* - the list of values in the select
        """

        out = '<select name="%(fieldname)s">' % {'fieldname': fieldname}

        if values:
            for pair in values:
                out += """<option value="%(value)s"%(selected)s>%(text)s</option>""" % {
                         'value'    : cgi.escape(pair['value']),
                         'selected' : self.tmpl_is_selected(pair['value'], selected),
                         'text'     : cgi.escape(pair['text'])
                       }
        out += """</select>"""
        return out

    def tmpl_select(self, fieldname, values, selected=None, css_class=''):
        """
          Produces a generic select box

        Parameters:

          - 'css_class' *string* - optional, a css class to display this select with

          - 'fieldname' *list* - the name of the select box produced

          - 'selected' *string* - which of the values is selected

          - 'values' *list* - the list of values in the select
        """
        if css_class != '':
            class_field = ' class="%s"' % css_class
        else:
            class_field = ''
        out = '<select name="%(fieldname)s"%(class)s>' % {
            'fieldname' : fieldname,
            'class' : class_field
            }

        for pair in values:
            if pair.get('selected', False) or pair['value'] == selected:
                flag = ' selected="selected"'
            else:
                flag = ''

            out += '<option value="%(value)s"%(selected)s>%(text)s</option>' % {
                     'value'    : cgi.escape(str(pair['value'])),
                     'selected' : flag,
                     'text'     : cgi.escape(pair['text'])
                   }

        out += """</select>"""
        return out

    def tmpl_record_links(self, weburl, recid, ln):
        """
          Displays the *More info* and *Find similar* links for a record

        Parameters:

          - 'ln' *string* - The language to display

          - 'weburl' *string* - The base URL for the site

          - 'recid' *string* - the id of the displayed record
        """

        # load the right message language
        _ = gettext_set_language(ln)

        out = '''<br /><span class="moreinfo">%(detailed)s - %(similar)s</span>''' % {
            'detailed': create_html_link(self.build_search_url(recid=recid, ln=ln),
                                         {},
                                         _("Detailed record"), {'class': "moreinfo"}),
            'similar': create_html_link(self.build_search_url(p="recid:%d" % recid, rm='wrd', ln=ln),
                                        {},
                                        _("Similar records"),
                                        {'class': "moreinfo"})}

        if CFG_BIBRANK_SHOW_CITATION_LINKS:
            out += '''<span class="moreinfo"> - %s </span>''' % \
                   create_html_link(self.build_search_url(p='recid:%d' % recid, rm='citation', ln=ln),
                                    {}, _("Cited by"), {'class': "moreinfo"})

        return out

    def tmpl_record_body(self, weburl, titles, authors, dates, rns, abstracts, urls_u, urls_z, ln):
        """
          Displays the "HTML basic" format of a record

        Parameters:

          - 'weburl' *string* - The base URL for the site

          - 'authors' *list* - the authors (as strings)

          - 'dates' *list* - the dates of publication

          - 'rns' *list* - the quicknotes for the record

          - 'abstracts' *list* - the abstracts for the record

          - 'urls_u' *list* - URLs to the original versions of the notice

          - 'urls_z' *list* - Not used
        """
        out = ""
        for title in titles:
            out += "<strong>%(title)s</strong> " % {
                     'title' : cgi.escape(title)
                   }
        if authors:
            out += " / "
            for author in authors[:CFG_WEBSEARCH_AUTHOR_ET_AL_THRESHOLD]:
                out += '%s; ' % \
                       create_html_link(self.build_search_url(p=author, f='author', ln=ln),
                                        {}, cgi.escape(author))

            if len(authors) > CFG_WEBSEARCH_AUTHOR_ET_AL_THRESHOLD:
                out += "<em>et al</em>"
        for date in dates:
            out += " %s." % cgi.escape(date)
        for rn in rns:
            out += """ <small class="quicknote">[%(rn)s]</small>""" % {'rn' : cgi.escape(rn)}
        for abstract in abstracts:
            out += "<br /><small>%(abstract)s [...]</small>" % {'abstract' : cgi.escape(abstract[:1+string.find(abstract, '.')]) }
        for idx in range(0, len(urls_u)):
            out += """<br /><small class="note"><a class="note" href="%(url)s">%(name)s</a></small>""" % {
                     'url' : urls_u[idx],
                     'name' : urls_u[idx]
                   }
        return out

    def tmpl_search_in_bibwords(self, p, f, ln, nearest_box):
        """
          Displays the *Words like current ones* links for a search

        Parameters:

          - 'p' *string* - Current search words

          - 'f' *string* - the fields in which the search was done

          - 'nearest_box' *string* - the HTML code for the "nearest_terms" box - most probably from a create_nearest_terms_box call
        """

        # load the right message language
        _ = gettext_set_language(ln)
        out = '<p>'
        if f:
            out += _("Words nearest to %(x_word)s inside %(x_field)s in any collection are:") % {'x_word': '<em>' + cgi.escape(p) + '</em>',
                                                                                                 'x_field': '<em>' + cgi.escape(f) + '</em>'}
        else:
            out += _("Words nearest to %(x_word)s in any collection are:") % {'x_word': '<em>' + cgi.escape(p) + '</em>'}
        out += '<br />' + nearest_box + '</p>'
        return out

    def tmpl_nearest_term_box(self, p, ln, f, terminfo, intro):
        """
          Displays the *Nearest search terms* box

        Parameters:

          - 'p' *string* - Current search words

          - 'f' *string* - a collection description (if the search has been completed in a collection)

          - 'ln' *string* - The language to display

          - 'weburl' *string* - The base URL for the site

          - 'terminfo': tuple (term, hits, argd) for each near term

          - 'intro' *string* - the intro HTML to prefix the box with
        """

        out = '''<table class="nearesttermsbox" cellpadding="0" cellspacing="0" border="0">'''

        for term, hits, argd in terminfo:

            if hits:
                hitsinfo = str(hits)
            else:
                hitsinfo = '-'

            term = cgi.escape(term)

            if term == p: # print search word for orientation:
                nearesttermsboxbody_class = "nearesttermsboxbodyselected"
                if hits > 0:
                    term = create_html_link(self.build_search_url(argd), {},
                                            term, {'class': "nearesttermsselected"})
            else:
                nearesttermsboxbody_class = "nearesttermsboxbody"
                term = create_html_link(self.build_search_url(argd), {},
                                        term, {'class': "nearestterms"})

            out += '''\
            <tr>
              <td class="%(nearesttermsboxbody_class)s" align="right">%(hits)s</td>
              <td class="%(nearesttermsboxbody_class)s" width="15">&nbsp;</td>
              <td class="%(nearesttermsboxbody_class)s" align="left">%(term)s</td>
            </tr>
            ''' % {'hits': hitsinfo,
                   'nearesttermsboxbody_class': nearesttermsboxbody_class,
                   'term': term}

        out += "</table>"
        return intro + "<blockquote>" + out + "</blockquote>"

    def tmpl_browse_pattern(self, f, fn, ln, browsed_phrases_in_colls, colls):
        """
          Displays the *Nearest search terms* box

        Parameters:

          - 'f' *string* - field (*not* i18nized)

          - 'fn' *string* - field name (i18nized)

          - 'ln' *string* - The language to display

          - 'weburl' *string* - The base URL for the site

          - 'browsed_phrases_in_colls' *array* - the phrases to display

          - 'colls' *array* - the list of collection parameters of the search (c's)
        """

        # load the right message language
        _ = gettext_set_language(ln)

        out = """<table class="searchresultsbox">
              <thead>
               <tr>
                <th class="searchresultsboxheader" style="text-align: right;">
                  %(hits)s
                </th>
                <th class="searchresultsboxheader" width="15">
                  &nbsp;
                </th>
                <th class="searchresultsboxheader" style="text-align: left;">
                  %(fn)s
                </th>
               </tr>
              </thead>
              <tbody>""" % {
                'hits' : _("Hits"),
                'fn' : cgi.escape(fn)
              }

        if len(browsed_phrases_in_colls) == 1:
            # one hit only found:
            phrase, nbhits = browsed_phrases_in_colls[0][0], browsed_phrases_in_colls[0][1]

            query = {'c': colls,
                     'ln': ln,
                     'p': phrase,
                     'f': f}

            out += """<tr>
                       <td class="searchresultsboxbody" style="text-align: right;">
                        %(nbhits)s
                       </td>
                       <td class="searchresultsboxbody" width="15">
                        &nbsp;
                       </td>
                       <td class="searchresultsboxbody" style="text-align: left;">
                        %(link)s
                       </td>
                      </tr>""" % {'nbhits': nbhits,
                                  'link': create_html_link(self.build_search_url(query),
                                                           {}, cgi.escape(phrase))}

        elif len(browsed_phrases_in_colls) > 1:
            # first display what was found but the last one:
            for phrase, nbhits in browsed_phrases_in_colls[:-1]:
                query = {'c': colls,
                         'ln': ln,
                         'p': phrase,
                         'f': f}

                out += """<tr>
                           <td class="searchresultsboxbody" style="text-align: right;">
                            %(nbhits)s
                           </td>
                           <td class="searchresultsboxbody" width="15">
                            &nbsp;
                           </td>
                           <td class="searchresultsboxbody" style="text-align: left;">
                            %(link)s
                           </td>
                          </tr>""" % {'nbhits' : nbhits,
                                      'link': create_html_link(self.build_search_url(query),
                                                               {},
                                                               cgi.escape(phrase))}

            # now display last hit as "next term":
            phrase, nbhits = browsed_phrases_in_colls[-1]
            query = {'c': colls,
                     'ln': ln,
                     'p': phrase,
                     'f': f}

            out += """<tr><td colspan="2" class="normal">
                            &nbsp;
                          </td>
                          <td class="normal">
                            <img src="%(weburl)s/img/sn.gif" alt="" border="0" />
                            %(link)s
                          </td>
                      </tr>""" % {'link': create_html_link(self.build_search_url(query, action='browse'),
                                                           {}, _("next")),
                                  'weburl' : weburl}
        out += """</tbody>
            </table>"""
        return out

    def tmpl_search_box(self, ln, as, cc, cc_intl, ot, sp,
                        action, fieldslist, f1, f2, f3, m1, m2, m3,
                        p1, p2, p3, op1, op2, rm, p, f, coll_selects,
                        d1y, d2y, d1m, d2m, d1d, d2d, dt, sort_fields,
                        sf, so, ranks, sc, rg, formats, of, pl, jrec, ec):

        """
          Displays the *Nearest search terms* box

        Parameters:

          - 'ln' *string* - The language to display

          - 'weburl' *string* - The base URL for the site

          - 'as' *bool* - Should we display an advanced search box?

          - 'cc_intl' *string* - the i18nized current collection name

          - 'cc' *string* - the internal current collection name

          - 'ot', 'sp' *string* - hidden values

          - 'action' *string* - the action demanded by the user

          - 'fieldslist' *list* - the list of all fields available, for use in select within boxes in advanced search

          - 'p, f, f1, f2, f3, m1, m2, m3, p1, p2, p3, op1, op2, op3, rm' *strings* - the search parameters

          - 'coll_selects' *array* - a list of lists, each containing the collections selects to display

          - 'd1y, d2y, d1m, d2m, d1d, d2d' *int* - the search between dates

          - 'dt' *string* - the dates' types (creation dates, modification dates)

          - 'sort_fields' *array* - the select information for the sort fields

          - 'sf' *string* - the currently selected sort field

          - 'so' *string* - the currently selected sort order ("a" or "d")

          - 'ranks' *array* - ranking methods

          - 'rm' *string* - selected ranking method

          - 'sc' *string* - split by collection or not

          - 'rg' *string* - selected results/page

          - 'formats' *array* - available output formats

          - 'of' *string* - the selected output format

          - 'pl' *string* - `limit to' search pattern
        """

        # load the right message language
        _ = gettext_set_language(ln)


        # These are hidden fields the user does not manipulate
        # directly
        argd = drop_default_urlargd({
            'ln': ln, 'as': as,
            'cc': cc, 'ot': ot, 'sp': sp, 'ec': ec,
            }, self.search_results_default_urlargd)


        out = '''
        <h1 class="headline">%(ccname)s</h1>
        <form name="search" action="%(weburl)s/search" method="get">
        ''' % {'ccname' : cgi.escape(cc_intl),
               'weburl' : weburl}

        # Only add non-default hidden values
        for field, value in argd.items():
            out += self.tmpl_input_hidden(field, value)

        leadingtext = _("Search")

        if action == 'browse':
            leadingtext = _("Browse")

        if as == 1:
            # print Advanced Search form:

            # define search box elements:
            out += '''
            <table class="searchbox">
             <thead>
              <tr>
               <th colspan="3" class="searchboxheader">
                %(leading)s:
               </th>
              </tr>
             </thead>
             <tbody>
              <tr valign="top" style="white-space:nowrap;">
                <td class="searchboxbody">%(matchbox1)s
                  <input type="text" name="p1" size="%(sizepattern)d" value="%(p1)s" />
                </td>
                <td class="searchboxbody">%(searchwithin1)s</td>
                <td class="searchboxbody">%(andornot1)s</td>
              </tr>
              <tr valign="top">
                <td class="searchboxbody">%(matchbox2)s
                  <input type="text" name="p2" size="%(sizepattern)d" value="%(p2)s" />
                </td>
                <td class="searchboxbody">%(searchwithin2)s</td>
                <td class="searchboxbody">%(andornot2)s</td>
              </tr>
              <tr valign="top">
                <td class="searchboxbody">%(matchbox3)s
                  <input type="text" name="p3" size="%(sizepattern)d" value="%(p3)s" />
                </td>
                <td class="searchboxbody">%(searchwithin3)s</td>
                <td class="searchboxbody"  style="white-space:nowrap;">
                  <input class="formbutton" type="submit" name="action_search" value="%(search)s" />
                  <input class="formbutton" type="submit" name="action_browse" value="%(browse)s" />&nbsp;
                </td>
              </tr>
              <tr valign="bottom">
                <td colspan="3" align="right" class="searchboxbody">
                  <small>
                    <a href="%(weburl)s/help/search-tips%(langlink)s">%(search_tips)s</a> ::
                    %(simple_search)s
                  </small>
                </td>
              </tr>
             </tbody>
            </table>
            ''' % {
                'simple_search': create_html_link(self.build_search_url(p=p1, f=f1, rm=rm, cc=cc, ln=ln, jrec=jrec, rg=rg),
                                                  {}, _("Simple Search")),

                'leading' : leadingtext,
                'sizepattern' : CFG_WEBSEARCH_ADVANCEDSEARCH_PATTERN_BOX_WIDTH,
                'matchbox1' : self.tmpl_matchtype_box('m1', m1, ln=ln),
                'p1' : cgi.escape(p1,1),
                'searchwithin1' : self.tmpl_searchwithin_select(
                                  ln = ln,
                                  fieldname = 'f1',
                                  selected = f1,
                                  values = self._add_mark_to_field(value = f1, fields = fieldslist, ln = ln)
                                ),
              'andornot1' : self.tmpl_andornot_box(
                                  name = 'op1',
                                  value = op1,
                                  ln = ln
                                ),
              'matchbox2' : self.tmpl_matchtype_box('m2', m2, ln=ln),
              'p2' : cgi.escape(p2,1),
              'searchwithin2' : self.tmpl_searchwithin_select(
                                  ln = ln,
                                  fieldname = 'f2',
                                  selected = f2,
                                  values = self._add_mark_to_field(value = f2, fields = fieldslist, ln = ln)
                                ),
              'andornot2' : self.tmpl_andornot_box(
                                  name = 'op2',
                                  value = op2,
                                  ln = ln
                                ),
              'matchbox3' : self.tmpl_matchtype_box('m3', m3, ln=ln),
              'p3' : cgi.escape(p3,1),
              'searchwithin3' : self.tmpl_searchwithin_select(
                                  ln = ln,
                                  fieldname = 'f3',
                                  selected = f3,
                                  values = self._add_mark_to_field(value = f3, fields = fieldslist, ln = ln)
                                ),
              'search' : _("Search"),
              'browse' : _("Browse"),
              'weburl' : weburl,
              'ln' : ln,
              'langlink': ln != cdslang and '?ln=' + ln or '',
              'search_tips': _("Search Tips")
            }
        else:
            # print Simple Search form:
            out += '''
            <table class="searchbox">
             <thead>
              <tr>
               <th colspan="3" class="searchboxheader">
                %(leading)s:
               </th>
              </tr>
             </thead>
             <tbody>
              <tr valign="top">
                <td class="searchboxbody"><input type="text" name="p" size="%(sizepattern)d" value="%(p)s" /></td>
                <td class="searchboxbody">%(searchwithin)s</td>
                <td class="searchboxbody">
                  <input class="formbutton" type="submit" name="action_search" value="%(search)s" />
                  <input class="formbutton" type="submit" name="action_browse" value="%(browse)s" />&nbsp;
                </td>
              </tr>
              <tr valign="bottom">
                <td colspan="3" align="right" class="searchboxbody">
                  <small>
                    <a href="%(weburl)s/help/search-tips%(langlink)s">%(search_tips)s</a> ::
                    %(advanced_search)s
                  </small>
                </td>
              </tr>
             </tbody>
            </table>
            ''' % {
              'advanced_search': create_html_link(self.build_search_url(p1=p,
                                                                        f1=f,
                                                                        rm=rm,
                                                                        as=1,
                                                                        cc=cc,
                                                                        jrec=jrec,
                                                                        ln=ln,
                                                                        rg=rg),
                                                  {}, _("Advanced Search")),

              'leading' : leadingtext,
              'sizepattern' : CFG_WEBSEARCH_ADVANCEDSEARCH_PATTERN_BOX_WIDTH,
              'p' : cgi.escape(p, 1),
              'searchwithin' : self.tmpl_searchwithin_select(
                                  ln = ln,
                                  fieldname = 'f',
                                  selected = f,
                                  values = self._add_mark_to_field(value=f, fields=fieldslist, ln=ln)
                                ),
              'search' : _("Search"),
              'browse' : _("Browse"),
              'weburl' : weburl,
              'ln' : ln,
              'langlink': ln != cdslang and '?ln=' + ln or '',
              'search_tips': _("Search Tips")
            }

        ## secondly, print Collection(s) box:
        selects = ''
        for sel in coll_selects:
            selects += self.tmpl_select(fieldname='c', values=sel)

        out += """
            <table class="searchbox">
             <thead>
              <tr>
               <th colspan="3" class="searchboxheader">
                %(leading)s %(msg_coll)s:
               </th>
              </tr>
             </thead>
             <tbody>
              <tr valign="bottom">
               <td valign="top" class="searchboxbody">
                 %(colls)s
               </td>
              </tr>
             </tbody>
            </table>
             """ % {
               'leading' : leadingtext,
               'msg_coll' : _("collections"),
               'colls' : selects,
             }

        ## thirdly, print search limits, if applicable:
        if action != _("Browse") and pl:
            out += """<table class="searchbox">
                       <thead>
                        <tr>
                          <th class="searchboxheader">
                            %(limitto)s
                          </th>
                        </tr>
                       </thead>
                       <tbody>
                        <tr valign="bottom">
                          <td class="searchboxbody">
                           <input type="text" name="pl" size="%(sizepattern)d" value="%(pl)s" />
                          </td>
                        </tr>
                       </tbody>
                      </table>""" % {
                        'limitto' : _("Limit to:"),
                        'sizepattern' : CFG_WEBSEARCH_ADVANCEDSEARCH_PATTERN_BOX_WIDTH,
                        'pl' : cgi.escape(pl, 1),
                      }

        ## fourthly, print from/until date boxen, if applicable:
        if action == _("Browse") or (d1y==0 and d1m==0 and d1d==0 and d2y==0 and d2m==0 and d2d==0):
            pass # do not need it
        else:
            cell_6_a = self.tmpl_inputdatetype(dt, ln) + self.tmpl_inputdate("d1", ln, d1y, d1m, d1d)
            cell_6_b = self.tmpl_inputdate("d2", ln, d2y, d2m, d2d)
            out += """<table class="searchbox">
                       <thead>
                        <tr>
                          <th class="searchboxheader">
                            %(added)s
                          </th>
                          <th class="searchboxheader">
                            %(until)s
                          </th>
                        </tr>
                       </thead>
                       <tbody>
                        <tr valign="bottom">
                          <td class="searchboxbody">%(added_or_modified)s %(date1)s</td>
                          <td class="searchboxbody">%(date2)s</td>
                        </tr>
                       </tbody>
                      </table>""" % {
                        'added' : _("Added/modified since:"),
                        'until' : _("until:"),
                        'added_or_modified': self.tmpl_inputdatetype(dt, ln),
                        'date1' : self.tmpl_inputdate("d1", ln, d1y, d1m, d1d),
                        'date2' : self.tmpl_inputdate("d2", ln, d2y, d2m, d2d),
                      }

        ## fifthly, print Display results box, including sort/rank, formats, etc:
        if action != _("Browse"):

            rgs = []
            for i in [10, 25, 50, 100, 250, 500]:
                rgs.append({ 'value' : i, 'text' : "%d %s" % (i, _("results"))})

            # sort by:
            out += """<table class="searchbox">
                 <thead>
                  <tr>
                   <th class="searchboxheader">
                    %(sort_by)s
                   </th>
                   <th class="searchboxheader">
                    %(display_res)s
                   </th>
                   <th class="searchboxheader">
                    %(out_format)s
                   </th>
                  </tr>
                 </thead>
                 <tbody>
                  <tr valign="bottom">
                   <td valign="top" class="searchboxbody">
                     %(select_sf)s %(select_so)s %(select_rm)s
                   </td>
                   <td valign="top" class="searchboxbody">
                     %(select_rg)s %(select_sc)s
                   </td>
                   <td valign="top" class="searchboxbody">%(select_of)s</td>
                  </tr>
                 </tbody>
                </table>""" % {
                  'sort_by' : _("Sort:"),
                  'display_res' : _("Display results:"),
                  'out_format' : _("Output format:"),
                  'select_sf' : self.tmpl_select(fieldname = 'sf', values = sort_fields, selected = sf, css_class = 'address'),
                  'select_so' : self.tmpl_select(fieldname = 'so', values = [{
                                    'value' : 'a',
                                    'text' : _("asc.")
                                  }, {
                                    'value' : 'd',
                                    'text' : _("desc.")
                                  }], selected = so, css_class = 'address'),
                  'select_rm' : self.tmpl_select(fieldname = 'rm', values = ranks, selected = rm, css_class = 'address'),
                  'select_rg' : self.tmpl_select(fieldname = 'rg', values = rgs, selected = rg, css_class = 'address'),
                  'select_sc' : self.tmpl_select(fieldname = 'sc', values = [{
                                    'value' : 0,
                                    'text' : _("single list")
                                  }, {
                                    'value' : 1,
                                    'text' : _("split by collection")
                                  }], selected = sc, css_class = 'address'),
                  'select_of' : self.tmpl_searchwithin_select(
                                  ln = ln,
                                  fieldname = 'of',
                                  selected = of,
                                  values = self._add_mark_to_field(value = of, fields = formats, chars = 3, ln = ln)
                                ),
                }

        ## last but not least, print end of search box:
        out += """</form>"""
        return out

    def tmpl_input_hidden(self, name, value):
        "Produces the HTML code for a hidden field "
        if isinstance(value, list):
            list_input = [self.tmpl_input_hidden(name, val) for val in value]
            return "\n".join(list_input)

        return """<input type="hidden" name="%(name)s" value="%(value)s" />""" % {
                 'name' : cgi.escape(str(name), 1),
                 'value' : cgi.escape(str(value), 1),
               }

    def _add_mark_to_field(self, value, fields, ln, chars = 1):
        """Adds the current value as a MARC tag in the fields array
        Useful for advanced search"""

        # load the right message language
        _ = gettext_set_language(ln)

        out = fields
        if value and str(value[0:chars]).isdigit():
            out.append({'value' : value,
                        'text' : str(value) + " " + _("MARC tag")
                        })
        return out

    def tmpl_search_pagestart(self, ln) :
        "page start for search page. Will display after the page header"
        return """<div class="pagebody"><div class="pagebodystripemiddle">"""

    def tmpl_search_pageend(self, ln) :
        "page end for search page. Will display just before the page footer"
        return """</div></div>"""

    def tmpl_print_warning(self, msg, type, prologue, epilogue):
        """Prints warning message and flushes output.

        Parameters:

          - 'msg' *string* - The message string

          - 'type' *string* - the warning type

          - 'prologue' *string* - HTML code to display before the warning

          - 'epilogue' *string* - HTML code to display after the warning
        """

        out = '\n%s<span class="quicknote">' % (prologue)
        if type:
            out += '%s: ' % type
        out += '%s</span>%s' % (msg, epilogue)
        return out

    def tmpl_print_search_info(self, ln, weburl, middle_only,
                               collection, collection_name, collection_id,
                               as, sf, so, rm, rg, nb_found, of, ot, p, f, f1,
                               f2, f3, m1, m2, m3, op1, op2, p1, p2,
                               p3, d1y, d1m, d1d, d2y, d2m, d2d, dt,
                               all_fieldcodes, cpu_time, pl_in_url,
                               jrec, sc, sp):

        """Prints stripe with the information on 'collection' and 'nb_found' results and CPU time.
           Also, prints navigation links (beg/next/prev/end) inside the results set.
           If middle_only is set to 1, it will only print the middle box information (beg/netx/prev/end/etc) links.
           This is suitable for displaying navigation links at the bottom of the search results page.

        Parameters:

          - 'ln' *string* - The language to display

          - 'weburl' *string* - The base URL for the site

          - 'middle_only' *bool* - Only display parts of the interface

          - 'collection' *string* - the collection name

          - 'collection_name' *string* - the i18nized current collection name

          - 'as' *bool* - if we display the advanced search interface

          - 'sf' *string* - the currently selected sort format

          - 'so' *string* - the currently selected sort order ("a" or "d")

          - 'rm' *string* - selected ranking method

          - 'rg' *int* - selected results/page

          - 'nb_found' *int* - number of results found

          - 'of' *string* - the selected output format

          - 'ot' *string* - hidden values

          - 'p' *string* - Current search words

          - 'f' *string* - the fields in which the search was done

          - 'f1, f2, f3, m1, m2, m3, p1, p2, p3, op1, op2' *strings* - the search parameters

          - 'jrec' *int* - number of first record on this page

          - 'd1y, d2y, d1m, d2m, d1d, d2d' *int* - the search between dates

          - 'dt' *string* the dates' type (creation date, modification date)

          - 'all_fieldcodes' *array* - all the available fields

          - 'cpu_time' *float* - the time of the query in seconds

        """

        # load the right message language
        _ = gettext_set_language(ln)

        out = ""
        # left table cells: print collection name
        if not middle_only:
            out += '''
                  <a name="%(collection_id)s"></a>
                  <form action="%(weburl)s/search" method="get">
                  <table class="searchresultsbox"><tr><td class="searchresultsboxheader" align="left">
                  <strong><big>%(collection_link)s</big></strong></td>
                  ''' % {
                    'collection_id': collection_id,
                    'weburl' : weburl,
                    'collection_link': create_html_link(self.build_search_interface_url(c=collection, as=as, ln=ln),
                                                        {}, cgi.escape(collection_name))
                  }
        else:
            out += """
                  <form action="%(weburl)s/search" method="get"><div align="center">
                  """ % { 'weburl' : weburl }

        # middle table cell: print beg/next/prev/end arrows:
        if not middle_only:
            out += """<td class="searchresultsboxheader" align="center">
                      %(recs_found)s &nbsp;""" % {
                     'recs_found' : _("%s records found") % ('<strong>' + self.tmpl_nice_number(nb_found, ln) + '</strong>')
                   }
        else:
            out += "<small>"
            if nb_found > rg:
                out += "" + cgi.escape(collection_name) + " : " + _("%s records found") % ('<strong>' + self.tmpl_nice_number(nb_found, ln) + '</strong>') + " &nbsp; "

        if nb_found > rg: # navig.arrows are needed, since we have many hits

            query = {'p': p, 'f': f,
                     'cc': collection,
                     'sf': sf, 'so': so,
                     'sp': sp, 'rm': rm,
                     'of': of, 'ot': ot,
                     'as': as, 'ln': ln,
                     'p1': p1, 'p2': p2, 'p3': p3,
                     'f1': f1, 'f2': f2, 'f3': f3,
                     'm1': m1, 'm2': m2, 'm3': m3,
                     'op1': op1, 'op2': op2,
                     'sc': 0,
                     'd1y': d1y, 'd1m': d1m, 'd1d': d1d,
                     'd2y': d2y, 'd2m': d2m, 'd2d': d2d,
                     'dt': dt,
                }

            # @todo here
            def img(gif, txt):
                return '<img src="%(weburl)s/img/%(gif)s.gif" alt="%(txt)s" border="0" />' % {
                    'txt': txt, 'gif': gif, 'weburl': weburl}

            if jrec-rg > 1:
                out += create_html_link(self.build_search_url(query, jrec=1, rg=rg),
                                        {}, img('sb', _("begin")),
                                        {'class': 'img'})

            if jrec > 1:
                out += create_html_link(self.build_search_url(query, jrec=max(jrec-rg, 1), rg=rg),
                                        {}, img('sp', _("previous")),
                                        {'class': 'img'})

            if jrec+rg-1 < nb_found:
                out += "%d - %d" % (jrec, jrec+rg-1)
            else:
                out += "%d - %d" % (jrec, nb_found)

            if nb_found >= jrec+rg:
                out += create_html_link(self.build_search_url(query,
                                                              jrec=jrec+rg,
                                                              rg=rg),
                                        {}, img('sn', _("next")),
                                        {'class':'img'})

            if nb_found >= jrec+rg+rg:
                out += create_html_link(self.build_search_url(query,
                                                            jrec=nb_found-rg+1,
                                                            rg=rg),
                                        {}, img('se', _("end")),
                                        {'class': 'img'})


            # still in the navigation part
            cc = collection
            sc = 0
            for var in ['p', 'cc', 'f', 'sf', 'so', 'of', 'rg', 'as', 'ln', 'p1', 'p2', 'p3', 'f1', 'f2', 'f3', 'm1', 'm2', 'm3', 'op1', 'op2', 'sc', 'd1y', 'd1m', 'd1d', 'd2y', 'd2m', 'd2d', 'dt']:
                out += self.tmpl_input_hidden(name = var, value = vars()[var])
            for var in ['ot', 'sp', 'rm']:
                if vars()[var]:
                    out += self.tmpl_input_hidden(name = var, value = vars()[var])
            if pl_in_url:
                fieldargs = cgi.parse_qs(pl_in_url)
                for fieldcode in all_fieldcodes:
                    # get_fieldcodes():
                    if fieldargs.has_key(fieldcode):
                        for val in fieldargs[fieldcode]:
                            out += self.tmpl_input_hidden(name = fieldcode, value = val)
            out += """&nbsp; %(jump)s <input type="text" name="jrec" size="4" value="%(jrec)d" />""" % {
                     'jump' : _("jump to record:"),
                     'jrec' : jrec,
                   }

        if not middle_only:
            out += "</td>"
        else:
            out += "</small>"

        # right table cell: cpu time info
        if not middle_only:
            if cpu_time > -1:
                out += """<td class="searchresultsboxheader" align="right"><small>%(time)s</small>&nbsp;</td>""" % {
                         'time' : _("Search took %s seconds.") % ('%.2f' % cpu_time),
                       }
            out += "</tr></table>"
        else:
            out += "</div>"
        out += "</form>"
        return out

    def tmpl_nice_number(self, number, ln=cdslang, thousands_separator=',', max_ndigits_after_dot=None):
        """
        Return nicely printed number NUMBER in language LN using
        given THOUSANDS_SEPARATOR character.
        If max_ndigits_after_dot is specified and the number is float, the
        number is rounded by taking in consideration up to max_ndigits_after_dot
        digit after the dot.

        This version does not pay attention to locale.  See
        tmpl_nice_number_via_locale().
        """
        if type(number) is float:
            if max_ndigits_after_dot is not None:
                number = round(number, max_ndigits_after_dot)
            int_part, frac_part = str(number).split('.')
            return '%s.%s' % (self.tmpl_nice_number(int(int_part), ln, thousands_separator), frac_part)
        else:
            chars_in = list(str(number))
            number = len(chars_in)
            chars_out = []
            for i in range(0, number):
                if i % 3 == 0 and i != 0:
                    chars_out.append(thousands_separator)
                chars_out.append(chars_in[number-i-1])
            chars_out.reverse()
            return ''.join(chars_out)

    def tmpl_nice_number_via_locale(self, number, ln=cdslang):
        """
        Return nicely printed number NUM in language LN using the locale.
        See also version tmpl_nice_number().
        """
        if number is None:
            return None
        # Temporarily switch the numeric locale to the requested one, and format the number
        # In case the system has no locale definition, use the vanilla form
        ol = locale.getlocale(locale.LC_NUMERIC)
        try:
            locale.setlocale(locale.LC_NUMERIC, self.tmpl_localemap.get(ln, self.tmpl_default_locale))
        except locale.Error:
            return str(number)
        try:
            number = locale.format('%d', number, True)
        except TypeError:
            return str(number)
        locale.setlocale(locale.LC_NUMERIC, ol)
        return number

    def tmpl_record_format_htmlbrief_header(self, ln):
        """Returns the header of the search results list when output
        is html brief. Note that this function is called for each collection
        results when 'split by collection' is enabled.

        See also: tmpl_record_format_htmlbrief_footer(..),
                  tmpl_record_format_htmlbrief_body(..)

        Parameters:

          - 'ln' *string* - The language to display

        """

        # load the right message language
        _ = gettext_set_language(ln)

        out = """
              <form action="%(weburl)s/yourbaskets/add" method="post">
              <table>
              """ % {
                'weburl' : weburl,
              }

        return out

    def tmpl_record_format_htmlbrief_footer(self, ln):
        """Returns the footer of the search results list when output
        is html brief. Note that this function is called for each collection
        results when 'split by collection' is enabled.

        See also: tmpl_record_format_htmlbrief_header(..),
                  tmpl_record_format_htmlbrief_body(..)

        Parameters:

          - 'ln' *string* - The language to display

        """

        # load the right message language
        _ = gettext_set_language(ln)

        out = """</table>
               <br /><input class="formbutton" type="submit" name="action" value="%(basket)s" />
               </form>""" % {
                 'basket' : _("ADD TO BASKET")
                 }

        return out

    def tmpl_record_format_htmlbrief_body(self, ln, recid,
                                          row_number, relevance,
                                          record, relevances_prologue,
                                          relevances_epilogue):
        """Returns the html brief format of one record. Used in the
        search results list for each record.

        See also: tmpl_record_format_htmlbrief_header(..),
                  tmpl_record_format_htmlbrief_footer(..)

        Parameters:

          - 'ln' *string* - The language to display

          - 'row_number' *int* - The position of this record in the list

          - 'recid' *int* - The recID

          - 'relevance' *string* - The relevance of the record

          - 'record' *string* - The formatted record

          - 'relevances_prologue' *string* - HTML code to prepend the relevance indicator

          - 'relevances_epilogue' *string* - HTML code to append to the relevance indicator (used mostly for formatting)

        """

        # load the right message language
        _ = gettext_set_language(ln)

        out = """
                <tr><td valign="top" align="right" style="white-space: nowrap;">
                    <input name="recid" type="checkbox" value="%(recid)s" />
                %(number)s.
               """ % {'recid': recid,
                      'number': row_number}
        if relevance:
            out += """<br /><div class="rankscoreinfo"><a title="rank score">%(prologue)s%(relevance)s%(epilogue)s</a></div>""" % {
                'prologue' : relevances_prologue,
                'epilogue' : relevances_epilogue,
                'relevance' : relevance
                }
        out += """</td><td valign="top">%s</td></tr>""" % record

        return out

    def tmpl_print_results_overview(self, ln, weburl, results_final_nb_total, cpu_time, results_final_nb, colls, ec):
        """Prints results overview box with links to particular collections below.

        Parameters:

          - 'ln' *string* - The language to display

          - 'weburl' *string* - The base URL for the site

          - 'results_final_nb_total' *int* - The total number of hits for the query

          - 'colls' *array* - The collections with hits, in the format:

          - 'coll[code]' *string* - The code of the collection (canonical name)

          - 'coll[name]' *string* - The display name of the collection

          - 'results_final_nb' *array* - The number of hits, indexed by the collection codes:

          - 'cpu_time' *string* - The time the query took

          - 'url_args' *string* - The rest of the search query

          - 'ec' *array* - selected external collections
        """

        if len(colls) == 1 and not ec:
            # if one collection only and no external collections, print nothing:
            return ""

        # load the right message language
        _ = gettext_set_language(ln)

        # first find total number of hits:
        out = """<table class="searchresultsbox">
                <thead><tr><th class="searchresultsboxheader">%(founds)s</th></tr></thead>
                <tbody><tr><td class="searchresultsboxbody"> """ % {
                'founds' : _("%(x_fmt_open)sResults overview:%(x_fmt_close)s Found %(x_nb_records)s records in %(x_nb_seconds)s seconds.") %\
                {'x_fmt_open': '<strong>',
                 'x_fmt_close': '</strong>',
                 'x_nb_records': '<strong>' + self.tmpl_nice_number(results_final_nb_total, ln) + '</strong>',
                 'x_nb_seconds': '%.2f' % cpu_time}
              }
        # then print hits per collection:
        for coll in colls:
            if results_final_nb.has_key(coll['code']) and results_final_nb[coll['code']] > 0:
                out += '''<strong><a href="#%(coll)s">%(coll_name)s</a></strong>,
                      <a href="#%(coll)s">%(number)s</a><br />''' % {
                        'coll' : coll['id'],
                        'coll_name' : cgi.escape(coll['name']),
                        'number' : _("%s records found") % ('<strong>' + self.tmpl_nice_number(results_final_nb[coll['code']], ln) + '</strong>')
                      }
        out += "</td></tr></tbody></table>"
        return out

    def tmpl_search_no_boolean_hits(self, ln, nearestterms):
        """No hits found, proposes alternative boolean queries

        Parameters:

          - 'ln' *string* - The language to display

          - 'weburl' *string* - The base URL for the site

          - 'nearestterms' *array* - Parts of the interface to display, in the format:

          - 'nearestterms[nbhits]' *int* - The resulting number of hits

          - 'nearestterms[url_args]' *string* - The search parameters

          - 'nearestterms[p]' *string* - The search terms

        """

        # load the right message language
        _ = gettext_set_language(ln)

        out = _("Boolean query returned no hits. Please combine your search terms differently.")

        out += '''<blockquote><table class="nearesttermsbox" cellpadding="0" cellspacing="0" border="0">'''
        for term, hits, argd in nearestterms:
            out += '''\
            <tr>
              <td class="nearesttermsboxbody" align="right">%(hits)s</td>
              <td class="nearesttermsboxbody" width="15">&nbsp;</td>
              <td class="nearesttermsboxbody" align="left">
                %(link)s
              </td>
            </tr>''' % {'hits' : hits,
                        'link': create_html_link(self.build_search_url(argd),
                                                 {}, cgi.escape(term),
                                                 {'class': "nearestterms"})}
        out += """</table></blockquote>"""
        return out

    def tmpl_similar_author_names(self, authors, ln):
        """No hits found, proposes alternative boolean queries

        Parameters:

          - 'authors': a list of (name, hits) tuples
          - 'ln' *string* - The language to display
        """

        # load the right message language
        _ = gettext_set_language(ln)

        out = '''<a name="googlebox"></a>
                 <table class="googlebox"><tr><th colspan="2" class="googleboxheader">%(similar)s</th></tr>''' % {
                'similar' : _("See also: similar author names")
              }
        for author, hits in authors:
            out += '''\
            <tr>
              <td class="googleboxbody">%(nb)d</td>
              <td class="googleboxbody">%(link)s</td>
            </tr>''' % {'link': create_html_link(
                                    self.build_search_url(p=author,
                                                          f='author',
                                                          ln=ln),
                                    {}, cgi.escape(author), {'class':"google"}),
                        'nb' : hits}

        out += """</table>"""

        return out

    def tmpl_print_record_detailed(self, recID, ln, weburl):
        """Displays a detailed on-the-fly record

        Parameters:

          - 'ln' *string* - The language to display

          - 'weburl' *string* - The base URL for the site

          - 'recID' *int* - The record id
        """
        # okay, need to construct a simple "Detailed record" format of our own:
        out = "<p>&nbsp;"
        # secondly, title:
        titles = get_fieldvalues(recID, "245__a")
        for title in titles:
            out += "<p><center><big><strong>%s</strong></big></center></p>" % cgi.escape(title)
        # thirdly, authors:
        authors = get_fieldvalues(recID, "100__a") + get_fieldvalues(recID, "700__a")
        if authors:
            out += "<p><center>"
            for author in authors:
                out += '%s; ' % create_html_link(self.build_search_url(
                                                                ln=ln,
                                                                p=author,
                                                                f='author'),
                                                 {}, cgi.escape(author))
            out += "</center></p>"
        # fourthly, date of creation:
        dates = get_fieldvalues(recID, "260__c")
        for date in dates:
            out += "<p><center><small>%s</small></center></p>" % date
        # fifthly, abstract:
        abstracts = get_fieldvalues(recID, "520__a")
        for abstract in abstracts:
            out += """<p style="margin-left: 15%%; width: 70%%">
                     <small><strong>Abstract:</strong> %s</small></p>""" % abstract
        # fifthly bis, keywords:
        keywords = get_fieldvalues(recID, "6531_a")
        if len(keywords):
            out += """<p style="margin-left: 15%%; width: 70%%">
                     <small><strong>Keyword(s):</strong>"""
            for keyword in keywords:
                out += '%s; ' % create_html_link(
                                    self.build_search_url(ln=ln,
                                                          p=keyword,
                                                          f='keyword'),
                                    {}, cgi.escape(keyword))

            out += '</small></p>'
        # fifthly bis bis, published in:
        prs_p = get_fieldvalues(recID, "909C4p")
        prs_v = get_fieldvalues(recID, "909C4v")
        prs_y = get_fieldvalues(recID, "909C4y")
        prs_n = get_fieldvalues(recID, "909C4n")
        prs_c = get_fieldvalues(recID, "909C4c")
        for idx in range(0, len(prs_p)):
            out += """<p style="margin-left: 15%%; width: 70%%">
                     <small><strong>Publ. in:</strong> %s"""  % prs_p[idx]
            if prs_v and prs_v[idx]:
                out += """<strong>%s</strong>""" % prs_v[idx]
            if prs_y and prs_y[idx]:
                out += """(%s)""" % prs_y[idx]
            if prs_n and prs_n[idx]:
                out += """, no.%s""" % prs_n[idx]
            if prs_c and prs_c[idx]:
                out += """, p.%s""" % prs_c[idx]
            out += """.</small></p>"""
        # sixthly, fulltext link:
        urls_z = get_fieldvalues(recID, "8564_z")
        urls_u = get_fieldvalues(recID, "8564_u")
        for idx in range(0, len(urls_u)):
            link_text = "URL"
            try:
                if urls_z[idx]:
                    link_text = urls_z[idx]
            except IndexError:
                pass
            out += """<p style="margin-left: 15%%; width: 70%%">
            <small><strong>%s:</strong> <a href="%s">%s</a></small></p>""" % (link_text, urls_u[idx], urls_u[idx])
        # print some white space at the end:
        out += "<br /><br />"
        return out

    def tmpl_print_record_list_for_similarity_boxen(self, title, recID_score_list, ln=cdslang):
        """Print list of records in the "hs" (HTML Similarity) format for similarity boxes.
           RECID_SCORE_LIST is a list of (recID1, score1), (recID2, score2), etc.
        """

        from invenio.search_engine import print_record, record_public_p

        recID_score_list_to_be_printed = []

        # firstly find 5 first public records to print:
        nb_records_to_be_printed = 0
        nb_records_seen = 0
        while nb_records_to_be_printed < 5 and nb_records_seen < len(recID_score_list) and nb_records_seen < 50:
            # looking through first 50 records only, picking first 5 public ones
            (recID, score) = recID_score_list[nb_records_seen]
            nb_records_seen += 1
            if record_public_p(recID):
                nb_records_to_be_printed += 1
                recID_score_list_to_be_printed.append([recID, score])

        # secondly print them:
        out = '''
        <table><tr>
         <td>
          <table><tr><td class="blocknote">%(title)s</td></tr></table>
         </td>
         </tr>
         <tr>
          <td><table>
        ''' % { 'title': cgi.escape(title) }
        for recid, score in recID_score_list_to_be_printed:
            out += '''
            <tr><td><font class="rankscoreinfo"><a>(%(score)s)&nbsp;</a></font><small>&nbsp;%(info)s</small></td></tr>''' % {
                'score': score,
                'info' : print_record(recid, format="hs", ln=ln),
                }

        out += """</table></td></tr></table> """
        return out

    def tmpl_print_record_brief(self, ln, recID, weburl):
        """Displays a brief record on-the-fly

        Parameters:

          - 'ln' *string* - The language to display

          - 'weburl' *string* - The base URL for the site

          - 'recID' *int* - The record id
        """
        out = ""

        # record 'recID' does not exist in format 'format', so print some default format:
        # firstly, title:
        titles = get_fieldvalues(recID, "245__a")
        # secondly, authors:
        authors = get_fieldvalues(recID, "100__a") + get_fieldvalues(recID, "700__a")
        # thirdly, date of creation:
        dates = get_fieldvalues(recID, "260__c")
        # thirdly bis, report numbers:
        rns = get_fieldvalues(recID, "037__a")
        rns = get_fieldvalues(recID, "088__a")
        # fourthly, beginning of abstract:
        abstracts = get_fieldvalues(recID, "520__a")
        # fifthly, fulltext link:
        urls_z = get_fieldvalues(recID, "8564_z")
        urls_u = get_fieldvalues(recID, "8564_u")

        return self.tmpl_record_body(
                 weburl = weburl,
                 titles = titles,
                 authors = authors,
                 dates = dates,
                 rns = rns,
                 abstracts = abstracts,
                 urls_u = urls_u,
                 urls_z = urls_z,
                 ln=ln)

    def tmpl_print_record_brief_links(self, ln, recID, weburl):
        """Displays links for brief record on-the-fly

        Parameters:

          - 'ln' *string* - The language to display

          - 'weburl' *string* - The base URL for the site

          - 'recID' *int* - The record id
        """
        # load the right message language
        _ = gettext_set_language(ln)

        out = ""
        if CFG_WEBSEARCH_USE_ALEPH_SYSNOS:
            alephsysnos = get_fieldvalues(recID, "970__a")
            if len(alephsysnos)>0:
                alephsysno = alephsysnos[0]
                out += '<br /><span class="moreinfo">%s</span>' % \
                    create_html_link(self.build_search_url(sysno=alephsysno,
                                                           ln=ln),
                                     {}, _("Detailed record"),
                                     {'class': "moreinfo"})
            else:
                out += '<br /><span class="moreinfo">%s</span>' % \
                    create_html_link(self.build_search_url(recid=recID, ln=ln),
                                     {},
                                     _("Detailed record"),
                                     {'class': "moreinfo"})
        else:
            out += '<br /><span class="moreinfo">%s</span>' % \
                   create_html_link(self.build_search_url(recid=recID, ln=ln),
                                    {}, _("Detailed record"),
                                    {'class': "moreinfo"})

            out += '<span class="moreinfo"> - %s</span>' % \
                   create_html_link(self.build_search_url(p="recid:%d" % recID,
                                                     rm="wrd",
                                                     ln=ln),
                                    {}, _("Similar records"),
                                    {'class': "moreinfo"})

        if CFG_BIBRANK_SHOW_CITATION_LINKS:
            out += '<span class="moreinfo"> - %s</span>' % \
                   create_html_link(self.build_search_url(p="recid:%d" % recID,
                                                          rm="citation",
                                                          ln=ln),
                                    {}, _("Cited by"),
                                    {'class': "moreinfo"})

        return out

    def tmpl_xml_rss_prologue(self):
        """Creates XML RSS 2.0 prologue."""
        out = """<rss version="2.0">
      <channel>
        <title>%(cdsname)s</title>
        <link>%(weburl)s</link>
        <description>%(cdsname)s latest documents</description>
        <language>%(cdslang)s</language>
        <pubDate>%(timestamp)s</pubDate>
        <category></category>
        <generator>CDS Invenio %(version)s</generator>
        <webMaster>%(supportemail)s</webMaster>
        <ttl>%(timetolive)s</ttl>
        <image>
            <url>%(weburl)s/img/cds.png</url>
            <title>%(cdsname)s</title>
            <link>%(weburl)s</link>
        </image>
        <textInput>
          <title>Search </title>
          <description>Search this site:</description>
          <name>p</name>
          <link>%(weburl)s/search</link>
        </textInput>
        """ % {'cdsname': cdsname,
               'weburl': weburl,
               'cdslang': cdslang,
               'timestamp': time.strftime("%a, %d %b %Y %H:%M:%S %Z", time.localtime()),
               'version': CFG_VERSION,
               'supportemail': supportemail,
               'timetolive': CFG_WEBSEARCH_RSS_TTL
               }
        return out

    def tmpl_xml_rss_epilogue(self):
        """Creates XML RSS 2.0 epilogue."""
        out = """\
      </channel>
</rss>\n"""
        return out

    def tmpl_xml_nlm_prologue(self):
        """Creates XML NLM prologue."""
        out = """<articles>\n"""
        return out

    def tmpl_xml_nlm_epilogue(self):
        """Creates XML NLM epilogue."""
        out = """\n</articles>"""
        return out

    def tmpl_xml_marc_prologue(self):
        """Creates XML MARC prologue."""
        out = """<collection xmlns="http://www.loc.gov/MARC21/slim">\n"""
        return out

    def tmpl_xml_marc_epilogue(self):
        """Creates XML MARC epilogue."""
        out = """\n</collection>"""
        return out

    def tmpl_xml_default_prologue(self):
        """Creates XML default format prologue. (Sanity calls only.)"""
        out = """<collection>\n"""
        return out

    def tmpl_xml_default_epilogue(self):
        """Creates XML default format epilogue. (Sanity calls only.)"""
        out = """\n</collection>"""
        return out


    def tmpl_collection_not_found_page_title(self, colname, ln=cdslang):
        """
        Create page title for cases when unexisting collection was asked for.
        """
        _ = gettext_set_language(ln)
        out = _("Collection %s Not Found") % cgi.escape(colname)
        return out

    def tmpl_collection_not_found_page_body(self, colname, ln=cdslang):
        """
        Create page body for cases when unexisting collection was asked for.
        """
        _ = gettext_set_language(ln)
        out = """<h1>%(title)s</h1>
                 <p>%(sorry)s</p>
                 <p>%(you_may_want)s</p>
              """ % { 'title': self.tmpl_collection_not_found_page_title(colname, ln),
                      'sorry': _("Sorry, collection %s does not seem to exist.") % \
                                ('<strong>' + cgi.escape(colname) + '</strong>'),
                      'you_may_want': _("You may want to start browsing from %s.") % \
                                 ('<a href="' + weburl + '?ln=' + ln + '">' + \
                                        cgi.escape(cdsnameintl.get(ln, cdsname)) + '</a>')}
        return out

    def tmpl_alert_rss_teaser_box_for_query(self, id_query, ln):
        """Propose teaser for setting up this query as alert or RSS feed.

        Parameters:
          - 'id_query' *int* - ID of the query we make teaser for
          - 'ln' *string* - The language to display
        """

        # load the right message language
        _ = gettext_set_language(ln)

        # get query arguments:
        res = run_sql("SELECT urlargs FROM query WHERE id=%s", (id_query,))
        argd = {}
        if res:
            argd = cgi.parse_qs(res[0][0])

        rssurl = self.build_rss_url(argd)
        alerturl = weburl + '/youralerts/input?ln=%s&amp;idq=%s' % (ln, id_query)

        out = '''<a name="googlebox"></a>
                 <table class="googlebox"><tr><th class="googleboxheader">%(similar)s</th></tr>
                 <tr><td class="googleboxbody">%(msg_alert)s</td></tr>
                 </table>
                 ''' % {
                'similar' : _("Interested in being notified about new results for this query?"),
                'msg_alert': _("""Set up a personal %(x_url1_open)semail alert%(x_url1_close)s
                                  or subscribe to the %(x_url2_open)sRSS feed%(x_url2_close)s.""") % \
                        {'x_url1_open': '<a href="%s"><img src="%s/img/mail-icon-12x8.gif" border="0" alt="" /></a> ' % (alerturl, weburl) + ' <a class="google" href="%s">' % (alerturl),
                         'x_url1_close': '</a>',
                         'x_url2_open': '<a href="%s"><img src="%s/img/feed-icon-12x12.gif" border="0" alt="" /></a> ' % (rssurl, weburl) + ' <a class="google" href="%s">' % rssurl,
                         'x_url2_close': '</a>',
                         }}
        return out

    def tmpl_detailed_record_metadata(self, recID, ln, format,
                                      content,
                                      creationdate=None,
                                      modifydate=None):
        """Returns the main detailed page of a record

        Parameters:

          - 'recID' *int* - The ID of the printed record

          - 'ln' *string* - The language to display

          - 'format' *string* - The format in used to print the record

          - 'content' *string* - The main content of the page

          - 'creationdate' *string* - The creation date of the printed record

          - 'modifydate' *string* - The last modification date of the printed record
        """
        _ = gettext_set_language(ln)

        out = content

        return out

    def tmpl_detailed_record_statistics(self, recID, ln,
                                        downloadsimilarity,
                                        downloadhistory, viewsimilarity):
        """Returns the statistics page of a record

        Parameters:

          - 'recID' *int* - The ID of the printed record

          - 'ln' *string* - The language to display

          - downloadsimilarity *string* - downloadsimilarity box

          - downloadhistory *string* - downloadhistory box

          - viewsimilarity *string* - viewsimilarity box

        """
        # load the right message language
        _ = gettext_set_language(ln)

        out = ''

        if CFG_BIBRANK_SHOW_DOWNLOAD_STATS and downloadsimilarity is not None:
            similar = self.tmpl_print_record_list_for_similarity_boxen (
                _("People who downloaded this document also downloaded:"), downloadsimilarity, ln)

            out = '<table>'
            out += '''
                    <tr><td>%(graph)s</td></tr>
                    <tr><td>%(similar)s</td></tr>
                    ''' % { 'weburl': weburl,   'recid': recID, 'ln': ln,
                             'similar': similar, 'more': _("more"),
                             'graph': downloadsimilarity
                             }

            out += '</table>'
            out +=  '<br />'

        if CFG_BIBRANK_SHOW_READING_STATS and viewsimilarity is not None:
            out += self.tmpl_print_record_list_for_similarity_boxen (
                _("People who viewed this page also viewed:"), viewsimilarity, ln)

        if CFG_BIBRANK_SHOW_DOWNLOAD_GRAPHS and downloadhistory is not None:
            out += downloadhistory + '<br />'

        return out

    def tmpl_detailed_record_citations(self, recID, ln,
                                       citinglist, citationhistory,
                                       cociting,selfcited):
        """Returns the citations page of a record

        Parameters:

          - 'recID' *int* - The ID of the printed record

          - 'ln' *string* - The language to display

          - citinglist *list* - a list of tuples [(x1,y1),(x2,y2),..] where x is doc id and y is number of citations

          - citationhistory *string* - citationhistory box

          - cociting *string* - cociting box

          - selfcited list - a list of self-citations for recID

        """
        # load the right message language
        _ = gettext_set_language(ln)

        out = '<table>'
        if CFG_BIBRANK_SHOW_CITATION_STATS and citinglist is not None:
            similar = self.tmpl_print_record_list_for_similarity_boxen(
                _("Cited by: %s records") % len (citinglist), citinglist, ln)

            out += '''
                    <tr><td>
                      %(similar)s&nbsp;%(more)s
                      <br /><br />
                    </td></tr>''' % {
                'more': create_html_link(
                self.build_search_url(p='recid:%d' % \
                                      recID,      #XXXX
                                      rm='citation', ln=ln),
                                      {}, _("more")),
                'similar': similar}

        if CFG_BIBRANK_SHOW_CITATION_GRAPHS and selfcited is not None:
	    sc_scorelist = [] #a score list for print..
	    for s in selfcited:
		#copy weight from citations
		weight = 0
		for c in citinglist:
			(crec,score) = c
			if crec == s:
				weight = score
		tmp = [s,weight]
		sc_scorelist.append(tmp)
            scite = self.tmpl_print_record_list_for_similarity_boxen (
                _(".. of which self-citations: %s records") % len (selfcited), sc_scorelist, ln)
            out += '<tr><td>'+scite+'</td></tr>'

        if CFG_BIBRANK_SHOW_CITATION_STATS and cociting is not None:
            similar = self.tmpl_print_record_list_for_similarity_boxen (
                _("Co-cited with: %s records") % len (cociting), cociting, ln)

            out += '''
                    <tr><td>
                      %(similar)s&nbsp;%(more)s
                      <br />
                    </td></tr>''' % { 'more': create_html_link(self.build_search_url(p='cocitedwith:%d' % recID, ln=ln),
                                                                {}, _("more")),
                                      'similar': similar}

        if CFG_BIBRANK_SHOW_CITATION_GRAPHS and citationhistory is not None:
            out += '<tr><td>%s</td></tr>' % citationhistory

        out += '</table>'

        return out

    def tmpl_detailed_record_references(self, recID, ln, content):
        """Returns the discussion page of a record

        Parameters:

          - 'recID' *int* - The ID of the printed record

          - 'ln' *string* - The language to display

          - 'content' *string* - The main content of the page
        """
        # load the right message language
        _ = gettext_set_language(ln)

        out = ''
        if content is not None:
            out += content

        return out
