import requests

def getQuestionFromNet(): 
    url = "https://pastebin.com/api/api_raw.php"

    payload = 'api_dev_key=xxx'
    headers = {
      'Content-Type': 'application/x-www-form-urlencoded',
      'Cookie': 'xxx'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    print(f"From Network: {response.text}")
    return response.text
