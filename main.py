from tree_sitter import Language, Parser
import json
from hashlib import sha256
from tqdm import tqdm
import chromadb

from helpers import getProjects, getFiles, getTokenCount, chunkByTokens
from customEmbedding import CodetEmbedding

# MAX_CHUNK_SIZE = 20_000
MAX_CHUNK_SIZE = 8_192
MAX_TOKEN_COUNT = 6_000
VERBOSE = False

# TODO: Change these two sections to process what is in vendors dir
Language.build_library(
    'build/my-languages.so',
    [
        'vendor/tree-sitter-python',
        'vendor/tree-sitter-go',
        'vendor/tree-sitter-javascript',
        'vendor/tree-sitter-html',
        'vendor/tree-sitter-css',
        'vendor/tree-sitter-json',
        'vendor/tree-sitter-bash',
        'vendor/tree-sitter-c',
        'vendor/tree-sitter-cpp',
        'vendor/tree-sitter-rust',
    ]
)

PARSERS = {
    'py': Language('build/my-languages.so', 'python'),
    'pyi': Language('build/my-languages.so', 'python'),
    'go': Language('build/my-languages.so', 'go'),
    'js': Language('build/my-languages.so', 'javascript'),
    'css': Language('build/my-languages.so', 'css'),
    'html': Language('build/my-languages.so', 'html'),
    'json': Language('build/my-languages.so', 'json'),
    'sh': Language('build/my-languages.so', 'bash'),
    'c': Language('build/my-languages.so', 'c'),
    'cpp': Language('build/my-languages.so', 'cpp'),
    'rs': Language('build/my-languages.so', 'rust'),
}


typeCounts = {}
typeInstances = {}

def get_funcs(tree, filename='', verbose=False):
    # TODO: Change this to get classes, THEN funcs outside classes
    node = tree.root_node
    keepers = [
        'function_definition',
        'class_definition',
        'function_item'
    ]

    q = [node]
    funcs = []

    while q:
        curr = q.pop()
        typeCounts[curr.type] = typeCounts.get(curr.type, 0) + 1
        if 'class' in curr.type:
            typeInstances[curr.type] = typeInstances.get(curr.type, []) + [(curr, filename)]

        if curr.type in keepers:
            funcs.append(curr)
            continue

        for child in curr.children:
            q.append(child)

    return funcs


def extract(node, fullBytes):
    # TODO: Modify this to also try to get preceding comments for documentation
    name_node = None
    for child in node.children:
        if child.type in ['identifier', 'word']:
            name_node = child
            break

    if name_node:
        name = fullBytes[name_node.start_byte:name_node.end_byte].decode('utf-8')
    else:
        name = ''
        # print(f"FAILED TO FIND NAME NODE FOR: {node}")

    funcDef = fullBytes[node.start_byte:node.end_byte].decode('utf-8')

    return name, funcDef

MAX_FULL_FILE_LEN = 1_000

projects = getProjects()
print(projects)

items_to_add = []
docs = []
file_types_processed = []

print(f"Found {len(projects)} total projects")

for projPath in projects:
    print(f"PROJ: {projPath}")
    print(f"Found {len(getFiles(projPath))} items in the project dir")
    processed = set()
    for fpath, contentText in tqdm(getFiles(projPath).items()):

        if fpath in processed:
            print(f"ALREADY PROCESSED: {fpath}")
            quit()
        processed.add(fpath)


        fname = fpath.split('/')[-1]
        if fname.startswith('.'):
            continue
        ftype = fname.split('.')[-1]
        file_types_processed.append(ftype)

        try:
            # Parse longer files for to just get functions
            if (ftype in PARSERS) and (len(contentText) > MAX_FULL_FILE_LEN):
                parser = Parser()
                parser.set_language(PARSERS[ftype])

                tree = parser.parse(contentText.encode('utf-8'))
                funcs = get_funcs(tree, fpath)

                for node in funcs:
                    funcName, funcText = extract(node, contentText.encode('utf-8'))
                    tokenCount = getTokenCount(funcText)
                    if tokenCount < MAX_TOKEN_COUNT:
                        item_object = {
                            'type': 'function',
                            'node_type': node.type,
                            'is_chunked': False,
                            'project': projPath,
                            'file_path': fpath,
                            'file_type': ftype,
                            'function_name': funcName,
                            'text': funcText,
                            'id': f"{fpath}:{funcName}",
                            'unique_id': sha256((str(node.start_point) + funcText + fpath + projPath).encode('utf-8')).hexdigest(),
                            'token_count': getTokenCount(funcText)
                        }
                        items_to_add.append(item_object)
                        docs.append(funcText)
                    else:
                        chunks = chunkByTokens(funcText)
                        for i, chunkText in enumerate(chunks):
                            item_object = {
                                'type': 'function',
                                'node_type': node.type,
                                'is_chunked': True,
                                'project': projPath,
                                'file_path': fpath,
                                'file_type': ftype,
                                'function_name': funcName,
                                'text': chunkText,
                                'id': f"{fpath}:{funcName}_({i+1}/{len(chunks)})",
                                'unique_id': sha256((str(node.start_point) + chunkText + fpath + projPath).encode('utf-8')).hexdigest(),
                                'token_count': getTokenCount(chunkText)
                            }
                            items_to_add.append(item_object)
                            docs.append(chunkText)

            elif contentText and (len(contentText) < MAX_FULL_FILE_LEN):
                # Add full text for short files
                item_object = {
                    'type': 'file',
                    'node_type': 'plaintext',
                    'is_chunked': False,
                    'project': projPath,
                    'file_path': fpath,
                    'file_type': ftype,
                    'function_name': '',
                    'text': contentText,
                    'id': fpath,
                    'unique_id': sha256((contentText + fpath + projPath).encode('utf-8')).hexdigest(),
                    'tokenCount': getTokenCount(contentText)
                }
                items_to_add.append(item_object)
                docs.append(contentText)

        except UnicodeDecodeError:
            # print(f"skipping because of decode error on : {fullpath}")
            pass


if VERBOSE:
    print(f"\nFound {len(items_to_add):,} total items")
    print(f"Processed sources from all of these file types:\n\t", end='')
    print('\n\t'.join(sorted(list(set(file_types_processed)))))


ids = [item['unique_id'] for item in items_to_add]
docs = [item['text'] for item in items_to_add]
metas = []
metaMapping = {}
for item in items_to_add:
    meta = {}
    for key, value in item.items():
        if key not in ['text']:
            meta[key] = value
    
    metas.append(meta)
    metaMapping[item['unique_id']] = metaMapping.get(item['unique_id'], []) + [meta]
        

print(f"\nFound {len(ids):,} total items to index")
anyDuplicated = len(ids) != len(set(ids))
print(f"ANY DUPLICATED?: {anyDuplicated}")

if anyDuplicated:
    counts = {}
    for idx in ids:
        counts[idx] = counts.get(idx, 0) + 1
    duplicated = list(filter(lambda x: x[1] > 1, counts.items()))

    print(f"There are {len(duplicated)} duplicated ids:\n")
    for idx, count in duplicated:
        print(idx)
        print(f"count: {count}")
        print(json.dumps(metaMapping[idx], indent=2))
        print()

    assert False, "There are duplicated ids"


if len(ids) == 0:
    print(f"No documents found to add.")
    quit()

# Add to collection
print(len(ids), len(docs), len(metas))

client = chromadb.PersistentClient(path='./db')
embedding_object = CodetEmbedding()

collection = client.get_or_create_collection(
    name='projects',
    embedding_function=embedding_object
)
print(f"Current collection count: {collection.count()}")

collection.add(
    ids=ids,
    documents=docs,
    metadatas=metas
)

print(f"NEW collection count: {collection.count()}")
