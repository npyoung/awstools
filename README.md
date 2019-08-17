AWS Tools
============
## What is AWS Tools?

AWS Tools is a lightweight wrapper that provides short and memorable commands for some of the most commonly-used, but verbose parts of the AWS CLI, and adds convenient logic to the basic AWS CLI commands as needed. It also provides shortcuts to some useful SSH commands for communicating with EC2 instances.

The biggest feature is that EC2 instances are all referenced by their Name tag rather than by ID. If you are diligent about naming your instances, this can make for very short and intuitive commands, e.g.

```bash
awstools start my-analysis-box
awstools forward my-analysis-box 8888 # Forward port 8888 to your remote instance
```

This was mostly for my personal use, but several of my colleagues found it useful so I'm making it publicly available and hope to develop it further and provide some support.

## Motivation
The goal of this project is to reduce friction for non-developers wanting to take advantage of AWS for data science and related fields.

I work in a science / data science setting where I and most of my co-workers would consider themselves computationally-fluent, but not software developers. As the pace of data collection increases, there's a desire to take advantage of cloud-based resources, but many balk at the extra steps required to do so. Even a few long commands that have to be memorized or clicks in a web interface that have to be done every time you want to log into your instance can make sitting down at a local machine and instantly being able to run and edit scripts seem more attractive. But with a tad of automation, we can convert repetitive tasks into plain-language commands.

## Compatibility and requirements

Should work on Windows, Mac, and Linux. Requires Python 3 (for use of boto3).

## Installation

Install from source:

```bash
git clone https://github.com/npyoung/awstools.git
cd awstools
pip install .
```

## You might also like

- [SAWS](https://github.com/donnemartin/saws) provides shortcuts and autocompletion for the AWS CLI, but adds no additional logic and is run through its own sub-shell.
