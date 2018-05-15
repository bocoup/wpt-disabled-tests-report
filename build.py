#!/usr/bin/env python3

import urllib.request
import json
import re
from string import Template
from datetime import date
import xlrd

mozillaURL = "https://searchfox.org/mozilla-central/search?q=disabled%3A&case=true&regexp=false&path=testing%2Fweb-platform%2Fmeta"
chromiumURL = "https://cs.chromium.org/codesearch/f/chromium/src/third_party/WebKit/LayoutTests/TestExpectations"
webkitURL = "https://raw.githubusercontent.com/WebKit/webkit/master/LayoutTests/TestExpectations"
edgeXLSXURL = "https://github.com/w3c/web-platform-tests/files/1984479/NotRunFiles.xlsx"
edgeHTMLURL = "https://github.com/w3c/web-platform-tests/issues/10655#issuecomment-387434035"
flakyQuery = "q=is%3Aissue+is%3Aopen+label%3Aflaky"
wptAPIURL = "https://api.github.com/search/issues?" + flakyQuery + "+repo%3Aw3c/web-platform-tests"
wptHTMLURL = "https://github.com/w3c/web-platform-tests/issues?utf8=%E2%9C%93&" + flakyQuery

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
    if path[0] != "/":
        path = "/" + path
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
    match = re.search(r"^(/[^ ]+) is (?:disabled|flaky|slow)", item["title"])
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

html = Template("""<!doctype html>
<meta charset=utf-8>
<title>$title</title>
<style>
 html { font-family: sans-serif; line-height: 1.5; background: white; color: black }
 body { margin-bottom: 50vh }
 p { margin: 0 40px; padding: 0.5em; background-color: #fdd73d; max-width: 55em }
 h1 { background-color: #eaeaea; font-size: 1.5em; font-weight: normal }
 img { padding: 10px 50px; vertical-align: -16px }
 table { border-collapse: collapse; width: 100% }
 td:nth-child(4) { white-space: nowrap }
 th, td { border: thin solid; padding: 0 0.5em }
 tr:nth-child(even) { background-color: #eaeaea }
 :link, :visited { text-decoration: none }
 :link:hover, :visited:hover { text-decoration: underline }
 path { fill: none }
</style>
<h1><a href="https://bocoup.com/"><img src="https://static.bocoup.com/assets/img/bocoup-logo@2x.png" alt="Bocoup" width=135 height=40></a> $title</h1>
<p>A <dfn>disabled</dfn> test is a test that is not run, maybe because it is flaky or because the feature it is testing is not yet implemented. For WebKit and Chromium, this is denoted as "[&nbsp;Skip&nbsp;]". For Mozilla and Edge, this is denoted as "disabled".
<p>A <dfn>flaky</dfn> test is a test that gives inconsistent results, e.g., sometimes passing and sometimes failing. For Chromium and WebKit, this is denoted as "[&nbsp;Pass&nbsp;Failure&nbsp;]" (or other combinations of results).
<p>A <dfn>slow</dfn> test is a test that is marked as taking a long time to run. For Chromium and WebKit, this is denoted as "[&nbsp;Slow&nbsp;]".
<p>The tables below show all tests in <a href="https://github.com/w3c/web-platform-tests">web-platform-tests</a> that are disabled, flaky, or slow, in 4, 3, 2, and 1 browsers. Tests that show up for more than one browser are likely to be due to issues with the tests.
<p>This report is generated from <a href="$mozillaURL">this search result for Mozilla</a>, <a href="$chromiumURL">this TestExpectations file for Chromium</a>, <a href="$webkitURL">this TestExpectations file for WebKit</a>, <a href="$edgeHTMLURL">this NotRunFiles.xslx file for Edge</a>, and <a href="$wptHTMLURL">this search result in web-platform-tests</a>.
<p>Generated on $date. <a href="https://github.com/bocoup/wpt-disabled-tests-report">Source on GitHub</a> (<a href="https://github.com/bocoup/wpt-disabled-tests-report/issues">issues/feedback</a>). Data is also available in <a href="common.json">JSON format</a>.
<p>The graph below shows changes of number of tests over time (<a href="data.csv">CSV format</a>).</p>
<!-- Graph is based on https://bl.ocks.org/mbostock/3884955 -->
<svg width="960" height="500"></svg>
<script src="https://d3js.org/d3.v4.min.js"></script>
<script>
var svg = d3.select("svg"),
    margin = {top: 20, right: 80, bottom: 30, left: 50},
    width = svg.attr("width") - margin.left - margin.right,
    height = svg.attr("height") - margin.top - margin.bottom,
    g = svg.append("g").attr("transform", "translate(" + margin.left + "," + margin.top + ")");

var parseTime = d3.timeParse("%Y-%m-%d");

var x = d3.scaleTime().range([0, width]),
    y = d3.scalePow().exponent(0.5).range([height, 0]),
    z = d3.scaleOrdinal(d3.schemeCategory10);

var line = d3.line()
    .curve(d3.curveBasis)
    .x(function(d) { return x(d.date); })
    .y(function(d) { return y(d.tests); });

var pos = 0;
function positionLegend() {
  var labelWidth = 100;
  pos += labelWidth;
  return pos;
}

d3.csv("data.csv", type, function(error, data) {
  if (error) throw error;

  var groups = data.columns.slice(1).map(function(id) {
    return {
      id: id,
      values: data.map(function(d) {
        return {date: d.date, tests: d[id]};
      })
    };
  });

  x.domain(d3.extent(data, function(d) { return d.date; }));

  y.domain([
    d3.min(groups, function(c) { return d3.min(c.values, function(d) { return d.tests; }); }),
    d3.max(groups, function(c) { return d3.max(c.values, function(d) { return d.tests; }); })
  ]);

  z.domain(groups.map(function(c) { return c.id; }));

  g.append("g")
      .attr("class", "axis axis--x")
      .attr("transform", "translate(0," + height + ")")
      .call(d3.axisBottom(x));

  g.append("g")
      .attr("class", "axis axis--y")
      .call(d3.axisLeft(y))
    .append("text")
      .attr("transform", "rotate(-90)")
      .attr("y", 6)
      .attr("dy", "0.71em")
      .attr("fill", "#000")
      .text("Tests");

  var group = g.selectAll(".group")
    .data(groups)
    .enter().append("g")
      .attr("class", "group");

  group.append("path")
      .attr("class", "line")
      .attr("d", function(d) { return line(d.values); })
      .style("stroke", function(d) { return z(d.id); });

  group.append("text")
      .datum(function(d) { return {id: d.id, value: d.values[d.values.length - 1]}; })
      .attr("transform", function(d) { return "translate(" + positionLegend() + ", " + (y(d.value.tests) - 5) + ")"; })
      .style("font", "10px sans-serif")
      .style("fill", function(d) { return z(d.id); })
      .text(function(d) { return d.id; });
});

function type(d, _, columns) {
  d.date = parseTime(d.date);
  for (var i = 1, n = columns.length, c; i < n; ++i) d[c = columns[i]] = +d[c];
  return d;
}
</script>
<h2 id="4-browsers">4 browsers ($numRows4 tests)</h2>
<table>
$thead
$rows4
</table>
<h2 id="3-browsers">3 browsers ($numRows3 tests)</h2>
<table>
$thead
$rows3
</table>
<h2 id="2-browsers">2 browsers ($numRows2 tests)</h2>
<table>
$thead
$rows2
</table>
<h2 id="1-browser">1 browser ($numRows1 tests)</h2>
<details id="flaky-tests">
<summary>Flaky tests ($flakyNum)</summary>
<table>
$thead
$flakyRows
</table>
</details>
<details id="slow-tests">
<summary>Slow tests ($slowNum)</summary>
<table>
$thead
$slowRows
</table>
</details>
<details id="timeout-tests">
<summary>Timeout tests ($timeoutNum)</summary>
<table>
$thead
$timeoutRows
</table>
</details>
<details id="disabled-tests">
<summary>Disabled tests ($disabledNum)</summary>
<table>
$thead
$disabledRows
</table>
</details>
<script>
const [flakyDetails, slowDetails, timeoutDetails, disabledDetails] = document.getElementsByTagName('details');

onpageshow = e => {
  flakyDetails.open = sessionStorage["flaky-tests-open"] === "true";
  slowDetails.open = sessionStorage["slow-tests-open"] === "true";
  timeoutDetails.open = sessionStorage["timeout-tests-open"] === "true";
  disabledDetails.open = sessionStorage["disabled-tests-open"] === "true";
  if (location.hash) {
    const element = document.querySelector(location.hash);
    if (element instanceof HTMLDetailsElement) {
      element.open = true;
    }
  }
}
addEventListener('toggle', e => {
  sessionStorage[e.target.id + "-open"] = String(e.target.open);
}, true);
</script>
""")
todayStr = date.today().isoformat()
theadStr = "<tr><th>Path<th>Products<th>Results<th>Bugs"
rowTemplate = Template("<tr><td>$path<td>$products<td>$results<td>$bugs")

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

def linkWPTFYI(path):
    return "<a href='https://wpt.fyi%s'>%s</a>" % (path, path)

def stringify(item, products, property):
    arr = []
    for product in products:
        if property == "bug":
            arr.append(link(item[product][property]))
        else:
            arr.append(item[product][property])
    if property == "bug":
        if "web-platform-tests" in item:
            arr.append(link(item["web-platform-tests"][property]))
    return "<br>".join(arr)

for item in common:
    products = getProducts(item)
    num = len(products)
    row = rowTemplate.substitute(bugs=stringify(item, products, "bug"),
                                 path=linkWPTFYI(item["path"]),
                                 products="<br>".join(products),
                                 results=stringify(item, products, "results"))
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

outHTML = html.substitute(title="Disabled/flaky/slow web-platform-tests Report",
                          mozillaURL=mozillaURL,
                          chromiumURL=chromiumURL,
                          webkitURL=webkitURL,
                          edgeHTMLURL=edgeHTMLURL,
                          wptHTMLURL=wptHTMLURL,
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

# Output CSV
with open('data.csv', 'a') as out:
    out.write((",".join([todayStr, str(numRows4), str(numRows3), str(numRows2), str(flakyNum), str(slowNum), str(timeoutNum), str(disabledNum)]) + "\n"))
