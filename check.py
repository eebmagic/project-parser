import json
from DBInterface import functionsCollection

col = functionsCollection
print(col.count())
results = col.get(include=['documents', 'metadatas', 'embeddings'])
# ids = results['ids']
# docs = results['documents']
# metas = results['metadatas']
# embeds = results['embeddings']

for key, val in results.items():
    if type(val) == list:
        print(key, len(val))
    else:
        print(key, val)


print('\n' + '='*80)
print('QUERY RESULTS:')

results = col.query(
    query_texts="this is a test",
    include=['metadatas'],
    n_results=10
)
print(results)
ids = results['ids'][0]
metas = results['metadatas'][0]
for idx, meta in zip(ids, metas):
    print(idx)
    # print(json.dumps(meta, indent=2))
    print(meta['file_path'])
    print()