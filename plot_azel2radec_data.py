#!/usr/bin/env python

import matplotlib.pyplot as plt
import datetime, pytz, ephem
import numpy as np

def utc_now():
    """
    Return current UTC as a timezone aware datetime.
    :rtype: datetime
    """
    dt=datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
    return dt

def getDUTCDt(dt=None):
    """
    Get the DUTC value in seconds that applied at the given (datetime)
    timestamp.
    """
    dt = dt or utc_now()
    for i in LEAPSECONDS:
        if i[0] < dt:
            return i[2]
    # Different system used before then
    return 0

# Leap seconds definition, [UTC datetime, MJD, DUTC]
LEAPSECONDS = [
    [datetime.datetime(2017, 1, 1, tzinfo=pytz.utc), 57754, 37],
    [datetime.datetime(2015, 7, 1, tzinfo=pytz.utc), 57205, 36],
    [datetime.datetime(2012, 7, 1, tzinfo=pytz.utc), 56109, 35],
    [datetime.datetime(2009, 1, 1, tzinfo=pytz.utc), 54832, 34],
    [datetime.datetime(2006, 1, 1, tzinfo=pytz.utc), 53736, 33],
    [datetime.datetime(1999, 1, 1, tzinfo=pytz.utc), 51179, 32],
    [datetime.datetime(1997, 7, 1, tzinfo=pytz.utc), 50630, 31],
    [datetime.datetime(1996, 1, 1, tzinfo=pytz.utc), 50083, 30],
    [datetime.datetime(1994, 7, 1, tzinfo=pytz.utc), 49534, 29],
    [datetime.datetime(1993, 7, 1, tzinfo=pytz.utc), 49169, 28],
    [datetime.datetime(1992, 7, 1, tzinfo=pytz.utc), 48804, 27],
    [datetime.datetime(1991, 1, 1, tzinfo=pytz.utc), 48257, 26],
    [datetime.datetime(1990, 1, 1, tzinfo=pytz.utc), 47892, 25],
    [datetime.datetime(1988, 1, 1, tzinfo=pytz.utc), 47161, 24],
    [datetime.datetime(1985, 7, 1, tzinfo=pytz.utc), 46247, 23],
    [datetime.datetime(1993, 7, 1, tzinfo=pytz.utc), 45516, 22],
    [datetime.datetime(1982, 7, 1, tzinfo=pytz.utc), 45151, 21],
    [datetime.datetime(1981, 7, 1, tzinfo=pytz.utc), 44786, 20],
    [datetime.datetime(1980, 1, 1, tzinfo=pytz.utc), 44239, 19],
    [datetime.datetime(1979, 1, 1, tzinfo=pytz.utc), 43874, 18],
    [datetime.datetime(1978, 1, 1, tzinfo=pytz.utc), 43509, 17],
    [datetime.datetime(1977, 1, 1, tzinfo=pytz.utc), 43144, 16],
    [datetime.datetime(1976, 1, 1, tzinfo=pytz.utc), 42778, 15],
    [datetime.datetime(1975, 1, 1, tzinfo=pytz.utc), 42413, 14],
    [datetime.datetime(1974, 1, 1, tzinfo=pytz.utc), 42048, 13],
    [datetime.datetime(1973, 1, 1, tzinfo=pytz.utc), 41683, 12],
    [datetime.datetime(1972, 7, 1, tzinfo=pytz.utc), 41499, 11],
    [datetime.datetime(1972, 1, 1, tzinfo=pytz.utc), 41317, 10],
]
"# Leap seconds definition, [UTC datetime, MJD, DUTC]"

def bat2utc(bat, dutc=None):
    """
    Convert Binary Atomic Time (BAT) to UTC.  At the ATNF, BAT corresponds to
    the number of microseconds of atomic clock since MJD (1858-11-17 00:00).

    :param bat: number of microseconds of atomic clock time since
        MJD 1858-11-17 00:00.
    :type bat: long
    :returns utcDJD: UTC date and time (Dublin Julian Day as used by pyephem)
    :rtype: float

    """
    dutc = dutc or getDUTCDt()
    if type(bat) is str:
        bat = long(bat, base=16)
    utcMJDs = (bat/1000000.0)-dutc
    utcDJDs = utcMJDs-86400.0*15019.5
    utcDJD = utcDJDs/86400.0
    return utcDJD + 2415020 - 2400000.5

beam       = 0
#time_stamp = "2018-06-28-00:22:10"
#time_stamp = "2018-06-28-20:15:20"
#time_stamp = "2018-06-28-14:42:12"
#time_stamp = "2018-06-28-13:05:31"
time_stamp = "2018-06-27-22:00:58"
time_stamp = "2018-06-27-22:11:21"
time_stamp = "2018-06-28-13:29:46"
time_stamp = "2018-06-28-22:30:25"
time_stamp = "2018-06-27-22:45:40"
time_stamp = "2018-06-28-13:37:12"
time_stamp = "2018-06-28-14:16:53"
time_stamp = "2018-06-28-14:42:12"

ddir       = "/beegfs/DENG/docker/beam{:d}".format(beam)
freq       = 210

eff        = ephem.Observer()
eff.long, eff.lat = '6.883611111', '50.52483333'

metadata = open("{:s}/{:s}.metadata".format(ddir, time_stamp)).readlines()

time    = []
time_c  = []
ra_r    = []
dk_r    = []
ra_cr   = []
dk_cr   = []
az_r    = []
el_r    = []
shift   = 0.0 / 86400.0
for metadata_line in metadata:
    bat_stamp = metadata_line.split('}')[0].split(',')[2].split('\'')[3]

    ra, dk = float(metadata_line.split('}')[0].split('[u\'')[2].split('\'')[0]), float(metadata_line.split('}')[0].split('[u\'')[2].split('\'')[2])  
    #az, el = float(metadata_line.split('{')[3].split(':')[3].split('\'')[1]) + 8.0 / 60.0 / 180.0 * np.pi - 1210.72474187 / 3600.0 / 180.0 * np.pi, float(metadata_line.split('{')[3].split(':')[3].split('\'')[3]) + 2.5 / 60.0 / 180.0 * np.pi + 453.67645525 / 3600.0 / 180.0 * np.pi
    az, el = float(metadata_line.split('{')[3].split(':')[3].split('\'')[1]), float(metadata_line.split('{')[3].split(':')[3].split('\'')[3]) 
    
    #az, el = float(metadata_line.split('{')[3].split(':')[3].split('\'')[1]), float(metadata_line.split('{')[3].split(':')[3].split('\'')[3])
    print "{:s}\t{:f}\t{:f}".format(bat_stamp, ra, dk)

    mjd = bat2utc(bat_stamp)
    djd = mjd - 2415020 + 2400000.5 + shift
    eff.date = djd 
    
    ra_c, dk_c = eff.radec_of(az, el)
    print "{:s}\t{:f}\t{:f}".format(bat_stamp, ra_c, dk_c)

    time.append(mjd)
    time_c.append(djd + 2415020 - 2400000.5)
    
    #ra_r.append(ra * 180.0 / np.pi * 60.0)
    #dk_r.append(dk * 180.0 / np.pi * 60.0)
    #
    #ra_cr.append(ra_c * 180.0 / np.pi * 60.0)
    #dk_cr.append(dk_c * 180.0 / np.pi * 60.0)

    ra_r.append(ra)
    dk_r.append(dk)
    
    ra_cr.append(ra_c)
    dk_cr.append(dk_c)

    az_r.append(az)
    el_r.append(el)
    
time   = np.array(time)
time_c = np.array(time_c)
ra_r = np.array(ra_r)
dk_r = np.array(dk_r)
ra_cr = np.array(ra_cr)
dk_cr = np.array(dk_cr)
az_r = np.array(az_r)
el_r = np.array(el_r)

result = np.concatenate(([time], [ra_cr], [dk_cr]), axis = 0).T
result_azel = np.concatenate(([time], [az_r], [el_r]), axis = 0).T

np.savetxt('{:s}.radec_new'.format(time_stamp), result)
np.savetxt('{:s}.azel'.format(time_stamp), result_azel)

print result

#print ra_cr

plt.figure()
plt.subplot(2,1,1)
plt.plot(time, ra_r)
plt.plot(time_c, ra_cr)
plt.subplot(2,1,2)
plt.plot(time, dk_r)
plt.plot(time_c, dk_cr)
plt.show()
