# day3：ORM Object Relational Mapping 对象关系映射

#创建全局的连接池，每个HTTP请求都可以从连接池中直接获取数据库连接。
#使用连接池的好处是不必频繁地打开和关闭数据库连接，而是能复用就尽量复用。
#连接池由全局变量__pool存储，缺省情况下将编码设置为utf8，自动提交事务：

import asyncio
import aiomysql   
import logging
@asyncio.coroutine
def create_pool(loop,**kw):
	logging.info('create database connection poop...')
	global __pool
	__pool=yield from aiomysql.create_pool(
		host=kw.get('host','localhost'),
		port=kw.get('port','3306'),
		user=kw['user'],
		password=kw['password'],
		db=kw['db'],
		charset=kw.get('charset','utf8'),
		autocommit=kw.get('autocommit',True),
		maxsize=kw.get('maxsize',10),# 池中最多有10个链接对象
		minsize=kw.get('minsize',1),
		loop=loop)


#封装select方法，传入SQL的语句和参数
'''
注意到yield from将调用一个子协程（也就是在一个协程中调用另一个协程）
并直接获得子协程的返回结果。
'''
@asyncio.coroutine
def select(sql,args,size=None):
	log(sql,args)
	global __pool
	with(yield from __pool)as conn:
		cur=yield from conn.cursor(aiomysql.DictCursor)
		# 用参数替换而非字符串拼接可以防止sql注入
		#SQL语句的占位符是?，而MySQL的占位符是%s，
		yield from cur.execute(sql.replace('?','%s'),args or ())
		if size:
			rs=yield from cur.fetchmany(size) #获取最多指定数量的记录
		else:
			rs=yield from cur.fetchall()#获取所有记录
		yield from cur.close()
		logging.info('rows returned:%s'%len(rs))
		return rs

#execute()函数,封装INSERT、UPDATE、DELETE语句
'''
update,insert,delete均只需返回一个影响行数
select方法要返回查询内容
'''
@asyncio.coroutine
def execute(sql,args):
	log(sql)
	with (yield from __pool) as conn:
		try:
			cur=yield from conn.cursor()
			yield from cur.execute(sql.replace('?','%s'),args)
			affected=cur.rowcount
			yield from cur.close()
		except BaseException as e:
			raise
		return affected

#ORM
'''
设计ORM：自顶向下
我们先考虑如何定义一个User对象，
然后把数据库表users和它关联起来。
'''

def create_args_string(num):
    L = []
    for n in range(num):
        L.append('?')
    return (','.join(L))

#Field字段类
class Field(object):

	def __init__(self,name,column_type,primary_key,default):
		self.name=name
		self.column_type=column_type
		self.primary_key=primary_key
		self.default=default

	def __str__(self):
		return '<%s, %s:%s>' %(
			self.__class__.__name__,self.column_type,self.name)


# 定义数据库中五个存储类型
class StringField(Field):
    def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
        super().__init__(name,ddl,primary_key,default)
# 布尔类型不可以作为主键
class BooleanField(Field):
    def __init__(self, name=None, default=None):
        super().__init__(name,'Boolean',False, default)
# 不知道这个column type是否可以自己定义 先自己定义看一下
class IntegerField(Field):
    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'int', primary_key, default)
class FloatField(Field):
    def __init__(self, name=None, primary_key=False,default=0.0):
        super().__init__(name, 'float', primary_key, default)
class TextField(Field):
    def __init__(self, name=None, default=None):
        super().__init__(name,'text',False, default)

#ModelMetaclass:将具体的子类如User的映射信息读取出来
'''
这样，任何继承自Model的类（比如User），会自动通过ModelMetaclass扫描映射关系，并存储到自身的类属性如__table__、__mappings__中。
'''

class ModelMetaclass(type):

    #当一个类指定通过某元类来创建，那么就会调用该元类的__new__方法
	# cls为当前准备创建的类的对象 
    # name为类的名字，创建User类，则name便是User
    # bases类继承的父类集合,创建User类，则base便是Model
    # attrs为类的属性/方法集合，创建User类，则attrs便是一个包含User类属性的dict

	def __new__(cls,name,bases,attrs):
		#排除model类本身
		if name=='Model':
			return type.__new__(cls,name,bases,attrs)
	#获取table名称
		tableName=attrs.get('__table__',None) or name
		logging.info('found model:%s(table:%s)' %(name,tableName))
		#获取所有的field(字段)和主键名：
		mappings=dict()
		fields=[]
		primaryKey=None
		for k,v in attrs.items():
			if isinstance(v,Field):
				logging.info('found mapping:%s==>%s'%(k,v))
				mappings[k]=v
				if v.primary_key:
					#找到主键
					if primaryKey:
						raise RuntimeError('Duplicate primary key for field:%s'%k)
					primaryKey=k
				else:
					fields.append(k)
		if not primaryKey:
			raise RuntimeError('Primary key not found.')
		for k in mappings.keys():
			attrs.pop(k)
		escaped_fields=list(map(lambda f:'`%s`' %f,fields))
		attrs['__mappings__']=mappings # 保存属性和列的映射关系
		attrs['__table__']=tableName
		attrs['__primary_key__']=primaryKey # 主键属性名
		attrs['__fields__']=fields# 除主键外的属性名
		
		# 构造默认的SELECT, INSERT, UPDATE和DELETE语句:
		attrs['__select__']='select `%s`,%s from `%s`'%(
			primaryKey,','.join(escaped_fields),tableName)
		attrs['__insert__']='insert into `%s`(%s,`%s`) values(%s)' %(
			tableName,','.join(escaped_fields),primaryKey,
			create_args_string(len(escaped_fields)+1))
		attrs['__update__']='update `%s` set %s where `%s`=?'%(tableName,
			','.join(map(lambda f:'`%s`=?'%(mappings.get(f).name or f),fields)),
			primaryKey)
		attrs['__delete__']='delete from `%s` where `%s`=?' %(tableName,primaryKey)
		return type.__new__(cls, name, bases, attrs)

#定义Model
'''
首先要定义的是所有ORM映射的基类Model：
# 让Model继承dict,主要是为了具备dict所有的功能，如get方法
# metaclass指定了Model类的元类为ModelMetaClass
'''
class Model(dict,metaclass=ModelMetaclass):

	def __init__(self,**kw):
		super(Model,self).__init__(**kw)

	def __getattr__(self,key):
		try:
			return self[key]
		except KeyError:
			raise AttributeError(r"'Model' object has no attribute: '%s' "%key)
	
	def __setattr__(self,key,value):
		self[key]=value

	def getValue(self,key):
		return getattr(self,key,None)

	# 取默认值，上面字段类不是有一个默认值属性嘛，默认值也可以是函数
	def getValueOrDefault(self,key):
		if value is None:
			field=self.__mappings__[key]
			if field.default is not None:
				value=field.default() if callable(field.default) else field.default
				logging.debug('using default value for %s:%s'%(key,str(value)))
				setattr(self,key,value)
		return value

	# 一步异步，处处异步，这些方法是协程
   	#下面 self.__mappings__,self.__insert__等变量据是根据对应表的字段不同，而动态创建
	@asyncio.coroutine
	def save(self):
		args=list(map(self.getValueOrDefault,self.__fields__))
		args.append(self.getValueOrDefault(self.__primary_key__))
		rows=yield from execute(self.__insert__,args)
		if rows !=1:
			logging.warn('failed to insert records:affected rows:%s' %rows)
	
	@asyncio.coroutine
	def remove(self):
	    args=[]
	    args.append(self[self.__primaryKey__])
	    print(self.__delete__)
	    yield from execute(self.__delete__,args)
    

	@asyncio.coroutine
	def update(self,**kw):
		print("enter update:")
		args=[]
		for key in kw:
			if key not in self.__fields__:
				raise RuntimeError("field not found")
		for key in self.__fields__:
			if key in kw:
				args.append(kw[key])
			else:
				args.append(getattr(self,key,None))
		args.append(getattr(self,self.__primary_key__))
		yield from execute(self.__update__,args)


	# 类方法
	@classmethod
	@asyncio.coroutine
	def find(cls,pk):
		'find object by primary key.'
		rs = yield from select('%s where `%s` =?'%(cls.__select__,
			cls.__primary_key__),[pk],1)
		if len(rs)==0:
			return None
		return cls(**rs[0]) # 返回的是一个实例对象引用

	@classmethod
	@asyncio.coroutine
	def findALL(cls,where=None,args=None):
		sql=[cls.__select__]
		if where:
			sql.append('where')
			sql.append(where)
		if args is None:
			args=[]
		rs=yield from select(''.join(sql),args)
		return [cls(**r) for r in rs]







'''	
#User类现在就可以通过类方法实现主键查找：
user=yield from User.find('123')

	
#这样，就可以把一个User实例存入数据库：
User=User(id=123,name='Michael')
yield from user.save()
'''
#from orm import Model,StringField,IntegerField
'''
if __name__=="__main__":
    class User(Model):
        id = IntegerField('id',primary_key=True)
        name = StringField('username')
        email = StringField('email')
        password = StringField('password')
    #创建异步事件的句柄
    loop = asyncio.get_event_loop()
 
    #创建实例
    @asyncio.coroutine
    def test():
        #yield from create_pool(loop=loop,host='localhost', port=3306, user='sly', password='070801382', db='test')
        user = User(id=8, name='sly', email='slysly759@gmail.com', password='fuckblog')
        yield from user.save()
        r = yield from User.find('11')
        print(r)
        r = yield from User.findAll()
        print(1, r)
        r = yield from User.findAll(id='12')
        print(2, r)
        yield from destroy_pool()
 
    loop.run_until_complete(test())
    loop.close()
    if loop.is_closed():
        sys.exit(0)
        '''