cookies = "PC_TOKEN=72f0729fe4; XSRF-TOKEN=q3H4wA04iYf5aIRFLA1JxkBI; SL_G_WPT_TO=zh; SL_GWPT_Show_Hide_tmp=1; SL_wptGlobTipTmp=1; SUB=_2A25OkVPhDeRhGeVH4lET8ifNzz-IHXVt58IprDV8PUNbmtAKLUnmkW9NTwsOvTLolfxkpsf6azqHRROdclBq_xuM; SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9W5vww5GEr5gKn__ED1nvf0X5JpX5KzhUgL.Foe41KeEeo.pShe2dJLoIEMLxKqLBo-LB--LxK-L12BL12-LxK-L12BL122LxKML1KBL1-9bdN.t; ALF=1702254385; SSOLoginState=1670718385; WBPSESS=tz4NAmcNmXlvdc7gFMeoAReT0V8Lt_TZC3qGGk0r8QxQ1VEwUZOFzOUotohC3uqmjfLiFKhdJ7uE6FcpmxzeXcVZKeVNkkJ_8aDdy22xMW1soChewNzAY8uB0x3Np9tX3lM31VP93oFVFRl_qYG28w=="

del_file = ['7e80fb31ec58b1ca2fb3548480e1b95e', '4cf24fe8401f7ab2eba2c6cb82dffb0e', '41e5d4e3002de5cea3c8feae189f0736']
ad_title = ['卫衣', 'T恤', '手机', '预售', '预定', '手机', '双12', '双11', '618', '短裤', '短袖',
            'http://t.cn/A6LPBAoE', 'http://t.cn/A6yTFnPH', 'http://t.cn/A6tnAUDS', 'http://t.cn/A6to7Snf']

save_dir = r'E:\OneDrive - johngao\medias\weibopro'
cookies_dict = {}
for cookie in cookies.split(";"):
    k, v = cookie.split("=", maxsplit=1)
    cookies_dict[k] = v

headers = {
    'authority': 'weibo.com',
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7',
    'client-version': 'v2.35.6',
    # Requests sorts cookies= alphabetically
    # 'cookie': 'SINAGLOBAL=4618184845274.955.1664029302764; ULV=1664029302766:1:1:1:4618184845274.955.1664029302764:; SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9WFybN0YodCC8sDaiK3hJFKd5JpX5KMhUgL.FoMNSoMN1h5EeK-2dJLoI7D3dcyVIJvQdo5p; WBPSESS=CIq1nOqC6X2VXYb4WSS3wMt_Z8Adek6Z5Tk5bl67sgJoDdwtcByi9nSlY_pkZwq_rgYB88Xz423xy7Xckz5d1W7KxZtiHwAL3D0uWhGpuzDAzQwFKZy4R1iVC4TZU1kcwjy3Y7K0p_D05BSrnQwtIA==; PC_TOKEN=c4b697e777; ALF=1695728648; SSOLoginState=1664192649; SCF=Aiz08J5yBpRSAa5G0VFwzMu7oPD6jbKyrEOJn2wi5CqJtEyMfJZxBn4OaeieOuh9p1RcAEopXL_Sbf3u8KHpNT4.; SUB=_2A25ONeDZDeRhGeFJ7VUW-C7OyjmIHXVtQ1URrDV8PUNbmtAKLVSlkW9Nf1NVvgV8C7SlKTGS3GrzoN1N4Q1xMh9F; XSRF-TOKEN=lq8kI9X3JhvvbhQRIA0-kLZF',
    'referer': 'https://weibo.com/',
    'sec-ch-ua': '"Google Chrome";v="105", "Not)A;Brand";v="8", "Chromium";v="105"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'server-version': 'v2022.09.23.2',
    'traceparent': '00-3d819258ad9faac2e22d7c82b71d0b58-37d1757024402885-00',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36',
    'x-requested-with': 'XMLHttpRequest',
    'x-xsrf-token': 'lq8kI9X3JhvvbhQRIA0-kLZF',
}
