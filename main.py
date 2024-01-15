from fastapi import FastAPI, BackgroundTasks, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from supabase import create_client, Client
from typing import Optional
from pydantic import BaseModel
import pandas as pd
import json
from crawl import get_crawl_data, check_url
from feature_extraction import FeatureExtraction
from forecast import predict_trend, summarize
from os import path
from dotenv import load_dotenv
import os
import datetime as dt
from transformers import PreTrainedTokenizerFast
from transformers import BartForConditionalGeneration
from custom_error import NotValidKeywordError, NotEnoughSearchVolumeError
import json

load_dotenv()
# Scripts\activate.bat
# uvicorn main:app --reload

SUPA_URL = os.environ.get('SUPA_URL')
SUPA_SECRET = os.environ.get('SUPA_PW')

app = FastAPI()
supabase: Client = create_client(SUPA_URL, SUPA_SECRET)

origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StartParam(BaseModel):
    url: str
    project_name: str
    product_name: str
    category: str
    client_id: str


@app.get('/')
def welcome():
    return {'response': 'wellcome'}


@app.post("/uploadfile")
async def create_upload_file(file: UploadFile):
    df = pd.read_csv(file.file)
    df.info()
    return {"filename": file.filename}


@app.get('/heartbeat')
def heartbeat(client_id: str):
    try:
         with open('user_status.json', 'r') as file:
            user_status = json.load(file)
            print(user_status)
            return {'success': True, 'status': user_status[client_id]}
    except:
        return {'success': False, 'message': 'no exact user'}


@app.get('/deleteuser')
def delete_user(client_id: str):
    try:
        with open('user_status.json', 'r') as file:
            user_status = json.load(file)
            user_status.pop(client_id)
            print(user_status)
        with open('user_status.json', 'w', encoding='utf-8') as file:
            json.dump(user_status, file)
            return {'success': True}
    except:
        print('delete error')
        return {'success': True, 'message': 'already deleted'}


@app.get('/adduser')
def add_user(client_id: str):
    try:
        with open('user_status.json', 'r') as file:
            user_status = json.load(file)
            user_status[client_id] = 0
            print(user_status)
        with open('user_status.json', 'w', encoding='utf-8') as file:
            json.dump(user_status, file)
        return {'success': True}
    except Exception as e:
        print('add error', e)
        return {'success': True, 'message': '???'}


def change_user_status(client_id: str, status: int):
    try:
        with open('user_status.json', 'r') as file:
            user_status = json.load(file)
            user_status[client_id] = status
            print(user_status)
        with open('user_status.json', 'w', encoding='utf-8') as file:
            json.dump(user_status, file)
    except Exception as e:
        print('add error', e)


@app.get("/downloadcsv")
def download_csv(filename: str):
    print(filename[:7], filename[-3:])
    if filename[:7] != 'reviews' or filename[-3:] != 'csv':
        return None;
    return FileResponse(path=filename, filename=filename)


@app.post('/start')
def crawl_data(info: StartParam, background_tasks: BackgroundTasks):
    change_user_status(info.client_id, 0)
    now = dt.datetime.now()
    now_str = now.strftime("%Y%m%d%H%M%S")
    filename = 'reviews_{}.csv'.format(now_str)
    project_names = json.loads(supabase.table('products').select('*').eq('project_name', info.project_name).execute().json())
    if len(project_names['data']) > 0:
        return {'success': False, 'message': 'exist project name', 'code': 2}
    if check_url(info.url):
        background_tasks.add_task(crawl_analysis_background, info.url, filename, info.project_name, info.product_name, info.category, info.client_id)
        return {'success': True, 'message': 'crawling in background', 'code': 0}
    return {'success': False, 'message': 'failed to get information, check your url', 'code': 1}


@app.get('/getdata')
def get_data(product_id: int):
    res = json.loads(supabase.table('products').select('*').eq('id', product_id).execute().json())['data']
    if len(res) == 0:
        return {'success': False, 'message': 'not exist item'}
    dtm_res = json.loads(supabase.table('dtm').select('*').eq('product_id', product_id).execute().json())['data']

    return {'success': True, 'p_data': res, 'dtm_result': dtm_res}


@app.get('/getoriginalreview')
def get_original_review(product_id: int, word: str):
    res = json.loads(supabase.table('originaldoc').select('document, tokens').like('tokens', '%'+word+'%').execute().json())['data']

    return {'success': True, 'reviews': res}


@app.get('/getwordtrend')
def get_word_trend(product_id: int, word: str):
    res = json.loads(supabase.rpc('get_trend', {'word': word, 'pid': product_id}).execute().json())['data']
    return {'success': True, 'trend': res}


@app.get('/getlist')
def get_list():
    res = json.loads(supabase.table('products').select('id, project_name').execute().json())['data']
    return {'success': True, 'list': res}


# @app.websocket("/ws/{client_id}")
# async def websocket_endpoint(websocket: WebSocket, client_id: str):
#     await manager.connect(websocket, client_id)
#     while True:
#         try:
#             data = await websocket.receive_text()
#         except:
#             await manager.disconnect(client_id)
#             return
#         await manager.broadcast(f"Client {client_id}: {data}")
    

def crawl_analysis_background(url, filename, project_name, product_name, category, client_id):
    
    try:
        res = get_crawl_data(url, filename)
    except NotValidKeywordError:
        change_user_status(client_id, 6)
        return
    try:
        change_user_status(client_id, 2)
    except:
        pass
    
    fe = FeatureExtraction()
    # pros extraction
    fe.train_topic_model_with_bertopic(filename, product_name, star_rating_range=[5, 5])
    pros_topics = fe.get_topics_with_keyword(top_n_word=10)
    # cons extraction
    try:
        fe.train_topic_model_with_bertopic(filename, product_name, star_rating_range=[1, 3])
        cons_topics = fe.get_topics_with_keyword(top_n_word=10)
    except:
        cons_topics = []
    print(pros_topics)

    try:
        change_user_status(client_id, 3)
    except:
        pass

    # dtm
    review_to_summ, original_doc = fe.train_topic_model_with_bertopic(filename, product_name)
    dtm_result = fe.get_topics_per_month().to_dict('records')

    try:
        change_user_status(client_id, 4)
    except:
        pass
    #summ_text = summarize(review_to_summ, summ_tokenizer, summ_model)
    summ_text = ' '.join(pros_topics[0])

    forecasting_conducted = True
    forecasting_warning = False
    try:
        past_trend, forecast, start_date, end_date = predict_trend(summ_text, product_name, category, url)
        past_trend = [i*100 for i in past_trend]
        zero_cnt = 0
        for i in past_trend:
            if i == 0:
                zero_cnt += 1
        if zero_cnt > 52:
            forecasting_warning = True
    except NotValidKeywordError:
        change_user_status(client_id, 6)
        return
    except NotEnoughSearchVolumeError:
        forecasting_conducted = False

    # db
    product_insert = supabase.table('products').insert({
        'product_name': product_name,
        'pros': pros_topics,
        'cons': cons_topics,
        'csvname': filename,
        'trend': past_trend + forecast.tolist() if forecasting_conducted else [-1],
        'project_name': project_name,
        'trend_start_date': start_date if forecasting_conducted else None,
        'trend_end_date': end_date if forecasting_conducted else None,
        'trend_warning': forecasting_warning
    }).execute()
    
    product_id = json.loads(product_insert.json())['data'][0]['id']
    print(original_doc[0])
    original_doc = [{'document': i['document'], 'tokens': i['tokens'], 'topic': i['topic'], 'month': i['month'], 'product_id': product_id} for i in original_doc]
    supabase.table("originaldoc").insert(original_doc).execute()

    dtm_result = [{'topic': i['topic'], 'month': i['Timestamp'], 'words': i['words'], 'product_id': product_id} for i in dtm_result]
    supabase.table("dtm").insert(dtm_result).execute()
    try:
        change_user_status(client_id, 5)
    except:
        pass
