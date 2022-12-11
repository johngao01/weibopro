import os
import sys
from datetime import datetime

import requests
import urllib3

from download import save_media
from utils import get_followings, video_media
from utils import get_weibo_data
from utils import log2file
from utils import mongo_db
from utils import user_weibos
from weibo import Weibo
from utils import mysql_db
from get_all import wbdata2mysql, medias2mysql
from utils import pic_media
from pymysql import Error as mySqlerror
from utils import get_weibo_media
from multiprocessing import Pool, cpu_count
from multiprocessing import Manager

urllib3.disable_warnings()


def scrapy_latest(user: list, scrapy_log):
    page = 1
    userid = user[0]
    username = user[1]
    update_response = mongo_db()['update_response']
    new_weibo = []
    old_weibos = user_weibos(userid)
    while True:
        page_add = 0
        # 此方法获取的信息不能下载v+内容，但不需要cookie
        info = one_page_latest(user_id=userid, page=page)
        info['userid'] = userid
        info['username'] = username
        info['scrapy_page'] = page
        info['scrapy_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        update_response.insert_one(info)
        if info['ok']:
            cards = info['data']['cards']
            cards_num = len(cards)
            for card in cards:
                if card['card_type'] == 9:
                    weibo_info = card['mblog']
                    weibo_id = weibo_info['id']
                    if weibo_id in old_weibos:
                        continue
                    old_weibos.append(weibo_id)
                    page_add += 1
                    new_weibo.append(weibo_info)
                else:
                    cards_num -= 1
            info = f'获取第{page}页完成，共有{cards_num}个微博'
            if page_add > 0:
                info += f"，获得{page_add}个新微博"
                page += 1
                scrapy_log.info(info)
                continue
            else:
                scrapy_log.info(info)
                break
        if info['ok'] == 0 and (info.get('msg') == "这里还没有内容" or info.get('msg') == '请求过于频繁'):
            break
    return new_weibo


def download(medias, weibo_url, db, cursor, user_log):
    download_logs = [weibo_url + "   " + str(len(medias))]
    for i, media in enumerate(medias, start=1):
        media_id = media[0]
        download_url = media[1]
        media_type = media[3]
        save_path = media[4].replace('/', "\\")
        filepath = os.path.join(r'C:\Users\john\Desktop\medias\weibopro', save_path)
        save_name = os.path.split(filepath)[1]
        file_status, md5_value, size = save_media(download_url, weibo_url, filepath)
        log_info = "  ".join([str(i), media_id, save_name, str(file_status), str(size)])
        user_log.info(log_info)
        download_logs.append(log_info)
        sql = "update medias set size=%s,file_status=%s,md5_value=%s where media_id=%s " \
              f"and media_type=%s"
        try:
            cursor.execute(sql, (size, file_status, md5_value, media_id, media_type))
        except mySqlerror as e:
            print(e)
            db.rollback()
        else:
            db.commit()
    download_logs.append('\n')
    return download_logs


def parse_weibos(weibos, user_id, username, wb_id_time: list, download_config: list, user_log):
    mysql_database = mysql_db()
    cursor = mysql_database.cursor()
    download_log_info = []
    parse_weibo_log = []
    fir_wb_id, fir_wb_time, l_wb_id, l_wb_time = wb_id_time
    for wb in weibos:
        medias = []
        weibo_id = wb['id']
        is_long = True if wb.get(
            'pic_num') > 9 else wb.get('isLongText')
        vip_weibo = wb.get('mblog_vip_type') or 0
        w = Weibo(wb, req_user_id=user_id, req_username=username)
        if is_long or vip_weibo:
            weibo = get_weibo_data(weibo_id)
            if weibo:
                w = Weibo(weibo, req_user_id=user_id, req_username=username)
            else:
                w = Weibo(wb, req_user_id=user_id, req_username=username)
        if w.create_time_f <= fir_wb_time:
            fir_wb_time = w.create_time_f
        if w.create_time_f >= l_wb_time:
            l_wb_time = w.create_time_f
        weibo_type = w.weibo_type
        media_type = w.media_type
        weibo_info = w.weibo_url + "\t" + weibo_type + media_type
        user_log.info(weibo_info)
        parse_weibo_log.append(weibo_info)
        wbdata2mysql(w, weibo_type, media_type, mysql_database)
        if get_weibo_media(weibo_type, media_type, download_config):
            if media_type == "图片微博":
                medias.extend(pic_media(w.pic_infos, weibo_type, w.text_raw, username, w.idstr, w.create_time))
            else:  # 视频微博
                medias.extend(video_media(w.page_info, weibo_type, w.text_raw, username, w.idstr, w.create_time))

        if len(medias) > 0:
            medias2mysql(medias=medias, vip=w.vip_type, owner_id=user_id, owner_name=username, wb_id=w.idstr,
                         wb_url=w.weibo_url, wb_type=weibo_type, db=mysql_database)
            download_log_info = download(medias, w.weibo_url, mysql_database, cursor, user_log)
            parse_weibo_log.extend(download_log_info)
    cursor.close()
    mysql_database.close()
    if len(download_log_info) > 0:
        download_log_info.insert(0, username)
    return parse_weibo_log, download_log_info


def one_page_latest(user_id: str, page):
    params = {'container_ext': 'profile_uid:' + user_id, 'containerid': '107603' + user_id,
              'page_type': 'searchall', 'page': page}
    url = 'https://m.weibo.cn/api/container/getIndex?'
    r = requests.get(url, params=params, headers={
        'User_Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/86.0.4240.111 Safari/537.36'}, verify=False)
    r.content.decode("utf-8")
    return r.json()


def start(user, logs, logs2, p_lock):
    userid = user[0]
    username = user[1]
    user_log = log2file(userid, f'files/latest/{username}', ch=True, mode='a')
    start_info = f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\t开始获取 {username} https://weibo.com/u/{userid} 的新微博'
    user_log.info(start_info)
    insert_log = [start_info]
    new = scrapy_latest(user, user_log)
    if len(new) > 0:
        parse_weibo_start_info = f"开始处理 {username} 的 {len(new)} 个微博"
        user_log.info(parse_weibo_start_info)
        parse_logs = [parse_weibo_start_info]
        parse_log, download_log = parse_weibos(weibos=new, user_id=userid, username=username, wb_id_time=user[7:11],
                                               download_config=user[3:7], user_log=user_log)
        if len(download_log) > 0:
            with p_lock:
                logs2.extend(download_log)
        parse_logs.extend(parse_log)
        parse_weibo_end_info = f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\t处理 {username} 微博完成\n'
        user_log.info(parse_weibo_end_info)
        parse_logs.append(parse_weibo_end_info)
        insert_log.extend(parse_logs)
    else:
        parse_weibo_end_info = f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\t没有新微博\n'
        user_log.info(parse_weibo_end_info)
        insert_log.append(parse_weibo_end_info)
    with p_lock:
        logs.append(insert_log)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        followings = get_followings(sys.argv[1])
    else:
        followings = get_followings()
    all_logs = Manager().list()
    all_download_log = Manager().list()
    lock = Manager().Lock()
    p = Pool(cpu_count())
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for following in followings:
        p.apply_async(start, args=(following, all_logs, all_download_log, lock))
    p.close()
    p.join()
    # for following in followings:
    #     start(following, all_logs, all_download_log, lock)
    with open("files/latest.log", encoding="utf-8", mode="w") as f:
        for user_logs in all_logs:
            for log in user_logs:
                f.write(log)
                f.write('\n')
        f.write("任务结束")

    if len(all_download_log) > 0:
        split = '\n\n*******************************\n\n'
        with open("files/download.log", encoding="utf-8", mode="r+") as f:
            content = f.read()
            all_download_log.insert(0, start_time)
            f.seek(0, 0)
            f.write('\n'.join(all_download_log) + split + content)
