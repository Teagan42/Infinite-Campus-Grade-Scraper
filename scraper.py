#!/usr/bin/env python

import ConfigParser
import cookielib
import os
import sys
from datetime import date, timedelta, datetime
from optparse import OptionParser

import mechanize
from BeautifulSoup import BeautifulSoup

import utils

br = mechanize.Browser()
date = date.today()

APPDIR = os.path.dirname(sys.argv[0])
CONFIG_FILE_NAME = os.path.join(APPDIR, ".", "config.ini")

Config = ConfigParser.ConfigParser()
Config.read(CONFIG_FILE_NAME)

parser = OptionParser(description='Scrapes grades from an infinite campus website')
parser.add_option('-p', '--print', action='store_true', dest='print_results',
        help='prints the grade report to stdout')
parser.add_option('-e', '--email', action='store_true', dest='email',
        help='email the grade report to user')
parser.add_option('-w', '--weekly', action='store_true', dest='weekly',
        help='diffs using the grades from a week ago')
parser.add_option('-n', '--no-log', action='store_true', dest='nolog',
        help='does not log grades in grades database')
parser.add_option('-v', '--verbose', action='store_true', dest='verbose',
        help='outputs more information')
parser.add_option('-d', '--diff', action='store_true', dest='diff',
        help='only returns classes with grades that have changed')

(options, args) = parser.parse_args()

def setup():
    """general setup commands"""
    # Cookie Jar
    cj = cookielib.LWPCookieJar()
    br.set_cookiejar(cj)

    # Browser options
    br.set_handle_equiv(True)
    br.set_handle_redirect(True)
    br.set_handle_referer(True)
    br.set_handle_robots(False)

    # Follows refresh 0 but not hangs on refresh > 0
    br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)

    if options.verbose:
        br.set_debug_http(True)

    # User-Agent
    br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]


def get_base_url():
    """returns the site's base url, taken from the login page url"""
    return get_config('Authentication')['base_url']

def get_recent_assignment_grades():
    """parses the class page at the provided url and returns a course object for it"""
    page = br.open(get_base_url() + 'portal/portal.xsl?x=portal.PortalOutline&lang=en&personType=parent&context=1396126-4732-5104&personID=1396126&studentFirstName=Persia&lastName=Ibanez%20Glenn&firstName=Persia&schoolID=172&calendarID=4732&structureID=5104&calendarName=9432%20Dennison%20K-6%2018-19&mode=grades&x=portal.PortalGrades')
    soup = BeautifulSoup(page)
    tables = soup.findAll(name="table", attrs={'class':'portalTable'})
    grades = []
    for table in tables:
        for body in table.findAll(name="tbody"):
            for row in body.findAll(name="tr"):
                columns = row.findAll(name="td")
                dateAgo = columns[0].string
                dateUnit = columns[1].string
                if 'day' in dateUnit:
                    timestamp = datetime.today() - timedelta(days=int(dateAgo))
                elif 'week' in dateUnit:
                    timestamp = datetime.today() - timedelta(weeks=int(dateAgo))
                else:
                    timestamp = datetime.today()

                timestamp = timestamp.replace(minute=0, hour=0, second=0, microsecond=0)
                course = columns[2].string
                assignment = columns[3].find(name="a").string
                grade = columns[6].string.replace('%', '')
                grades.append({
                    'key': get_row_key(timestamp, course, assignment),
                    'date': timestamp,
                    'course': course,
                    'assignment': assignment,
                    'grade': grade
                })

    return grades

def get_row_key(date, course, assignment):
    return '{}-{}-{}'.format(date, course, assignment)

def login():
    """Logs in to the Infinite Campus at the
    address specified in the config
    """
    br.open(get_config('Authentication')['login_url'])
    br.select_form(nr=0) #select the first form
    br.form['username'] = get_config('Authentication')['username']
    br.form['password'] = get_config('Authentication')['password']
    br.submit()


def add_to_grades_database(grades):
    """Adds the class and grade combination to the database under
    the current date.
    """
    utils.add_to_csv('data.csv', grades)

def get_config(section):
    """returns a list of config options in the provided sections
    requires that config is initialized"""
    if not Config:
        return 'Config not found'
    dict1 = {}
    for opt in Config.options(section):
        try:
            dict1[opt] = Config.get(section, opt)
            if dict1[opt] == -1:
                print('skip: %s' % opt)
        except Exception:
            print('exception on %s!' % opt)
            dict1[opt] = None
    return dict1

def main():
    setup()
    login()
    grades = get_recent_assignment_grades()

    add_to_grades_database(grades)

if __name__ == '__main__':
    main()
