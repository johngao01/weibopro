import json
import os
from datetime import datetime
from multiprocessing import Pool
from multiprocessing import cpu_count
from setting import del_file
from setting import ad_title
from setting import save_dir
import requests
from pymysql import Error as mySqlerror

from utils import pic_media, get_weibo_media, mongo_all_weibos
from utils import get_followings
from utils import log2file
from utils import login
from utils import mongo_db
from utils import mysql_db
from weibo import Weibo
from utils import file2md5
from utils import user_weibos
from utils import video_media


def scrapy_all_weibo(user_id, username, user_log):
    page_response = mongo_db()['page_response']
    page_response.delete_many({'userid': user_id})
    session = login()
    if not isinstance(session, requests.Session):
        quit()
    all_weibos = []
    page = 1
    since_id = ''
    empty_time = 0
    first_scrapy_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    while True:
        page_data = get_one_page_data(session, page, since_id, user_id, user_log)
        page_data['userid'] = user_id
        page_data['username'] = username
        page_data['scrapy_page'] = page
        page_data['scrapy_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        page_weibos = page_data['data']['list']
        all_weibos.extend(page_weibos)
        page_data['weibo_num'] = len(page_weibos)
        user_log.info(
            f"爬取 {page_data['username']} 第{page}页，获得{page_data['weibo_num']}个微博，共获得{len(all_weibos)}个微博")
        since_id = page_data['data']['since_id']
        if since_id == '' and page_data['weibo_num'] == 0:
            if empty_time > 20:
                page_data['scrapy_page'] = 0
                page_response.insert_one(page_data)
                break
            else:
                empty_time += 1
                page += 1
                continue
        empty_time = 0
        page_response.insert_one(page_data)
        page += 1
    user_log.info(f"获取 {username} 所有微博完成，截至 {first_scrapy_time} 一共获取到 {len(all_weibos)} 个微博")
    return all_weibos


def get_one_page_data(session, page: int, since_id: str, user_id, user_log):
    params = {
        'uid': user_id,
        'page': page,
        'feature': '0'
    }
    if page != 1:
        params['since_id'] = since_id
    error_time = 0
    while True:
        try:
            response = session.get('https://weibo.com/ajax/statuses/mymblog', params=params, )
            page_data = json.loads(response.text)
            if page_data['ok'] != 1:
                if error_time > 4:
                    user_log.info("获取信息失败超过5次，cookies可能已失效，重新登陆获取新的cookies")
                    SystemExit()
                else:
                    error_time += 1
                    user_log.info(f"获取信息失败，尝试第{error_time}次获取")
                    continue
            else:
                return page_data
        except Exception as e:
            user_log.info(f"something get error，error info：{e}")
            error_time += 1
            user_log.info(f"获取信息失败，尝试第{error_time}次获取")
            continue


def parse_weibos(weibos, user_id, username, wb_id_time: list, download_config: list, user_log):
    old_weibos = user_weibos(user_id)
    mysql_database = mysql_db()
    fir_wb_id, fir_wb_time, l_wb_id, l_wb_time = wb_id_time
    if fir_wb_time is None:
        fir_wb_time = datetime.strptime("2099-12-31 00:00:00", "%Y-%m-%d %H:%M:%S")
    if l_wb_time is None:
        l_wb_time = datetime.strptime("2000-12-31 00:00:00", "%Y-%m-%d %H:%M:%S")
    weibos_num = len(weibos)
    for i, w in enumerate(weibos, start=1):
        medias = []
        if w.create_time_f <= fir_wb_time:
            fir_wb_time = w.create_time_f
            fir_wb_id = w.idstr
        if w.create_time_f >= l_wb_time:
            l_wb_time = w.create_time_f
            l_wb_id = w.idstr

        weibo_type = w.weibo_type
        if weibo_type == '转发' and w.retweeted_weibo is not None and w.retweeted_weibo['created_at'] == '':
            user_log.info(
                f"{username}" + "\t" + f"{i}/{weibos_num}" + "\t" + w.weibo_url + '\t' + w.retweeted_weibo['text_raw'])
            continue
        media_type = w.media_type
        user_log.info(f"{username}" + "\t" + f"{i}/{weibos_num}" + "\t" + w.weibo_url + '\t' + weibo_type + media_type)
        if w.idstr in old_weibos:
            continue
        wbdata2mysql(w, weibo_type, media_type, mysql_database)
        if get_weibo_media(weibo_type, media_type, download_config):
            if media_type == "图片微博":
                medias.extend(pic_media(w.pic_infos, weibo_type, w.text_raw, username, w.idstr, w.create_time))
            else:  # 视频微博
                medias.extend(video_media(w.page_info, weibo_type, w.text_raw, username, w.idstr, w.create_time))
        if len(medias) > 0:
            medias2mysql(medias=medias, vip=w.vip_type, owner_id=user_id, owner_name=username, wb_id=w.idstr,
                         wb_url=w.weibo_url, wb_type=weibo_type, db=mysql_database)

    cursor = mysql_database.cursor()
    sql = f"update followings set first_weibo_id='{fir_wb_id}',fweibo_time='{fir_wb_time}',last_weibo_id='{l_wb_id}'," \
          f"lweibo_time='{l_wb_time}',count={len(weibos)} where use_id = '{user_id}'"
    execute_sql(mysql_database, cursor, sql)
    cursor.close()
    mysql_database.close()


def medias2mysql(medias: list, vip, owner_id, owner_name, wb_id, wb_url, wb_type, db):
    cursor = db.cursor()
    for media in medias:
        media_id, download_url, wb_title, media_type, save_path, status = media
        file_path = os.path.join(save_dir, save_path)
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            md5_value = file2md5(file_path)
            status = 'stored'
            if md5_value in del_file:
                md5_value = None
                size = 0
                os.remove(file_path)
                status = 'delete'
        else:
            md5_value = None
            size = 0
        # 删除 火影忍者贴吧官方微博 中一些广告媒体
        if owner_id == '2267396400':
            if True in list(map(lambda x: True if x in wb_title else False, ad_title)):
                status = 'delete'
                md5_value = None
                size = 0

        save_name = os.path.basename(save_path)
        media_date = int(save_name[0:8])
        sql = "replace into medias  (media_id, download_url, title, vip, media_date, save_name, save_path, owner_id, " \
              "owner_name, weibo_id, weibo_url, weibo_type, media_type, size, md5_value, file_status) " \
              "values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        execute_sql(db, cursor, sql, (media_id, download_url, wb_title, vip, media_date, save_name, save_path, owner_id,
                                      owner_name, wb_id, wb_url, wb_type, media_type, size, md5_value, status))
    cursor.close()


def wbdata2mysql(weibo, weibo_type, media_type, db):
    if weibo_type == '转发':
        if isinstance(weibo.retweeted_weibo, dict):
            w = Weibo(weibo.retweeted_weibo, '', '')
            if w.owner_name:
                wbdata2mysql(w, '原创', media_type, db)
    idstr = weibo.idstr
    mblogid = weibo.mblogid
    txt = weibo.text
    txtraw = weibo.text_raw
    userid = weibo.owner_id
    username = weibo.owner_name
    req_userid = weibo.req_user_id
    req_username = weibo.req_username
    if isinstance(weibo.retweeted_weibo, dict):
        ret_weiboid = str(weibo.retweeted_weibo['id'])
    else:
        ret_weiboid = ''
    create_time = weibo.create_time_f
    vip_weibo = weibo.vip_type
    src = weibo.source
    pic_num = weibo.pic_nums()
    scrapy_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor = db.cursor()
    sql = 'replace into weibos (idstr, mblogid, txt, txtraw, userid, username, req_userid, req_username, weibo_type, ' \
          'media_type, ret_weiboid, create_time, vip_weibo, src, pic_num, scrapy_time) values ' \
          '(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'
    execute_sql(db, cursor, sql, (idstr, mblogid, txt, txtraw, userid, username, req_userid, req_username, weibo_type,
                                  media_type, ret_weiboid, create_time, vip_weibo, src, pic_num, scrapy_time))
    cursor.close()


def execute_sql(db, cursor, sql, data=None):
    try:
        if data:
            cursor.execute(sql, data)
        else:
            cursor.execute(sql)
    except mySqlerror:
        db.rollback()
    else:
        db.commit()


def start(user):
    userid = user[0]
    username = user[1]
    user_log = log2file(userid, f'files/all/{username}', ch=True, mode='w')
    user_log.info(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    all_dict_weibo = scrapy_all_weibo(user_id=userid, username=username, user_log=user_log)
    # all_dict_weibo = mongo_all_weibos(user_id=userid)
    weibos = [Weibo(weibo, req_user_id=userid, req_username=username) for weibo in all_dict_weibo]
    user_log.info(f"开始处理 {username} 这些微博")
    parse_weibos(weibos=weibos, user_id=userid, username=username, wb_id_time=user[7:11], download_config=user[3:7],
                 user_log=user_log)
    user_log.info(f"处理 {username} 微博完成")


if __name__ == '__main__':
    followings = get_followings('null')  # vip, notvip,''
    for j in range(len(followings)):
        print(j + 1, followings[j][1])
    confirm = input(f"确定重新获取这些人的全部微博吗？")
    if confirm != '1':
        quit()
    p = Pool(cpu_count())
    for following in followings:
        p.apply_async(start, args=(following,))
    p.close()
    p.join()

    # for following in followings:
    #     start(following)
