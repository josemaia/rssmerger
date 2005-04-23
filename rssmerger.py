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
# Requires: Python 2.1+
#
# Changelog:
# 0.2 
#     Added --items parameter
#     Added correct writing of XML RSS files (using DOM)
#     Added namespaces ('id' is now 'rm:publisher')
#     Output feeds are now valid RSS 2.0
# 0.3
#     Multiple root nodes (xml-stylesheet) are now handled
#
import sys
import urllib
import time
import getopt
import xml.dom.ext
from xml.dom import minidom, Node

# URL's for feeds to merge. Do not use weird chars in key.
rssUrls = {
	"debsec":"http://www.debian.org/security/dsa-long",
	"osnews":"http://www.osnews.com/files/recent.rdf",
	"devchannel":"http://www.devchannel.org/index.rss",
	"linuxsecurity":"http://www.linuxsecurity.com/linuxsecurity_articles.rdf",
	"kuro5hin":"http://www.kuro5hin.org/backend.rdf",
	"slashdot":"http://slashdot.org/index.rss",
	"lwn":"http://lwn.net/headlines/rss",
	"gnomenews":"http://news.gnome.org/gnome-news/rdf",
	"oreilly":"http://www.oreillynet.com/meerkat/?&p=7619&_fl=rss10",
	"nooface":"http://nooface.net/nooface.rdf",
	"debianplanet":"http://www.debianplanet.org/module.php?mod=node&op=feed",
	"artima":"http://www.artima.com/newatartima.rss",
	"geekpress":"http://www.geekpress.com/index.rdf",
	"linuxcom":"http://www.linux.com/index.rss",
	"newsforge":"http://www.newsforge.com/index.rss",
	"gnomefiles":"http://www.gnomefiles.org/files/gnomefiles.rdf",
	"joel":"http://www.joelonsoftware.com/rss.xml",
}

rssItemsMax = 60 
silent = 0 
verbose = 0


def rssFetch (url):
	"""
	Fetch a RSS file from somewhere.
	"""

	f_rss = urllib.urlopen (url)
	return f_rss.read()
    

def rssWrite (filename, channelTitle, channelDescription, channelLink, items):
	"""
	Write items to a RSS2.0 file
	"""

	rssNew = xml.dom.minidom.Document()
	elemRss = rssNew.createElementNS("http://blogs.law.harvard.edu/tech/rss", "rss")
	elemRss.setAttribute("version", "2.0")
	
	elemChannel = rssNew.createElement("channel")
	elemChannel.appendChild(createElementText("title", channelTitle))
	elemChannel.appendChild(createElementText("link", channelLink))
	elemChannel.appendChild(createElementText("description", channelDescription))

	for item in items:
		elemChannel.appendChild(rssComposeItem(item))
	
	elemRss.appendChild(elemChannel)
	rssNew.appendChild(elemRss)

	rssFile = open(filename, "w")
	xml.dom.ext.PrettyPrint(rssNew, rssFile)
	rssFile.close()


def createElementText (element, text):
	"""
	Create an XML DOM element with a child Text node and return it
	"""

	elemNew = xml.dom.minidom.Document().createElement(element)
	textNew = xml.dom.minidom.Document().createTextNode(text)
	elemNew.appendChild(textNew)

	return elemNew

def createElementTextNS (namespace, element, text):
	"""
	Create an XML DOM element with a child Text node and return it
	"""

	elemNew = xml.dom.minidom.Document().createElementNS(namespace, element)
	textNew = xml.dom.minidom.Document().createTextNode(text)
	elemNew.appendChild(textNew)

	return elemNew


def rssComposeItem (item):
	"""
	Composes a RSS <item> element from the item dict
	"""
	
	elemItem = xml.dom.minidom.Document().createElement("item")
	
	elemItem.appendChild(createElementText("title", item["title"]))
	elemItem.appendChild(createElementText("link", item["link"]))
	elemItem.appendChild(createElementText("date", item["date"]))
	elemItem.appendChild(createElementTextNS("http://localhost/rssmerger/", "rm:publisher", item["publisher"]))
	if item.has_key("description"):
		elemItem.appendChild(createElementText("description", item["description"]))

	return elemItem
	

def rssExtractItem (node, rssID):
	"""
	Given an <item> node, extract all possible RSS information from the node
	"""
	
	rssItem = {}
	for childNode in node.childNodes:
		if childNode.firstChild != None:
			if childNode.nodeName == "title":
				rssItem["title"] = childNode.firstChild.data.strip()
			if childNode.nodeName == "link":
				rssItem["link"] = childNode.firstChild.data.strip()
			if childNode.nodeName == "description":
				rssItem["description"] = childNode.firstChild.data.strip()
			if childNode.nodeName == "rm:publisher":
				rssItem["publisher"] = childNode.firstChild.data.strip()
			if childNode.nodeName == "date":
				rssItem["date"] = childNode.firstChild.data.strip()

	if not rssItem.has_key("publisher"):
		rssItem["publisher"] = rssID
				
	if not rssItem.has_key("date"):
		rssItem["date"] = time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime())
		
	if verbose:
		print "Item: " + rssItem["publisher"] + ": " + rssItem["title"]

	return rssItem
    

def rssFindItems(node, rssItems, rssID):
	"""
	Walk through a XML DOM and take action upon finding <item> nodes
	"""

	if node.nodeType == Node.ELEMENT_NODE:
		for childNode in node.childNodes:
			if childNode.nodeName == "item":
				rssItems.append (rssExtractItem (childNode, rssID))
			else:
				rssFindItems(childNode, rssItems, rssID)

	return (rssItems)
    

def usage():
	"""
	Print usage information to stdout
	"""

	print "Usage: "+sys.argv[0]+" [OPTION]"
	print "Merges the items in a couple of RDF RSS feeds to a single RSS feed."
	print "Appearance of new items over time are remembered and added in the"
	print "correct sequence"
	print
	print "Arguments:"
	print "  -s, --silent        Silent. Do not report errors in RSS files"
	print "  -i, --items ITEMS   Only keep ITEMS rss items in merged list"
	print "  -v, --verbose       Be verbose"
	print "  -h, --help          Show short help message (this)"
	print
	print "(C) Ferry Boender, 2004-2005 <f DOT boender AT electricmonk DOT nl>"

# Parse commandline options
try:
	opts, args = getopt.getopt(sys.argv[1:], "hsvi:", ["help", "silent", "verbose", "items:"])
except getopt.GetoptError:
	usage()
	sys.exit(2)
for o, a in opts:
	if o in ("-h", "--help"):
		usage()
		sys.exit()
	if o in ("-s", "--silent"):
		silent = 1
	if o in ("-i", "--items"):
		rssItemsMax = a
	if o in ("-v", "--verbose"):
		verbose = 1
		
# Get seen items
rssItemsSeen = []
try:
	rssSeen = rssFetch ("merged.rss")
	root = minidom.parseString(rssSeen)
except IOError:
	pass
except:
	if not silent:
		print "Cannot parse merged.rss: " + str(sys.exc_info()[1])
else:
	# Extract all seen items
	node = root.firstChild
	rssItemsSeen = rssFindItems(node, rssItemsSeen, "seen")

# Get last seen items (to determine which items are new)
rssItemsLastSeen = []
try:
	rssSeen = rssFetch ("seen.rss")
	root = minidom.parseString(rssSeen)

except IOError:
	pass
except:
	if not silent:
		print "Cannot parse seen.rss: " + str(sys.exc_info()[1])
else:
	# Extract all seen items
	node = root.firstChild
	rssItemsLastSeen = rssFindItems(node, rssItemsLastSeen, "lastseen")
	
# Merge seen items and new published items
rssItemsMerged = []
rssItemsNewLastSeen = []

for rssID in rssUrls.keys():

	rssItemsPub = []
	
	# Read published items
	try:
		rssPub = rssFetch (rssUrls[rssID])
		root = minidom.parseString(rssPub)
	except:
		if not silent:
			print "Cannot parse " + rssUrls[rssID] + ": " + str(sys.exc_info()[1])
	else:
		# Walk through all root-items (handles xml-stylesheet, etc)
		for rootNode in root.childNodes:
			if rootNode.nodeType == Node.ELEMENT_NODE:
				# Extract all items
				node = rootNode
				rssItemsPub = rssFindItems(node, rssItemsPub, rssID)

				if len(rssItemsPub) > 0:
					# Find last seen item for this feed
					lastId = -1
					for i in range(len(rssItemsLastSeen)):
						if verbose:
							print "Find last seen: " + rssItemsLastSeen[i]["publisher"] + " - " + rssID
						if rssItemsLastSeen[i]["publisher"] == rssID:
							lastId = i
							
					rssItemLastSeenTitle = ""
					if lastId > -1:
						rssItemLastSeenTitle = rssItemsLastSeen[lastId]["title"]
						if verbose:
							print "Last seen for " + rssID + ": " + rssItemLastSeenTitle
					
					# First extract all new rss items
					for rssItem in rssItemsPub:
						if rssItem["title"] == rssItemLastSeenTitle:
							# No more new items, stop extracting from published
							break
						else:
							# Ah, a new item. Let's add it to the merged list of seen and unseen items
							if len(rssItemsMerged) < rssItemsMax:
								rssItemsMerged.append (rssItem)

					# Save the new latest seen item
					rssItemsNewLastSeen.append (rssItemsPub[0])

# Now add all items we've already seen to the list too.
for rssItem in rssItemsSeen:
	if len(rssItemsMerged) < rssItemsMax:
		rssItemsMerged.append (rssItem)

# find feeds which don't have a 'last seen' item anymore due to errors in 
# the rss feed or something and set it back to the previous last seen item
for rssID in rssUrls.keys():
	found = 0;
	for rssItem in rssItemsNewLastSeen:
		if rssItem["publisher"] == rssID:
			found = 1;
			
	if found == 0:
		# Find old last seen item
		for rssItem in rssItemsLastSeen:
			if rssItem["publisher"] == rssID:
				rssItemsNewLastSeen.append (rssItem)

# Write the new merged list of items to a rss file
try:
	rssWrite (
	"merged.rss", 
	"rssmerger Merged items", 
	"This file contains items which have been merged from various RSS feeds", 
	"http://www.electricmonk.nl", 
	rssItemsMerged
	)
except IOError:
	if not silent:
		print "couldn't write merged.rss file" + str(sys.exc_value)
except:
	if not silent:
		print "Unknow error: " + str(sys.exc_value)

# Write the new list of seen items to a rss file
try:
	rssWrite (
	"seen.rss", 
	"rssmerger Seen items", 
	"This file contains the last seen items for each feed", 
	"http://www.electricmonk.nl", 
	rssItemsNewLastSeen
	)
except IOError:
	if not silent:
		print "couldn't write merged.rss file" + str(sys.exc_value)
except:
	if not silent:
		print "Unknow error: " + str(sys.exc_value)
