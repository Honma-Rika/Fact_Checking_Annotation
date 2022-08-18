import os

import copy

import json

from flask import Flask, render_template, redirect, request, jsonify, make_response, flash, url_for

from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         current_user, login_required, fresh_login_required)

app = Flask(__name__)
debug = True

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Unauthorized User'
login_manager.login_message_category = "info"

users = {
    'LXY': {'password': '123456', 'count': 0, 'work_range': [0, 15000]},
    'PLM': {'password': '123456', 'count': 0, 'work_range': [0, 15000]}
}

dataset_lookup = {}
ALL_DATA = {}
dataset = None
paragraphs = None

###############################################
DATA_PATH = './data/strategyqa_dataset/strategyqa_train.json'
DATA_DESTINATION = './data/strategyqa_dataset/strategyqa_output.json'
CORPUS_PATH = './data/strategyqa_dataset/strategyqa_train_paragraphs.json'
###############################################

# get raw text of the docs
def get_document(title):
    doc = paragraphs.get(title, None)
    title = doc['title'].strip()
    text = doc['content'].strip()
    return title, text

def query_user(username):
    return users.get(username)

def update_count(username):
    if users.get(username):
        users[username]['count'] += 1

# load dataset and initilize the annotation status
print('Loading the dataset... (without annotations)')
with open(DATA_PATH, 'r', encoding='utf-8') as f:
    dataset = json.load(f)

with open(CORPUS_PATH, 'r') as f:
    paragraphs = json.load(f)
    
temp_uid = 0
for sample in dataset[:5]:
    # set status and original text by uid
    candidate_evidence = set()
    for annotation in sample['evidence']:
        for decomposition_step in annotation:
            for item in decomposition_step:
                if isinstance(item, list):
                    for doc_id in item:
                        candidate_evidence.add(doc_id)

    for decomp in sample['decomposition']:
        dataset_lookup[temp_uid] = copy.deepcopy(sample)
        dataset_lookup[temp_uid]['uid'] = temp_uid
        dataset_lookup[temp_uid]['focus'] = decomp
        dataset_lookup[temp_uid]['evidence'] = list(candidate_evidence)
        dataset_lookup[temp_uid]['status'] = False
        dataset_lookup[temp_uid]['evidence_paragraphs'] = []

        temp_uid += 1

# Each user will have its own copy of the whole dataset
for user in users:
    ALL_DATA[user] = copy.deepcopy(dataset_lookup)

# loading existing annotations
print('Loading annotations from the result files...')
if not os.path.exists(DATA_DESTINATION):
    os.system(r'touch {}'.format(DATA_DESTINATION))

with open(DATA_DESTINATION, 'r', encoding='utf-8') as f:
    # mark the annotated items
    if f:
        for line in f:
            d = json.loads(line)
            ALL_DATA[d['user']][d['uid']]['status'] = True
            ALL_DATA[d['user']][d['uid']]['evidence_paragraphs'] = d['evidence_paragraphs']
            update_count(d['user'])

print("All data are loaded into memory")

##########################################################################
class User(UserMixin):
    pass

@login_manager.user_loader
def load_user(username):
    if query_user(username):
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
        if user and request.form['password'] == user['password']:
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


def get_fresh_data(user, previous_uid=0):
    work_range = users[user]['work_range']
    uid = previous_uid if previous_uid else work_range[0]
    user_item = ALL_DATA[user]

    while user_item[uid]['status'] and uid >= work_range[0] and uid < work_range[1]:
        uid += 1
    
    return uid if not user_item[uid]['status'] and uid >= work_range[0] \
        and uid < work_range[1] else -1
        

@app.route('/home')
@fresh_login_required
def home(previous_uid=0):
    cur_user = current_user.get_id()
    uid = get_fresh_data(cur_user, previous_uid)

    # if finished
    if uid == -1:
        print('All annotation tasks done')
        logout_user()
        return render_template('login.html')

    # render this sample to frontend
    sample = ALL_DATA[cur_user][uid]
    documents = []
    for doc_id in sample['evidence']:
        title, passage = get_document(doc_id)
        documents.append({'id': doc_id, 'title': title, 'passage': passage})
    
    return render_template('index.html', user=cur_user, uid=uid, sample=sample, documents=documents, count=query_user(cur_user)['count'])

@app.route('/<user>/<uid>/<sample>', methods=['POST'])
def submit(user, uid, sample):
    uid = int(uid)
    sample = eval(sample)
    qid = sample['qid']
    annotations = []
    for doc_id in sample['evidence']:
        ann_evidence = request.form.get(doc_id, '').strip()
        if ann_evidence:
            annotations.append((doc_id, ann_evidence))

    # Update the state in memory
    ALL_DATA[user][uid]['status'] = True
    ALL_DATA[user][uid]['evidence_paragraphs'] = annotations
    update_count(user)

    print('Data labeled: {}\t{}\t{}\t{}'.format(
        user, uid, qid, annotations))


    # Write to output file
    with open(DATA_DESTINATION, 'a+', encoding='utf-8') as filed:
        data_sample = {
                        'user': user, 'id': qid, 'uid': uid, 
                        'focus': sample['focus'], 
                        'evidence_paragraphs': annotations
                    }
        filed.write(json.dumps(data_sample, ensure_ascii=False) + '\n')
    
    print('Writing data to file...')

    return redirect(url_for('home', previous_uid=uid))

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=2022, threaded=True, debug=debug)