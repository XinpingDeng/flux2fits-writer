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
#include "flux2udp.h"
#include "paf_flux2udp.h"

extern multilog_t *runtime_log;

int init_flux2udp(conf_t *conf)
{
  ipcbuf_t *db = NULL;
  uint64_t block_id;
  size_t curbufsz;

  conf->buf_size = NCHAN_CHK * NCHK_NIC * NBYTE_BUF;
  
  conf->hdu = dada_hdu_create(runtime_log);
  dada_hdu_set_key(conf->hdu, conf->key);
  if(dada_hdu_connect(conf->hdu) < 0)
    {
      multilog(runtime_log, LOG_ERR, "could not connect to hdu\n");
      fprintf(stderr, "Can not connect to hdu, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;    
    }  
  db = (ipcbuf_t *) conf->hdu->data_block;
  if(ipcbuf_get_bufsz(db) != conf->buf_size)
    {
      multilog(runtime_log, LOG_ERR, "data buffer size mismatch\n");
      fprintf(stderr, "Buffer size mismatch, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;    
    }
  
  if(ipcbuf_get_bufsz(conf->hdu->header_block) != DADA_HDR_SIZE)    // This number should match
    {
      multilog(runtime_log, LOG_ERR, "Header buffer size mismatch\n");
      fprintf(stderr, "Buffer size mismatch, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;    
    }
  
  /* make ourselves the read client */
  if(dada_hdu_lock_read(conf->hdu) < 0)
    {
      multilog(runtime_log, LOG_ERR, "open_hdu: could not lock write\n");
      fprintf(stderr, "Error locking HDU, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;
    }

  conf->hdu->data_block->curbuf = ipcio_open_block_read(conf->hdu->data_block, &curbufsz, &block_id);
  
  return EXIT_SUCCESS;
}

int do_flux2udp(conf_t conf)
{
  // To make sure the binary file is okay;
  // To make sure that binary in stdout is okay;
  // To make sure that I can send it via UDP;
  // To make sure that I can receive the data on UDP port;
  uint64_t block_id;
  size_t curbufsz;
  struct tm tm;
  char utc[MSTR_LEN];
  double tsamp, tt, tt_f;
  time_t tt_i;
  char binary_fname[MSTR_LEN];
  FILE *binary_fp = NULL;

  // We need to be careful here, float may not be 4 bytes !!!!
  
  sprintf(binary_fname, "%s/flux2udp.bin", conf.dir);
  
  read_header(&conf); // Get information from header
  strptime(conf.utc_start, DADA_TIMESTR, &tm);
  tsamp = conf.tsamp / 1.0E6; // In seconds
  tt    = mktime(&tm) + conf.picoseconds / 1E12 + tsamp / 2.0; // To added in the fraction part of reference time and half of the sampling time (the time stamps should be at the middle of integration)
  
  while(conf.hdu->data_block->curbufsz == conf.buf_size)
    {
      tt_i = (time_t)tt;
      tt_f = tt - tt_i;
      
      binary_fp = fopen(binary_fname, "wb+");
      /* Put key information into binary stream */
      fwrite(&conf.nchan, NBYTE_BIN, 1, binary_fp);                          // Number of channels
      fwrite(conf.hdu->data_block->curbuf, NBYTE_BIN, conf.nchan, binary_fp);// Flux of all channels
      
      strftime (utc, MSTR_LEN, FITS_TIMESTR, gmtime(&tt_i));    // String start time without fraction second
      sprintf(utc, "%s.%04dUTC ", utc, (int)(tt_f * 1E4 + 0.5));// To put the fraction part in and make sure that it rounds to closest integer
      //fprintf(stdout, "%s\t%f\n", utc, tt_f);
      fwrite(utc, NBYTE_UTC, 1, binary_fp);                     // UTC timestamps
      fwrite(&conf.beam, NBYTE_BIN, 1, binary_fp);              // The beam id

      /* Put TOS position information into binary stream*/

      /* Put TOS frequency information into binary stream*/
      fwrite(&conf.freq, NBYTE_BIN, 1, binary_fp);              // The beam id
      fwrite(&conf.chan_width, NBYTE_BIN, 1, binary_fp);              // The beam id
      
      fclose(binary_fp);
      
      if(ipcio_close_block_read(conf.hdu->data_block, conf.hdu->data_block->curbufsz)<0)
      	{
	  multilog (runtime_log, LOG_ERR, "close_buffer: ipcio_close_block_write failed\n");
	  fprintf(stderr, "close_buffer: ipcio_close_block_write failed, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
	  return EXIT_FAILURE;
	}
      conf.hdu->data_block->curbuf = ipcio_open_block_read(conf.hdu->data_block, &curbufsz, &block_id);
      tt += tsamp;
    }

  return EXIT_SUCCESS;
}

int destroy_flux2udp(conf_t conf)
{
  dada_hdu_unlock_read(conf.hdu);
  dada_hdu_disconnect(conf.hdu);
  dada_hdu_destroy(conf.hdu);
  
  return EXIT_SUCCESS;
}

int read_header(conf_t *conf)
{
  size_t hdrsz;
  float bw;
  conf->hdrbuf  = ipcbuf_get_next_read(conf->hdu->header_block, &hdrsz);

  if(hdrsz != DADA_HDR_SIZE)
    {
      multilog(runtime_log, LOG_ERR, "get next header block error.\n");
      fprintf(stderr, "Header size mismatch, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;
    }
  if (!conf->hdrbuf)
    {
      multilog(runtime_log, LOG_ERR, "get next header block error.\n");
      fprintf(stderr, "Error getting header_buf, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;
    }

  if (ascii_header_get(conf->hdrbuf, "TSAMP", "%lf", &(conf->tsamp)) < 0)  
    {
      multilog(runtime_log, LOG_ERR, "Error getting TSAMP, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      fprintf(stderr, "Error getting TSAMP, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;
    }    
  
  if (ascii_header_get(conf->hdrbuf, "PICOSECONDS", "%lf", &(conf->picoseconds)) < 0)  
    {
      multilog(runtime_log, LOG_ERR, "Error getting PICOSECONDS, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      fprintf(stderr, "Error getting PICOSECONDS, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;
    }

  if (ascii_header_get(conf->hdrbuf, "UTC_START", "%s", conf->utc_start) < 0)  
    {
      multilog(runtime_log, LOG_ERR, "Error getting UTC_START, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      fprintf(stderr, "Error getting UTC_START, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;
    }

  if (ascii_header_get(conf->hdrbuf, "FREQ", "%f", &conf->freq) < 0)  
    {
      multilog(runtime_log, LOG_ERR, "Error getting FREQ, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      fprintf(stderr, "Error getting FREQ, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;
    }
  
  if (ascii_header_get(conf->hdrbuf, "NCHAN", "%ld", &conf->nchan) < 0)  
    {
      multilog(runtime_log, LOG_ERR, "Error getting NCHAN, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      fprintf(stderr, "Error getting NCHAN, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;
    }

  if (ascii_header_get(conf->hdrbuf, "BW", "%f", &bw) < 0)  
    {
      multilog(runtime_log, LOG_ERR, "Error getting BW, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      fprintf(stderr, "Error getting BW, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;
    }  

  conf->chan_width = bw / conf->nchan;
  //fprintf(stdout, "%f\t%f\t%d\t%f\n", conf->freq, bw, conf->nchan, conf->chan_width);
  
  if(ipcbuf_mark_cleared (conf->hdu->header_block))  // We are the only one reader, so that we can clear it after read;
    {
      multilog(runtime_log, LOG_ERR, "Could not clear header block\n");
      fprintf(stderr, "Error header_clear, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;
    }
  
  return EXIT_SUCCESS;
}
