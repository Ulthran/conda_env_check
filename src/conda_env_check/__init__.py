import requests
from bs4 import BeautifulSoup
from .Version import Version

__version__ = "1.0.0"


def get_latest_package_version(channel: str, package: str) -> Version | None:
    # Create the URL for the Anaconda channel/package page
    url = f"https://anaconda.org/{channel}/{package}"

    # Send an HTTP GET request to the URL
    response = requests.get(url)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the HTML content of the page
        soup = BeautifulSoup(response.text, "html.parser")

        # Find the element containing package version information
        version_element = soup.find("small", class_="subheader")

        if version_element:
            # Extract the version information
            version = version_element.text.strip()
            return Version(version)

    # If the request was not successful or version information was not found, return None
    return None
