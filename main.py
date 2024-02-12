from tree_sitter import Language, Parser
import os
import json

from DBInterface import SafeInterface, functionsCollection

# MAX_CHUNK_SIZE = 20_000
MAX_CHUNK_SIZE = 8_192
print(f"{MAX_CHUNK_SIZE = }")
interface = SafeInterface(
    functionsCollection,
    charCap=MAX_CHUNK_SIZE,
    threaded=False,
    timeDelay=0.3,
)


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
        print(f"FAILED TO FIND NAME NODE FOR: {node}")

    funcDef = fullBytes[node.start_byte:node.end_byte].decode('utf-8')

    return name, funcDef

MAX_FULL_FILE_LEN = 1_000

projects = os.listdir('projects')
print(projects)

items_to_add = []
docs = []
func_types_processed = []

for projName in projects:
    maxlens = {}
    projPath = f"projects/{projName}"

    for root, dirs, files in os.walk(projPath):
        if '/.' not in root: # ignore hidden files/dirs

            for file in files:
                if file.startswith('.'):
                    continue

                fullpath = f"{root}/{file}"
                ftype = file.split('.')[-1]
                try:
                    with open(fullpath) as f:
                        contentText = f.read()

                    with open(fullpath, 'rb') as f:
                        contentBytes = f.read()

                    maxlens[ftype] = max(len(contentText), maxlens.get(ftype, 0))

                    # Parse longer files for to just get functions
                    # if ftype == 'py' and len(contentText) > MAX_FULL_FILE_LEN:
                    if (ftype in PARSERS) and (len(contentText) > MAX_FULL_FILE_LEN):
                        justFilePath = fullpath[len(projPath)+1:]
                        parser = Parser()
                        parser.set_language(PARSERS[ftype])

                        tree = parser.parse(contentBytes)
                        funcs = get_funcs(tree, contentText, fullpath)

                        # print(f"Working in file: {justFilePath}")
                        # print(f"Built tree: {tree}")
                        # print(f"Found funcs: {funcs}")

                        for node in funcs:
                            # funcName, funcText = extract(node, contentText)
                            funcName, funcText = extract(node, contentBytes)
                            # print(node)
                            # print(funcName)
                            # print(funcText)
                            # print()

                            item_object = {
                                'type': 'function',
                                'project': projName,
                                'file_path': fullpath,
                                'function_name': funcName,
                                'text': funcText,
                                'id': f"{fullpath}:{funcName}"
                            }
                            items_to_add.append(item_object)
                            docs.append(funcText)
                            func_types_processed.append(ftype)
                    elif contentText:
                        # Add full text for short files
                        item_object = {
                            'type': 'file',
                            'project': projName,
                            'file_path': fullpath,
                            'function_name': '',
                            'text': contentText,
                            'id': fullpath
                        }
                        items_to_add.append(item_object)
                        docs.append(contentText)

                except UnicodeDecodeError:
                    # print(f"skipping because of decode error on : {fullpath}")
                    pass

    # break

print(f"Found {len(items_to_add):,} total items")
print(f"Have functions in all of these file types:\n\t", end='')
print('\n\t'.join(set(func_types_processed)))

# print(f"Found these node types:")
# for nodeType, count in sorted(typeCounts.items(), key=lambda x: x[1], reverse=False):
#     print(f"{count:>5} {nodeType:>20}")


print(f"\nADDING TO INTERFACE:")
ids = [item['id'] for item in items_to_add]
docs = [item['text'] for item in items_to_add]
metas = []
for item in items_to_add:
    result = {}
    for key, value in item.items():
        if key not in ['text', 'id']:
            result[key] = value
    metas.append(result)
doclens = [len(d) for d in docs]
print(min(doclens), max(doclens))

# for idx, meta in zip(ids, metas):
#     print(idx)
#     print(meta['file_path'])
#     print()


print(len(ids))
print(len(set(ids)))
print(f"ANY DUPLICATED?: {len(ids) != len(set(ids))}")

for i, idx in enumerate(ids):
    for j, jdx in enumerate(ids):
        if i < j and idx == jdx:
            print(idx)


interface.add(
    ids=ids,
    documents=docs,
    metadatas=metas
    # metadatas=items_to_add
)
