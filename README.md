# library-to-todoist

## Usage

Rename `.env.example` to `.env` and fill in your personal library and Todoist credentials

In Todoist, create a dedicated project for library books and three labels called something like 'renewed_1_time', 'renewed_2_times', and 'renewed_3_times'. Then via the API get the IDs for all of those and add them to the `.env` file.

### Install necessary packages

```
$ pip install -r requirements.txt
```

### Run locally

```
$ python main.py
```

## AWS

### Example of packaging for upload to AWS

```
$ cd venv/lib/python3.7/site-packages
$ zip -r9 ../../../../aws_lambda_function.zip *
$ zip -u ../../../../aws_lambda_function.zip ../../../../main.py
```
