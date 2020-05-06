import os
import subprocess

def git(git_args, repo_dir):
    """Execute a git command with |git_args| for the repo located in
    |repo_dir|."""
    command = ['git', '-C', repo_dir] + git_args
    return subprocess.run(command)


def fetch_unshallow(repo_dir):
    """Gets the history of |repo_dir|."""
    shallow_file = os.path.join(repo_dir, '.git', 'shallow')
    if os.path.exists(shallow_file):
      git(['fetch', '--unshallow'], repo_dir)


def checkout_repo_commit(commit, repo_dir):
    """Checkout |commit| in |repo_dir|."""
    fetch_unshallow(repo_dir)
    # TODO(metzman): Figure out if we need to run clean.
    git(['checkout', '-f', commit], repo_dir)



def main():
    # TODO(metzman): Infer repo_path to make integration of these benchamrks
    # easier.
    repo_dir = os.getenv('CHECKOUT_COMMIT_REPO_PATH')
    commit = os.getenv('CHECKOUT_COMMIT')
    if not commit or not repo_dir:
        print('Not checking out commit.')
        return 0
    checkout_repo_commit(commit, repo_dir)
    return 0


if __name__ == '__main__':
    main()
