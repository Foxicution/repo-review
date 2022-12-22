use git2::{Repository, Tree, Commit, };
use std::fs;
use std::path::Path;
use std::str::FromStr;
use serde::Deserialize;

#[derive(Deserialize)]
struct File {
    name: String,
    content: String,
}

// TODO: Learn about Rusts error handling and why expect/unwrap is bad to use
fn get_repository(url: &str) -> Result<Repository, git2::Error> {
    let path = format!(
        "repos/{}",
        url.split('/').last().expect("Not a valid repository link!")
    );
    let path = Path::new(&path);
    match path.exists() {
        true => Repository::open(path),
        false => {
            fs::create_dir_all(path).expect("Can't create a local repository directory!");
            Repository::clone(url, path)
        }
    }
}

fn repository(path: &str) -> Result<Repository, git2::Error> {
    match path.contains("github.com") {
        true => get_repository(path),
        false => Repository::open(path),
    }
}

fn _expand_tree(repo: &Repository, tree: &git2::Tree) {
    for entry in tree.iter() {
        match entry.kind() {
            Some(git2::ObjectType::Blob) => {
                let blob = repo.find_blob(entry.id()).unwrap();
                println!("{:?}", blob.size())
            }
            Some(git2::ObjectType::Tree) => {
                let subtree = repo.find_tree(entry.id()).unwrap();
                _expand_tree(repo, &subtree);
            }
            _ => {}
        }
    }
}

fn main() {
    let repo = repository("https://github.com/kachayev/fn.py").unwrap();
    let tree = repo.head().unwrap().peel_to_tree().unwrap();
    _expand_tree(&repo, &tree);
    // for entry in tree.iter() {
    //     match entry.kind() {
    //         Some(git2::ObjectType::Blob) => entry.name().unwrap(),
    //         Some(git2::ObjectType::Tree) => entry.into(),
    //         _ => {}
    //     }
    //     println!("{}", entry.name().unwrap())
    // }
    // Open the repository located at the given path
    let repo = match Repository::open("repos/fn.py") {
        Ok(repo) => repo,
        Err(e) => panic!("failed to open repository: {}", e),
    };

    // Get the head commit
    let head = match repo.head() {
        Ok(reference) => reference,
        Err(e) => panic!("failed to get head reference: {}", e),
    };

    let mut commit = match head.peel_to_commit() {
        Ok(commit) => commit,
        Err(e) => panic!("failed to get commit: {}", e),
    };

    // Walk through the commit history and print the commit messages and trees
    loop {
        println!("Commit: {}", commit.summary().unwrap());

        // Get the tree for the commit
        let tree = match commit.tree() {
            Ok(tree) => tree,
            Err(e) => panic!("failed to get tree for commit: {}", e),
        };

        println!("Tree: {}", tree.id());

        // Get the parent of the current commit
        let parent = match commit.parent(0) {
            Ok(parent) => parent,
            Err(_) => break,
        };

        commit = parent;
    }
}
