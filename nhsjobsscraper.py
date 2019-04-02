#!/usr/bin/env python

import scraperwiki
import requests
import urllib2
import lxml.html
import re

#The NHS jobs site
nhsurl = "https://www.jobs.nhs.uk"
# Allows you to browse jobs at https://www.jobs.nhs.uk/xi/browsejobs
# Gather employer id numbers by looping through browse by letter: https://www.jobs.nhs.uk/xi/employer_list/?action=search&sl=A&el=A
# Then generate employer id page: https://www.jobs.nhs.uk/xi/search_vacancy/?action=search&master_id=122553
nhstesturl = "https://www.jobs.nhs.uk/xi/search_vacancy/?action=search&master_id=122553&max_result=100"

#Define a function to create a letter page 
def scrapeletterpage(url):
    print("scraping"), url
    #Turn the page into an lxml object to scrape
    html = requests.get(url, verify=False)
    root = lxml.html.fromstring(html.content)
    #jbos are contained within a link within h3
    orglinks = root.cssselect("h3 a")
    for i in orglinks:
        orgname = i.text_content()
        orglink = i.attrib['href']
        orgid = orglink.split("id=")[1]
        print(orgname, orglink)
        orgjoburl = "https://www.jobs.nhs.uk/xi/search_vacancy/?action=search&master_id="+orgid+"&max_result=100"
        #Run next function, defined below
        scrape_listings(orgjoburl)

#Create a function to scrape a organisation's jobs results page
def scrape_listings(url):
    #Turn the page into an lxml object to scrape
    html = requests.get(url, verify=False)
    root = lxml.html.fromstring(html.content)
    #jbos are contained within a link within h2
    joblinks = root.cssselect("h2 a")
    print(len(joblinks))
    for job in joblinks:
        #These all have an arbitrary code in the middle which could be removed
        print(job.attrib['href'])
        jobid = job.attrib['href'].split("?")[1]
        joburl = job.attrib['href']
        fulljoburl = nhsurl+joburl
        #Run next function, defined below
        scrapenhsjobpage(fulljoburl)

#Create a function to scrape the specific jobs page
def scrapenhsjobpage(fulljoburl):
    print(fulljoburl)
    html = requests.get(fulljoburl, verify=False)
    root = lxml.html.fromstring(html.content)
    jobtitles = root.cssselect("h1")
    jobtitle = jobtitles[0].text_content()
    jobrefs = root.cssselect("h2 strong")
    jobref = jobrefs[0].text_content()
    jobid = fulljoburl.split("?vac_ref=")[1]
    #create empty dict to store data
    record = {}
    record['jobtitle'] = jobtitle
    record['jobref'] = jobref
    record['jobid'] = jobid 
    record['joburl'] = fulljoburl
    #All the details on employer, salary, etc. are in 3 <dl> boxes
    ddlinks = root.cssselect("dl.pairedData dd a")
    dds = root.cssselect("dl.pairedData dd")
    vacSummary = root.cssselect("dl.pairedData.vacSummary dd")
    vacSummarydt = root.cssselect("dl.pairedData.vacSummary dt")
    #Create 2 empty lists...
    vacSummarytext = []
    vacSummarytitles = []
    #...then fill them with the labels and values in the table, respectively
    for i in range(0,len(vacSummary)):
        vacSummarytext.append(vacSummary[i].text_content())
        vacSummarytitles.append(vacSummarydt[i].text_content())
    #The labels are consistent: ['Job Type:', 'Working pattern:', 'Pay Scheme:', 'Pay Band:', 'Staff Group:', 'Specialty/Function:']
    #And the position of each on any page helps us to identify the same position of the relevant values
    #But we need a try/except to handle pages where the label doesn't appear at all (or its value)
    try:
        record['payscheme'] = vacSummary[vacSummarytitles.index('Pay Scheme:')].text_content()
    except ValueError:
        record['payscheme'] = "None given"
    try:
        record['type'] = vacSummary[vacSummarytitles.index('Job Type:')].text_content()
    except ValueError:
        record['type'] = "None given"
    try:
        record['workpattern'] = vacSummary[vacSummarytitles.index('Working pattern:')].text_content()
    except ValueError:
        record['workpattern'] = "None given"
    try:
        record['payband'] = vacSummary[vacSummarytitles.index('Pay Band:')].text_content()
    except ValueError:
        record['payband'] = "None given"
    try:
        record['staffgroup'] = vacSummary[vacSummarytitles.index('Staff Group:')].text_content()
    except ValueError:
        record['staffgroup'] = "None given"
    try:
        record['speciality'] = vacSummary[vacSummarytitles.index('Specialty/Function:')].text_content()
    except ValueError:
        record['speciality'] = "None given"
    salary = dds[3].text_content()
    record['salary'] = salary
    #print(len(dds))
    employer = ddlinks[0].text_content()
    print(employer)
    record['employer'] = employer
    ps = root.cssselect("p")
    #Create some empty strings which we will populate with the text scraped below
    description = ""
    deductext = ""
    dbs = ""
    chargetxt = ""
    #create a default value for the number of mentions
    deduccount = 0
    dbscount = 0
    chargecount = 0
    #loop through each par
    for p in ps:
        print(p.text_content())
        #add each paragraph to the description
        description = description+p.text_content()
        #look for 'deducted' and variants
        if "deduc" in p.text_content():
            #store any matched text
            deductext = deductext+p.text_content()
            #increment the count of mentions by 1
            deduccount += 1
        if "charge will" in p.text_content():
            #store any matched text
            chargetxt = chargetxt+p.text_content()
            #increment the count of mentions by 1
            chargecount += 1
        if "isclosure and Barring Service" in p.text_content():
            #store any matched text
            dbs = dbs+p.text_content()
            #increment the count of mentions by 1
            dbscount += 1
    #When loop has finished adding pars, store the results
    record['desc'] = description
    #Create a true/false value to test if there are *any* mentions
    if deduccount >0:
        deducted = True
    else:
        deducted = False
    #store the count of matches and any matching text in 'record'
    record['deduc'] = deducted
    record['deducmentions'] = deduccount
    record['deductext'] = deductext
    record['dbs'] = dbs
    record['dbscount'] = dbscount
    record['chargetxt'] = chargetxt
    record['chargecount'] = chargecount
    record['timestamp'] = st
    print record
    #save to database
    scraperwiki.sqlite.save(['jobid'], record, table_name = "nhsjobs")
    

#NHS SCRAPER STARTS HERE

#We use the string library to grab a list of upper case letters: https://docs.python.org/2/library/string.html
from string import ascii_uppercase
#Loop through them
for letter in ascii_uppercase[23:]:
    #Add to URL
    letterurl = "https://www.jobs.nhs.uk/xi/employer_list/?action=search&sl="+letter
    #Run first function defined above
    scrapeletterpage(letterurl)


