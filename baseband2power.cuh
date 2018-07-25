#ifndef _BASEBAND2POWER_CUH
#define _BASEBAND2POWER_CUH

#include <cuda_runtime.h>
#include <cuda.h>
#include <cufft.h>
#include <stdio.h>

#include "dada_cuda.h"
#include "dada_hdu.h"
#include "dada_def.h"
#include "ipcio.h"
#include "ascii_header.h"
#include "daemon.h"
#include "futils.h"
#include "paf_baseband2power.cuh"

#define DADA_HDR_SIZE 4096
#define NSAMP_DF      128
#define NPOL_SAMP     2
#define NDIM_POL      2
#define NCHK_NIC      48
#define NCHAN_CHK     7
#define BLKSZ_SUM1    1024
//#define BLKSZ_SUM1    512
#define NBYTE_RT      4 // float
#define NBYTE_IN      2 // int16_t
#define NBYTE_OUT     4 // float
#define TSAMP         0.84375  // micro second

typedef struct conf_t
{
  int sod;
  int device_id;
  char dir[MSTR_LEN];

  key_t key_in, key_out;
  dada_hdu_t *hdu_in, *hdu_out;
  char *hdrbuf_in, *hdrbuf_out;
  
  size_t bufin_size, bufrt_size, bufout_size;
  size_t nsamp_in, nsamp_rt, nsamp_out;
  size_t hdrsz;
  size_t picoseconds;
  double mjd_start;
  
  double bufin_ndf;
  int nchan_out;

  int64_t *dbuf_in;
  float *dbuf_out;
  float *buf_rt1, *buf_rt2;

  double tsamp_out, tsamp_in;
  double fsz_out, fsz_in;
  double bps_out, bps_in;
  
  dim3 gridsize_unpack_detect, blocksize_unpack_detect;
  dim3 gridsize_sum1, blocksize_sum1;
  dim3 gridsize_sum2, blocksize_sum2;
  
}conf_t;

int init_baseband2power(conf_t *conf);
int do_baseband2power(conf_t conf);
int register_header(conf_t *conf);
#endif