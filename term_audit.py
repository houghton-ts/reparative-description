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
from asnake.client import ASnakeClient
from asnake.utils import text_in_note, get_note_text

def get_term_context(text):
    """ finds the location of search terms within a field
        and returns the text with a set number of characters
        before and after
    """
    context = []
    char_length = 50
    positions = [m.span() for m in re.finditer(regex, text, flags=re.I)]
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
# TO_DO: Check that digital objects are being retrieved; none found so far?

with open('search_terms.csv', 'r', newline='') as term_file:
    reader = csv.DictReader(term_file)
    search_terms = list(reader)

repos = client.get('repositories').json()
# TO_DO: Add way to either get list of repos as system arg or loop through all repos

# Loop through ASpace repositories
for repo in repos:
    repo_no = repo['uri']
    repo_code = repo['repo_code']
    repo_filename = f'term_audit_{repo_code}.csv'
    fields = []
    rows = []

    ## For each repository search the API for the terms in the file list
    for search_term in search_terms:
        term = search_term['term']
        regex = search_term['regex']

        results = client.get_paged(f"{repo_no}/search",
                        params={"q": f"primary_type:{primary_types} \
                        NOT types:pui \
                        AND (title:/{regex}/ OR notes:/{regex}/)"})
        search_results = list(results)
        print(repo_code, term, len(search_results))

        ## Process the search results for each term
        for result in search_results:

            matches = []
            json_data = json.loads(result.get('json'))

            ## Process title
            title = json_data['title']
            title_match = re.search(regex, title)
            if title_match:
                matches.append(['title', get_term_context(title)])

            ## Process notes
            notes = json_data.get('notes')

            if notes:
                for note in notes:
                    if text_in_note(note, term, client, confidence=90):
                        note_type = note.get('type')
                        note_text = ' '.join(get_note_text(note, client))
                        note_text = ' '.join(note_text.split())

                        matches.append([f'note: {note_type}', get_term_context(note_text)])

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
                    fields += list(row_data.keys())
                rows.append(row_data)

    ## Write output to CSV file
    with open(repo_filename, 'w', encoding='utf-8', newline='') as report_file:
        writer = csv.DictWriter(report_file, fieldnames=fields)
        writer.writeheader()

        for row in rows:
            writer.writerow(row)
