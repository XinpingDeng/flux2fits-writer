#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif

#include <time.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <inttypes.h>
#include <math.h>

#include "multilog.h"
#include "baseband2power.cuh"
#include "paf_baseband2power.cuh"
#include "cudautil.cuh"
#include "kernel.cuh"

extern multilog_t *runtime_log;

int init_baseband2power(conf_t *conf)
{
  CudaSafeCall(cudaSetDevice(conf->device_id));
  size_t curbufsz;
  uint64_t block_id;
  
  ipcbuf_t *db = NULL;
  if(conf->nchan_out != (NCHAN_CHK * NCHK_NIC))
    {
      multilog(runtime_log, LOG_ERR, "Channel number mismatch\n");
      fprintf(stderr, "The number of channel is not match %d != %d, which happens at \"%s\", line [%d].\n",conf->nchan_out, NCHAN_CHK * NCHK_NIC, __FILE__, __LINE__);
    }
  conf->bufin_size  = conf->bufin_ndf * NCHAN_CHK * NCHK_NIC * NSAMP_DF * NPOL_SAMP * NDIM_POL * NBYTE_IN;
  conf->bufrt_size  = conf->bufin_ndf * NCHAN_CHK * NCHK_NIC * NSAMP_DF * NBYTE_RT;
  conf->bufout_size = NCHAN_CHK * NCHK_NIC * NBYTE_OUT;
  
  conf->nsamp_in  = conf->bufin_ndf * NCHAN_CHK * NCHK_NIC * NSAMP_DF;
  conf->nsamp_rt  = conf->nsamp_in;
  conf->nsamp_out = conf->nchan_out;
  
  CudaSafeCall(cudaMalloc((void **)&conf->dbuf_in, conf->bufin_size));
  CudaSafeCall(cudaMalloc((void **)&conf->dbuf_out, conf->bufout_size));
  CudaSafeCall(cudaMalloc((void **)&conf->buf_rt1, conf->bufrt_size));
  CudaSafeCall(cudaMalloc((void **)&conf->buf_rt2, conf->bufrt_size));
  
  /* Prepare the setup of kernels */
  conf->gridsize_unpack_detect.x = conf->bufin_ndf;
  conf->gridsize_unpack_detect.y = NCHK_NIC;
  conf->gridsize_unpack_detect.z = 1;
  conf->blocksize_unpack_detect.x = NSAMP_DF; 
  conf->blocksize_unpack_detect.y = NCHAN_CHK;
  conf->blocksize_unpack_detect.z = 1;

  conf->gridsize_sum1.x = NCHK_NIC * NCHAN_CHK;
  conf->gridsize_sum1.y = conf->bufin_ndf * NSAMP_DF / (2 * BLKSZ_SUM1);
  conf->gridsize_sum1.z = 1;
  conf->blocksize_sum1.x = BLKSZ_SUM1;
  conf->blocksize_sum1.y = 1;
  conf->blocksize_sum1.z = 1;

  conf->gridsize_sum2.x = NCHK_NIC * NCHAN_CHK;
  conf->gridsize_sum2.y = 1;
  conf->gridsize_sum2.z = 1;
  conf->blocksize_sum2.x = conf->bufin_ndf * NSAMP_DF / (4 * BLKSZ_SUM1);
  conf->blocksize_sum2.y = 1;
  conf->blocksize_sum2.z = 1;

  /* Attach to input ring buffer */
  conf->hdu_in = dada_hdu_create(runtime_log);
  dada_hdu_set_key(conf->hdu_in, conf->key_in);
  if(dada_hdu_connect(conf->hdu_in) < 0)
    {
      multilog(runtime_log, LOG_ERR, "could not connect to hdu\n");
      fprintf(stderr, "Can not connect to hdu, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;    
    }  
  db = (ipcbuf_t *) conf->hdu_in->data_block;
  if(ipcbuf_get_bufsz(db) != conf->bufin_size)
    {
      multilog(runtime_log, LOG_ERR, "data buffer size mismatch\n");
      fprintf(stderr, "Buffer size mismatch, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;    
    }

  /* registers the existing host memory range for use by CUDA */
  dada_cuda_dbregister(conf->hdu_in);
  
  if(ipcbuf_get_bufsz(conf->hdu_in->header_block) != DADA_HDR_SIZE)    // This number should match
    {
      multilog(runtime_log, LOG_ERR, "Header buffer size mismatch\n");
      fprintf(stderr, "Buffer size mismatch, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;    
    }
  
  /* make ourselves the read client */
  if(dada_hdu_lock_read(conf->hdu_in) < 0)
    {
      multilog(runtime_log, LOG_ERR, "open_hdu: could not lock write\n");
      fprintf(stderr, "Error locking HDU, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;
    }
  
  /* Prepare output ring buffer */
  conf->hdu_out = dada_hdu_create(runtime_log);
  dada_hdu_set_key(conf->hdu_out, conf->key_out);
  if(dada_hdu_connect(conf->hdu_out) < 0)
    {
      multilog(runtime_log, LOG_ERR, "could not connect to hdu\n");
      fprintf(stderr, "Can not connect to hdu, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;    
    }
  db = (ipcbuf_t *) conf->hdu_out->data_block;
  if(ipcbuf_get_bufsz(db) != conf->bufout_size)  
    {
      multilog(runtime_log, LOG_ERR, "data buffer size mismatch\n");
      fprintf(stderr, "Buffer size mismatch, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;    
    }
  
  if(ipcbuf_get_bufsz(conf->hdu_out->header_block) != DADA_HDR_SIZE)    // This number should match
    {
      multilog(runtime_log, LOG_ERR, "Header buffer size mismatch\n");
      fprintf(stderr, "Buffer size mismatch, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;    
    }  
  /* make ourselves the write client */
  if(dada_hdu_lock_write(conf->hdu_out) < 0)
    {
      multilog(runtime_log, LOG_ERR, "open_hdu: could not lock write\n");
      fprintf(stderr, "Error locking HDU, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;
    }
  
  if(conf->sod)
    {      
      if(ipcbuf_enable_sod(db, 0, 0) < 0)  // We start at the beginning
  	{
	  multilog(runtime_log, LOG_ERR, "Can not write data before start, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
  	  fprintf(stderr, "Can not write data before start, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
  	  return EXIT_FAILURE;
  	}
    }
  else
    {
      if(ipcbuf_disable_sod(db) < 0)
  	{
	  multilog(runtime_log, LOG_ERR, "Can not write data before start, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
  	  fprintf(stderr, "Can not write data before start, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
  	  return EXIT_FAILURE;
  	}
    }
  
  /* Register header */
  if(register_header(conf))
    {
      multilog(runtime_log, LOG_ERR, "header register failed, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      fprintf(stderr, "header register failed, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;
    }

  conf->hdu_out->data_block->curbuf = ipcio_open_block_write(conf->hdu_out->data_block, &block_id);   /* Open buffer to write */
  conf->hdu_in->data_block->curbuf = ipcio_open_block_read(conf->hdu_in->data_block, &curbufsz, &block_id);
    
  return EXIT_SUCCESS;
}

int destroy_process(conf_t conf)
{
  CudaSafeCall(cudaSetDevice(conf.device_id));

  cudaFree(conf.dbuf_in);
  cudaFree(conf.dbuf_out);
  cudaFree(conf.buf_rt1);
  cudaFree(conf.buf_rt2);

  dada_cuda_dbunregister(conf.hdu_in);
  dada_hdu_unlock_read(conf.hdu_in);
  dada_hdu_unlock_write(conf.hdu_out);
  
  return EXIT_SUCCESS;
}

int do_baseband2power(conf_t conf)
{
  CudaSafeCall(cudaSetDevice(conf.device_id));
  size_t curbufsz;
  uint64_t block_id;
  dim3 gridsize_unpack_detect, blocksize_unpack_detect;
  dim3 gridsize_sum1, blocksize_sum1;
  dim3 gridsize_sum2, blocksize_sum2;

  gridsize_unpack_detect = conf.gridsize_unpack_detect;
  blocksize_unpack_detect = conf.blocksize_unpack_detect;
  gridsize_sum1 = conf.gridsize_sum1;
  blocksize_sum1 = conf.blocksize_sum1;
  gridsize_sum2 = conf.gridsize_sum2;
  blocksize_sum2 = conf.blocksize_sum2;
  
#ifdef DEBUG
  struct timespec start, stop;
  double elapsed_time;
#endif
  
  while(conf.hdu_in->data_block->curbufsz == conf.bufin_size)
    {
#ifdef DEBUG
      clock_gettime(CLOCK_REALTIME, &start);
#endif

      /* Copy data from host to device */
      CudaSafeCall(cudaMemcpy(conf.dbuf_in, conf.hdu_in->data_block->curbuf, conf.bufin_size, cudaMemcpyHostToDevice));
      
#ifdef DEBUG
      clock_gettime(CLOCK_REALTIME, &stop);
      elapsed_time = (stop.tv_sec - start.tv_sec) + (stop.tv_nsec - start.tv_nsec)/1000000000.0L;
      fprintf(stdout, "Elapsed time to copy %"PRIu64" bytes data is %f second.\n", conf.bufin_size, elapsed_time);
#endif

      /* Do processing here */
      unpack_detect_kernel<<<gridsize_unpack_detect, blocksize_unpack_detect, 0>>>(conf.dbuf_in, conf.buf_rt1);
      sum_kernel<<<gridsize_sum1, blocksize_sum1, blocksize_sum1.x * sizeof(float)>>>(conf.buf_rt1, conf.buf_rt2);
      sum_kernel<<<gridsize_sum2, blocksize_sum2, blocksize_sum2.x * sizeof(float)>>>(conf.buf_rt2, conf.dbuf_out);
      
      /* Close previous data block and open a new one to read */
      if(ipcio_close_block_read(conf.hdu_in->data_block, conf.hdu_in->data_block->curbufsz)<0)
      	{
	  multilog (runtime_log, LOG_ERR, "close_buffer: ipcio_close_block_write failed\n");
	  fprintf(stderr, "close_buffer: ipcio_close_block_write failed, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
	  return EXIT_FAILURE;
	}
      conf.hdu_in->data_block->curbuf = ipcio_open_block_read(conf.hdu_in->data_block, &curbufsz, &block_id);

      /* Copy data from device to host */
      CudaSafeCall(cudaMemcpy(conf.hdu_out->data_block->curbuf, conf.dbuf_out, conf.bufout_size, cudaMemcpyDeviceToHost));
      /* Close previous data block and open a new one to write */
      if(ipcio_close_block_write(conf.hdu_out->data_block, conf.bufout_size)<0)
	{
	  multilog (runtime_log, LOG_ERR, "close_buffer: ipcio_close_block_write failed\n");
	  fprintf(stderr, "close_buffer: ipcio_close_block_write failed, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
	  return EXIT_FAILURE;
	}

      conf.hdu_out->data_block->curbuf = ipcio_open_block_write(conf.hdu_out->data_block, &block_id);   /* Open buffer to write */     
    }
  
  return EXIT_SUCCESS;
}

int register_header(conf_t *conf)
{
  size_t hdrsz;
  double scale;
  conf->tsamp_out = NSAMP_DF * conf->bufin_ndf * TSAMP;
  
  conf->hdrbuf_in  = ipcbuf_get_next_read(conf->hdu_in->header_block, &hdrsz);
  if(hdrsz != DADA_HDR_SIZE)
    {
      multilog(runtime_log, LOG_ERR, "get next header block error.\n");
      fprintf(stderr, "Header size mismatch, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;
    }
  if (!conf->hdrbuf_in)
    {
      multilog(runtime_log, LOG_ERR, "get next header block error.\n");
      fprintf(stderr, "Error getting header_buf, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;
    }
  if (ascii_header_get(conf->hdrbuf_in, "TSAMP", "%lf", &(conf->tsamp_in)) < 0)  
    {
      multilog(runtime_log, LOG_ERR, "Error getting TSAMP, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      fprintf(stderr, "Error getting TSAMP, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;
    }    
  if (ascii_header_get(conf->hdrbuf_in, "BYTES_PER_SECOND", "%lf", &(conf->bps_in)) < 0)  
    {
      multilog(runtime_log, LOG_ERR, "Error getting BYTES_PER_SECOND, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      fprintf(stderr, "Error getting BYTES_PER_SECOND, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;
    }    
  if (ascii_header_get(conf->hdrbuf_in, "FILE_SIZE", "%lf", &(conf->fsz_in)) < 0)  
    {
      multilog(runtime_log, LOG_ERR, "Error getting FILE_SIZE, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      fprintf(stderr, "Error getting FILE_SIZE, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;
    }
  if (ascii_header_get(conf->hdrbuf_in, "MJD_START", "%lf", &(conf->mjd_start)) < 0)  
    {
      multilog(runtime_log, LOG_ERR, "Error getting MJD_START, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      fprintf(stderr, "Error getting MJD_START, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;
    }
  if (ascii_header_get(conf->hdrbuf_in, "PICOSECONDS", "%ld", &(conf->picoseconds)) < 0)  
    {
      multilog(runtime_log, LOG_ERR, "Error getting PICOSECONDS, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      fprintf(stderr, "Error getting PICOSECONDS, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;
    }
  fprintf(stdout, "%f\t%E\t%E\t", conf->mjd_start, conf->picoseconds / 86400.0E12, 0.5 * conf->tsamp_out / 86400.0E6);
  
  conf->mjd_start = conf->mjd_start + conf->picoseconds / 86400.0E12 + 0.5 * conf->tsamp_out / 86400.0E6;  // to the middle of interval
  fprintf(stdout, "%f\n\n\n\n\n", conf->mjd_start);
  
  scale = conf->tsamp_in / conf->tsamp_out;

  conf->hdrbuf_out = ipcbuf_get_next_write(conf->hdu_out->header_block);
  if (!conf->hdrbuf_out)
    {
      multilog(runtime_log, LOG_ERR, "get next header block error.\n");
      fprintf(stderr, "Error getting header_buf, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;
    }
  memcpy(conf->hdrbuf_out, conf->hdrbuf_in, DADA_HDR_SIZE);  
  if (ascii_header_set(conf->hdrbuf_out, "TSAMP", "%lf", conf->tsamp_out) < 0)  
    {
      multilog(runtime_log, LOG_ERR, "Error setting TSAMP, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      fprintf(stderr, "Error setting TSAMP, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;
    }  
  if (ascii_header_set(conf->hdrbuf_out, "MJD_START", "%lf", conf->mjd_start) < 0)  
    {
      multilog(runtime_log, LOG_ERR, "Error setting MJD_START, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      fprintf(stderr, "Error setting MJD_START, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;
    }    
  //if (ascii_header_set(conf->hdrbuf_out, "PICOSECONDS", "unset") < 0)  
  //  {
  //    multilog(runtime_log, LOG_ERR, "Error setting PICOSECONDS, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
  //    fprintf(stderr, "Error setting PICOSECONDS, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
  //    return EXIT_FAILURE;
  //  }
  //if (ascii_header_set(conf->hdrbuf_out, "UTC_START", "unset") < 0)  
  //  {
  //    multilog(runtime_log, LOG_ERR, "Error setting UTC_START, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
  //    fprintf(stderr, "Error setting UTC_START, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
  //    return EXIT_FAILURE;
  //  }    
  if (ascii_header_set(conf->hdrbuf_out, "BYTES_PER_SECOND", "%lf", conf->bps_in * scale) < 0)  
    {
      multilog(runtime_log, LOG_ERR, "Error setting BYTES_PER_SECOND, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      fprintf(stderr, "Error setting BYTES_PER_SECOND, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;
    }    
  if (ascii_header_set(conf->hdrbuf_out, "FILE_SIZE", "%lf", conf->fsz_in * scale) < 0)  
    {
      multilog(runtime_log, LOG_ERR, "Error setting FILE_SIZE, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      fprintf(stderr, "Error setting FILE_SIZE, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;
    }

  if (ipcbuf_mark_filled (conf->hdu_out->header_block, DADA_HDR_SIZE) < 0)
    {
      multilog(runtime_log, LOG_ERR, "Could not mark filled header block\n");
      fprintf(stderr, "Error header_fill, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;
    }
  
  if(ipcbuf_mark_cleared (conf->hdu_in->header_block))  // We are the only one reader, so that we can clear it after read;
    {
      multilog(runtime_log, LOG_ERR, "Could not clear header block\n");
      fprintf(stderr, "Error header_clear, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;
    }
  
  return EXIT_SUCCESS;
}