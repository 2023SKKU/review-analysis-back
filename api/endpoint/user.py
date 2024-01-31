from fastapi import APIRouter
import json

router = APIRouter()

@router.get('/heartbeat')
def heartbeat(client_id: str):
    try:
         with open('util/user_status.json', 'r') as file:
            user_status = json.load(file)
            print(user_status)
            return {'success': True, 'status': user_status[client_id]}
    except:
        return {'success': False, 'message': 'no exact user'}
    

@router.get('/deleteuser')
def delete_user(client_id: str):
    try:
        with open('util/user_status.json', 'r') as file:
            user_status = json.load(file)
            user_status.pop(client_id)
            print(user_status)
        with open('util/user_status.json', 'w', encoding='utf-8') as file:
            json.dump(user_status, file)
            return {'success': True}
    except:
        print('delete error')
        return {'success': True, 'message': 'already deleted'}
    

@router.get('/adduser')
def add_user(client_id: str):
    try:
        with open('util/user_status.json', 'r') as file:
            user_status = json.load(file)
            user_status[client_id] = 0
            print(user_status)
        with open('util/user_status.json', 'w', encoding='utf-8') as file:
            json.dump(user_status, file)
        return {'success': True}
    except Exception as e:
        print('add error', e)
        return {'success': True, 'message': '???'}