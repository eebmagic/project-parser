import os
import tiktoken

enc = tiktoken.get_encoding("cl100k_base")


def getProjects():
    return [f"projects/{f}" for f in os.listdir('projects') if os.path.isdir(os.path.join('projects', f))]


def getFiles(project, contents=True):
    cmd = f"cd {project} && git ls-files"
    projFiles = os.popen(cmd).readlines()
    projFilePaths = [x.strip() for x in projFiles]

    if not contents:
        return projFilePaths

    fileContents = {}
    for path in projFilePaths:
        try:
            with open(f"{project}/{path}") as f:
                fileContents[path] = f.read()
        except UnicodeDecodeError:
            fileContents[path] = None

    return fileContents


def getTokenCount(text):
    return len(enc.encode(text))


def chunkByTokens(text, chunkSize=1_000, overlap=100):
    tokens = enc.encode(text)
    chunks = []
    for i in range(0, len(tokens), chunkSize - overlap):
        chunk = tokens[i:i + chunkSize]
        chunks.append(enc.decode(chunk))
    return chunks



if __name__ == '__main__':
    for project in getProjects():
        contents = getFiles(project)
        print(len(contents))
        print(type(contents))

        break
