import json
import requests
import os
import pathlib
from config import *
from PyPDF2 import PdfFileReader
from typing import NamedTuple


class Attachment(NamedTuple):
    id_: str
    number: str
    creator: str
    date: str
    link: str
    name: str


def authorize():
    authorization_redirect_url = AUTHORIZE_URL + \
        '?response_type=code&client_id=' + CLIENT_ID + '&redirect_uri=' + REDIRECT_URI

    print('Go to the following url on the browser and enter the code on your screen: ')
    print(f'=====>{authorization_redirect_url}')
    authorization_code = input('code: ')

    data = {
        'grant_type': 'authorization_code',
        'code': authorization_code,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'redirect_uri': REDIRECT_URI,
    }

    access_token_response = requests.post(TOKEN_URL, json=data)
    tokens = json.loads(access_token_response.text)
    access_token = tokens['access_token']
    refresh_token = tokens['refresh_token']
    print(f'access token: {access_token}')

    api_call_header = {
        'Authorization': 'Bearer ' + access_token,
        'Procore-Company-Id': COMPANY_ID,
    }
    return api_call_header, refresh_token


def get_user_permissions(api_call_header, refresh_token):
    project_users = f'https://api.procore.com/vapid/projects/{PROJECT_ID}/users'
    response = requests.get(project_users, headers=api_call_header)
    if response.status_code != 200:
        return 'ERROR retrieving permissions list'
    users = response.json()
    permissions = {}
    for user in users:
        if(user['permission_template']):
            name = user['first_name'] + ' ' + user['last_name']
            permission = user['permission_template']['name']
            permissions[name] = permission
    with open('permissions.json', 'w', encoding='utf-8') as file:
        json.dump(permissions, file, ensure_ascii=False, indent=4)


def get_rfis(api_call_header):
    all_rfis = f'https://api.procore.com/vapid/projects/{PROJECT_ID}/rfis'
    response = requests.get(all_rfis, headers=api_call_header)
    if response.status_code != 200:
        return 'ERROR retrieving RFI list'
    rfis = response.json()
    with open('rfis.json', 'w', encoding='utf-8') as file:
        json.dump(rfis, file, ensure_ascii=False, indent=4)


def get_rfi_attachments(api_call_header, refresh_token):
    attachments = []

    with open('rfis.json') as file:
        all_rfis = json.load(file)

    for rfi_item in all_rfis:
        rfi_id = rfi_item['id']
        rfi_number = rfi_item['number']

        response = requests.get(
            f'{all_rfis}/{rfi_id}', headers=api_call_header)
        if response.status_code != 200:
            return f'ERROR retrieving RFI'
        rfi = response.json()
        for question in rfi['questions']:
            date = question['question_date'][:10]
            creator = question['created_by']
            rfi_attachments = question['attachments']
            answers = question['answers']
            for item in rfi_attachments:
                attachments.append(Attachment(
                    id_=rfi_id,
                    num=rfi_number,
                    creator=creator,
                    date=date,
                    link=item['url'],
                    name=item['name']))
            for answer in answers:
                date = answer['answer_date'][:10]
                creator = answer['created_by']
                rfi_attachments = answer['attachments']
                for item in rfi_attachments:
                    attachments.append(Attachment(
                        id_=rfi_id,
                        num=rfi_number,
                        creator=creator,
                        date=date,
                        link=item['url'],
                        name=item['name']))
    download_attachments(attachments)


def download_attachments(attachments):
    pathlib.Path('001_Rec_TPS').mkdir(parents=True, exist_ok=True)
    pathlib.Path('002_Sub_TCCO').mkdir(parents=True, exist_ok=True)
    pathlib.Path('003_Ret_DT').mkdir(parents=True, exist_ok=True)
    with open('permissions.json') as file:
        permissions = json.load(file)

    perm_folders = {
        "Subcontractor Superintendent": "001_Rec_TPS",
        "Turner Project Manager": "002_Sub_TCCO",
        "Architect/Engineer": "003_Ret_DT",
        "Owner/Client": "003_Ret_DT"
    }

    for attachment in attachments:
        print(attachment)
        req = requests.get(attachment.link, allow_redirects=True)
        name, ext = os.path.splitext(attachment.name)
        init = get_initials(attachment.creator)
        perm = permissions.get(attachment.creator)
        folder = perm_folders.get(perm)

        if perm is None:
            folder = f'PERMISSION: {attachment.creator}'
        elif folder is None:
            folder = f'PERMISSION: {perm}'
        pathlib.Path(folder).mkdir(parents=True, exist_ok=True)

        sketch = f'{folder}/RFI {attachment.number}_{attachment.date}_{name[:10]}_SKETCH_{init}{ext}'
        drawing = f'{folder}/RFI {attachment.number}_{attachment.date}_{name[:10]}_DRAWING_{init}{ext}'

        with open(sketch, 'wb') as file:
            file.write(req.content)

        if ext == '.pdf' and is_drawing(sketch):
            os.rename(sketch, drawing)


def get_initials(string):
    if string is None:
        return ''
    new_string = ''
    for name in filter(None, string.split(' ')):
        new_string += name[0]
    return new_string


def is_drawing(filename):
    try:
        pdf = PdfFileReader(open(filename, 'rb'))
        rectangle = pdf.getPage(0).mediaBox
        # 1pt == 1/72 inches, a drawing is 42x30 inches
        if ((rectangle[2]//72) * (rectangle[3]//72)) == 1260:
            return True
        return False
    except Exception as error:
        print(f'Invalid PDF File: {error}')
        return False


def main():
    api_call_header, refresh_token = authorize()
    get_user_permissions(api_call_header, refresh_token)
    get_rfi_attachments(api_call_header, refresh_token)
    print("*Complete*")


main()
