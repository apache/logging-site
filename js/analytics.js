(function () {
    // List of URLs that do not need any analytics code
    const noAnalyticsUrls = [


    ];

    // List of URLs that need a special version of Matomo code for obsolete websites
    const dormantUrls = [
        'https://logging.apache.org/flume',
        'https://logging.apache.org/chainsaw/2.x/',
        'https://logging.apache.org/log4php',
        'https://logging.apache.org/log4j/1.x/',
        'https://logging.apache.org/log4j/extras/',
        'https://logging.apache.org/log4php/'
    ];

    function isUrlInList(url, list) {
        return list.includes(url);
    }

    const url = window.location.href;

    if (isUrlInList(url, dormantUrls)) {
        // Load Matomo code for obsolete websites
        var _paq = window._paq = window._paq || [];
        _paq.push(["disableCookies"]);
        _paq.push(['trackPageView']);
        _paq.push(['enableLinkTracking']);
        (function () {
            var u = "https://analytics.apache.org/";
            _paq.push(['setTrackerUrl', u + 'matomo.php']);
            _paq.push(['setSiteId', '42']);
            var d = document, g = d.createElement('script'), s = d.getElementsByTagName('script')[0];
            g.async = true; g.src = u + 'matomo.js'; s.parentNode.insertBefore(g, s);
        })();
    } else if (isUrlInList(url, noAnalyticsUrls)) {
        // Do not load any analytics code
        return
    } else {
        var _paq = window._paq = window._paq || [];
        _paq.push(["disableCookies"]);
        _paq.push(['trackPageView']);
        _paq.push(['enableLinkTracking']);
        (function () {
            var u = "https://analytics.apache.org/";
            _paq.push(['setTrackerUrl', u + 'matomo.php']);
            _paq.push(['setSiteId', '42']);
            var d = document, g = d.createElement('script'), s = d.getElementsByTagName('script')[0];
            g.async = true; g.src = u + 'matomo.js'; s.parentNode.insertBefore(g, s);
        })();
    }
})();
