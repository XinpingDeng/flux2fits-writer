#ifndef _FLUX2UDP_H
#define _FLUX2UDP_H

#include "dada_hdu.h"
#include "dada_def.h"
#include "ipcio.h"
#include "ascii_header.h"
#include "daemon.h"
#include "futils.h"

#include "paf_flux2udp.h"

#define DADA_HDR_SIZE 4096
#define NCHAN_CHK     7
#define NCHK_NIC      48
#define NBYTE_BUF     4

#define DADA_TIMESTR  "%Y-%m-%d-%H:%M:%S"
#define FITS_TIMESTR  "%Y-%m-%dT%H:%M:%S"
#define NBYTE_UTC     28  // Bytes of UTC time stamp
#define NBYTE_BIN     4   // Bytes for other number in the output binary
typedef struct conf_t
{
  key_t key;
  char ip[MSTR_LEN];
  char dir[MSTR_LEN];
  int port;

  dada_hdu_t *hdu;
  char *hdrbuf;
  size_t buf_size;
  int beam;
  double tsamp;
  char utc_start[MSTR_LEN];
  double picoseconds;
  float freq;
  float chan_width;
  int32_t nchan;
}conf_t;

int init_flux2udp(conf_t *conf);
int do_flux2udp(conf_t conf);
int destroy_flux2udp(conf_t conf);
int read_header(conf_t *conf);

#endif
