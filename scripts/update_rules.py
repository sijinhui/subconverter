import argparse
import configparser
import glob
import logging
import os
import re
import shutil
import stat
import urllib.request
import pathlib
import tempfile
from git import InvalidGitRepositoryError, Repo, GitCommandError


def del_rw(action, name: str, exc):
    os.chmod(name, stat.S_IWRITE)
    os.remove(name)


def open_repo(path: str):
    if not os.path.exists(path):
        return None
    try:
        return Repo(path)
    except InvalidGitRepositoryError:
        return None


def update_rules(repo_path: str, save_path: str, matches: list[str], keep_tree: bool):
    os.makedirs(save_path, exist_ok=True)
    for pattern in matches:
        files = glob.glob(os.path.join(repo_path, pattern), recursive=True)
        if len(files) == 0:
            logging.warn(f"no files found for pattern {pattern}")
            continue
        for file in files:
            if os.path.isdir(file):
                continue
            file_rel_path, file_name = os.path.split(os.path.relpath(file, repo_path))
            if keep_tree:
                file_dest_dir = os.path.join(save_path, file_rel_path)
                os.makedirs(file_dest_dir, exist_ok=True)
                file_dest_path = os.path.join(file_dest_dir, file_name)
            else:
                file_dest_path = os.path.join(save_path, file_name)
            shutil.copy2(file, file_dest_path)
            logging.info(f"copied {file} to {file_dest_path}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default="rules_config.conf")
    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read(args.config)
    logging.basicConfig(format="%(asctime)s %(message)s", level=logging.DEBUG)

    with tempfile.TemporaryDirectory() as tmpdir:
        print("临时目录路径:", tmpdir)

        for section in config.sections():
            repo = config.get(section, "name", fallback=section)
            url = config.get(section, "url")
            commit = config.get(section, "commit", fallback=None)
            branch = config.get(section, "branch", fallback=None)
            matches = config.get(section, "match").split("|")
            save_path = config.get(section, "dest", fallback=f"base/rules/{repo}")
            keep_tree = config.getboolean(section, "keep_tree", fallback=True)

            logging.info(f"reading files from url {url}, matches {matches}, save to {save_path} keep_tree {keep_tree}")

            repo_path = os.path.join(tmpdir, "repo", repo)

            only_download_url = False
            if url.endswith('.txt'):
                only_download_url = True
            r = open_repo(repo_path)
            if r is None:
                logging.info(f"cloning repo {url} to {repo_path}")
                if only_download_url:
                    os.makedirs(repo_path, exist_ok=True)
                    urllib.request.urlretrieve(url, os.path.join(repo_path, os.path.basename(url)))
                else:
                    r = Repo.clone_from(url, repo_path, depth=1)
            else:
                logging.info(f"repo {repo_path} exists")

            try:
                # 2. 获取远程默认分支
                default_remote_branch = r.git.symbolic_ref("refs/remotes/origin/HEAD").split("/")[-1]
                logging.info(f"远程默认分支: {default_remote_branch}")
            except GitCommandError:
                # 如果远程没有默认分支（极少见）
                default_remote_branch = None
                logging.error("无法获取远程默认分支")

            try:
                if only_download_url:
                    logging.info(f"only download url, skip update")
                elif commit is not None:
                    logging.info(f"checking out to commit {commit}")
                    r.git.checkout(commit)
                elif branch is not None:
                    if default_remote_branch == branch:
                        logging.info(f"checking out to branch {branch}")
                        r.git.checkout(branch)
                    else:
                        print(f"默认分支不是 {branch}，手动 fetch 并切换分支")
                        r.git.fetch("origin", f"+refs/heads/{branch}:refs/remotes/origin/{branch}", "--depth=1")
                        r.git.checkout('-b', branch, f'origin/{branch}')

                else:
                    logging.info(f"checking out to default branch")
                    r.active_branch.checkout()
            except Exception as e:
                logging.error(f"checkout failed {e}")
                continue

            update_rules(repo_path, save_path, matches, keep_tree)

    # shutil.rmtree("./tmp", ignore_errors=True)


def is_binary_file(file_path):
    """检查文件是否为二进制文件"""
    try:
        # 读取文件前1024字节，检测空字符
        with file_path.open('rb') as f:
            return b'\x00' in f.read(1024)
    except IOError:
        return True
def find_matching_lines(root_dir, search_text):
    root_path = pathlib.Path(root_dir)
    not_comment_pattern = re.compile(r'^\s*#')  # 匹配注释行的正则表达式
    results = []
    comment_pattern = re.compile(r'%s[^,"]+' % search_text)

    for file_path in root_path.rglob('*'):
        if file_path.is_file() and not is_binary_file(file_path):
            try:
                with file_path.open('r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.rstrip('\n')
                        # 检查是否包含目标文本（不区分大小写）且不是注释行
                        if (search_text.lower() in line.lower() and
                            not not_comment_pattern.match(line)):
                            r = re.findall(comment_pattern, line)
                            results.extend(r)
            except (UnicodeDecodeError, IOError):
                continue
    return results

def remove_empty_directories(path):
    path = pathlib.Path(path)
    # 从底向上遍历，确保子目录先被处理
    for child in sorted(path.rglob('*'), key=lambda x: len(x.parts), reverse=True):
        if child.is_dir() and not any(child.iterdir()):
            child.rmdir()
            print(f"删除空文件夹: {child}")

def clean_not_used_rules():

    try:
        used_rules = (find_matching_lines('base/snippets', 'rules/'))
        for file in pathlib.Path('base/rules').rglob('*'):
            if file.is_file() and str(file.relative_to('base').as_posix()) not in used_rules:
                file.unlink()
        remove_empty_directories('base/rules')
    except Exception as e:
        logging.error(f"clean_not_used_rules failed {e}")


if __name__ == "__main__":
    main()
    clean_not_used_rules()
