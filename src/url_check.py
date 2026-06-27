import requests
from langsmith import traceable

@traceable(name="PVN URL liveness check")
def url_is_live(url):
    """
    Return True if the URL seems reachable.
    Return False if the URL is broken, blocked, timed out, or returns an error status.
    """
    try:
        # First try a HEAD request.
        # HEAD asks the server whether the page exists without downloading the full page body.
        # This is faster and lighter than GET.
        response = requests.head(
            url,
            allow_redirects=True,  
            timeout=10,            
            headers={
                # Some websites block script-like requests.
                # This User-Agent makes the request look more like a normal browser.
                "User-Agent": "Mozilla/5.0"
            },
        )

        # Some websites do not allow HEAD requests.
        # 403 means forbidden.
        # 405 means method not allowed.
        # In those cases, the page may still work in a browser, so try GET.
        if response.status_code in [403, 405]:
            response = requests.get(
                url,
                allow_redirects=True,
                timeout=10,
                headers={"User-Agent": "Mozilla/5.0"},
                stream=True,  # Do not download the whole page body immediately.
            )

        # HTTP status codes below 400 usually mean success or redirect.
        # Examples:
        # 200 = OK
        # 301/302 = redirect
        #
        # Status codes 400 and above usually mean failure.
        # Examples:
        # 404 = not found
        # 500 = server error
        return response.status_code < 400

    except requests.RequestException:
        # If the request fails because of timeout, bad URL, SSL error,
        # connection error, or too many redirects, treat the URL as not live.
        return False
