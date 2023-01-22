import argparse
import glob
import os
from polymath import LIBRARY_DIR, Library

DEFAULT_GLOB = os.path.join(LIBRARY_DIR, '**/*.json')

parser = argparse.ArgumentParser()
parser.add_argument('--files', help='A glob of the names of the files to be processed', default=DEFAULT_GLOB)
parser.add_argument('--run', help='If not passed, this will be dry run.', action='store_true')
args = parser.parse_args()

files = glob.glob(args.files, recursive=True)

run = args.run

count_needs_upgrade = 0

for file in files:
    lib = Library(filename=file)
    if not lib.upgraded:
        print(f'File {file} was found but did not need to be upgraded.')
        continue
    count_needs_upgrade += 1
    if run:
        print(f'Upgrading {file}')
        lib.save(file)
    else:
        print(f'Would have upgraded {file}')

print('')
if count_needs_upgrade:
    print('')
    print(f'{count_needs_upgrade} files needed upgrade')
    if not run:
        print('Once confirming that the output is as expected, re-run this command with --run to acutally upgrade in place.')
        print('It\'s recommended to copy all files first into a backup just in case the upgrade fails.')
else:
    print('No files needed upgrade')
