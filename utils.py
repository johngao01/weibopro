import hashlib
from datetime import datetime
from typing import Union

import pymysql
import requests.utils
from pymongo import MongoClient

from setting import cookies_dict
from setting import headers


def login():
    params = {
        'list_id': '100017767780215',
        'refresh': '4',
        'since_id': '0',
        'count': '15',
    }
    session = requests.Session()
    session.cookies.update(cookies_dict)
    session.headers.update(headers)
    response = session.get('https://weibo.com/ajax/feed/unreadfriendstimeline', params=params)
    data = response.json()
    num = len(data['statuses'])
    if num > 0:
        return session
    else:
        return False


def mysql_db():
    return pymysql.connect(
        host='localhost',
        port=3306,
        db="weibopro",
        user="root",
        password="123456")


def mongo_db():
    return MongoClient("mongodb://localhost:27017/")["weibopro"]


def log2file(name, filename, ch=False, mode='a', time=False):
    import logging
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    filepath = f'{filename}.log'
    handler = logging.FileHandler(filepath, mode=mode, encoding='utf-8')
    handler.setLevel(logging.NOTSET)
    if time:
        log_format = logging.Formatter("%(asctime)s - %(message)s")
    else:
        log_format = logging.Formatter("%(message)s")
    handler.setFormatter(log_format)
    if ch:
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(log_format)
        logger.addHandler(ch)
    logger.addHandler(handler)
    return logger


def get_followings(following_type=None):
    db = mysql_db()
    cursor = db.cursor()
    if following_type == 'vip':
        cursor.execute('select * from followings where hasvip=1')
    elif following_type == 'notvip':
        cursor.execute('select * from followings where hasvip=0')
    elif following_type == 'null':
        cursor.execute('select * from followings where count=0')
    else:
        cursor.execute('select * from followings')
    followings = cursor.fetchall()
    cursor.close()
    db.close()
    return followings


def get_weibo_data(weibo_id, session=None):
    start_time = datetime.now()
    # 根据微博id获取单个微博的信息，可能需要cookies
    params = {'id': weibo_id}
    try:
        if session:
            response = session.get('https://weibo.com/ajax/statuses/show', params=params, headers=headers, timeout=10)
        else:
            response = requests.get('https://weibo.com/ajax/statuses/show', params=params, headers=headers,
                                    cookies=cookies_dict, timeout=10)
        data = response.json()
        if "由于博主设置，目前内容暂不可见。" in response.text:
            return 'bad'
        elif "该微博不存在" in response.text:
            return 'bad'
        elif data['user']['idstr']:
            # print("--- %s seconds ---" % (datetime.now() - start_time))
            return data
        return False
    except (KeyError, requests.HTTPError):
        return False


def update_media(media_id, media_type, size, md5_value, file_status, db, download_url=None):
    cursor = db.cursor()
    sql = f'update medias set size="{size}",md5_value="{md5_value}",file_status="{file_status}" ' \
          f'where media_id="{media_id}" and media_type="{media_type}"'
    if download_url:
        sql = f'update medias set size="{size}",download_url="{download_url}",md5_value="{md5_value}",file_status="{file_status}" ' \
              f'where media_id="{media_id}" and media_type="{media_type}"'
    try:
        cursor.execute(sql)
    except pymysql.Error:
        db.rollback()
    else:
        db.commit()
    finally:
        cursor.close()


def del_media(media_id, media_type, db):
    cursor = db.cursor()
    sql = f'delete from medias where media_id="{media_id}" and media_type="{media_type}"'
    try:
        cursor.execute(sql)
    except pymysql.Error:
        db.rollback()
    else:
        db.commit()
    finally:
        cursor.close()


def standardize_date(created_at):
    created_at = created_at.replace("+0800 ", "")
    ts = datetime.strptime(created_at, "%c")
    full_created_at = ts.strftime("%Y-%m-%d %H:%M:%S")
    return full_created_at


def waiting_medias(status=None):
    db = mysql_db()
    cursor = db.cursor()
    medias = []
    if status:
        sql = f"select * from medias where file_status='{status}'"
    else:
        sql = "select * from medias"
    # sql = "select * from medias"
    cursor.execute(sql)
    for data in cursor.fetchall():
        medias.append(data)
    cursor.close()
    db.close()
    return medias


def delete_medias():
    db = mysql_db()
    cursor = db.cursor()
    sql = "select media_id,media_type from delete_medias"
    cursor.execute(sql)
    medias = [data for data in cursor.fetchall()]
    cursor.close()
    db.close()
    return medias


def video_url(media_info):
    url = media_info.get("mp4_hd_url")
    if not url:
        url = media_info.get("hevc_mp4_hd")
    if not url:
        url = media_info.get("mp4_sd_url")
    if not url:
        url = media_info.get("mp4_ld_mp4")
    if not url:
        url = media_info.get("h265_mp4_hd")
    if not url:
        url = media_info.get("h265_mp4_ld")
    if not url:
        url = media_info.get("inch_4_mp4_hd")
    if not url:
        url = media_info.get("inch_5_5_mp4_hd")
    if not url:
        url = media_info.get("inch_5_mp4_hd")
    if not url:
        url = media_info.get("stream_url_hd")
    if not url:
        url = media_info.get("stream_url")
    return url


def mongo_all_weibos(user_id):
    following_pages = mongo_db()['page_response'].find({'userid': user_id})
    all_weibos = []
    for page in following_pages:
        page_weibo = page['data']['list']
        all_weibos.extend(page_weibo)
    return all_weibos


def get_file_path(file_type, weibo_type, username, media_type, weibo_id, create_day, index=None):
    create_day = create_day[0:10].replace('-', '')
    # 是原创
    if media_type == 'pic':
        sec_dir = 'img' + '/' + f'{weibo_type}' + '微博图片'
    else:
        sec_dir = 'video' + '/' + f'{weibo_type}' + '微博视频'
    file_dir = username + '/' + sec_dir
    if index is None:
        filename = create_day + "_" + weibo_id + '.' + file_type
    else:
        filename = create_day + "_" + weibo_id + "_" + str(index) + '.' + file_type
    file_path = file_dir + '/' + filename
    return file_path


def pic_media(pic_infos: Union[list, dict], wb_type, wb_title, username, wb_id, create_day):
    def some_info(pic_dict):
        url = pic_dict['largest']['url'] if 'largest' in pic_dict else pic_dict['large']['url']
        file_type = url.split('?')[0].split('/')[-1].split('.')[-1]
        path = get_file_path(file_type=file_type, weibo_type=wb_type, username=username, media_type='pic',
                             weibo_id=wb_id, create_day=create_day, index=index)
        return url, file_type, path

    index = 0
    medias = []
    status = 'waiting'
    if isinstance(pic_infos, dict):
        for k, v in pic_infos.items():
            index += 1
            pic_id = k
            pic_url, pic_file_type, file_path = some_info(v)
            medias.append([pic_id, pic_url, wb_title, pic_file_type, file_path, status])
            if v.get('type') == 'livephoto':
                mov_url = v.get('video')
                mov_file_path = get_file_path(file_type='mov', weibo_type=wb_type, username=username,
                                              media_type='video',
                                              weibo_id=wb_id, create_day=create_day, index=index)
                medias.append([pic_id, mov_url, wb_title, 'mov', mov_file_path, status])
    else:
        for item in pic_infos:
            index += 1
            pic_id = item['pid']
            pic_url, pic_file_type, file_path = some_info(item)
            medias.append([pic_id, pic_url, wb_title, pic_file_type, file_path, status])
            if item.get('type') == 'livephotos':
                mov_url = item.get('videoSrc')
                mov_file_path = get_file_path(file_type='mov', weibo_type=wb_type, username=username,
                                              media_type='video',
                                              weibo_id=wb_id, create_day=create_day, index=index)
                medias.append([pic_id, mov_url, wb_title, 'mov', mov_file_path, status])
    return medias


def video_media(page_info: dict, wb_type, wb_title, username, wb_id, create_day):
    medias = []
    status = 'waiting'
    media_info, video_id, url, video_type = video_info(page_info=page_info)
    if video_type != 'mp4':
        return medias
    if url is None:
        return medias
    video_save_path = get_file_path(file_type=video_type, weibo_type=wb_type, username=username, media_type='video',
                                    weibo_id=wb_id, create_day=create_day)
    medias.append([video_id, url, wb_title, video_type, video_save_path, status])
    return medias


def user_weibos(userid):
    db = mysql_db()
    cursor = db.cursor()
    sql = f"select idstr from weibos where req_userid='{userid}'"
    cursor.execute(sql)
    wb_ids = [idstr[0] for idstr in cursor.fetchall()]
    cursor.close()
    db.close()
    return wb_ids


def get_weibo_media(w_type: str, m_type: str, media_config: list) -> bool:
    """
    :param w_type: 微博类型：转发，原创
    :param m_type: 微博媒体类型：图片微博，视频微博，文本微博
    :param media_config: 列表，长度4
    :return: 是否获取这个微博的媒体 bool
    """
    ori_pic, rtw_pic, ori_video, rtw_video = media_config
    if w_type == '转发' and m_type == "图片微博" and rtw_pic:
        return True
    elif w_type == '转发' and m_type == "视频微博" and rtw_pic:
        return True
    elif w_type == '原创' and m_type == "图片微博" and ori_pic:
        return True
    elif w_type == '原创' and m_type == "视频微博" and ori_video:
        return True
    else:
        return False


def video_info(page_info):
    media_info = page_info.get('media_info')
    media_id = media_info.get('media_id') or page_info.get('object_id').split(":", 1)[1]
    url = media_info.get("mp4_720p_mp4") or media_info.get('stream_url')
    if url:
        video_type = url.split('?')[0].split('/')[-1].split('.')[-1]
    else:
        url = video_url(media_info)
        video_type = url.split('?')[0].split('/')[-1].split('.')[-1]
    return media_info, media_id, url, video_type


def file2md5(filepath) -> str:
    with open(filepath, "rb") as f:
        file_hash = hashlib.md5()
        while chunk := f.read(8192):
            file_hash.update(chunk)
    return file_hash.hexdigest()  # to get a printable str instead of bytes


def bytes2md5(r_bytes):
    file_hash = hashlib.md5()
    file_hash.update(r_bytes)
    return file_hash.hexdigest()
