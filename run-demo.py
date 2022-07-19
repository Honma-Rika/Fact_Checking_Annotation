import json
import numpy as np
from flask import Flask, render_template, redirect, request, jsonify, make_response, flash, url_for

from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         current_user, login_required, fresh_login_required)
import copy

from pyserini.search import SimpleSearcher

app = Flask(__name__)
debug = True

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Unauthorized User'
login_manager.login_message_category = "info"

users = [
    {'username': 'LXY', 'password': '123456', 'count': 0, 'work_range': [0, 2000]},
    {'username': 'PLM', 'password': '123456', 'count': 0, 'work_range': [2000, 4000]}
]

###############################################
DATA_PATH = './data/input_raw.json'
DATA_DESTINATION = './data/outputs_raw.json'
CORPUS_PATH = '/mnt/edward/data/liangming/Implicit_Reasoning_FV/data_processing/StrategyQA/corpus/wiki36M/wiki36M_index'
###############################################

WORK_LOAD = {user['username']: user['work_range'] for user in users}

# load the pyserini searcher
print('Loading the pyserini searcher...')
searcher = SimpleSearcher(CORPUS_PATH)

def get_document(doc_id):
    doc = searcher.doc(doc_id)
    sample = json.loads(doc.raw())
    text = sample['contents'].strip()
    return text

# load dataset and initilize the annotation status
print('Loading the dataset... (without annotations)')
with open(DATA_PATH, 'r') as f:
    dataset = json.load(f)

dataset_lookup = {}
status_lookup = {}
for sample in dataset:
    ID = sample['uid']
    if ID not in dataset_lookup:
        dataset_lookup[ID] = sample
        dataset_lookup[ID]['status'] = 0
        dataset_lookup[ID]['evidence_paragraphs'] = []
    status_lookup[ID] = False

# Each user will have its own copy of the whole dataset
ALL_DATA = {}
for user in users:
    username = user['username']
    ALL_DATA[username] = copy.deepcopy(dataset_lookup)

# This checks whether a whole data sample is finished
# 0: not finished
# 1: finished
STATUS = {}
for user in users:
    username = user['username']
    STATUS[username] = copy.deepcopy(status_lookup)

def query_user(username):
    for user in users:
        if user['username'] == username:
            return user

def update_count(username):
    for i, u in enumerate(users):
        if u['username'] == username:
            users[i]['count'] += 1
            break

# loading existing annotations
print('Loading annotations from the result files...')
with open(DATA_DESTINATION, 'r') as f:
    dataset_ = [json.loads(line) for line in f]

for d in dataset_:
    ALL_DATA[d['user']][d['uid']]['status'] = 1
    ALL_DATA[d['user']][d['uid']]['evidence_paragraphs'] = d['evidence_paragraphs']
    update_count(d['user'])
    STATUS[d['user']][d['uid']] = True

print("All data are loaded into memory")

class User(UserMixin):
    pass

def query_user(username):
    for user in users:
        if user['username'] == username:
            return user

def update_count(username):
    for i, u in enumerate(users):
        if u['username'] == username:
            users[i]['count'] += 1
            break

@login_manager.user_loader
def load_user(username):
    if query_user(username) is not None:
        curr_user = User()
        curr_user.id = username
        return curr_user

@login_manager.unauthorized_handler
def unauthorized_handler():
    return redirect(url_for('login'))


@app.errorhandler(401)
def custom_401(error):
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return redirect(url_for('home'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        user = query_user(username)
        if user is not None and request.form['password'] == user['password']:
            curr_user = User()
            curr_user.id = username
            login_user(curr_user, remember=True)
            return redirect(url_for('index'))

        flash('Wrong username or password!')
    return render_template('login.html')


@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return render_template('login.html')

app.secret_key = '1234567'

def get_fresh_data(user):
    work_range = WORK_LOAD[user]
    for index, item in enumerate(STATUS[user].items()):
        ID, status = item
        if status == False and index >= work_range[0] and index < work_range[1]:
            return ID
    return -1

@app.route('/home')
@fresh_login_required
def home():
    cur_user = current_user.get_id()
    ID = get_fresh_data(cur_user)

    # if finished
    if ID == -1:
        logout_user()
        return render_template('login.html')

    # render this sample to frontend
    sample = ALL_DATA[cur_user][ID]
    sample['user'] = cur_user
    documents = []
    for doc_id in sample['candiadte_evidence']:
        documents.append({'id': doc_id, 'title': doc_id, 'passage': get_document(doc_id)})
    
    return render_template('index.html', sample=sample, documents = documents, count=query_user(cur_user)['count'])

@app.route('/<sample>', methods=['POST'])
def submit(sample):
    user, uid = sample.split('\t')
    uid = int(uid)
    example = ALL_DATA[user][uid]
    ID = example['id']
    claim = example['claim']
    doc_ids = example['candiadte_evidence']
    annotations = []
    for doc_id in doc_ids:
        ann_evidence = request.form[doc_id].strip()
        if not ann_evidence == "":
            annotations.append((doc_id, request.form[doc_id]))

    # Update the state in memory
    ALL_DATA[user][uid]['status'] = 1
    ALL_DATA[user][uid]['evidence_paragraphs'] = annotations
    update_count(user)

    print('Data labeled: {}\t{}\t{}\t{}'.format(
        user, uid, ID, ALL_DATA[user][uid]['evidence_paragraphs']))

    # Update status
    STATUS[user][uid] = True

    # Write to output file
    with open(DATA_DESTINATION, 'a+') as filed:
        evidence_paragraphs = ALL_DATA[user][uid]['evidence_paragraphs']
        data_sample = {'user': user, 
                       'id': ID, 'uid': uid, 'claim': claim, 
                       'evidence_paragraphs': evidence_paragraphs}
        filed.write(json.dumps(data_sample, ensure_ascii=False) + '\n')

    print('Writing data to file...')
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=2020, threaded=True, debug= True)







