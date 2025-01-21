import requests
import json
import http.client
import re
from threading import Thread
thr_count = int(input('Введите кол-во потоков:'))
thr_address = input('Введите ip или адрес: ')
req = None
if re.search(r'https://', thr_address) != 'https://':
   thr_address = 'https://'+ thr_address
   print(thr_address)
def workThread(thr_i:int, thr_address:str) -> None:
   req = requests.post(thr_address)
   print('Поток {} в работе'.format(thr_i))
   print(req.status_code)

for thr in range(thr_count):
   th = Thread(target=workThread, args=(thr,thr_address, ))
   th.start()

