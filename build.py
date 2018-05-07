#!/usr/bin/env python3

import urllib.request
import json
import re
from string import Template
from datetime import date

mozillaURL = "https://searchfox.org/mozilla-central/search?q=disabled%3A&case=true&regexp=false&path=testing%2Fweb-platform%2Fmeta"
chromiumURL = "https://cs.chromium.org/codesearch/f/chromium/src/third_party/WebKit/LayoutTests/TestExpectations"
webkitURL = "https://raw.githubusercontent.com/WebKit/webkit/master/LayoutTests/TestExpectations"

# Mozilla
contents = urllib.request.urlopen(mozillaURL).readlines()
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
common = json.loads(line)["test"]["Textual Occurrences"]
for item in common:
    line = item["lines"][0]["line"]
    values = line.split(': https://')
    results = values.pop(0)
    if len(values) > 0:
        bug = values[0]
    else:
        bug = None
    item["mozilla"] = {"bug": bug, "results": results}
    del item["lines"]
    item["path"] = item["path"].replace("testing/web-platform/meta", "").replace(".ini", "")

# Add path to common, merging with existing if present
def addPath(bug, path, results, product):
    pathFound = False
    for item in common:
        if item["path"] == path:
            item[product] = {"bug": bug, "results": results}
            pathFound = True
            break
    if pathFound == False:
        common.append({"path": path, product: {"bug": bug, "results": results}})

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
            # Don't collect stable but failing tests
            if results == "[ Failure ]":
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

# Output json file
with open('common.json', 'w') as out:
    out.write(json.dumps(common))

# Output HTML file
foundIn3 = []
foundIn2 = []
foundIn1 = []
html = Template("""<!doctype html>
<meta charset=utf-8>
<title>$title</title>
<style>
 html { font-family: sans-serif; line-height: 1.5; background: white; color: black }
 p { margin: 0 40px; padding: 0.5em; background-color: #fdd73d; max-width: 55em }
 h1 { background-color: #eaeaea; font-size: 1.5em; font-weight: normal }
 img { padding: 10px 50px; vertical-align: -16px }
 table { border-collapse: collapse; width: 100% }
 td:nth-child(4) { white-space: nowrap }
 th, td { border: thin solid; padding: 0 0.5em }
 tr:nth-child(even) { background-color: #eaeaea }
 :link, :visited { text-decoration: none }
 :link:hover, :visited:hover { text-decoration: underline }
</style>
<h1><a href="https://bocoup.com/"><img src="https://static.bocoup.com/assets/img/bocoup-logo@2x.png" alt="Bocoup" width=135 height=40></a> $title</h1>
<p>A <dfn>disabled</dfn> test is a test that is not run, maybe because it is flaky or because the feature it is testing is not yet implemented. For WebKit and Chromium, this is denoted as "[&nbsp;Skip&nbsp;]". For Mozilla, this is denoted as "disabled".
<p>A <dfn>flaky</dfn> test is a test that gives inconsistent results, e.g., sometimes passing and sometimes failing. For Chromium and WebKit, this is denoted as "[&nbsp;Pass&nbsp;Failure&nbsp;]" (or other combinations of results).
<p>A <dfn>slow</dfn> test is a test that is marked as taking a long time to run. For Chromium and WebKit, this is denoted as "[&nbsp;Slow&nbsp;]".
<p>The tables below show all tests in <a href="https://github.com/w3c/web-platform-tests">web-platform-tests</a> that are disabled, flaky, or slow, in 3, 2, and 1 browsers. Tests that show up for more than one browser are likely to be due to issues with the tests.
<p>This report is generated from <a href="$mozillaURL">this search result for Mozilla</a>, <a href="$chromiumURL">this TestExpectations file for Chromium</a>, and <a href="$webkitURL">this TestExpectations file for WebKit</a>.</p>
<p>Generated on $date. <a href="https://github.com/bocoup/wpt-disabled-tests-report">Source on GitHub</a> (<a href="https://github.com/bocoup/wpt-disabled-tests-report/issues">issues/feedback</a>). Data is also available in <a href="common.json">JSON format</a>.</p>
<h2>3 browsers ($numRows3 tests)</h2>
<table>
$thead
$rows3
</table>
<h2>2 browsers ($numRows2 tests)</h2>
<table>
$thead
$rows2
</table>
<h2>1 browser ($numRows1 tests)</h2>
<table>
$thead
$rows1
</table>
""")
todayStr = date.today().isoformat()
theadStr = "<tr><th>Path<th>Products<th>Results<th>Bugs"
rowTemplate = Template("<tr><td>$path<td>$products<td>$results<td>$bugs")

def getProducts(item):
    products = []
    for product in ("mozilla", "chromium", "webkit"):
        if product in item:
            products.append(product)
    return products

def link(url):
    if url is None:
        return "None"
    return "<a href='https://%s'>%s</a>" % (url, url)

def linkWPTFYI(path):
    return "<a href='https://wpt.fyi%s'>%s</a>" % (path, path)

for item in common:
    products = getProducts(item)
    num = len(products)
    if num == 3:
        foundIn3.append(rowTemplate.substitute(bugs="<br>".join([link(item["mozilla"]["bug"]), link(item["chromium"]["bug"]), link(item["webkit"]["bug"])]),
                                               path=linkWPTFYI(item["path"]),
                                               products="<br>".join(products),
                                               results="<br>".join([item["mozilla"]["results"], item["chromium"]["results"], item["webkit"]["results"]])))
    if num == 2:
        foundIn2.append(rowTemplate.substitute(bugs="<br>".join([link(item[products[0]]["bug"]), link(item[products[1]]["bug"])]),
                                               path=linkWPTFYI(item["path"]),
                                               products="<br>".join(products),
                                               results="<br>".join([item[products[0]]["results"], item[products[1]]["results"]])))
    if num == 1:
        foundIn1.append(rowTemplate.substitute(bugs=link(item[products[0]]["bug"]),
                                               path=linkWPTFYI(item["path"]),
                                               products=products[0],
                                               results=item[products[0]]["results"]))

outHTML = html.substitute(title="Disabled/flaky/slow web-platform-tests Report",
                          mozillaURL=mozillaURL,
                          chromiumURL=chromiumURL,
                          webkitURL=webkitURL,
                          date=todayStr,
                          thead=theadStr,
                          numRows3=str(len(foundIn3)),
                          rows3="\n".join(foundIn3),
                          numRows2=str(len(foundIn2)),
                          rows2="\n".join(foundIn2),
                          numRows1=str(len(foundIn1)),
                          rows1="\n".join(foundIn1)
                          )

with open('index.html', 'w') as out:
    out.write(outHTML)
