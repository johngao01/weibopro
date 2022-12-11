import datetime
import os
from multiprocessing import Manager
from multiprocessing import Pool
from multiprocessing import cpu_count

import requests
from pymysql import Error as mySqlerror
from utils import bytes2md5
from utils import mysql_db
from utils import waiting_medias
from utils import delete_medias
from setting import del_file
from setting import ad_title


def split_pics(pics):
    process_list = []
    max_process_num = cpu_count()
    pic_nums = len(pics)
    if pic_nums > max_process_num:
        if pic_nums % max_process_num == 0:
            cnt = pic_nums // max_process_num
            for i in range(max_process_num):
                dict1 = {}
                start = i * cnt
                end = (i + 1) * cnt
                for j in range(start, end):
                    dict1[j + 1] = pics[j]
                process_list.append(dict1)
            return max_process_num, process_list
        else:
            cnt = pic_nums // max_process_num
            other = pic_nums % max_process_num
            for i in range(max_process_num):
                dict1 = {}
                start = i * cnt
                end = (i + 1) * cnt
                for j in range(start, end):
                    dict1[j + 1] = pics[j]
                process_list.append(dict1)
            for j in range(other):
                process_list[-1][max_process_num * cnt + j + 1] = pics[max_process_num * cnt + j]
            return max_process_num, process_list
    else:
        dict1 = {}
        for i in range(pic_nums):
            dict1[i + 1] = pics[i]
        process_list.append(dict1)
        return pic_nums, process_list


def save_media(url, referer, filepath):
    retry_time = 0
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/107.0.0.0 Safari/537.36',
        'referer': referer
    }
    while True:
        try:
            r = requests.get(url=url, headers=headers, stream=True)
            size = len(r.content)
            if size > 0 and r.status_code == 200:
                md5_value = bytes2md5(r.content)
                if md5_value in del_file:
                    return 'delete', md5_value, 0
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, mode='wb') as f:
                    f.write(r.content)
                    return 'stored', md5_value, size
            else:
                retry_time += 1
        except (requests.HTTPError, OSError):
            retry_time += 1
        finally:
            if retry_time == 5:
                return 'fail', None, 0


def download_medias(media_dict: dict, lock):
    db = mysql_db()
    del_medias = delete_medias()
    cursor = db.cursor()
    done_medias = []
    for i, media in media_dict.items():
        media_id = media[0]
        download_url = media[1]
        wb_title = media[2]
        save_name = media[5]
        save_path = media[6].replace('/', "\\")
        owner_id = media[7]
        owner_name = media[8]
        weibo_url = media[10]
        media_type = media[12]
        filepath = os.path.join(r'C:\Users\16498\Desktop\medias\weibopro', save_path)
        if (media_id, media_type) in del_medias:
            status, md5_value, size = 'delete', None, 0
        elif owner_id == '2267396400' and (True in list(map(lambda x: True if x in wb_title else False, ad_title))):
            status, md5_value, size = 'delete', None, 0
        else:
            status, md5_value, size = save_media(download_url, weibo_url, filepath)
        print(i, owner_name, weibo_url, save_name, round(size / 1024 / 1024, 2), status)
        done_medias.append([size, status, media_id, media_type, md5_value])
        if i % 20 == 0 or i == list(media_dict.keys())[-1]:
            update_mysql(done_medias, db, cursor)
            done_medias.clear()


def update_mysql(v_medias, db, cursor):
    for media in v_medias:
        size, file_status, media_id, media_type, md5_value = media
        sql = "update medias set size=%s,file_status=%s,md5_value=%s where media_id=%s " \
              f"and media_type=%s"
        try:
            cursor.execute(sql, (size, file_status, md5_value, media_id, media_type))
        except mySqlerror as e:
            print(e)
            db.rollback()
        else:
            db.commit()
        finally:
            pass


if __name__ == '__main__':
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    medias = waiting_medias('waiting')
    num_process, psls = split_pics(medias)
    print(num_process)
    if num_process > 0:
        m = Manager()
        lock_ = m.Lock()
        print(f"一共有{len(medias)}个等待下载")
        print(f"开启 {num_process} 个并发进程")
        with Pool(num_process) as p:
            for psl in psls:
                p.apply_async(func=download_medias, args=(psl, lock_,))
            p.close()
            p.join()
