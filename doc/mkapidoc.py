#!/usr/bin/env python
# Generates the *public* API documentation.
# Remember to hide your private parts, people!
import os, re, sys

project  = 'pyexist'
base_dir = os.path.join('..', 'src')
doc_dir  = 'api'

# Create the documentation directory.
if not os.path.exists(doc_dir):
    os.makedirs(doc_dir)

# Generate the API documentation.
cmd = 'epydoc ' + ' '.join(['--name', project,
                            '--html',
                            '--no-private',
                            '--introspect-only',
                            '--no-source',
                            '--no-frames',
                            '--inheritance=included',
                            '-v',
                            '-o %s' % doc_dir,
                            os.path.join(base_dir, project)])
print cmd
os.system(cmd)
