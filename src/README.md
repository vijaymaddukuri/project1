# Git submodule:

Git submodule enables us to add a Git repository as a subdirectory (sub-folder) of another Git repository at a specific
path. This subdirectory still contains its own Git system, which means you can set the subdirectory to a specific commit
with which you want to work with.

A file ‘.gitmodules’ is created in the parent directory which keeps track of the all the submodules configuration.
This file maps the Project’s repository Url and the local subdirectory. Multiple entries will be recorded for multiple
submodules.


## Adding git submodule into our repo:

git submodule add https://github.com/user/submodule submodule-dir

## When files are updated in sub module, how to get those changes into parent repo:

 git submodule update --remote


## Now whenever you execute git update, it will execute a git pull and a git submodule update --init --recursive,
thus updating all the code in your project.

git config --global alias.update '!git pull && git submodule update --init --recursive'

## How to update/add the file in submodule from parent repo

when we create ‘AnotherSampleFile’ in a Submodule folder, it isn’t tracked by the MainModule repository.
MainModule repository does recognise that there is a modified content in the Submodule directory,
but it is unable to track or commit the changes. Once we change your current working directory into a Submodule1 folder,
we’ll be able to track and commit it using a Submodule repository

## Edit the Submodule Branch:

git config --file=.gitmodules submodule.Submod.branch development

## Edit the Submodule URL

git config --file=.gitmodules submodule.Submod.url https://github.com/username/ABC.git

## Sync and update the Submodule

$  git submodule sync
$  git submodule update --init --recursive --remote

## Commit the file in submodule from parent dir:

git submodule foreach git pull origin master

## Delete a submodule from a repository
### Remove submodule from parent repo:

git submodule deinit -f — mymodule

rm -rf .git/modules/mymodule

git rm -f mymodule 