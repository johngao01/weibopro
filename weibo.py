import re
from datetime import datetime

from utils import standardize_date


class Weibo:
    def __init__(self, weibo: dict, req_user_id, req_username):
        self._weibo = weibo
        # 微博中pic_num可能和pic_ids中不一致，pic_num可能比pic_ids大
        self.pic_ids = weibo.get('pic_ids')
        self.isTop = weibo.get('isTop') or 0
        self.page_info = weibo.get('page_info')
        self.source = weibo.get('source') or ''
        self.vip_type = weibo.get('mblog_vip_type') or 0
        # 谁发的微博，在请求用户微博中，会有点赞的微博和快转的微博，
        # 这些微博的owner和请求的人可能不一样
        self.owner = weibo['user']
        self.req_user_id = req_user_id
        self.req_username = req_username
        self.owner_id, self.owner_name, self.weibo_url = self.user_info()
        # 格式化的微博发布时间，str 类型，形如：2022-07-08 12:12:12
        self.create_time = standardize_date(weibo['created_at'])
        # 格式化的微博发布时间，datetime 类型，可用于大小比较，形如：2022-07-08 12:12:12
        self.create_time_f = datetime.strptime(self.create_time, "%Y-%m-%d %H:%M:%S")
        # 最终转发的微博，这个是个微博字典，可以直接Weibo(self.retweeted_weibo)生成个微博对象
        self.retweeted_weibo = weibo.get('retweeted_status')

    @property
    def mblogid(self):
        return self._weibo.get('mblogid') or self._weibo.get('bid')

    @property
    def idstr(self):
        return self._weibo['idstr'] if 'idstr' in self._weibo else self._weibo['id']

    @property
    def text(self):
        return self._weibo['text']

    @property
    def text_raw(self):
        return self._weibo['text_raw'].replace('\n', '') if 'text_raw' in self._weibo else re.sub(
            r"<(\S*?)[^>]*>.*?|<.*? />", '', self.text)

    @property
    def pic_infos(self):
        if 'pic_infos' in self._weibo:
            return self._weibo['pic_infos']
        elif 'pics' in self._weibo:
            return self._weibo['pics']
        else:
            return None

    def user_info(self):
        if self.owner is None:
            return None, None, None
        else:
            if 'idstr' in self.owner:
                return self.owner['idstr'], self.owner['screen_name'], "https://www.weibo.com" + "/" \
                       + self.owner['idstr'] + "/" + self.idstr
            else:
                return str(self.owner['id']), self.owner['screen_name'], "https://www.weibo.com" \
                       + "/" + str(self.owner['id']) + "/" + self.idstr

    def pic_nums(self):
        if (isinstance(self.pic_infos, dict) or isinstance(self.pic_infos, list)) and len(self.pic_infos) > 0:
            return len(self.pic_infos)
        else:
            return 0

    def f_has_video(self):
        has_video = False
        if self.page_info is not None:
            object_type = self.page_info.get('object_type') or self.page_info.get('type')
            media_info = self.page_info.get('media_info')
            if (object_type == 'video' or object_type == 11) and media_info:
                has_video = True
        return has_video

    @property
    def weibo_type(self):
        if self.req_user_id == '':
            return '原创'
        if self.owner_id != self.req_user_id or isinstance(self.retweeted_weibo, dict):
            return '转发'
        else:
            return '原创'

    @property
    def media_type(self):
        if self.weibo_type == '转发':
            if isinstance(self.retweeted_weibo, dict):
                wb = Weibo(self.retweeted_weibo, '', '')
                if wb.pic_nums() > 0:
                    return "图片微博"
                elif wb.f_has_video():
                    return "视频微博"
                else:
                    return "文本微博"
        if self.pic_nums() > 0:
            return "图片微博"
        elif self.f_has_video():
            return "视频微博"
        else:
            return "文本微博"
