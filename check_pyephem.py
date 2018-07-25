#!/usr/bin/env python

import ephem
import time

mjd1970 = 40587.0

secday = 86400.0
ephem_now = ephem.now().real + 2415020 - 2400000.5
computer_now = time.time() / secday + mjd1970

print ephem_now * secday
print computer_now * secday
print (ephem_now - computer_now) * secday
