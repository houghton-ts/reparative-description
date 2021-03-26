#!/usr/bin/env python3

""" Python script to query the ArchivesSpace API and create a CSV report
    of titles and notes in resource, archival object, digital object, and
    accession records that contain terms in a CSV file with terms and regular
    expressions for those terms.

    This script was created as part of the Harvard Library Reparative
    Archival Description project.
"""

import csv
import json
import re
import sys
from asnake.client import ASnakeClient
from asnake.utils import text_in_note, get_note_text

def get_term_context(expression, text):
    """ finds the location of search terms within a field
        and returns the text with a set number of characters
        before and after
    """
    context = []
    char_length = 50
    positions = [m.span() for m in re.finditer(expression, text, flags=re.I)]
    term_count = len(positions)

    for position in positions:
        if position[0] < char_length:
            start = 0
            prefix = ''
        else:
            start = position[0] - char_length
            prefix = '...'

        if position[1] + char_length > len(text):
            end = len(text)
            postfix = ''
        else:
            end = position[1] + char_length
            postfix = '...'

        context.append(prefix + text[start : end] + postfix)
    context = ' | '.join(context)

    return term_count, context

client = ASnakeClient()

primary_types = '/(resource|archival_object|accession|digital_object)/'
results_file = 'term_audit_results.csv'

# Repo list can either be a command line argument or prompted
if len(sys.argv) == 2:
    repos = sys.argv[1]
elif len(sys.argv) < 2:
    repos = input('Enter repository number (e.g., 1): ')
else:
    sys.exit('Run script again with valid repo number(s)')

if repos:
    repos = re.split(r'\D+', repos)
    repos = list(filter(None, repos))
else:
    repos = client.get('repositories').json()

# Get list of search terms from CSV file
with open('search_terms.csv', 'r', newline='') as term_file:
    reader = csv.DictReader(term_file)
    search_terms = list(reader)

# Loop through ASpace repositories
for repo in repos:
    headers = []
    rows = []

    if isinstance(repo, str): # For prompted or arg value repo lists
        repo_no = repo
        response = client.get(f'repositories/{repo_no}')

        if response.status_code == 200:
            response_json = response.json()
            repo_code = response_json['repo_code']
            repo_uri = response_json['uri']
        else:
            sys.exit(f'Error (status code): {response.status_code}')
    elif isinstance(repo, dict): # For pulling all repos from ASpace
        repo_code = repo['repo_code']
        repo_uri = repo['uri']
        repo_no = repo_uri.split('/')[-1]
    else:
        sys.exit('List of repositories is not valid')

    # For each repository search the API for the terms in the file list
    for search_term in search_terms:
        term = search_term['term']
        regex = search_term['regex']

        results = client.get_paged(f'repositories/{repo_no}/search',
                        params={"q": f"primary_type:{primary_types} \
                        # NOT types:pui \
                        AND (title:/{regex}/ OR notes:/{regex}/)"})
        search_results = list(results)
        print(repo_code, repo_uri, term, len(search_results))

        ## Process the search results for each term
        for result in search_results:
            json_data = json.loads(result.get('json'))

            matches = []
            json_data = json.loads(result.get('json'))

            ## Process title
            title = json_data.get('title')
            if title:
                title_match = re.search(regex, title, re.IGNORECASE)
                if title_match:
                    matches.append(['title', get_term_context(regex, title)])

            ## Process notes
            notes = json_data.get('notes')

            if notes:
                for note in notes:
                    if text_in_note(note, term, client, confidence=90):
                        note_type = note.get('type')
                        note_text = ' '.join(get_note_text(note, client))
                        note_text = ' '.join(note_text.split())
                        matches.append([f'note: {note_type}', get_term_context(regex, note_text)])

            ## Collect data for output
            for match in matches:
                row_data = {
                        'repo_code' : repo_code,
                        'repository' : result['repository'],
                        'uri' : result['uri'],
                        'ead_id' : result.get('ead_id'),
                        'four_part_id' : result.get('four_part_id'),
                        'identifier' : result.get('identifier'),
                        'digital_object_id' : result.get('digital_object_id'),
                        'ref_id' : result.get('ref_id'),
                        'primary_type' : result['primary_type'],
                        'level' : result.get('level'),
                        'term' : term,
                        'location' : match[0],
                        'occurrences' : match[1][0],
                        'text' : match[1][1]
                        }
                if not rows:
                    headers += list(row_data.keys())
                rows.append(row_data)

    ## Append output to CSV file
    with open(results_file, 'a+', encoding='utf-8', newline='') as report_file:
        writer = csv.DictWriter(report_file, fieldnames=headers)

        if rows:
            report_file.seek(0,2)
            if report_file.tell() == 0: # Only add header if file is new
                writer.writeheader()

        for row in rows:
            writer.writerow(row)
