#!/usr/bin/python
"""
#  Copyright (C)2013  Alexander Gude - alex.public.account+GetWiki@gmail.com
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option)any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
#  The most recent version of this program is avaible at:
#  http://code.google.com/p/wikipedia-article-exporter/
"""

import urllib
import urllib2
from optparse import OptionParser
import json

# This part is called before functions... because if it isn't then the
# functions complain that options.FOO isn't defined
"""
    Allows command line options to be parsed
"""
usage = "usage: python %prog [OPTIONS] -f 'DEST_FILE' -a 'SOURCE_ARTICLE'"
version = "%prog Version 2.2\nCopyright (C)2013 Alexander Gude - alex.public.account+GetWiki@gmail.com\nThis is free software.  You may redistribute copies of it under the terms of\nthe GNU General Public License <http://www.gnu.org/licenses/gpl.html>.\nThere is NO WARRANTY, to the extent permitted by law.\n\nWritten by Alexander Gude."
parser = OptionParser(usage=usage, version=version)
parser.add_option("-a", "--article", action="store", type="string", dest="articlename", help="the article name to be exported")
parser.add_option("-f", "--file", action="store", type="string", dest="filename", help="the file to save the article to")
parser.add_option("-c", "--cat", "--concatenate", action="store_false", dest="split", help="save all revisions to one xml file")
parser.add_option("-s", "--split", action="store_true", dest="split", default=True, help="Split into multiple xml files with length equal to limit revisions")
parser.add_option("-l", "--limit", action="store", type="string", dest="limit", default="50", help="the number of Wikipedia revisions to return at a time, max 50")
parser.add_option("-q", "--quiet", action="store_false", dest="verbose", help="don't print status messages to stdout")
parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False, help="print status messages to stdout")
parser.add_option("-t", "--action", action="store", type="string", dest="action", default='query', help="sets action, currently only works with 'query'")
parser.add_option("-p", "--prop", action="store", type="string", dest="prop", default='revisions', help="sets prop, currently only works with 'revisions'")
parser.add_option("-r", "--rvdir", action="store", type="string", dest="rvdir", default='newer', help="'newer' or 'older', if newer items are returned with oldest first, otherwise newest first")
parser.add_option("-i", "--rvstartid", action="store", type="string", dest="rvstartid", default=None, help="rvstartid to begin downloading")

(options, args) = parser.parse_args()


def getArticle(articlename=options.articlename, action=options.action, prop=options.prop, rvstartid=options.rvstartid, rvdir=options.rvdir, limit=options.limit, verbose=options.verbose, split=options.split):
    """
    This function downloads the contents of the requested article. It has to be
    looped to fully grab the article though. It returns a mixed dictions/list
    object, that must be parsed by toXML().

    usage:
        (contents, startid)= getArticle(articlename, action, prop, rvstartid, rvdir, limit, verbose, split)

    input:
        articlename     (str)     : the name of the article to download
        action          (str)     : sets the action, currently only query is useful if you want to use prop=revisions
        prop            (str)     : sets the property, currently script only supports revisions (downloads revisions)
        rvstartid       (int)     : sets the inclusive comment id to start at
        rvdir           (str)     : 'newer' or 'older', newer means oldest first, older means newest entries first
        limit           (int)     : the number of revisions to request at one time, [1:50] inclusive
                                     if split = True, then each file will have this many revisions saved to it
        verbose         (bool)    : print progress to stdout or not
        split           (bool)    : split revisions into files if true, else saves all revisions to one large file

    output:
        contents        (dict)    : a dictionary/list object, to be parsed by toXML()
        startid         (int)     : rvstartid of the first entry in the NEXT set
    """
    if verbose:
        print "\tFetching Article from Wikipedia and parsing"
    if rvstartid == None:
        if verbose:
            print "\t\tDownloading first revisions"
    else:
        if verbose:
            print "\t\tDownloading revisions starting at: " + str(rvstartid)

    ## Sets up urllib and urllib2 to open the page, submit the request, and read the contents into a local variable
    ### If start id is provided use it, else start at the begining
    paramsd = {'action': action, 'prop': prop, 'titles': articlename, 'rvlimit': limit, 'rvprop': 'ids|timestamp|user|comment|content', 'rvdir': rvdir, 'format': 'json'}
    if rvstartid != None:
        paramsd['rvstartid'] = rvstartid

    params = urllib.urlencode(paramsd)
    req = urllib2.Request(url='http://en.wikipedia.org/w/api.php', data=params)
    f = urllib2.urlopen(req)
    contents = f.read()
    f.close()
    if verbose:
        print "\t\tDownloading complete"

    # using json to convert json to dictionaries and lists
    if verbose:
        print "\t\tConverting JSON data into dictionary"
    contents = json.loads(contents)

    ## Check if there are more to download, if so set startid to the next rvstartid
    if verbose:
        print "\t\tExtracting rvstartid"
    try:
        startid = contents['query-continue']['revisions']['rvstartid']
    except KeyError:
        startid = None  # None is used to terminate

    ## Now we return the contents, and startid as a tuple
    return (contents, startid)


def toXML(contents, verbose=options.verbose):
    """
    This function takes in a dictionary/list object (of a very special form, as
    output by getArticle())and returns XML in a str

    usage:
         contents = toXML(contents, verbose )

    input:
        contents        (str)     : the contents to be converted to XML
        verbose         (bool)    : print progress to stdout or not

    output:
        finalxml        (str)     : xml string
    """
    if verbose:
        print "\tConverting article to XML"
    finalxml = returnXMLhead()
    # First we try to grab the inner dictionary containing just the article
    try:
        contents = contents['query']['pages']
    except KeyError:
        raise "Can not extract contents['query']['pages'] in toXML()"

    # Now we grab the page ID, namespace, and title
    if verbose:
        print "\t\tExtracting page ID, namespace, and title"
    ## If there is more than one key, then you've requested two pages (although I don't know how you did this)
    ## otherwise we set an articleid and set the value from the dictionary to articlecont
    if len(contents.keys()) != 1:
        raise "Unknown key in contents in toXML()"
    else:
        articleid = contents.keys()[0]
        articlecont = contents[articleid]

    ## if Missing keyword is given, then error! :(
    if 'missing' in articlecont.keys():
        raise "Article is missing!"

    ## Now lets get the namespace
    try:
        namespace = articlecont['ns']
    except KeyError:
        raise "Can not determine namespace in toXML()"

    ## And the title
    try:
        title = makesafe(articlecont['title'])
    except KeyError:
        raise "Can not determine title in toXML()"

    ## Finally, we pull out the list of revisions
    if verbose:
        print "\t\tExtracting revision list"
    try:
        revlist = articlecont['revisions']
    except KeyError:
        raise "Can not find revisions in toXML()"

    ## Adding xml tags
    finalxml.append(returnXMLtag('title', title, space='    '))
    finalxml.append(returnXMLtag('id', articleid, space='    '))

    # Loop through revisions
    if verbose:
        i = 0
        print "\t\tBegining revision loop"
    for rev in revlist:
        if verbose:
            print "\t\t\tWorking on Revision %03i" % (i)
            i += 1
        # Start a new list to contain the xml
        revxml = ['    <revision>']
        ## Trying to pull out various values, and making them into xml
        if verbose:
            print "\t\t\t\tExtracting revision ID, timestamp, user, and comment"
        ### ID
        try:
            revid = rev['revid']
        except:
            raise "Can not find revid for %s in toXML()" % (rev)
        revxml.append(returnXMLtag('id', revid, space='      '))
        ### Timestamp
        try:
            timestamp = rev['timestamp']
        except:
            raise "Can not find timestamp for %s in toXML()" % (rev)
        revxml.append(returnXMLtag('timestamp', timestamp, space='      '))
        ### User
        try:
            user = rev['user']
        except:
            raise "Can not find user for %s in toXML()" % (rev)
        #### Users need <contributor> tags around them, also IPs and Users are different
        revxml.append('      <contributor>')
        if isIP(user):
            revxml.append(returnXMLtag('ip', user, space='        '))
        else:
            revxml.append(returnXMLtag('username', user, space='        '))
        revxml.append('      </contributor>')
        ### Comment
        try:
            comment = makesafe(rev['comment'])
        except:
            comment = ''  # They do not return a comment if it is blank
        revxml.append(returnXMLtag('comment', comment, space='      '))
        ### Pulling out the actual contents
        if verbose:
            print "\t\t\t\tExtracting contents"
        try:
            editcont = makesafe(rev['*'])
        except:
            raise "Can not find content for %s in toXML()" % (rev)
        revxml.append(returnXMLtag('text', editcont, space='      ', alt='xml:space="preserve"'))
        # Close up the xml and add to the finalxml
        revxml.append('    </revision>')
        finalxml += revxml

    if verbose:
        print "\t\tFinished revision loop"

    # Closing up the tags
    if verbose:
        print "\t\tClosing XML"
    finalxml.append('  </page>')
    finalxml.append('</mediawiki>')

    return '\n'.join(finalxml)


def makesafe(str):
    """
    Subs <, >, & and " in strings, also replaces '\\/'

    usage:
         str = makesafe(str )

    input:
        str             (str)     : a string
    output:
        newstr          (str)     : safe str
    """
    str = str.replace('&', '&amp;')  # ALWAYS FIRST or it messes up the other &
    str = str.replace('<', '&lt;')
    str = str.replace('>', '&gt;')
    str = str.replace('"', '&quot;')
    str = str.replace('\\/', '/')
    return str


def isIP(name):
    """
    If the string is an IP address, returns True, else False

    usage:
         bool = isIP(name )

    input:
        name            (str)     : username to test
    output:
        bool            (bool)    : True = IP, False = User
    """
    # Can it be split on . into 4?
    namelen = len(name.split('.'))
    try:
        assert namelen == 4
    except AssertionError:
        return False
    # Ok, is each of the 4 an Int? And between 0-255
    for i in range(4):
        try:
            null = int(name.split('.')[i])
            assert 0 <= null <= 255
        except ValueError:
            return False
        except AssertionError:
            return False
    # Ok, I guess it's an IP
    return True


def returnXMLtag(tag, cont, space='', alt=None):
    """
    Returns 'space<tag alt>Cont</tag>'

    usage:
         xml.append(returnXMLtag(tag, cont, space, alt ))

    input:
        tag             (str)     : xml tag name
        cont            (str)     : value to store in tag
        space           (str)     : str of the form '    '
        alt             (str)     : aditional values to pack into the tag
                                     if none, uses 'space<tag>cont</tag>'
    output:
        xml             (str)     : string in the form 'space<tag alt>Cont</tag>'
    """
    if not alt:
        return '%s<%s>%s</%s>' % (space, tag, cont, tag)
    else:
        return '%s<%s %s>%s</%s>' % (space, tag, alt, cont, tag)


def writeFile(contents, filename=options.filename, verbose=options.verbose):
    """
    This function writes the contents to a file

    usage:
         writeFile(contents, filename, verbose )

    input:
        contents        (str)     : the contents to be writen to a file
        filename        (str)     : the name of the file to save to
        verbose         (bool)    : print progress to stdout or not

    output:
        No output (not even None)
    """
    if verbose:
        print "\tWriting file " + filename + " now."

    try:
        ff = open(filename, 'w')
    except IOError, (errno, strerror):
        raise "I/O error(%s): %s" % (errno, strerror)
    else:
        # If it's only ascii, we can just write a nice happy ascii file
        try:
            ff.write(contents)
            if verbose:
                print "\t\tWriting as ASCII"
        # otherwise we have to convert it all to unicode
        except UnicodeEncodeError:
            ff.write(contents.encode("utf-8"))
            if verbose:
                print "\t\tWriting as utf-8"

        ff.close()


def returnXMLhead(verbose=options.verbose):
    """
    This function returns the standard header for our wikipedia XML.

    This huge, stupidly large string has to go somewhere... Might as well put
    it here

    usage:
         xmllist = returnXMLhead(verbose)

    input:
        verbose         (bool)    : print progress to stdout or not

    output:
        xmllist         (list)    : contains the xml header, each lines is a line of xml
    """
    if verbose:
        print "\t\tWriting XML header"
    finalxml = """<mediawiki xmlns="http://www.mediawiki.org/xml/export-0.3/"\
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" \
xsi:schemaLocation="http://www.mediawiki.org/xml/export-0.3/ \
http://www.mediawiki.org/xml/export-0.3.xsd" version="0.3" xml:lang="en">
  <siteinfo>
    <sitename>Wikipedia</sitename>
    <base>http://en.wikipedia.org/wiki/Main_Page</base>
    <generator>MediaWiki 1.14alpha</generator>
    <case>first-letter</case>
      <namespaces>
      <namespace key="-2">Media</namespace>
      <namespace key="-1">Special</namespace>
      <namespace key="0" />
      <namespace key="1">Talk</namespace>
      <namespace key="2">User</namespace>
      <namespace key="3">User talk</namespace>
      <namespace key="4">Wikipedia</namespace>
      <namespace key="5">Wikipedia talk</namespace>
      <namespace key="6">Image</namespace>
      <namespace key="7">Image talk</namespace>
      <namespace key="8">MediaWiki</namespace>
      <namespace key="9">MediaWiki talk</namespace>
      <namespace key="10">Template</namespace>
      <namespace key="11">Template talk</namespace>
      <namespace key="12">Help</namespace>
      <namespace key="13">Help talk</namespace>
      <namespace key="14">Category</namespace>
      <namespace key="15">Category talk</namespace>
      <namespace key="100">Portal</namespace>
      <namespace key="101">Portal talk</namespace>
    </namespaces>
  </siteinfo>
  <page>""".splitlines()

    return finalxml


def downloadArticles(articlename=options.articlename, action=options.action, prop=options.prop, rvstartid=options.rvstartid, rvdir=options.rvdir, limit=options.limit, verbose=options.verbose, split=options.split, filename=options.filename):
    """
    This function loops getArticle()to download the article, as well as passes
    it to toXML()to convert it, before finally passing it to writeFile()to
    output it

    usage:
        downloadArticles(articlename, action, prop, rvstartid, rvdir, limit, verbose, split, filename)

    input:
        articlename     (str)     : the name of the article to download
        action          (str)     : sets the action, currently only query is useful if you want to use prop=revisions
        prop            (str)     : sets the property, currently script only supports revisions (downloads revisions)
        rvstartid       (int)     : sets the inclusive comment id to start at
        rvdir           (str)     : 'newer' or 'older', newer means oldest first, older means newest entries first
        limit           (int)     : the number of revisions to request at one time, [1:50] inclusive
                                     if split = True, then each file will have this many revisions saved to it
        verbose         (bool)    : print progress to stdout or not
        split           (bool)    : split revisions into files if true, else saves all revisions to one large file
        filename        (str)     : the name of the file to save to

    output:
        No output (not even None)
    """
    if verbose:
        print "Begining Export"
    if verbose:
        print "\tSplit article into multiple files set to: " + str(split)

    ## If the content is going to be split
    if split:
        i = 0
        while True:
            (cont, startid) = getArticle(articlename=articlename, action=action, prop=prop, rvstartid=rvstartid, rvdir=rvdir, limit=limit, verbose=verbose, split=split)
            cont = toXML(cont)
            writeFile(cont, filename + "%03i" % i)
            if startid == None:
                break
            else:
                rvstartid = startid
                i += 1
    ## If the content is going to be spit out as one huge file
    else:
        # Run the first time
        limit = 50  # no need to do it in smaller amounts
        (cont, startid) = getArticle(articlename=articlename, action=action, prop=prop, rvstartid=rvstartid, rvdir=rvdir, limit=limit, verbose=verbose, split=split)
        while startid:  # If None, terminates
            (newcont, startid) = getArticle(articlename=articlename, action=action, prop=prop, rvstartid=startid, rvdir=rvdir, limit=limit, verbose=verbose, split=split)
            try:
                articleid = cont['query']['pages'].keys()[0]
            except KeyError:
                raise "Can not determine articleid"
            try:
                cont['query']['pages'][articleid]['revisions'] += newcont['query']['pages'][articleid]['revisions']  # Trying too add revisions lists together
            except KeyError:
                raise "Can not open the revisions lists in one of the content versions"
        # Now with one combined list, we run as normal
        cont = toXML(cont)
        writeFile(cont, filename)

    if verbose:
        print "Finished Export"

# If running as the main script, instead of imported
if __name__ == '__main__':
    downloadArticles()
