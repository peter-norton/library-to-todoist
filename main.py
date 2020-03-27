import json
import mechanize
from bs4 import BeautifulSoup
import urllib.request
import http.cookiejar
import sys
import os
from todoist.api import TodoistAPI
from datetime import datetime, date
from dotenv import load_dotenv, find_dotenv

class LibraryPage:
    def __init__(self, name, url_path, title_offset, status_offset, max_title_length, date_type):
        self.name = name
        self.url_path = url_path
        self.title_offset = title_offset
        self.status_offset = status_offset
        self.max_title_length = max_title_length
        self.date_type = date_type
        self.books = []

    def get_due_date(self, val):
        if self.date_type == 'due_cell':
            return datetime.strftime(datetime.strptime(val[1], '%m-%d-%y'), '%Y-%m-%d')
        elif self.date_type == 'today':
            return date.today()
        elif self.date_type == 'split_status':
            return datetime.strftime(datetime.strptime(val.split(' by ')[-1], '%m-%d-%y'), '%Y-%m-%d')

class LibraryScraper:
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.pages = {
            "checkouts": LibraryPage(
                name = "Checkout",
                url_path = "items",
                title_offset = 1,
                status_offset = None,
                max_title_length = 50,
                date_type = 'due_cell'
            ),
            "ill": LibraryPage(
                name = "ILL",
                url_path = "illreqs",
                title_offset = 0,
                status_offset = 2,
                max_title_length = 35,
                date_type = 'today'
            ),
            "holds": LibraryPage(
                name = "Hold",
                url_path = "holds",
                title_offset = 1,
                status_offset = 3,
                max_title_length = 35,
                date_type = 'split_status'
            ),
        }

    def init_browser(self):
        cj = http.cookiejar.CookieJar()
        self.browser = mechanize.Browser()
        self.browser.set_cookiejar(cj)
        self.browser.set_handle_robots(False)

    def login(self):
        print('--- opening library login page...')
        self.browser.open(self.base_url)
        self.browser.form = list(self.browser.forms())[0]
        self.browser["code"] = self.username
        self.browser["pin"] = self.password
        print('--- logging in...')
        self.browser.submit()

    def parse_page(self, page_type):
        page = self.pages[page_type]
        print('--- switching to library %s page...' % page.name)
        self.browser.open("%s/%s" % (self.base_url, page.url_path))
        soup = BeautifulSoup(self.browser.response().read(), features="html5lib")
        print('--- parsing %s page...' % page.name)
        table = soup.find(lambda tag: tag.name=='table')
        rows = table.findAll(lambda tag: tag.name=='tr')
        if not rows:
            print('--- no %s table found, exiting process.' % page.name)
            return page
        books = []
        for row in rows:
            cols = row.find_all('td')
            cols = [elem.text.strip() for elem in cols]
            vals = [val for val in cols]
            if len(vals) > 1:
                book_title = vals[page.title_offset].split(' / ')[0].strip() # get the book title and remove the author name (anything after the ' / ')
                if len(book_title) > page.max_title_length:
                    book_title = book_title[:page.max_title_length-4] + ' ...' # trim book title if necessary
                book_status = vals[page.status_offset] if page.status_offset is not None else 'CHECKED_OUT'
                book_date = None
                book_renewed = None
                if book_status == 'CHECKED_OUT':
                    due_cell = vals[4].split(' ')
                    book_date = page.get_due_date(due_cell)
                    book_renewed = int(due_cell[4]) if len(due_cell) >= 5 else None
                elif book_status == '':
                    book_status = 'PLACED'
                elif book_status.lower().startswith('ready'):
                    book_date = page.get_due_date(book_status)
                    book_status = 'READY'
                books.append({ 'title': book_title, 'date': book_date, 'status': book_status, 'renewed': book_renewed })
        print('--- %s books on %s...' % (len(books), page.name))
        for book in books:
            print('\t--- %s -- %s -- %s -- %s' % (book['status'], book['date'], book['renewed'], book['title']))
            page.books.append(book)
        return page

class TodoistClient:
    def __init__(self, token, project_id, label_ids):
        self.api = TodoistAPI(token)
        self.project_id = project_id
        self.label_ids = label_ids

    def sync(self):
        print('--- syncing with Todoist...')
        self.api.sync()

    def commit(self):
        print('--- committing changes to Todoist...')
        self.api.commit()

    def clear_project(self):
        print('--- removing all tasks from project...')
        tasks = [task for task in self.api.state['items'] if task.data['project_id'] == self.project_id and task.data.get('date_completed', None) is None]
        for task in tasks:
            if task.data['project_id'] == self.project_id: # double check that it is in the correct project
                task.delete() # CAREFUL!!!

    def add_items_to_project(self, page_name, page_items):
        print('--- adding %s books to project...' % page_name)
        for item in page_items:
            if page_name == 'Checkout':
                task_name = 'Return "%s"' % item['title']
            else:
                task_name = 'On %s (%s): "%s"' % (page_name, item['status'], item['title'])
            labels = [ self.label_ids[item['renewed']-1] ] if item['renewed'] is not None and item['renewed'] >= 1 and item['renewed'] <= 3 else []
            self.api.items.add(task_name, project_id=self.project_id, due={ 'date': item['date'] }, labels=labels)


def pull_from_library():
    LIB_BASE_URL = os.getenv("LIB_BASE_URL")
    LIB_USERNAME = os.getenv("LIB_USERNAME")
    LIB_PASSWORD = os.getenv("LIB_PASSWORD")
    scraper = LibraryScraper(LIB_BASE_URL, LIB_USERNAME, LIB_PASSWORD)
    scraper.init_browser()
    scraper.login()
    checkouts = scraper.parse_page('checkouts')
    ill = scraper.parse_page('ill')
    holds = scraper.parse_page('holds')
    print('--- pull from library complete...')
    return [ checkouts, ill, holds ]

def push_to_todoist(library_pages):
    TODOIST_TOKEN = os.getenv("TODOIST_TOKEN")
    TODOIST_PROJECT_ID = int(os.getenv("TODOIST_PROJECT_ID"))
    TODOIST_LABEL_1_ID = int(os.getenv("TODOIST_LABEL_1_ID"))
    TODOIST_LABEL_2_ID = int(os.getenv("TODOIST_LABEL_2_ID"))
    TODOIST_LABEL_3_ID = int(os.getenv("TODOIST_LABEL_3_ID"))
    TODOIST_LABEL_IDS = [TODOIST_LABEL_1_ID, TODOIST_LABEL_2_ID, TODOIST_LABEL_3_ID]
    todoist_client = TodoistClient(TODOIST_TOKEN, TODOIST_PROJECT_ID, TODOIST_LABEL_IDS)
    todoist_client.sync()
    todoist_client.clear_project()
    for page in library_pages:
        todoist_client.add_items_to_project(page.name, page.books)
    todoist_client.commit()
    print('--- push to Todoist complete...')

def lambda_handler(event, context):
    main()
    return {
        'statusCode': 200,
        'body': json.dumps('Succeeded!')
    }

def main():
    print('--- starting library_to_todoist...')
    pages = pull_from_library()
    push_to_todoist(pages)
    print('--- library_to_todoist finished.')

if __name__ == "__main__":
    load_dotenv(find_dotenv())
    main()
