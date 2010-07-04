#!/usr/bin/python
"""
#  Copyright (C) 2008  Alexander Gude - alex.public.account+GetWiki@gmail.com
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
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
#
#  Version 1.1
#  January 26th (Saturday), 2008
"""

import urllib,urllib2
from optparse import OptionParser

## This part is called before functions... because if it isn't then the functions complain that options.FOO isn't defined
"""
    This part allows command line options to be parsed
"""
usage = "usage: %prog [OPTIONS] -f DEST_FILE -a SOURCE_ARTICLE"
version = "%prog Version 1.1\nCopyright (C) 2008 Alexander Gude - alex.public.account+GetWiki@gmail.com\nThis is free software.  You may redistribute copies of it under the terms of\nthe GNU General Public License <http://www.gnu.org/licenses/gpl.html>.\nThere is NO WARRANTY, to the extent permitted by law.\n\nWritten by Alexander Gude."
parser = OptionParser(usage=usage,version=version)
parser.add_option("-a", "--article", action="store", type="string", dest="articlename", help="the article name to be exported")
parser.add_option("-c", "--cat", "--concatenate", action="store_false", dest="split", help="save all revisions to one xml file")
parser.add_option("-f", "--file", action="store", type="string", dest="filename", help="the file to save the article to")
parser.add_option("-l", "--limit", action="store", type="string", dest="limit", default="100", help="the number of Wikipedia revisions to return at a time, max 100")
parser.add_option("-q", "--quiet", action="store_false", dest="verbose", help="don't print status messages to stdout")
parser.add_option("-s", "--split", action="store_true", dest="split", default=True, help="Split into multiple xml files with length equal to limit revisions")
parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False, help="print status messages to stdout")

(options, args) = parser.parse_args()

def getArticle(articlename=options.articlename, action='submit', limit=options.limit, offset=1, verbose=options.verbose, split=options.split):
    """
    This function actually downloads the contents of the requested article. It has to be looped to fully grab the article though.

    usage:
        getArticle(articlename, action, limit, offset, verbose, split)

    input:
        articlename     (str)      : the name of the article to download
        action          (str)      : sets the action for export, currently only 'submit' is valid 
        limit           (int)      : the number of revisions to request at one time, [1:100] inclusive 
                                     if split = True, then each file will have this many revisions saved to it
        offset          (str)      : either an int, in which case returns edits starting with the the int'th edit (1 is first, etc.)
                                     or a date in which case it returns edits after that date but not including that date (2002-01-27T20:25:56Z form)
        verbose         (bool)     : print progress to stdout or not
        split           (bool)     : split revisions into files if true, else saves all revisions to one large file

    output:
        contents        (str)      : Returned if requested page has revisions, and is the content of those revisions
        None            (None)     : Returned if requested page has no revisions, used to halt loops
    """
    if verbose: print "Downloading revisions with offset: "+str(offset)

    ## Sets up urllib and urllib2 to open the page, submit the request, and read the contents into a local variable
    headers = {'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.8.0.4) Gecko/20060508 Firefox/1.5.0.4'} # Needed to fool Wikipedia, it blocks urllib scripts otherwise
    params = urllib.urlencode({'title': 'Special:Export', 'pages': articlename, 'action': action, 'limit': limit, 'offset': offset})
    req = urllib2.Request(url='http://en.wikipedia.org/w/index.php', data=params, headers=headers)
    f = urllib2.urlopen(req)
    contents = f.read()
    f.close()

#    if verbose: print contents

    ## If we want the file split, then we need only save whatever Wikipedia gives us, otherwise we have to remove extra headers if we want one file 
    if '<revision>' not in contents: # The last version that contains no new pages will not have a revision tag, so we return None and use it to halt
        return None

    if split: 
        return contents
    else: 
        if offset != 1: # If not the first request, strip header
            return '\n'.join(contents.splitlines()[30:-2])
        else: # If the first request then we only strip the very last closing tags.
            return '\n'.join(contents.splitlines()[:-2])

def getLastEditDate(contents,verbose=options.verbose):
    """
    This function returns the date of the last edit to the contents given it.

    usage:
        getLastEditDate(contents,verbose)

    input:
        contents        (str)      : the content of revisions in one long string
        verbose         (bool)     : print progress to stdout or not

    output:
        dates           (str)      : Returned if requested page has revisions
        None            (None)     : Returned if requested page has no revisions, used to halt loops
    """
    dates = []

    if verbose: print "Checking for last edit date."

    for line in contents.splitlines():
        if '<timestamp>' in line:
            date = (line.split('>')[1]).split('<')[0]
            dates.append(date)
#           if verbose: print date

    dates.sort()
    
    try:
        return dates[-1]
    except: 
        return None

def writeFile(contents, filename=options.filename, verbose=options.verbose):
    """
    This function writes the contents to a file

    usage:
         writeFile(contents,filename)

    input:
        contents        (str)      : Returned if requested page has revisions, and is the content of those revisions
        filename        (str)      : the name of the file to be saved to
        verbose         (bool)     : print progress to stdout or not

    output:
        No output (not even None)
    """
    if verbose: print "Writing file "+filename+" now."

    try:
        ff = open(filename,'a')
    except IOError, (errno, strerror):
        raise "I/O error(%s): %s" % (errno, strerror)
    else:
        ff.write(contents)
        ff.close()

def downloadArticles(articlename=options.articlename, action='submit', limit=options.limit, offset=1, verbose=options.verbose, split=options.split, filename=options.filename):
    """
    This function loops getArticle() and getLastEditDate() to download the article and get it contents in final order.

    usage:
        downloadArticles(articlename, action, limit, offset, verbose, split)

    input:
        articlename     (str)      : the name of the article to download
        filename        (str)      : the name of the file to be saved to
        action          (str)      : sets the action for export, currently only 'submit' is valid 
        limit           (int)      : the number of revisions to request at one time, [1:100] inclusive 
                                     if split = True, then each file will have this many revisions saved to it
        offset          (str)      : either an int, in which case returns edits starting with the the int'th edit (1 is first, etc.)
                                     or a date in which case it returns edits after that date but not including that date (2002-01-27T20:25:56Z form)
        verbose         (bool)     : print progress to stdout or not
        split           (bool)     : split revisions into files if true, else saves all revisions to one large file

    output:
        No output (not even None)
    """
    if verbose: print "Split article into multiple files set to: "+str(split)

    if split:
        i = 0
        while True:
            newcontents = getArticle(articlename=articlename, action=action, limit=limit, offset=offset, verbose=verbose, split=split)
            if newcontents:
                writeFile(newcontents,filename+"%03i" % i)
                offset = getLastEditDate(newcontents)
                i += 1
            else: 
                break
    else:
        contentslist = []
        while True:
            newcontents = getArticle(articlename=articlename, action=action, limit=limit, offset=offset, verbose=verbose, split=split)
            if newcontents:
                contentslist.append(newcontents)
                offset = getLastEditDate(newcontents)
            else:
                break

        contentslist.append('</page>') # We have removed these two tags before, so we have to finally add them back.
        contentslist.append('</mediawiki>')
        contents = '\n'.join(contentslist)
        writeFile(contents,filename)

### RUN Python, RUN!
downloadArticles()
