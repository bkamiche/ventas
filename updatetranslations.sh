#!/bin/sh
# para inicilizar
#pybabel extract -F babel.cfg -o messages.pot .
#pybabel init -i messages.pot -d translations -l es
#pybabel init -i messages.pot -d translations -l en
#pybabel init -i messages.pot -d translations -l fr
#pybabel init -i messages.pot -d translations -l pt
#pybabel init -i messages.pot -d translations -l de
#pybabel init -i messages.pot -d translations -l it
# proceso normal
pybabel extract -F babel.cfg -o messages.pot .
pybabel update -i messages.pot -d translations --no-fuzzy-matching
python3 -u translate.py
