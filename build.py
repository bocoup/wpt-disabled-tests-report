#!/usr/bin/env python3

import urllib.request
import json
import re
from string import Template
from datetime import date
import xlrd
import html
import urllib

mozillaURL = "https://searchfox.org/mozilla-central/search?q=disabled%3A&case=true&regexp=false&path=testing%2Fweb-platform%2Fmeta"
mozillaBugzillaURL = "https://searchfox.org/mozilla-central/search?q=bugzilla&case=true&path=testing%2Fweb-platform%2Fmeta"
chromiumURL = "https://cs.chromium.org/codesearch/f/chromium/src/third_party/WebKit/LayoutTests/TestExpectations"
webkitURL = "https://raw.githubusercontent.com/WebKit/webkit/master/LayoutTests/TestExpectations"
edgeXLSXURL = "https://github.com/w3c/web-platform-tests/files/1984479/NotRunFiles.xlsx"
edgeHTMLURL = "https://github.com/w3c/web-platform-tests/issues/10655#issuecomment-387434035"
flakyQuery = "q=is%3Aissue+label%3Aflaky"
wptAPIURL = "https://api.github.com/search/issues?" + flakyQuery + "+repo%3Aw3c/web-platform-tests"
wptHTMLURL = "https://github.com/w3c/web-platform-tests/issues?utf8=%E2%9C%93&" + flakyQuery

common = []

# Add path to common, merging with existing if present
def addPath(bug, path, results, product, onlyBug = False):
    if path[0] != "/":
        path = "/" + path
    pathFound = False
    pathPrefix = None
    if product == "web-platform-tests" and path[-1:] == "*":
        pathPrefix = path[:-1]
    for item in common:
        if pathPrefix and item["path"].find(pathPrefix) == 0 or item["path"] == path:
            if product in item and item[product]["bug"] == None:
                item[product]["bug"] = bug
                item[product]["results"] += " " + results
            else:
                item[product] = {"bug": bug, "results": results}
            pathFound = True
    if pathFound == False and onlyBug == False:
        common.append({"path": path, product: {"bug": bug, "results": results}})

# Mozilla
def scrapeSearchFox(url, isBugzillaSearch = False):
    contents = urllib.request.urlopen(url).readlines()
    # Extract the data, it's on a single line after a "<script>" line
    foundScript = False
    for line in contents:
        if foundScript:
            line = line.split(b"var results = ")[1][:-2]
            break
        if b"<script>" in line:
            foundScript = True
        continue

    # Massage data structure into a common format
    items = json.loads(line)["test"]["Textual Occurrences"]
    for item in items:
        line = item["lines"][0]["line"]
        values = line.split(' https://')
        results = values.pop(0)
        if len(values) > 0:
            bug = values[0]
        else:
            bug = None
        addPath(bug, item["path"].replace("testing/web-platform/meta", "").replace(".ini", ""), results, "mozilla", isBugzillaSearch)

scrapeSearchFox(mozillaURL)
scrapeSearchFox(mozillaBugzillaURL, True)

# Fetch and parse TestExpectations file
def extractFromTestExpectations(url, wptPrefix, product):
    contents = urllib.request.urlopen(url).readlines()
    for line in contents:
        if line[0:1] == b"#":
            continue
        if wptPrefix in line:
            line = str(line[:-1], 'utf-8')
            # Extract the path and expected results tokens
            match = re.search(r"^((?:webkit|crbug)[^ ]+)? ?(?:\[ (?:Release|Debug) \] )?" + str(wptPrefix, 'utf-8') + "([^ ]+) (\[.+\])", line)
            if match == None:
                continue
            bug = match.group(1)
            path = match.group(2)
            results = match.group(3)
            # Remove tags we're not interested in
            results = results.replace(" DumpJSConsoleLogInStdErr", "").replace("ImageOnly", "")
            # Don't collect stable but failing tests
            if results == "[ Failure ]" or results == "[ ]":
                continue
            addPath(bug, path, results, product)

# Chromium
extractFromTestExpectations(chromiumURL,
                            b"external/wpt/",
                            "chromium")

# WebKit
extractFromTestExpectations(webkitURL,
                            b"imported/w3c/web-platform-tests",
                            "webkit")

# EdgeHTML
xlsx = urllib.request.urlopen(edgeXLSXURL).read()
workbook = xlrd.open_workbook(filename="NotRunFiles.xlsx", file_contents=xlsx)
sheet = workbook.sheet_by_name('NotRunFiles')
for rownum in range(sheet.nrows):
    # Skip the header row
    if rownum == 0:
        continue
    addPath(None, "/" + "/".join(sheet.row_values(rownum)), "disabled", "edge")

# web-platform-tests issues
wptIssues = json.loads(urllib.request.urlopen(wptAPIURL).read())["items"]
for item in wptIssues:
    match = re.search(r"^(/[^ ]+) (?:is|are) (?:disabled|flaky|slow)", item["title"])
    if match == None:
        continue
    bug = item["html_url"][len("https://"):]
    path = match.group(1)
    addPath(bug, path, None, "web-platform-tests")

# Output json file
with open('common.json', 'w') as out:
    out.write(json.dumps(common))

# Output HTML file
foundIn4 = []
foundIn3 = []
foundIn2 = []
flakyRows = []
slowRows = []
timeoutRows = []
disabledRows = []

htmlTemplate = Template(open('templates/index.html', 'r').read())
todayStr = date.today().isoformat()
theadStr = "<tr><th>Path<th>Products<th>Results<th>Bugs<th>New issue"
rowTemplate = Template("<tr><td>$path<td>$products<td>$results<td>$bugs<td>$newIssue")
issueTitleTemplate = Template("$path is $results in $products")
issueBodyTemplate = Template(open('templates/issue-body.md', 'r').read())
newIssueTemplate = Template("""<a href="https://github.com/w3c/web-platform-tests/issues/new?title=$title&amp;body=$body&amp;labels=flaky" class="gh-button">New issue</a>""")

def getProducts(item):
    products = []
    for product in ("mozilla", "chromium", "webkit", "edge"):
        if product in item:
            products.append(product)
    return products

def link(url):
    if url is None:
        return "None"
    return "<a href='https://%s'>%s</a>" % (url, url)

def githubLink(url):
    if url is None:
        return "None"
    return "https://%s" % url

def linkWPTFYI(path):
    return "<a href='https://wpt.fyi%s'>%s</a>" % (path, path)

def stringify(item, products, property, joiner):
    arr = []
    for product in products:
        if property == "bug":
            if joiner == "<br>":
                arr.append(link(item[product][property]))
            else:
                arr.append(githubLink(item[product][property]))
        else:
            arr.append(item[product][property])
    if property == "bug":
        if "web-platform-tests" in item:
            arr.append(link(item["web-platform-tests"][property]))
    return joiner.join(arr)

def shortResult(item, products):
    arr = []
    for product in products:
        result = item[product]["results"]
        if result.find("disabled") != -1 or result == "[ Skip ]":
            arr.append("disabled")
        elif result == "[ Slow ]" or result == "[ Timeout ]":
            arr.append("slow")
        else:
            arr.append("flaky")
    # Remove duplicates
    arr = list(set(arr))
    return "/".join(arr)

for item in common:
    products = getProducts(item)
    num = len(products)
    if "web-platform-tests" in item and "bug" in item["web-platform-tests"]:
        newIssue = ""
    else:
        issueTitle = titleTemplate.substitute(path=item["path"],
                                              results=shortResult(item, products),
                                              products=" ".join(products)
                                              )
        issueBody = bodyTemplate.substitute(path=item["path"],
                                            products=" ".join(products),
                                            results=stringify(item, products, "results", " "),
                                            bugs=stringify(item, products, "bug", " ")
                                            )
        newIssue = newIssueTemplate.substitute(title=urllib.parse.quote_plus(issueTitle),
                                               body=urllib.parse.quote_plus(issueBody)
                                               )
    row = rowTemplate.substitute(path=linkWPTFYI(item["path"]),
                                 products="<br>".join(products),
                                 results=stringify(item, products, "results", "<br>"),
                                 bugs=stringify(item, products, "bug", "<br>"),
                                 newIssue=newIssue
                                 )
    if num == 4:
        foundIn4.append(row)
    if num == 3:
        foundIn3.append(row)
    if num == 2:
        foundIn2.append(row)
    if num == 1:
        match = re.search(r"(\[ (Slow|Timeout|Skip) \]|disabled)", item[products[0]]["results"])
        if match:
            if match.group(0) == "[ Slow ]":
                slowRows.append(row)
            elif match.group(0) == "[ Timeout ]":
                timeoutRows.append(row)
            elif match.group(0) == "disabled" or match.group(0) == "[ Skip ]":
                disabledRows.append(row)
            else:
               raise Exception(row)
        else:
            flakyRows.append(row)

flakyNum = len(flakyRows)
slowNum = len(slowRows)
timeoutNum = len(timeoutRows)
disabledNum = len(disabledRows)
numRows4 = len(foundIn4)
numRows3 = len(foundIn3)
numRows2 = len(foundIn2)
numRows1 = flakyNum + slowNum + timeoutNum + disabledNum

outHTML = htmlTemplate.substitute(title="Disabled/flaky/slow web-platform-tests Report",
                                  mozillaURL=html.escape(mozillaURL),
                                  chromiumURL=html.escape(chromiumURL),
                                  webkitURL=html.escape(webkitURL),
                                  edgeHTMLURL=html.escape(edgeHTMLURL),
                                  wptHTMLURL=html.escape(wptHTMLURL),
                                  date=todayStr,
                                  thead=theadStr,
                                  numRows4=str(numRows4),
                                  rows4="\n".join(foundIn4),
                                  numRows3=str(numRows3),
                                  rows3="\n".join(foundIn3),
                                  numRows2=str(numRows2),
                                  rows2="\n".join(foundIn2),
                                  numRows1=str(numRows1),
                                  flakyNum=str(flakyNum),
                                  flakyRows="\n".join(flakyRows),
                                  slowNum=str(slowNum),
                                  slowRows="\n".join(slowRows),
                                  timeoutNum=str(timeoutNum),
                                  timeoutRows="\n".join(timeoutRows),
                                  disabledNum=str(disabledNum),
                                  disabledRows="\n".join(disabledRows),
                                  )

with open('index.html', 'w') as out:
    out.write(outHTML)

# Normalize data.csv (1 entry per day)
csvData = {}
with open('data.csv', 'r') as file:
    for line in file:
        date, values = line.split(",", maxsplit=1)
        csvData[date] = values

csvData[todayStr] = ",".join([str(numRows4), str(numRows3), str(numRows2), str(flakyNum), str(slowNum), str(timeoutNum), str(disabledNum)])

# Output CSV
with open('data.csv', 'w') as out:
    for date in csvData:
        out.write((date + "," + csvData[date]))
    out.write("\n")
