import requests
from bs4 import BeautifulSoup as bs
import json
import csv
import math
import pandas as pd
from custom_error import NotValidKeywordError, NotEnoughSearchVolumeError
import datetime
from dateutil.relativedelta import relativedelta

review_api = ['https://smartstore.naver.com/i/v1/reviews/paged-reviews', 'https://brand.naver.com/n/v1/reviews/paged-reviews']
origin_li = ['https://smartstore.naver.com', 'https://brand.naver.com']

cookies = {
    'NNB': 'GTZ22E7ZJ5HGK',
}

headers = {
    'authority': 'smartstore.naver.com',
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'ko-KR,ko;q=0.9',
    'content-type': 'application/json;charset=UTF-8',
    # 'cookie': 'NNB=GTZ22E7ZJ5HGK',
    'origin': 'https://smartstore.naver.com',
    'referer': 'https://smartstore.naver.com/breastdak/products/7290642963',
    'sec-ch-ua': '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
}


def check_url(url: str):
    res = requests.get(url, cookies=cookies, headers=headers)
    html = res.text
    soup = bs(html, 'html.parser')
    json_element = soup.select_one('body > script')
    if json_element is None:
        return False
    return True


def get_crawl_data(url: str, filename: str):
    
    cf = open(filename, 'w', encoding='utf-8', newline='')
    wr = csv.writer(cf)
    wr.writerow(['userid', 'content', 'star_rating', 'time'])
    api_idx = 0

    headers['referer'] = url
    if url[8:28] == 'smartstore.naver.com':
        api_idx = 0
    elif url[8:23] == 'brand.naver.com':
        api_idx = 1
    else:
        return 'fail'
    
    headers['origin'] = origin_li[api_idx]

    res = requests.get(url, cookies=cookies, headers=headers)
    html = res.text
    # print(html)
    soup = bs(html, 'html.parser')
    json_element = soup.select_one('body > script')
    if json_element is None:
        raise NotValidKeywordError('Keyword for get reviews is not valid.');

    # merchantNo: categoryTree > product > A > channel > naverPaySellerNo
    item_json = json.loads(json_element.get_text()[27:])
    merchantNo = item_json['product']['A']['channel']['naverPaySellerNo']
    originProductNo = item_json['product']['A']['productNo']

    print(merchantNo, originProductNo)
    json_data = {
        'page': 1,
        'pageSize': 20,
        'merchantNo': str(merchantNo),
        'originProductNo': str(originProductNo),
        'sortType': 'REVIEW_RANKING',
    }

    try:
        i = 1
        total_review_num = 20
        while i <= math.ceil(total_review_num / 20):
            if i > 100:
                break
            json_data['page'] = i
            res = requests.post(
                review_api[api_idx],
                cookies=cookies,
                headers=headers,
                json=json_data,
            )
            # print(res.text)
            if res.text == 'OK':
                print('end on', i)
                break
            review_json = json.loads(res.text)
            review_cont = review_json['contents']
            total_review_num = int(review_json['totalElements'])
            i += 1
            for item in review_cont:
                userid = item['writerMemberId']
                cont = item['reviewContent']
                review_time = item['createDate']
                cont = cont.replace('\n', ' ').replace(',', ' ')
                sr = item['reviewScore']
                wr.writerow([userid, cont, sr, review_time])
    except Exception as e:
        print(e)

    cf.close()
    return filename


cookies_trend = {
    'NNB': '3PM2SQOU6VFWI',
    'ASID': 'afc335a00000018808d00bf600000053',
    '_ga': 'GA1.2.1183798841.1684295968',
    'm_loc': 'a79f082866164b5cbd5def9f414b20d2378ad517b2394162ddde5927eed53cfe',
    'NV_WETR_LAST_ACCESS_RGN_M': '"MDIxMTE1NjY="',
    'NV_WETR_LOCATION_RGN_M': '"MDIxMTE1NjY="',
    'nx_ssl': '2',
    '_datalab_cid': '50000000',
    'page_uid': 'ink/fsp0J1sssuiQZYNssssss+V-226264',
}

headers_trend = {
    'authority': 'datalab.naver.com',
    'accept': '*/*',
    'accept-language': 'ko,en;q=0.9,en-US;q=0.8,ja;q=0.7',
    'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
    # 'cookie': 'NNB=3PM2SQOU6VFWI; ASID=afc335a00000018808d00bf600000053; _ga=GA1.2.1183798841.1684295968; m_loc=a79f082866164b5cbd5def9f414b20d2378ad517b2394162ddde5927eed53cfe; NV_WETR_LAST_ACCESS_RGN_M="MDIxMTE1NjY="; NV_WETR_LOCATION_RGN_M="MDIxMTE1NjY="; nx_ssl=2; _datalab_cid=50000000; page_uid=ink/fsp0J1sssuiQZYNssssss+V-226264',
    'origin': 'https://datalab.naver.com',
    'referer': 'https://datalab.naver.com/shoppingInsight/sKeyword.naver',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'none',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
    'x-requested-with': 'XMLHttpRequest',
}


def make_date_li(start_date, end_date):
    data = {
        'cid': '50000006',
        'timeUnit': 'week',
        'startDate': start_date,
        'endDate': end_date,
        'age': '',
        'gender': '',
        'device': '',
        'keyword': '닭가슴살',
    }

    res = requests.post(
        'https://datalab.naver.com/shoppingInsight/getKeywordClickTrend.naver',
        cookies=cookies_trend,
        headers=headers_trend,
        data=data,
    )

    data_json = json.loads(res.text)['result']
    if len(data_json) == 0:
        print('no record')
        return 'no record'

    data_json = data_json[0]['data']
    print(len(data_json))
    print(data_json)

    if len(data_json) > 157:
        data_json = data_json[-157:]
    return [item['period'] for item in data_json]

def get_search_volume(keyword: str):

    end_date = datetime.datetime.now()
    start_date = end_date - relativedelta(years=3)
    end_date_str = end_date.strftime('%Y-%m-%d')
    start_date_str = start_date.strftime('%Y-%m-%d')
    print(start_date_str, end_date_str)
    
    date_li = make_date_li(start_date_str, end_date_str)
    print(len(date_li), date_li)
    
    keyword = keyword.replace('/', '')
    keyword_id = json.loads(requests.post('https://api.itemscout.io/api/keyword', data={'keyword': keyword}).text)['data']

    category_id_list = json.loads(requests.get('https://api.itemscout.io/api/v2/keyword/products?kid={}&type=total'.format(keyword_id)).text)['data']['productListResult']
    if len(category_id_list) == 0:
        raise NotValidKeywordError()
    
    category_id = category_id_list[0]['categoryStack'][0]
    print(category_id)
    data = {
        'cid': category_id,
        'timeUnit': 'week',
        'startDate': start_date_str,
        'endDate': end_date_str,
        'age': '',
        'gender': '',
        'device': '',
        'keyword': keyword,
    }

    res = requests.post(
        'https://datalab.naver.com/shoppingInsight/getKeywordClickTrend.naver',
        cookies=cookies_trend,
        headers=headers_trend,
        data=data,
    )
    print(res.text)

    data_json = json.loads(res.text)['result']
    if len(data_json) == 0:
        print('no record')
        raise NotEnoughSearchVolumeError()

    data_json = data_json[0]['data']
    print(len(data_json))
    if len(data_json) < 100:
        print('warning')
        return
    
    if len(data_json) > 157:
        data_json = data_json[-157:]
    
    idx = 0
    temp = []
    for data in data_json:
        while date_li[idx] != data['period']:
            idx += 1
            temp.append(0)
        temp.append(data['value'])
        idx += 1
    for i in range(len(temp), 157):
        temp.append(0)
    
    print(keyword, temp)
    return temp
    
