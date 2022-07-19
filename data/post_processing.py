import json
from collections import defaultdict

'''
final format of our dataset
{
    id: 
    claim: 
    label: 
    decomposition: [
        {
            fact: 
            evidence: [['wiki_title', 'wiki_sent'], xxx]
        }
    ]
}
'''

def process_annotation(dataset, ann_file, save_path):

    with open(ann_file, 'r') as f:
        annotations = [json.loads(line) for line in f]
    
    num_valid_sample = 0
    ann_group_by_id = defaultdict(list)
    for ann in annotations:
        ann_group_by_id[ann['id']].append(ann)
    
    print(f'Number pf annotated sub-claims: {len(annotations)}')
    print(f'Number of annotated samples: {len(ann_group_by_id)}')

    valid_samples = []
    for id, samples in ann_group_by_id.items():
        is_valid = True
        for sample in samples:
            if len(sample['evidence_paragraphs']) == 0:
                is_valid = False
                break
        if is_valid == True:
            num_valid_sample += 1
            valid_samples.append({'id': id, 'evidence': samples})
    print(f'Number of valid annotated samples: {num_valid_sample}')

    final_dataset = []
    for sample in valid_samples:
        # finding corresponding samples in raw dataset
        for item in dataset:
            if item['id'].split(':::')[1].strip() == sample['id']:
                ID = item['id']
                claim = item['claim']
                label = item['label']
                decomposition = []
                for eve in sample['evidence']:
                    decomposition.append({'fact' : eve['claim'], 'evidence': eve['evidence_paragraphs']})
                output_sample = {
                    'id': ID, 
                    'claim': claim,
                    'label': label,
                    'question': item['question'],
                    'demoposition': decomposition
                }
                final_dataset.append(output_sample)
    print(f'Number of final data samples: {len(final_dataset)}')

    with open(save_path, 'w') as f:
        f.write(json.dumps(final_dataset, indent=2))

def process_raw_dataset(train_file, dev_file):
    with open(train_file, 'r') as f:
        train_dataset = json.load(f)
    with open(dev_file, 'r') as f:
        dev_dataset = json.load(f)
    for ind, sample in enumerate(train_dataset):
        train_dataset[ind]['split'] = 'train'
    for ind, sample in enumerate(dev_dataset):
        dev_dataset[ind]['split'] = 'dev'
    return train_dataset + dev_dataset

if __name__ == "__main__":
    dev_file = '/mnt/edward/data/liangming/Implicit_Reasoning_FV/data_processing/StrategyQA/data/dev.claims.revised.json'
    train_file = '/mnt/edward/data/liangming/Implicit_Reasoning_FV/data_processing/StrategyQA/data/train.claims.revised.json'
    raw_dataset = process_raw_dataset(train_file, dev_file)
    
    save_path = '/mnt/edward/data/liangming/Implicit_Reasoning_FV/data_processing/StrategyQA/data/evidence_linking_trail_new.json'
    process_annotation(raw_dataset, 'outputs_raw.json', save_path)