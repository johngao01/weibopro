import os

from utils import mysql_db
from utils import waiting_medias
from utils import file2md5
from setting import save_dir


def delete_media():
    if os.path.exists(filepath):
        os.remove(filepath)
        print(owner_name, save_name, 'delete')
    return f"update medias set size=0,file_status='delete',md5_value=NULL where media_id='{media_id}' " \
           f"and media_type='{media_type}' "


def waiting_media():
    if os.path.exists(filepath):
        size = os.path.getsize(filepath)
        md5_value = file2md5(filepath)
        print(owner_name, save_name, 'stored')
        return f"update medias set size={size},file_status='stored',md5_value='{md5_value}' where media_id='{media_id}' " \
               f"and media_type='{media_type}' "
    else:
        print(owner_name, save_name, 'waiting')
        return f"update medias set size=0,file_status='waiting',md5_value=NULL where media_id='{media_id}' " \
               f"and media_type='{media_type}' "


if __name__ == '__main__':
    medias_type = 'fail'
    medias = waiting_medias(medias_type)
    print(len(medias))
    input()
    db = mysql_db()
    cursor = db.cursor()
    count = 0
    for media in medias:
        media_id = media[0]
        save_path = media[5].replace('/', "\\")
        media_type = media[11]
        save_name = media[4]
        owner_name = media[8]
        filepath = os.path.join(save_dir, save_path)
        if medias_type == 'delete':
            sql = delete_media()
        else:  # waiting stored
            sql = waiting_media()
        try:
            cursor.execute(sql)
        except Exception as e:
            print(e)
            db.rollback()
        else:
            db.commit()
    cursor.close()
    db.close()
