import os.path
from os import getpid
from utils import mysql_db
import pandas as pd
from utils import login
from utils import get_weibo_data
from utils import update_media
from utils import bytes2md5
from utils import del_media
from multiprocessing import Pool
from multiprocessing import cpu_count


def is_url(link: str):
    if link.startswith("http"):
        return True


def handler_response(r, media_id, media_type, save_path):
    if r.status_code == 404 and r.text == 'bad request!\n':
        update_media(media_id, media_type, 0, '', 'bad', mysql_db())
        print(r.url, media_type, 'bad', getpid())
    elif r.status_code == 403 and "403 Forbidden" in r.text:
        update_media(media_id, media_type, 0, '', 'forbidden', mysql_db())
        print(r.url, media_type, 'forbidden', getpid())
    else:
        if r.status_code == 200 and isinstance(r.content, bytes):
            file_path = os.path.join(r'C:\Users\john\Desktop\medias\weibopro', save_path)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, mode='wb') as f:
                f.write(r.content)
            print(file_path, len(r.content), getpid())
            update_media(media_id, media_type, len(r.content), bytes2md5(r.content), 'stored', mysql_db(), r.url)


def handler_weibo(weibo_id, df, session):
    weibo = get_weibo_data(weibo_id, session)
    medias = df[df['weibo_id'] == weibo_id]
    if isinstance(weibo, dict):
        for media in medias.values:
            headers = {
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                              'Chrome/107.0.0.0 Safari/537.36',
                'referer': media[-6]
            }
            media_id = media[0]
            media_type = media[-4]
            if media_type == 'jpg':
                url = weibo['pic_infos'][media_id]['largest']['url']
            elif media_type == 'mp4':
                url = weibo['page_info']['media_info']['stream_url_hd']
            else:
                url = weibo['pic_infos'][media_id]['video']
            if is_url(url):
                r = session.get(url, headers=headers)
                handler_response(r, media_id, media_type, media[6])
    elif weibo == 'bad':
        print("微博不可见或微博不存在")
        for media in medias.values:
            media_id = media[0]
            media_type = media[-4]
            del_media(media_id, media_type, mysql_db())


if __name__ == '__main__':
    login_session = login()

    data = pd.read_sql_query('select * from medias where file_status="fail" ', mysql_db())
    weibo_ids = data.weibo_id.value_counts().index

    p = Pool(cpu_count())
    for idstr in weibo_ids:
        p.apply_async(handler_weibo, args=(idstr, data, login_session))
    p.close()
    p.join()
