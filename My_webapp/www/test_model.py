'''
import ORM
from Model import User,Blog,Comment

def test():
	yield from ORM.create_pool(user='www_data',password='www_data',databese='awesome')

	u=User(name='Test',email='123@gmail.com',passwd='0000',image='about:blank')

	yield from u.save()

for x in test():
	pass
'''

#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import ORM, asyncio
from Model import User, Blog, Comment

async def test(loop):
    await ORM.create_pool(loop=loop, user='root', password='', db='awesome',charset='utf8')
    u = User(name='LIU Shusi', email='i_love_lin@163.com', passwd='18656590', image='about:blank')
    await u.save()


loop = asyncio.get_event_loop()
loop.run_until_complete(test(loop))
loop.close()
