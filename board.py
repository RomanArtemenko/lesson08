import os
import json
from flask import Flask, jsonify, request, abort
import redis
from jinja2 import Environment, FileSystemLoader
from datetime import datetime, timedelta
import hashlib
from validators import UserValidator, CommentValidator, AdvertValidator
from functools import wraps

config = {
        'redis_host':       'localhost',
        'redis_port':       6379
    }
redis = redis.Redis(config['redis_host'], config['redis_port'], decode_responses=True)

class User():
    
    def __init__(self, data):
        try:
            self._name = data.split(':')[0][1:-1]
            self._pass = data.split(':')[1][1:-1]
        except Exception:
            self._name = 'anonimus'
            self._pass = '321'

    @property
    def name(self):
        return self._name

    @property
    def password(self):
        return self._pass


def _check_pass(user):
    return redis.get(user.name) == hashlib.md5(user.password.encode('utf-8')).hexdigest()
    
def login(user):
    return redis.exists(user.name) and _check_pass(user)

def requires_login(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        user = User(request.headers.get('Authorization'))
        if not login(user):
            return "Incorrect username or password", 401
        return f(*args, **kwargs)
    return wrapped
      
def _time_stamp():
    return  datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M")

def _insert_advert(user, header):
    id = redis.incr('ad_counter')

    redis.set('ad:%s' % id, header)
    redis.set('user:ad:%s' % id, user)
    redis.set('date:ad:%s' % id, _time_stamp())

def _insert_comment(ad_id, user, text):
    id = redis.incr('comment_counter')

    redis.set('comment:%s:ad:%s' % (id, ad_id), text)
    redis.set('user:comment:%s:ad:%s' % (id, ad_id), user)
    redis.set('date:comment:%s:ad:%s' % (id, ad_id), _time_stamp())   

def _get_comment_list(ad_id): 
    comments = redis.keys('comment:*:%s' % ad_id)
    comment_list = []

    for comment in comments:
        com_id = comment.split(':')[1]
        com_text = redis.get('comment:%s:%s' % (com_id, ad_id))
        com_user = redis.get('user:comment:%s:%s' % (com_id, ad_id))
        com_date = redis.get('date:comment:%s:%s' % (com_id, ad_id))

        comment_list.append({'id': com_id, 'text': com_text, 'user': com_user, 'date': com_date })
    
    return comment_list

def _insert_like(ad_id, user):
    id = redis.incr('like_counter')

    redis.set('user:like:%s:ad:%s' % (id, ad_id), user)
    redis.set('date:like:%s:ad:%s' % (id, ad_id), _time_stamp())

def _get_like_list(ad_id):             
    likes = redis.keys('user:like:*:%s' % ad_id)
    like_list = []

    for like in likes:
        l_user = redis.get(like)
        l_date = redis.get('date:%s' % ":".join(like.split(':')[1:]))

        like_list.append({'user': l_user, 'date': l_date})

    return like_list

def _insert_user(name, password):
    redis.set('%s' % name, hashlib.md5(password.encode('utf-8')).hexdigest())

def _is_reached_limit_comment(user):
    hour_ago = datetime.now() - timedelta(hours=1)
    comment_counter = 0
    limit = 5

    comments = redis.keys('comment:*:%s' % 'ad:*')
    comment_list = []

    for comment in comments:
        com_id = comment.split(':')[1]
        ad_id = comment.split(':')[-1]
        com_text = redis.get('comment:%s:ad:%s' % (com_id, ad_id))
        com_user = redis.get('user:comment:%s:ad:%s' % (com_id, ad_id))
        com_date = redis.get('date:comment:%s:ad:%s' % (com_id, ad_id))

        if user == com_user and hour_ago < datetime.strptime(com_date, '%Y-%m-%d %H:%M'):
            comment_counter += 1

    return comment_counter >= limit

def _is_reached_limit_like(user):
    hour_ago = datetime.now() - timedelta(hours=1)
    like_counter = 0
    limit = 5

    likes = redis.keys('user:like:*:%s' % 'ad:*')
    like_list = []

    for like in likes:
        l_user = redis.get(like)
        l_date = redis.get('date:%s' % ":".join(like.split(':')[1:]))

        if user == l_user and hour_ago < datetime.strptime(l_date, '%Y-%m-%d %H:%M'):
            like_counter += 1

    return like_counter >= limit


app = Flask(__name__)

@app.route('/api/V1.0/', methods=["GET"])
@app.route('/api/V1.0/advert', methods=["GET"])
@requires_login
def advert_list():
    adverts = redis.keys('ad:*')
    advert_list = []

    for advert in adverts:
        id = advert.split(":")[1]
        header = redis.get(advert)
        user = redis.get('user:%s' % advert)
        date = redis.get('date:%s' % advert)
  
        advert_list.append({'id': id, 'header': header, 'user': user, 'date': date, 
        'comments': _get_comment_list(advert), 'likes': _get_like_list(advert)})

    return jsonify({"advert_list": advert_list})

@app.route('/api/V1.0/advert/<int:id>', methods=["GET"])
@requires_login
def advert(id):
    ad_id = 'ad:%s' % id

    if not redis.exists(ad_id):
        abort(404) 

    header = redis.get(ad_id)
    user = redis.get('user:%s' % ad_id)
    date = redis.get('date:%s' % ad_id)

    advert = {'id': id, 'header': header, 'user': user, 'date': date, 
    'comments': _get_comment_list(ad_id), 'likes': _get_like_list(ad_id)}

    return jsonify({"advert": advert}), 200

@app.route('/api/V1.0/advert/add', methods=["POST"])
@requires_login
def add_advert():
    advert = request.get_json()
    user = User(request.headers.get('Authorization'))

    av = AdvertValidator(advert) 
    av.validate()

    if av.errors:
        return jsonify({"errors":av.errors}), 400

    _insert_advert(user.name, advert["text"])

    return 'Advert successfully created', 201

@app.route('/api/V1.0/advert/<int:id>/add_comment', methods=["POST"])
@requires_login
def add_comment(id):
    comment = request.get_json()
    user = User(request.headers.get('Authorization')) 

    cv = CommentValidator(comment)
    cv.validate()

    if cv.errors:
        return jsonify({"errors":cv.errors}), 400

    if _is_reached_limit_comment(user.name):
        return "Comments limit reached", 501

    _insert_comment(id, user.name, comment["text"])

    return "Comment successfully created", 201

@app.route('/api/V1.0/advert/<int:id>/add_like', methods=["POST"])
@requires_login
def add_like(id):
    user = User(request.headers.get('Authorization'))

    if _is_reached_limit_like(user.name):
        return "Likes limit reached", 501

    _insert_like(id, user.name)

    return "Like successfully created", 201

@app.route('/api/V1.0/user/add', methods=["POST"])
def add_user():
    user = request.get_json()

    uv = UserValidator(user, redis)
    uv.validate()

    if uv.errors:
        return jsonify({'errors' : uv.errors}), 400

    _insert_user(user["username"], user["password"])

    return "Users successfully created", 201



if __name__ == '__main__':
    app.run(debug=True)