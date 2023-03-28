# url for auth https://login.procore.com/oauth/authorize?response_type=code&client_id=6510ef4494b80c480ef89f1298c05f959bc9bbf918eed206224bff238242b67c&redirect_uri=urn:ietf:wg:oauth:2.0:oob

'''
import requests

headers = {
    'Accept-Encoding': 'gzip, deflate, sdch',
    'Accept-Language': 'en-US,en;q=0.8',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Referer': 'http://www.wikipedia.org/',
    'Connection': 'keep-alive',
}

response = requests.get('/vapid/projects/592429/rfis?filters[responsible_contractor_id]=2133211', headers=headers)

https://app.procore.com/592429/project/rfi/show/{rfi_id}
'''
import pickle
import json
import requests

data = {}
with open('rfi2.json') as json_file:
    data = json.load(json_file)

filenames = {}

for d in data:
    rfi_id = d['id']
    rfi_number = d['number']
    headers = {
        'Authorization': 'Bearer <access token>',
    }
    response = requests.get(
        'https://api.procore.com/vapid/projects/<PROJECT ID>/rfis/{}'.format(rfi_id), headers=headers)
    rfi = response.json()

    for item in rfi['questions']:
        attachments = item['attachments']
        answers = item['answers']
        for attachment in attachments:
            filenames[attachment['name']] = rfi_number
        for answer in answers:
            for attachment in answer['attachments']:
                filenames[attachment['name']] = rfi_number

# Store data
with open('rfi_data.pickle', 'wb') as handle:
    pickle.dump(filenames, handle, protocol=pickle.HIGHEST_PROTOCOL)
