import requests
from bs4 import BeautifulSoup as bs
import json
import csv
import math
import pandas as pd
from service.custom_error import NotValidKeywordError, NotEnoughSearchVolumeError
import datetime
from dateutil.relativedelta import relativedelta
from service.header_info import review_cookies, review_headers, trend_cookies, trend_headers

review_api = ['https://smartstore.naver.com/i/v1/contents/reviews/query-pages', 'https://brand.naver.com/n/v1/contents/reviews/query-pages']
origin_li = ['https://smartstore.naver.com', 'https://brand.naver.com']


def check_url(url: str):
    res = requests.get(url, cookies=review_cookies, headers=review_headers)
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
    
    headers = review_headers.copy()
    headers['referer'] = url
    if url[8:28] == 'smartstore.naver.com':
        api_idx = 0
    elif url[8:23] == 'brand.naver.com':
        api_idx = 1
    else:
        return 'fail'
    
    headers['origin'] = origin_li[api_idx]

    res = requests.get(url, cookies=review_cookies, headers=headers)
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
        'checkoutMerchantNo': merchantNo,
        'originProductNo': originProductNo,
        'page': 1,
        'pageSize': 20,
        'reviewSearchSortType': 'REVIEW_RANKING',
    }

    try:
        i = 1
        total_review_num = 20
        while i <= math.ceil(total_review_num / 20):
            if i > 1000:
                break
            json_data['page'] = i
            res = requests.post(
                review_api[api_idx],
                cookies=review_cookies,
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
                userid = item['writerId']
                cont = item['reviewContent']
                review_time = item['createDate']
                cont = cont.replace('\n', ' ').replace(',', ' ')
                sr = item['reviewScore']
                wr.writerow([userid, cont, sr, review_time])
    except Exception as e:
        print(e)

    cf.close()
    return filename


def get_product_basic_info(url):
    headers = review_headers.copy()
    headers['referer'] = url
    if url[8:28] == 'smartstore.naver.com':
        api_idx = 0
    elif url[8:23] == 'brand.naver.com':
        api_idx = 1
    else:
        raise Exception
    
    headers['origin'] = origin_li[api_idx]

    res = requests.get(url, cookies=review_cookies, headers=headers)
    html = res.text

    soup = bs(html, 'html.parser')
    json_element = soup.select_one('body > script')
    if json_element is None:
        raise NotValidKeywordError('Keyword for get reviews is not valid.');

    # merchantNo: categoryTree > product > A > channel > naverPaySellerNo
    item_json = json.loads(json_element.get_text()[27:])
    product_name = item_json["product"]["A"]["name"]
    category_list = item_json["product"]["A"]["category"]["wholeCategoryName"].split('>')
    review_cnt = item_json["product"]["A"]["reviewAmount"]["totalReviewCount"]
    brand_name = item_json["product"]["A"]["naverShoppingSearchInfo"]["brandName"]
    try:
        model_name = item_json["product"]["A"]["naverShoppingSearchInfo"]["modelName"]
    except:
        model_name = None
    word_list = [item['text'] for item in item_json["product"]["A"]["seoInfo"]["sellerTags"]]
    img_url = item_json["product"]["A"]["productImages"][0]["url"]
    return {'product_name': product_name, 
            'category_list': category_list, 
            'review_cnt': review_cnt,
            'brand_name': brand_name,
            'model_name': model_name,
            'word_list': word_list,
            'img_url': img_url}



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
        cookies=trend_cookies,
        headers=trend_headers,
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

def get_search_volume(keyword: str, url: str):

    end_date = datetime.datetime.now()
    start_date = end_date - relativedelta(years=3)
    end_date_str = end_date.strftime('%Y-%m-%d')
    start_date_str = start_date.strftime('%Y-%m-%d')
    print(start_date_str, end_date_str)
    
    date_li = make_date_li(start_date_str, end_date_str)
    print(len(date_li), date_li)
    
    # keyword = keyword.replace('/', '')
    # keyword_id = json.loads(requests.post('https://api.itemscout.io/api/keyword', data={'keyword': keyword}).text)['data']

    # category_id_list = json.loads(requests.get('https://api.itemscout.io/api/v2/keyword/products?kid={}&type=total'.format(keyword_id)).text)['data']['productListResult']
    # if len(category_id_list) == 0:
    #     raise NotValidKeywordError()
    headers = review_headers.copy()
    headers['referer'] = url
    if url[8:28] == 'smartstore.naver.com':
        api_idx = 0
    elif url[8:23] == 'brand.naver.com':
        api_idx = 1
    else:
        return 'fail'
    
    headers['origin'] = origin_li[api_idx]

    res = requests.get(url, cookies=review_cookies, headers=headers)
    html = res.text
    # print(html)
    soup = bs(html, 'html.parser')
    json_element = soup.select_one('body > script')
    if json_element is None:
        raise NotValidKeywordError('Keyword for get reviews is not valid.');

    # merchantNo: categoryTree > product > A > channel > naverPaySellerNo
    item_json = json.loads(json_element.get_text()[27:])
    category_id = item_json["product"]["A"]["category"]["category1Id"]
    
    # category_id = category_id_list[0]['categoryStack'][0]
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
        cookies=trend_cookies,
        headers=trend_headers,
        data=data,
    )

    data_json = json.loads(res.text)['result']
    if len(data_json) == 0:
        print('no record')
        raise NotEnoughSearchVolumeError()

    data_json = data_json[0]['data']
    print(len(data_json))
    
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
    return temp, date_li[0], date_li[-1]