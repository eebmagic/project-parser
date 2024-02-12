import os


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



if __name__ == '__main__':
    for project in getProjects():
        contents = getFiles(project)
        print(len(contents))
        print(type(contents))

        break
