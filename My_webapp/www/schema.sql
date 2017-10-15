drop database if exists awesome:

create database awesome:

use awesome:

grant select,insert,updata,delete on awesome.* to 'www-data'@'localhost' identified by 'www-data':


create table users(
	'id'varchar(50) not null,
	'email'varchar(50)not null,
	'passwd'varchar(50)not null,
	'admin'bool not null,
	'name'varchar(50)not null,
	'image'varchar(500)not null,
	'create_at'real not null,
	unique key 'idx_email'('email'),
	key 'idx_create_at'('create_at'),
	primary key('id')
 )engine=innobd default charset=utf8;

create table blogs (
    'id' varchar(50) not null,
    'user_id' varchar(50) not null,
    'user_name' varchar(50) not null,
    'user_image' varchar(500) not null,
    'name' varchar(50) not null,
    'summary' varchar(200) not null,
    'content' mediumtext not null,
    'created_at' real not null,
    key 'idx_created_at' ('created_at'),
    primary key ('id')
) engine=innodb default charset=utf8;

create table comments (
    'id' varchar(50) not null,
    'blog_id' varchar(50) not null,
    'user_id' varchar(50) not null,
    'user_name' varchar(50) not null,
    'user_image' varchar(500) not null,
    'content' mediumtext not null,
    'created_at' real not null,
    key 'idx_created_at' ('created_at'),
    primary key ('id')
) engine=innodb default charset=utf8;

