# reparative-description
Python scripts created for the Harvard Library Reparative Archival Description project.

## Requirements
* ArchivesSnake


## term_audit.py
Searches for terms in titles and notes of ArchivesSpace resource, archival object, digital object, and accession records. The search terms are pulled from a CSV file (search_terms.csv) that users must create before running the script. The CSV file should have term and regex columns.

If searching a single repository, the user can either enter the repository number (or a comma-separated list of numbers) as a command line argument or enter it when prompted. If no repository is entered when prompted, the script will loop through all repositories. Note: the script assumes the user has permissions for the repositories entered and does not handle errors about permissions.
