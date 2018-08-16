#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif

#include <time.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <inttypes.h>
#include <math.h>
#include <sys/socket.h>
#include <arpa/inet.h>

#include "multilog.h"
#include "flux2udp.h"
#include "paf_flux2udp.h"
#include "jsmn.h"

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

  init_sock(conf);  // init socket
   
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
  double tsamp, tt, tt_f, tt0;
  time_t tt_i;
  char binary_fname[MSTR_LEN];
  FILE *binary_fp = NULL;
  struct sockaddr_in sa_meta, sa_udp;
  char buf_meta[1<<16], buf_udp[1<<16]; // 1<<16 = 2^16
  socklen_t fromlen, tolen;
  jsmn_parser parser;
  jsmntok_t tokens[NTOKEN_META];  
  char bat[MSTR_LEN];
  char ra[MSTR_LEN], dec[MSTR_LEN];
  char az[MSTR_LEN], el[MSTR_LEN];
  float ra_f, dec_f, az_f, el_f;   // We need to be careful here, float may not be 4 bytes !!!!
  double mjd;
  int32_t mjd_i;
  float mjd_f;
  float tsamp_f;
  int byte_sum;
  fromlen = sizeof(sa_meta);
  tolen = sizeof(sa_meta);

  sa_udp.sin_family = AF_INET;
  sa_udp.sin_port   = htons(conf.port_udp);
  sa_udp.sin_addr.s_addr = inet_addr(conf.ip_udp);

  /* Do the job */
  read_header(&conf); // Get information from header
  strptime(conf.utc_start, DADA_TIMESTR, &tm);
  tsamp = conf.tsamp / 1.0E6; // In seconds
  tsamp_f = conf.tsamp;
  //fprintf(stdout, "%f\n", tsamp);
  tt    = mktime(&tm) + conf.picoseconds / 1E12 + tsamp / 2.0; // To added in the fraction part of reference time and half of the sampling time (the time stamps should be at the middle of integration)
  tt0 = tt;
  
  /* First TOS metadata information */
  recvfrom(conf.sock_meta, (void *)buf_meta, 1<<16, 0, (struct sockaddr *)&sa_meta, &fromlen);
  jsmn_init(&parser);
  jsmn_parse(&parser, buf_meta, strlen(buf_meta), tokens, NTOKEN_META);
  strncpy(bat, &buf_meta[tokens[2].start], tokens[2].end - tokens[2].start);  // Becareful the index here, most ugly code I do 
  strncpy(ra, &buf_meta[tokens[27].start], tokens[27].end - tokens[27].start);
  strncpy(dec, &buf_meta[tokens[28].start], tokens[28].end - tokens[28].start);
  strncpy(az, &buf_meta[tokens[177].start], tokens[177].end - tokens[177].start);
  strncpy(el, &buf_meta[tokens[178].start], tokens[178].end - tokens[178].start);
  ra_f = atof(ra);
  dec_f = atof(dec);
  az_f = atof(az);
  el_f = atof(el);
  
  int index = 0;
  time_t seconds;
  char utc_now[MSTR_LEN];
  //struct tm *loc_time;
  while(conf.hdu->data_block->curbufsz == conf.buf_size)
    {
      byte_sum = 0;
      //fprintf(stdout, "%f\t", tt);
      //sprintf(binary_fname, "%s/flux2udp.bin%d", conf.dir, index);
      sprintf(binary_fname, "%s/flux2udp.bin", conf.dir);
      index ++;
      
      tt_i = (time_t)tt;
      tt_f = tt - tt_i;
      binary_fp = fopen(binary_fname, "wb+");
      
      /* Put key information into binary stream */
      fwrite(&conf.nchan, NBYTE_BIN, 1, binary_fp);                          // Number of channels
      byte_sum +=NBYTE_BIN;
      fwrite(conf.hdu->data_block->curbuf, NBYTE_BIN, conf.nchan, binary_fp);// Flux of all channels
      byte_sum +=(NBYTE_BIN * conf.nchan);
      fwrite(&tsamp_f, NBYTE_BIN, 1, binary_fp);                          // Number of channels
      byte_sum +=NBYTE_BIN;
      
      strftime (utc, MSTR_LEN, FITS_TIMESTR, gmtime(&tt_i));    // String start time without fraction second
      sprintf(utc, "%s.%04dUTC ", utc, (int)(tt_f * 1E4 + 0.5));// To put the fraction part in and make sure that it rounds to closest integer

      seconds = time (NULL);
      //loc_time = localtime (&seconds);
      strftime(utc_now, MSTR_LEN, FITS_TIMESTR, gmtime(&seconds));
	
      //fprintf(stdout, "%s\t%s,\tDELAY: %f seconds.\n", utc, utc_now, seconds - tt);
      
      fwrite(utc, 1, NBYTE_UTC, binary_fp);                     // UTC timestamps
      byte_sum +=NBYTE_UTC;
      fwrite(&conf.beam, NBYTE_BIN, 1, binary_fp);              // The beam id
      byte_sum +=NBYTE_BIN;
      
      /* Put TOS position information into binary stream*/
      if (tt - tt0 > 2.0)  // For safe, we only update metadata every 2 seconds;
	{
	  recvfrom(conf.sock_meta, (void *)buf_meta, 1<<16, 0, (struct sockaddr *)&sa_meta, &fromlen);	  
	  jsmn_init(&parser);
	  jsmn_parse(&parser, buf_meta, strlen(buf_meta), tokens, NTOKEN_META);
	  strncpy(bat, &buf_meta[tokens[2].start], tokens[2].end - tokens[2].start);  // Becareful the index here, most ugly code I do 
	  strncpy(ra, &buf_meta[tokens[27].start], tokens[27].end - tokens[27].start);
	  strncpy(dec, &buf_meta[tokens[28].start], tokens[28].end - tokens[28].start);
	  strncpy(az, &buf_meta[tokens[177].start], tokens[177].end - tokens[177].start);
	  strncpy(el, &buf_meta[tokens[178].start], tokens[178].end - tokens[178].start);
	  ra_f = atof(ra);
	  dec_f = atof(dec);
	  az_f = atof(az);
	  el_f = atof(el);

	  tt0 = tt;
	}
      conf.leap = 37;
      bat2mjd(bat, conf.leap, &mjd);
      mjd_i = (int32_t)mjd;
      mjd_f = mjd - mjd_i;
      //fprintf(stdout, "%s\t%f\t%d\t%f\n", bat, mjd * 86400.0, mjd_i, mjd_f);
      //fprintf(stdout, "%s\t%f\t", ra, ra_f);
      //fprintf(stdout, "%s\t%f\t", dec, dec_f);
      //fprintf(stdout, "%s\t%f\t", az, az_f);
      //fprintf(stdout, "%s\t%f\n", el, el_f);

      fwrite(&ra_f, NBYTE_BIN, 1, binary_fp);              // RA of boresight
      byte_sum +=NBYTE_BIN;
      fwrite(&dec_f, NBYTE_BIN, 1, binary_fp);             // DEC of boresight
      byte_sum +=NBYTE_BIN;
      fwrite(&mjd_i, NBYTE_BIN, 1, binary_fp);           // MJD int converted from BMF BAT
      byte_sum +=NBYTE_BIN;
      fwrite(&mjd_f, NBYTE_BIN, 1, binary_fp);           // MJD float converted from BMF BAT
      byte_sum +=NBYTE_BIN;
      fwrite(&az_f, NBYTE_BIN, 1, binary_fp);              // Azimuth from TOS, it is the copy from Effelsberg multicast 1602
      byte_sum +=NBYTE_BIN;
      fwrite(&el_f, NBYTE_BIN, 1, binary_fp);              // Elevation from TOS, it is the copy from Effelsberg multicast 1602
      byte_sum +=NBYTE_BIN;
      
      /* Put TOS frequency information into binary stream*/
      fwrite(&conf.freq, NBYTE_BIN, 1, binary_fp);              // The beam id
      byte_sum +=NBYTE_BIN;
      fwrite(&conf.chan_width, NBYTE_BIN, 1, binary_fp);              // The beam id
      byte_sum +=NBYTE_BIN;
      fclose(binary_fp);

      /* Read the file and sent the content with UDP socket */
      binary_fp = fopen(binary_fname, "rb");
      fread(buf_udp, byte_sum, 1, binary_fp);

      fprintf(stdout, "HERE\t%d\n", byte_sum);
      
      if(sendto(conf.sock_udp, buf_udp, byte_sum, 0, (struct sockaddr *)&sa_udp, tolen) == -1)
        {	  
	  multilog (runtime_log, LOG_ERR, "sento() failed\n");
	  fprintf(stderr, "sendto() failed, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
	  return EXIT_FAILURE;
        }

      //fprintf(stdout, "%s\n", buf_udp);
      
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

  close(conf.sock_meta);
  close(conf.sock_udp);
  
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

  if (ascii_header_get(conf->hdrbuf, "BEAM", "%ld", &conf->beam) < 0)  
    {
      multilog(runtime_log, LOG_ERR, "Error getting BEAM, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      fprintf(stderr, "Error getting BEAM, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;
    }
  //fprintf(stdout, "HERE\t%d\n", conf->beam);
  
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

int init_sock(conf_t *conf)
{
  /* Init metadata socket */
  /* create what looks like an ordinary UDP socket */
  if ((conf->sock_meta = socket(AF_INET, SOCK_DGRAM, 0)) < 0)
    {      
      multilog(runtime_log, LOG_ERR, "Can not open metadata socket\n");
      fprintf(stderr, "Can not open metadata socket, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;
    }
  /* allow multiple sockets to use the same PORT number */
  u_int yes=1;            /*** MODIFICATION TO ORIGINAL */
  if (setsockopt(conf->sock_meta,SOL_SOCKET,SO_REUSEADDR,&yes,sizeof(yes)) < 0)
    {      
      multilog(runtime_log, LOG_ERR, "Reusing ADDR failed\n");
      fprintf(stderr, "Reusing ADDR failed, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;
    }

  struct sockaddr_in addr;
  /* set up destination address */
  memset(&addr,0,sizeof(addr));
  addr.sin_family      = AF_INET;
  addr.sin_addr.s_addr = htonl(INADDR_ANY);
  addr.sin_port        = htons(conf->port_meta);

  /* bind to receive address */
  if (bind(conf->sock_meta,(struct sockaddr *) &addr,sizeof(addr)) < 0)
    {      
      multilog(runtime_log, LOG_ERR, "Bind failed\n");
      fprintf(stderr, "Bind failed, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;
    }

  /* use setsockopt() to request that the kernel join a multicast group */
  struct ip_mreq mreq;
  mreq.imr_multiaddr.s_addr = inet_addr(conf->ip_meta);
  mreq.imr_interface.s_addr = htonl(INADDR_ANY);
  if (setsockopt(conf->sock_meta, IPPROTO_IP, IP_ADD_MEMBERSHIP, &mreq,sizeof(mreq)) < 0)
    {      
      multilog(runtime_log, LOG_ERR, "setsockopt failed\n");
      fprintf(stderr, "setsockopt failed, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;
    }

  /* Create UDP socket */
  if((conf->sock_udp = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP)) == -1)
    {
      multilog(runtime_log, LOG_ERR, "socket creation failed\n");
      fprintf(stderr, "socket creation failed, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;
    }
  struct sockaddr_in si_other;
  int slen=sizeof(si_other);
  memset((char *) &si_other, 0, sizeof(si_other));
  si_other.sin_family = AF_INET;
  si_other.sin_port = htons(conf->port_udp);
  if(inet_aton(conf->ip_udp, &si_other.sin_addr) == 0) 
    {      
      multilog(runtime_log, LOG_ERR, "inet_aton() failed\n");
      fprintf(stderr, "inet_aton() failed, which happens at \"%s\", line [%d].\n", __FILE__, __LINE__);
      return EXIT_FAILURE;
    }
    
  return EXIT_SUCCESS;
}

int bat2mjd(char bat[MSTR_LEN], int leap, double *mjd)
{
  uint64_t bat_i;
  
  sscanf(bat, "%lx", &bat_i);

  //fprintf(stdout, "%f\t", *mjd);
  *mjd = (bat_i/1.0E6 - leap) / 86400.0;
  //fprintf(stdout, "%f\t%f\t", *mjd, (bat_i/1.0E6 - leap) / 86400.0);
  
  return EXIT_SUCCESS;
}


//def getDUTCDt(dt=None):
//    """
//    Get the DUTC value in seconds that applied at the given (datetime)
//    timestamp.
//    """
//    dt = dt or utc_now()
//    for i in LEAPSECONDS:
//        if i[0] < dt:
//            return i[2]
//    # Different system used before then
//    return 0
//
//# Leap seconds definition, [UTC datetime, MJD, DUTC]
//LEAPSECONDS = [
//    [datetime.datetime(2017, 1, 1, tzinfo=pytz.utc), 57754, 37],
//    [datetime.datetime(2015, 7, 1, tzinfo=pytz.utc), 57205, 36],
//    [datetime.datetime(2012, 7, 1, tzinfo=pytz.utc), 56109, 35],
//    [datetime.datetime(2009, 1, 1, tzinfo=pytz.utc), 54832, 34],
//    [datetime.datetime(2006, 1, 1, tzinfo=pytz.utc), 53736, 33],
//    [datetime.datetime(1999, 1, 1, tzinfo=pytz.utc), 51179, 32],
//    [datetime.datetime(1997, 7, 1, tzinfo=pytz.utc), 50630, 31],
//    [datetime.datetime(1996, 1, 1, tzinfo=pytz.utc), 50083, 30],
//    [datetime.datetime(1994, 7, 1, tzinfo=pytz.utc), 49534, 29],
//    [datetime.datetime(1993, 7, 1, tzinfo=pytz.utc), 49169, 28],
//    [datetime.datetime(1992, 7, 1, tzinfo=pytz.utc), 48804, 27],
//    [datetime.datetime(1991, 1, 1, tzinfo=pytz.utc), 48257, 26],
//    [datetime.datetime(1990, 1, 1, tzinfo=pytz.utc), 47892, 25],
//    [datetime.datetime(1988, 1, 1, tzinfo=pytz.utc), 47161, 24],
//    [datetime.datetime(1985, 7, 1, tzinfo=pytz.utc), 46247, 23],
//    [datetime.datetime(1993, 7, 1, tzinfo=pytz.utc), 45516, 22],
//    [datetime.datetime(1982, 7, 1, tzinfo=pytz.utc), 45151, 21],
//    [datetime.datetime(1981, 7, 1, tzinfo=pytz.utc), 44786, 20],
//    [datetime.datetime(1980, 1, 1, tzinfo=pytz.utc), 44239, 19],
//    [datetime.datetime(1979, 1, 1, tzinfo=pytz.utc), 43874, 18],
//    [datetime.datetime(1978, 1, 1, tzinfo=pytz.utc), 43509, 17],
//    [datetime.datetime(1977, 1, 1, tzinfo=pytz.utc), 43144, 16],
//    [datetime.datetime(1976, 1, 1, tzinfo=pytz.utc), 42778, 15],
//    [datetime.datetime(1975, 1, 1, tzinfo=pytz.utc), 42413, 14],
//    [datetime.datetime(1974, 1, 1, tzinfo=pytz.utc), 42048, 13],
//    [datetime.datetime(1973, 1, 1, tzinfo=pytz.utc), 41683, 12],
//    [datetime.datetime(1972, 7, 1, tzinfo=pytz.utc), 41499, 11],
//    [datetime.datetime(1972, 1, 1, tzinfo=pytz.utc), 41317, 10],
//]
//"# Leap seconds definition, [UTC datetime, MJD, DUTC]"
//
//def bat2utc(bat, dutc=None):
//    """
//    Convert Binary Atomic Time (BAT) to UTC.  At the ATNF, BAT corresponds to
//    the number of microseconds of atomic clock since MJD (1858-11-17 00:00).
//
//    :param bat: number of microseconds of atomic clock time since
//        MJD 1858-11-17 00:00.
//    :type bat: long
//    :returns utcDJD: UTC date and time (Dublin Julian Day as used by pyephem)
//    :rtype: float
//
//    """
//    dutc = dutc or getDUTCDt()
//    if type(bat) is str:
//        bat = long(bat, base=16)
//    utcMJDs = (bat/1000000.0)-dutc
//    utcDJDs = utcMJDs-86400.0*15019.5
//    utcDJD = utcDJDs/86400.0
//    return utcDJD + 2415020 - 2400000.5
//
//def utc_now():
//    """
//    Return current UTC as a timezone aware datetime.
//    :rtype: datetime
//    """
//    dt=datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
//    return dt
