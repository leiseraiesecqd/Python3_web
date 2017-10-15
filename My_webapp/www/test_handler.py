import asyncio,re,time,json,logging,hashlib,base64 
from Webframe import get,post
from Model import User,Comment,Blog,next_id
from apis import Page,APIError,APIValueError,APIResourceNotFoundError
from config import configs
from aiohttp import web
import markdown2
#编写用于测试的URL处理函数
'''
@get('/')
async def handler_url_blog(request):
	body='<h1>Awesome</h1>'
	return body
@get('/greeting')
async def handler_url_greeting(*,name,request):
	body='<h1>Awesome:/greeting%s</h1>'%name
	return body
#测试数据库链接
@get('/')
async def index(request):
	users=await User.findAll()
	return  {
		'__template__':'test.html',	
		'users':users
		}	
@get('/')
async def index(request):
	summary="don't limit yourself."
	blogs=[
	Blog(id='1',name='Test Blog',summary=summary,created_at=time.time()-120),
	Blog(id='2',name='Something New',summary=summary,created_at=time.time()-3600),
	Blog(id='3',name='Learn Swift',summary=summary,created_at=time.time()-7200)]
	return{
	'__template__':'blogs.html',
	'blogs':blogs
	}
#测试API
@get('/api/users')
async def api_get_users(*,page='1'):
	page_index=get_page_index(pages)
	num=await User.findNumber('count(id)')
	p=Page(num,page_index)
	if num==0:
		return dict(page=p,users=())
	users=await User.findAll(orderBy='created_at desc',limit=(p.offset,p.limit))
	for u in users:
		u.password=''
	return dict(page=p,users=users)
'''


#-------------函数定义-----------------------

# 文本转html
def text2html(text):
    lines = map(lambda s: '<p>%s</p>' % s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'), filter(lambda s: s.strip() != '', text.split('\n')))
    return ''.join(lines)

#验证管理员身份
def check_admin(request):
    if request.__user__ is None or not request.__user__.admin:
        raise APIPermissionError()

#获取页码
def get_page_index(page_str):
    p = 1
    try:
        p = int(page_str)
    except ValueError as e:
        pass
    if p < 1:
        p = 1
    return p

#用户登录cookie
COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs.session.secret

#计算加载cookie
def user2cookie(user,max_age):
	# build cookie string by: id-expires-sha1（id-到期时间-摘要算法）
	expires=str(time.time()+max_age)
	s='%s-%s-%s-%s'%(user.id,user.passwd,expires,_COOKIE_KEY)
	L=[user.id,expires,hashlib.sha1(s.encode('utf-8')).hexdigest()]
	return '-'.join(L)

# 解析验证cookie:
async def cookie2user(cookie_str): 
    
    if not cookie_str:
        return None
    try:
        L = cookie_str.split('-')
        if len(L) != 3:
            return None
        uid, expires, sha1 = L
        if float(expires) < time.time():
            return None
        user = await User.find(uid)
        if user is None:
            return None
        s = '%s-%s-%s-%s' % (uid, user.passwd, expires, _COOKIE_KEY)
        if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
            logging.info('invalid sha1')
            return None
        user.passwd = '******'
        return user
    except Exception as e:
        logging.exception(e)
        return None

#---------get/post指令-----------------------------------

#####get指令：将()内容输入http://127.0.0.1:9000后面，会显示对应界面；get指令出现在html的herf里面

'''
@get('/')#显示主界面
def index(request):
	summary = 'Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
	blogs = [
		Blog(id='1',name='Test Bolg',summary=summary,created_at=time.time()-120),
		Blog(id='2',name='Something New',summary=summary,created_at=time.time()-3600),
		Blog(id='3',name='Learn Swift',summary=summary,created_at=time.time()-7200)
	]
	return{
		'__template__' : 'blogs.html',
		'blogs' : blogs,
		'__user__' : request.__user__
	}
'''

@get('/')#显示主界面
async def index(request,*, page='1'):
    page_index = get_page_index(page)
    num = await Blog.findNumber('count(id)')
    page = Page(num)
    if num == 0:
        blogs = []
    else:
        blogs = await Blog.findAll(orderBy='created_at desc', limit=(page.offset, page.limit))
    return {
        '__template__': 'blogs.html',
        'page': page,  #显示的博文条目
        'blogs': blogs, #博文信息
        '__user__': request.__user__
    }

@get('/register')#显示注册页面,http://127.0.0.1:9000/register
def register():
	return {
	'__template__':'register.html'
	}


@get('/signin')#显示登录页面,http://127.0.0.1:9000/signin
def signin():
	return {
		'__template__' : 'signin.html'
	}

@get('/signout')#登出，http://127.0.0.1:9000/signout
def signout(request):
	referer = request.headers.get('Referer')
	r = web.HTTPFound(referer or '/')
	r.set_cookie(COOKIE_NAME,'-delete-',max_age=0,httponly=True)
	logging.info('user signed out')
	return r

@get('/manage/blogs/create') #创建博文,http://127.0.0.1:9000/manage/blogs/create
def manage_create_blog(): 
	return { 
		'__template__': 'manage_blog_edit.html', 
		'id': '', 
		'action': '/api/blogs' 
 	} 

@get('/api/blogs') #显示分页
async def api_blogs(*,page='1'):
	page_index=get_page_index(page)
	num=await Blog.findNumber('count(id)')
	p=Page(num,page_index)
	if num==0:
		return dict(page=p,blogs=())
	blogs=await Blog.findAll(orderBy='created_at desc',limit=(p.offset,p.limit))
	return dict(page=p,blogs=blogs)

@get('/manage/blogs') #管理博文页面
def manage_blogs(*,page='1'):
	return {
	'__template__':'manage_blogs.html',
	'page_index':get_page_index(page)
	}

@get('/api/blogs/{id}') #显示Blog的数据信息
async def api_get_blog(*, id): 
    blog = await Blog.find(id) 
    return blog 

@get('/manage/blogs/modify') # 显示修改博客后的页面
def manage_modify_blog(*,id):
    #通过输入id和post指令给‘manage_blog_edit.html’，实现编辑时有原信息
    return {
        '__template__': 'manage_blog_edit.html',
        'id': id,
        'action': '/api/blogs/%s'%id     
    }


@get('/blog/{id}')#返回单条微博详细内容
async def get_blog(id):
    blog = await Blog.find(id)
    comments = await Comment.findAll('blog_id=?', [id], orderBy='created_at desc')
    for c in comments:
        c.html_content = text2html(c.content)
    blog.html_content = markdown2.markdown(blog.content)
    return {
        '__template__': 'blog.html',
        'blog': blog,
        'comments': comments
    }


@get('/manage/')
def manage():
    return 'redirect:/manage/comments'


@get('/manage/comments')#管理评论
def manage_comments(*, page='1'):
    return {
        '__template__': 'manage_comments.html',
        'page_index': get_page_index(page)
    }


@get('/manage/users')#管理用户
def manage_users(*, page='1'):
    return {
        '__template__': 'manage_users.html',
        'page_index': get_page_index(page)
    }


@get('/api/comments')#获取评论
async def api_comments(*, page='1'):
    page_index = get_page_index(page)
    num = await Comment.findNumber('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page=p, comments=())
    comments = await Comment.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
    return dict(page=p, comments=comments)


@get('/api/users')#获取用户信息
async def api_get_users(*, page='1'):
    page_index = get_page_index(page)
    num = await User.findNumber('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page=p, users=())
    users = await User.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
    for u in users:
        u.passwd = '******'
    return dict(page=p, users=users)

#####Post操作：点击某个按钮，提交信息的时候，系统通过post命令操作
#post出现在html的function中

#正则表达式
_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')

#用户注册api
@post('/api/users')
async def api_register_user(*, email, name, passwd):
    if not name or not name.strip():
        raise APIValueError('name')
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email')
    if not passwd or not _RE_SHA1.match(passwd):
        raise APIValueError('passwd')
    #查询邮箱是否已注册
    users = await User.findAll('email=?', [email])
    if len(users) > 0:
        raise APIError('register:failed', 'email', 'Email is already in use.')
     #接下来就是注册到数据库上,
    uid = next_id()
    sha1_passwd = '%s:%s' % (uid, passwd)
    user = User(id=uid, name=name.strip(), email=email, passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(), image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest())
    await user.save()
    #制作cookie返回浏览器客户端
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'#掩盖passwd
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r


#用户登录验证api
@post('/api/authenticate')
async def authenticate(*,email,passwd):
	if not email:
		raise APIValueError('email','Invalid email.')
	if not passwd:
		raise APIValueError('passwd','Invalid password.')

	users=await User.findAll('email=?',[email])
	if len(users)==0:
		raise APIValueError('email','Email not exit.')
	user=users[0]
	#check passwd
	sha1=hashlib.sha1()
	sha1.update(user.id.encode('utf-8'))
	sha1.update(b':')
	sha1.update(passwd.encode('utf-8'))

	if user.passwd!=sha1.hexdigest():
		raise APIValueError('passwd','Invalid password')

	#验证通过，设置cookie
	r = web.Response()
	r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
	user.passwd ='******'
	r.content_type ='application/json'
	r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
	return r



#创建博客的api
@post('/api/blogs')
async def api_create_blog(request, *, name, summary, content):
    check_admin(request)
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty.')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty.')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty.')
    blog = Blog(user_id=request.__user__.id, user_name=request.__user__.name,
     user_image=request.__user__.image, name=name.strip(), 
     summary=summary.strip(), content=content.strip())
    await blog.save()
    return blog

#修改博客的api
@post('/api/blogs/{id}')
async def api_modify_blog(request, *, id, name, summary, content):
    # 修改一条博客
    check_admin(request)
    logging.info("修改的博客的博客ID为：%s", id)
    # name，summary,content 不能为空
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty')

    # 获取指定id的blog数据
    blog = await Blog.find(id)
    blog.name = name.strip()
    blog.summary = summary.strip()
    blog.content = content.strip()

    # 保存
    await blog.update()
    return blog

#删除博客的api
@post('/api/blogs/{id}/delete')
async def api_delete_blog(id,*, request):
    # 删除一条博客
    logging.info("删除博客的博客ID为：%s" % id)
    # 先检查是否是管理员操作，只有管理员才有删除评论权限
    check_admin(request)
    # 查询一下评论id是否有对应的评论
    b = await Blog.find(id)
    # 没有的话抛出错误
    if b is None:
        raise APIResourceNotFoundError('Comment')
    # 有的话删除
    await b.remove()
    return dict(id=id)

#用户留言api
@post('/api/blogs/{id}/comments')
async def api_create_comment(id, request, *, content):
    user = request.__user__
    if user is None:
        raise APIPermissionError('Please signin first.')
    if not content or not content.strip():
        raise APIValueError('content')
    blog = await Blog.find(id)
    if blog is None:
        raise APIResourceNotFoundError('Blog')
    comment = Comment(blog_id=blog.id, user_id=user.id, user_name=user.name, user_image=user.image, content=content.strip())
    await comment.save()
    return comment

#删除用户留言api
@post('/api/comments/{id}/delete')
async def api_delete_comments(id, request):
    check_admin(request)
    c = await Comment.find(id)
    if c is None:
        raise APIResourceNotFoundError('Comment')
    await c.remove()
    return dict(id=id)