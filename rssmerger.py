#!/usr/bin/python
#
# rssmerger
#
# Merges several RSS feeds into a single RSS 2.0 feed while retaining the
# order of appearance.
#
# By default it outputs two files: seen.rdf and
# merged.rdf. seen.rdf contains the last item we've seen for each feed.
# merged.rdf contains the last 60 (mixed) items from feeds.
#
# A identifier for each feed is added to each item by putting the id in
# a <rm:publisher> element (rm namespace).
#
# Usage: see rssmerger --help
#
# Requires: Python 2.6+
#
# Changelog:
# 0.2
#     Added --items parameter
#     Added correct writing of XML RSS files (using DOM)
#     Added namespaces ('id' is now 'rm:publisher')
#     Output feeds are now valid RSS 2.0
# 0.3
#     Multiple root nodes (xml-stylesheet) are now handled
# 0.4
#     Added --version parameter.
#     Added copyright notice to source and --version output.
#     Fixed a bug caused by empty <title> tags, thanks to Jeroen Leijen.
# 0.5
#     Added --queries parameter. It tells RssMerger to output SQL queries
#     that will insert items into a database.
# 0.6
#     Better handling of unicode when doing verbose outputting.
#     'content:encoded' tags in RSS items are now recognised as a description.
# 0.7
#     Timeouts set on retrieving of individual feeds (10 sec).
#     Various changes in logging/error reporting.
# 0.8
#    Deprecate python-xml. Now uses built-in XML package.
#    Python 2.6+ compatibility
#
# 1.0
#    Python 3 port
#    Load RSS feeds from file
# Copyright (C) 2004-2013 Ferry Boender <f.boender@electricmonk.nl>"
#
# This program is free software; you can redistribute it and/or modify"
# it under the terms of the GNU General Public License as published by"
# the Free Software Foundation; either version 2 of the License, or"
# (at your option) any later version."
#
# This program is distributed in the hope that it will be useful,"
# but WITHOUT ANY WARRANTY; without even the implied warranty of"
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the"
# GNU General Public License for more details."
#
# You should have received a copy of the GNU General Public License"
# along with this program; if not, write to the Free Software"
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA"
#

import sys
import socket
import urllib.request
import urllib.parse
import urllib.error
import time
import getopt
import xml.dom.minidom
import json

# URL's for feeds to merge. Do not use weird chars in key.
with open('feeds.json') as json_file:
    rssUrls = json.load(json_file)

rssItemsMax = 1000
silent = 0
verbose = 0
queries = False


def rssFetch(url):
    """
    Fetch a RSS file from somewhere.
    """

    try:
        f_rss = urllib.request.urlopen(url)
    except IOError as e:
        if not silent and url != 'file://merged.rss' and url != 'file://seen.rss':
            print("Failed to retrieve RSS feed %s" % (url))
        return False

    return f_rss.read()


def rssWrite(filename, channelTitle, channelDescription, channelLink, items):
    """
    Write items to a RSS2.0 file
    """

    rssNew = xml.dom.minidom.Document()
    elemRss = rssNew.createElementNS(
        "http://blogs.law.harvard.edu/tech/rss", "rss")
    elemRss.setAttribute("version", "2.0")

    elemChannel = rssNew.createElement("channel")
    elemChannel.appendChild(createElementText("title", channelTitle))
    elemChannel.appendChild(createElementText("link", channelLink))
    elemChannel.appendChild(createElementText(
        "description", channelDescription))

    for item in items:
        elemChannel.appendChild(rssComposeItem(item))

    elemRss.appendChild(elemChannel)
    rssNew.appendChild(elemRss)

    rssFile = open(filename, "w")
    rssFile.write(rssNew.toprettyxml())
    rssFile.close()


def createElementText(element, text):
    """
    Create an XML DOM element with a child Text node and return it
    """

    elemNew = xml.dom.minidom.Document().createElement(element)
    textNew = xml.dom.minidom.Document().createTextNode(text)
    elemNew.appendChild(textNew)

    return elemNew


def createElementTextNS(namespace, element, text):
    """
    Create an XML DOM element with a child Text node and return it
    """

    elemNew = xml.dom.minidom.Document().createElementNS(namespace, element)
    elemNew.setAttribute("xmlns:" + element.split(':', 1)[0], namespace)
    textNew = xml.dom.minidom.Document().createTextNode(text)
    elemNew.appendChild(textNew)

    return elemNew


def rssComposeItem(item):
    """
    Composes a RSS <item> element from the item dict
    """

    elemItem = xml.dom.minidom.Document().createElement("item")

    elemItem.appendChild(createElementText("title", item["title"]))
    elemItem.appendChild(createElementText("link", item["link"]))
    elemItem.appendChild(createElementText("date", item["date"]))
    elemItem.appendChild(createElementTextNS(
        "http://localhost/rssmerger/", "rm:publisher", item["publisher"]))
    if "description" in item:
        elemItem.appendChild(createElementText(
            "description", item["description"]))

    return elemItem


def rssItemElementGetData(node, rssID):
    global verbose
    if hasattr(node, 'data'):
        return(node.data.strip())
    else:
        if verbose:
            print("Node has no data in %s! (HTML tag in data?)" % (rssID))
        return("??")


def rssExtractItem(node, rssID):
    """
    Given an <item> node, extract all possible RSS information from the node
    """

    rssItem = {
        "title": "No title",
        "link": "http://localhost/",
        "description": "No description",
        "publisher": rssID,
        "date": time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime())
    }

    for childNode in node.childNodes:
        if childNode.firstChild != None:
            if childNode.nodeName == "title":
                rssItem["title"] = rssItemElementGetData(
                    childNode.firstChild, rssID)
            if childNode.nodeName == "link":
                rssItem["link"] = rssItemElementGetData(
                    childNode.firstChild, rssID)
            if childNode.nodeName == "description":
                rssItem["description"] = rssItemElementGetData(
                    childNode.firstChild, rssID)
            if childNode.nodeName == "content:encoded":
                rssItem["description"] = rssItemElementGetData(
                    childNode.firstChild, rssID)
            if childNode.nodeName == "rm:publisher":
                rssItem["publisher"] = rssItemElementGetData(
                    childNode.firstChild, rssID)
            if childNode.nodeName == "date":
                rssItem["date"] = rssItemElementGetData(
                    childNode.firstChild, rssID)

    if verbose:
        print("\t\tItem: " + rssItem["publisher"].encode('ascii',
                                                         'replace') + ": " + rssItem["title"].encode('ascii', 'replace'))

    return rssItem


def rssFindItems(node, rssItems, rssID):
    """
    Walk through a XML DOM and take action upon finding <item> nodes
    """

    if node.nodeType == xml.dom.Node.ELEMENT_NODE:
        for childNode in node.childNodes:
            if childNode.nodeName == "item":
                rssItems.append(rssExtractItem(childNode, rssID))
            else:
                rssFindItems(childNode, rssItems, rssID)

    return (rssItems)


def usage():
    """
    Print usage information to stdout
    """

    print("Usage: "+sys.argv[0]+" [OPTION]")
    print("Merges the items in a couple of RSS feeds to a single RSS feed.")
    print("Appearance of new items over time are remembered and added in the")
    print("correct sequence")
    print()
    print("Arguments:")
    print("  -s, --silent        Silent. Do not report errors in RSS files")
    print("  -q, --queries       Output all new RSS items as SQL queries")
    print("  -i, --items ITEMS   Only keep ITEMS rss items in merged list")
    print("  -v, --verbose       Be verbose")
    print("  -V, --version       Show version information")
    print("  -h, --help          Show short help message (this)")
    print()
    print("(C) Ferry Boender, 2004-2013 <ferry.boender@electricmonk.nl>")


def version():
    """
    Print version and other information to stdout
    """

    print("RSSmerger v0.8")
    print()
    print("Copyright (C) 2004-2013 Ferry Boender <ferry.boender@electricmonk.nl>")
    print()
    print("This program is free software; you can redistribute it and/or modify")
    print("it under the terms of the GNU General Public License as published by")
    print("the Free Software Foundation; either version 2 of the License, or")
    print("(at your option) any later version.")
    print()
    print("This program is distributed in the hope that it will be useful,")
    print("but WITHOUT ANY WARRANTY; without even the implied warranty of")
    print("MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the")
    print("GNU General Public License for more details.")
    print()
    print("You should have received a copy of the GNU General Public License")
    print("along with this program; if not, write to the Free Software")
    print("Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA")


# Parse commandline options
try:
    opts, args = getopt.getopt(sys.argv[1:], "hsqvVi:", [
                               "help", "silent", "queries", "verbose", "version", "items:"])
except getopt.GetoptError:
    usage()
    sys.exit(2)
for o, a in opts:
    if o in ("-h", "--help"):
        usage()
        sys.exit()
    if o in ("-s", "--silent"):
        silent = 1
    if o in ("-q", "--queries"):
        queries = 1
    if o in ("-i", "--items"):
        rssItemsMax = a
    if o in ("-v", "--verbose"):
        verbose = 1
    if o in ("-V", "--version"):
        version()
        sys.exit()

# Set default socket timeout so urllib doesn't hang when retrieving RSS feeds
socket.setdefaulttimeout(10)

# Get seen items
rssItemsSeen = []
try:
    rssSeen = rssFetch("file://merged.rss")
    if rssSeen:
        root = xml.dom.minidom.parseString(rssSeen)
    else:
        root = xml.dom.minidom.Document()
except:
    if not silent:
        print("Cannot parse merged.rss: " + str(sys.exc_info()[1]))
        raise
else:
    # Extract all seen items
    if rssSeen:
        node = root.firstChild
        rssItemsSeen = rssFindItems(node, rssItemsSeen, "seen")

# Get last seen items (to determine which items are new)
rssItemsLastSeen = []
try:
    rssSeen = rssFetch("file://seen.rss")
    if rssSeen:
        root = xml.dom.minidom.parseString(rssSeen)
    else:
        root = xml.dom.minidom.Document()
except:
    if not silent:
        print("Cannot parse seen.rss: " + str(sys.exc_info()[1]))
        raise
else:
    # Extract all seen items
    if rssSeen:
        node = root.firstChild
        rssItemsLastSeen = rssFindItems(node, rssItemsLastSeen, "lastseen")

# Merge seen items and new published items
rssItemsMerged = []
rssItemsNew = []
rssItemsNewLastSeen = []

for rssID in list(rssUrls.keys()):
    if verbose:
        print("Processing %s" % (rssID))

    rssItemsPub = []

    # Read published items
    try:
        if verbose:
            print("\tRetrieving %s" % (rssUrls[rssID]))
        rssPub = rssFetch(rssUrls[rssID])
        if not rssPub:
            if not silent:
                print("\tError")
        else:
            if verbose:
                print("\tRetrieved.")
        root = xml.dom.minidom.parseString(rssPub)
    except:
        if not silent:
            print("Cannot parse " +
                  rssUrls[rssID] + ": " + str(sys.exc_info()[1]))
    else:
        # Walk through all root-items (handles xml-stylesheet, etc)
        for rootNode in root.childNodes:
            if rootNode.nodeType == xml.dom.Node.ELEMENT_NODE:
                # Extract all items
                node = rootNode
                if verbose:
                    print("\tFinding all published items in '%s'" % (rssID))

                rssItemsPub = rssFindItems(node, rssItemsPub, rssID)

                if len(rssItemsPub) > 0:
                    # Find last seen item for this feed
                    lastId = -1
                    for i in range(len(rssItemsLastSeen)):
                        if verbose:
                            print("Find last seen: " + rssItemsLastSeen[i]["publisher"].encode(
                                'ascii', 'replace') + " - " + rssID)
                        if rssItemsLastSeen[i]["publisher"] == rssID:
                            lastId = i

                    rssItemLastSeenTitle = ""
                    if lastId > -1:
                        rssItemLastSeenTitle = rssItemsLastSeen[lastId]["title"]
                        if verbose:
                            print("\tLast seen for " + rssID + ": " +
                                  rssItemLastSeenTitle.encode('ascii', 'replace'))

                    # First extract all new rss items
                    for rssItem in rssItemsPub:
                        if rssItem["title"] == rssItemLastSeenTitle:
                            # No more new items, stop extracting from published
                            break
                        else:
                            # Ah, a new item. Let's add it to the merged list of seen and unseen items
                            if len(rssItemsMerged) < rssItemsMax:
                                rssItemsMerged.append(rssItem)
                            # Also add it to a seperate list of all new items
                            rssItemsNew.append(rssItem)

                    # Save the new latest seen item
                    rssItemsNewLastSeen.append(rssItemsPub[0])

# Now add all items we've already seen to the list too.
for rssItem in rssItemsSeen:
    if len(rssItemsMerged) < rssItemsMax:
        rssItemsMerged.append(rssItem)

# find feeds which don't have a 'last seen' item anymore due to errors in
# the rss feed or something and set it back to the previous last seen item
for rssID in list(rssUrls.keys()):
    found = 0
    for rssItem in rssItemsNewLastSeen:
        if rssItem["publisher"] == rssID:
            found = 1

    if found == 0:
        # Find old last seen item
        for rssItem in rssItemsLastSeen:
            if rssItem["publisher"] == rssID:
                rssItemsNewLastSeen.append(rssItem)

if queries:
    rssItemsNew.reverse()
    for rssItem in rssItemsNew:
        # Remove Unicode encodings for Database.
        for property in rssItem:
            rssItem[property] = rssItem[property].encode('ascii', 'replace')
        qry = "INSERT INTO rssitems (title, link, date, publisher, description) VALUES ('%s','%s','%s','%s', '%s');" % (rssItem["title"].replace('\'', '\\\''), rssItem["link"].replace(
            '\'', '\\\''), rssItem["date"].replace('\'', '\\\''), rssItem["publisher"].replace('\'', '\\\''), rssItem["description"].replace('\'', '\\\''))
        print(qry)
else:
    # Write the new merged list of items to a rss file
    try:
        rssWrite(
            "merged.rss",
            "rssmerger Merged items",
            "This file contains items which have been merged from various RSS feeds",
            "http://www.electricmonk.nl",
            rssItemsMerged
        )
    except IOError:
        if not silent:
            print("couldn't write merged.rss file" + str(sys.exc_info()[1]))
    except:
        if not silent:
            print("Unknow error: " + str(sys.exc_info()[1]))

# Write the new list of seen items to a rss file
try:
    rssWrite(
        "seen.rss",
        "rssmerger Seen items",
        "This file contains the last seen items for each feed",
        "http://www.electricmonk.nl",
        rssItemsNewLastSeen
    )
except IOError:
    if not silent:
        print("couldn't write merged.rss file" + str(sys.exc_info()[1]))
except:
    if not silent:
        print("Unknow error: " + str(sys.exc_info()[1]))
