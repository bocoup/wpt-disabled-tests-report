const [flakyDetails, slowDetails, timeoutDetails, disabledDetails] = document.getElementsByTagName('details');

onpageshow = e => {
  flakyDetails.open = sessionStorage["flaky-tests-open"] === "true";
  slowDetails.open = sessionStorage["slow-tests-open"] === "true";
  timeoutDetails.open = sessionStorage["timeout-tests-open"] === "true";
  disabledDetails.open = sessionStorage["disabled-tests-open"] === "true";
  if (location.hash) {
    if (/^#(flaky|slow|timeout|disabled)-tests$/.test(location.hash)) {
      const element = document.querySelector(location.hash);
      element.open = true;
    }
  }
}
addEventListener('toggle', e => {
  sessionStorage[e.target.id + "-open"] = String(e.target.open);
}, true);
