import requests
from bs4 import BeautifulSoup


def get_etherscan_verification(address):
    url = f"https://etherscan.io/address/{address}"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching {address}: {e}")
        return "Error"

    soup = BeautifulSoup(response.text, "html.parser")
    label_tag = soup.find(
        "span",
        {
            "class": (
                "badge bg-success bg-opacity-10 border border-success "
                "border-opacity-25 text-green-600 text-nowrap rounded-pill "
                "py-1.5 px-2"
            )
        },
    )

    if label_tag:
        return label_tag.get_text(strip=True) == "Source Code"
    else:
        return False


def get_etherscan_label(address):
    url = f"https://etherscan.io/address/{address}"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching {address}: {e}")
        return "Error"

    soup = BeautifulSoup(response.text, "html.parser")
    label_tag = soup.find("span", {"class": "hash-tag text-truncate lh-sm my-n1"})

    if label_tag:
        return label_tag.get_text(strip=True)
    else:
        return None
