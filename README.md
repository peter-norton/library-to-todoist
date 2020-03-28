# library-to-todoist

## Usage

Rename `.env.example` to `.env` and fill in your personal library and Todoist credentials

In Todoist, create a dedicated project for library books and three labels called something like 'renewed_1_time', 'renewed_2_times', and 'renewed_3_times'. Then via the API get the IDs for all of those and add them to the `.env` file.

The LibraryScraper class will obviously have to be customized for your library's site layout, my library uses the PrairieCat Catalog software.

### Install necessary packages

```
$ pip install -r requirements.txt
```

### Run locally

```
$ python main.py
```

## AWS

I have my script running hourly on AWS Lambda. In order to upload to AWS, `main.py` must be zipped with the necessary dependencies, and your environment variables can be added manually to the AWS console.

### Example of packaging for upload to AWS

```
$ cd venv/lib/python3.7/site-packages
$ zip -r9 ../../../../aws_lambda_function.zip *
$ zip -u ../../../../aws_lambda_function.zip ../../../../main.py
```
