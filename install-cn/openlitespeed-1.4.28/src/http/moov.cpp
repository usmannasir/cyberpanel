/*****************************************************************************
*    Open LiteSpeed is an open source HTTP server.                           *
*    Copyright (C) 2013 - 2015  LiteSpeed Technologies, Inc.                 *
*                                                                            *
*    This program is free software: you can redistribute it and/or modify    *
*    it under the terms of the GNU General Public License as published by    *
*    the Free Software Foundation, either version 3 of the License, or       *
*    (at your option) any later version.                                     *
*                                                                            *
*    This program is distributed in the hope that it will be useful,         *
*    but WITHOUT ANY WARRANTY; without even the implied warranty of          *
*    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the            *
*    GNU General Public License for more details.                            *
*                                                                            *
*    You should have received a copy of the GNU General Public License       *
*    along with this program. If not, see http://www.gnu.org/licenses/.      *
*****************************************************************************/
#include "moov.h"
#include "moovP.h"

#include <lsdef.h>

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>


#ifndef MAP_FILE
#define MAP_FILE 0
#endif //MAP_FILE


static uint64_t bytes_read(unsigned char *buf, int count);
static int boxheader_read(unsigned char *buf, boxheader_t *header,
                          unsigned char *boundry);
static int boxheader_read_file(int fd, off_t pos, box_in_file_t *box);
static int moov_read(unsigned char *buf, void *box);
static int mvhd_read(unsigned char *buf, void *box);
static int trak_read(unsigned char *buf, void *box);
static int tkhd_read(unsigned char *buf, void *box);
static int mdia_read(unsigned char *buf, void *box);
static int mdhd_read(unsigned char *buf, void *box);
static int minf_read(unsigned char *buf, void *box);
static int stbl_read(unsigned char *buf, void *box);
static int stsc_read(unsigned char *buf, void *box);
static int stts_read(unsigned char *buf, void *box);
static int stsz_read(unsigned char *buf, void *box);
static int stco_co64_read(unsigned char *buf, void *box);
static int stss_read(unsigned char *buf, void *box);
static int ctts_read(unsigned char *buf, void *box);
static int stsd_read(unsigned char *buf, void *box);

static unsigned char *bytes_write(unsigned char *buf, int count,
                                  uint64_t ui);
static unsigned char *boxheader_write(unsigned char *buf,
                                      boxheader_t *header);
static unsigned char *stsc_write(unsigned char *dst, void *box);
static unsigned char *stts_write(unsigned char *dst, void *box);
static unsigned char *stsz_write(unsigned char *dst, void *box,
                                 int no_size_table);
static unsigned char *stco_co64_write(unsigned char *dst, void *box);
static unsigned char *stss_write(unsigned char *dst, void *box);

static uint32_t stsc_adjust(stsc_t *stsc, uint32_t c1, uint32_t c2,
                            unsigned char *stsc_entries);
static uint32_t stts_adjust(stts_t *stts, uint32_t s1, uint32_t s2,
                            unsigned char *stts_entries);
static uint32_t stsz_adjust(stsz_t *stsz, uint32_t s1, uint32_t s2);
static uint32_t stco_co64_adjust(stco_co64_t *stco_co64, uint32_t c1,
                                 uint32_t c2);
static uint32_t stss_adjust(stss_t *stss, uint32_t s1, uint32_t s2);
static uint32_t ctts_adjust(ctts_t *ctts, uint32_t s1, uint32_t s2);

static int calc_new_moov_diff(moov_t *moov_box, float start_time,
                              float end_time);
static uint32_t duration_to_sample(uint64_t duration,
                                   unsigned char *stts_entries, uint32_t count);
static uint32_t sample_to_chunk(uint32_t sample,
                                unsigned char *stsc_entries, uint32_t count, uint32_t max_chunk,
                                uint32_t  *chunkFirstSample, uint32_t *chunkLastSample);
static uint32_t sample_to_duration(uint32_t s1, uint32_t s2,
                                   unsigned char  *stts_entries, uint32_t count);
static uint64_t trak_max_offset_new(stbl_t *stbl, uint32_t chunk,
                                    moov_t *moov);

static int mini_moov_calc_size(moov_t *box);
static int mini_moov_write(unsigned char *buf, moov_t *box);
static int mini_moov_read(unsigned char *buf, moov_t *moov_box);
static int moov_write_chunk(moov_data_t     *moov_data, moov_t *moov_box);

static int moov_getpagesize()
{
    static int s_pagesize = 0;
    if (!s_pagesize)
        s_pagesize = sysconf(_SC_PAGESIZE);
    return s_pagesize;
}


/*    return: -1 -- error. not an mp4/mov/f4v file or invalid file
 *             1 -- return mini_moov
 */
int get_mini_moov(int fd,                    //in - video file descriptor
                  unsigned char **mini_moov,     //in-out
                  uint32_t *mini_moov_size)     //in-out
{
    moov_t moov;
    struct stat status;
    uint64_t file_size, pos;

    box_in_file_t moov_box;
    box_in_file_t mdat_box;
    box_in_file_t worker_box;

    memset(&moov_box, 0, sizeof(moov_box));
    memset(&mdat_box, 0, sizeof(mdat_box));
    memset(&moov, 0, sizeof(moov));
    unsigned char *moov_data = 0;
    void *mmap_data = NULL;
    int mmap_size = 0;
    int r, fail;

    if (fstat(fd, &status) == -1)
    {
#ifdef UNIT_TEST
        printf("Error: failed to get media file length/stat\n");
#endif
        return (-1);
    }
    file_size = status.st_size;

    pos = 0;
    while (pos < file_size)
    {
        if (!boxheader_read_file(fd, pos, &worker_box))
            break;

        switch (worker_box.header.BoxType)
        {
        case FourCC('m', 'o', 'o', 'v'):
            if (moov_box.end !=
                0)  //An F4V file must contain one and only one moov box
            {
#ifdef UNIT_TEST
                printf("Error: there are 2 more moov boxes\n");
#endif
                return (-1);
            }
            moov_box = worker_box;
            if (moov_box.header.ExtendedSize >= file_size)
                return (-1);
            break;
        case FourCC('m', 'd', 'a', 't'):
            if (mdat_box.end !=
                0)  //An F4V file must contain one and only one mdat box
            {
#ifdef UNIT_TEST
                printf("Error: there are 2 more mdat boxes\n");
#endif
                return LS_FAIL;
            }
            mdat_box = worker_box;
            break;
        }
        if (worker_box.header.ExtendedSize <= 0)
            return LS_FAIL;
        pos += worker_box.header.ExtendedSize;
    }

    if (moov_box.header.ExtendedSize == 0)
    {
#ifdef UNIT_TEST
        printf("Error: moov box not found\n");
#endif
        return LS_FAIL;
    }
    if (mdat_box.header.ExtendedSize == 0)
    {
#ifdef UNIT_TEST
        printf("Error: mdat box not found\n");
#endif
        return LS_FAIL;
    }
    mmap_size = (size_t)moov_box.header.ExtendedSize + moov_box.start %
                moov_getpagesize();
    off_t map_start = moov_box.start - moov_box.start % moov_getpagesize();

    mmap_data = mmap(NULL, mmap_size, PROT_READ,
                     MAP_SHARED | MAP_FILE, fd, map_start);
    if (!mmap_data)
        return LS_FAIL;
    moov_data = (unsigned char *)mmap_data + moov_box.start %
                moov_getpagesize();
    /*
    moov_data = (unsigned char*)malloc((size_t)moov_box.header.ExtendedSize);
    if(pread(fd, moov_data, (size_t)moov_box.header.ExtendedSize,moov_box.start)<=0)
    {
    #ifdef UNIT_TEST
        printf("Error: failed to reading moov box\n");
    #endif
        free(moov_data);
        return(-1);
    }
    */

    unsigned char *buf = NULL;
    fail = 0;
    do
    {
        moov_box.header.start = moov_data;
        moov.header = moov_box.header;
        moov.offset_in_file = moov_box.start;
        r = moov_read(moov_data, (void *)& moov);
        if (r == 0)
        {
            fail = 1;
            break;
        }

        mini_moov_calc_size(&moov);
        moov.mdat_header_length = mdat_box.header.length;
        moov.mdat_start_offset = mdat_box.start;
        moov.mdat_end_offset = mdat_box.end;
        buf = (unsigned char *)calloc((size_t)moov.header.ExtendedSize, 1);
        r = mini_moov_write(buf, &moov);
        break;
    }
    while (1);

    //free(moov_data);
    munmap(mmap_data, mmap_size);
    if (fail == 1)
    {
        if (buf)
            free(buf);
        return (-1);
    }
    else
    {
        *mini_moov = buf;
        *mini_moov_size = (uint32_t)moov.header.ExtendedSize;
        return (1);
    }
}


int get_moov(int
             fd,                            //in - video file descriptor
             float start_time,            //in - seconds
             float end_time,                //in - seconds. 0 means end of moovie
             moov_data_t     *moov_data,    //out - store returned moov data
             unsigned char *mini_moov,     //in
             uint32_t mini_moov_size)    //in
{
    moov_t moov;
    boxheader_t dummy;

    int r, fail, i;
    int64_t t;

    memset(&moov, 0, sizeof(moov));
    fail = 0;
    do
    {
        boxheader_read(mini_moov, &dummy, mini_moov + mini_moov_size);
        moov.header = dummy;

        r = mini_moov_read(mini_moov, & moov);
        if (r == 0)
        {
            fail = 1;
            break;
        }

        r = calc_new_moov_diff(&moov, start_time, end_time);
        if (r == 0)
        {
            fail = 1;
            break;
        }

        t = (int64_t)(moov.header.ExtendedSize + moov.header.deltaSize     -
                      moov.mdat_start_offset + moov.mdat_header_length);

        for (i = 0; i < moov.track_num; i++)
            moov.trak[i].mdia.minf.stbl.stco_co64.deltaOffset = t;

        moov_write_chunk(moov_data, & moov);
        break;
    }
    while (1);

    if (fail == 1)
        return (-1);
    else
    {
        if (moov_data->remaining_bytes == 0)
            return (1);
        else
            return (0);
    }
}


int get_mdat(int
             fd,                            //in - video file descriptor
             float start_time,            //in - seconds
             float end_time,                //in - seconds. 0 means end of moovie
             uint64_t *mdat_start,        //out
             uint64_t *mdat_size,        //out
             int *mdat_64bit,             //out
             unsigned char *mini_moov,     //in
             uint32_t mini_moov_size)    //in
{
    moov_t moov;
    boxheader_t dummy;

    int r, fail;

    memset(&moov, 0, sizeof(moov));
    fail = 0;
    do
    {
        boxheader_read(mini_moov, &dummy, mini_moov + mini_moov_size);
        moov.header = dummy;

        r = mini_moov_read(mini_moov, & moov);
        if (r == 0)
        {
            fail = 1;
            break;
        }
        r = calc_new_moov_diff(&moov, start_time, end_time);
        if (r == 0)
        {
            fail = 1;
            break;
        }
        break;
    }
    while (1);

    if (fail == 1)
        return (-1);
    else
    {
        *mdat_start = moov.mdat_start_offset;
        *mdat_size = moov.mdat_end_offset - moov.mdat_start_offset;
        if (moov.mdat_header_length == 16)
            *mdat_64bit = 1;
        else
            *mdat_64bit = 0;
        return (1);
    }
}


// count = one of [1,2,3,4,8]
static uint64_t bytes_read(unsigned char *buf, int count)
{
    int i;
    uint64_t r = buf[0];

    for (i = 1; i < count; i++)
    {
        r <<= 8;
        r |= buf[i];
    }
    return r;
}


//0:exceed boundry;
//1:successful
static int boxheader_read(unsigned char *buf, boxheader_t *header,
                          unsigned char *boundry)
{
    uint32_t t;

    if (buf + 8 > boundry)
        return (0);
    t = bytes_read(buf, 4);
    header->TotalSize = t;
    header->BoxType = bytes_read(buf + 4, 4);
    header->start = buf;
    if (t == 1)
    {
        if (buf + 16 > boundry)
            return (0);
        header->ExtendedSize = bytes_read(buf + 8, 8);
        header->length = 16;
    }
    else
    {
        header->ExtendedSize = t;
        header->length = 8;
    }
#ifdef UNIT_TEST
    printf("Box(%c%c%c%c,%u)\n",
           header->BoxType >> 24, header->BoxType >> 16,
           header->BoxType >> 8, header->BoxType,
           (uint32_t)header->ExtendedSize);
#endif
    header->deltaSize = 0;
    return (1);
}


static int boxheader_read_file(int fd, off_t pos, box_in_file_t *box)
{
    unsigned char buf[32];
    boxheader_t header;
    uint32_t t;

    box->start = pos;
    if (pread(fd, buf, 8, pos) != 8)
    {
#ifdef UNIT_TEST
        printf("Error: reading box header from file\n");
#endif
        return (0);
    }
    t = bytes_read(buf, 4);
    if (t == 1)
    {
        if (pread(fd, buf, 16, pos) != 16)
        {
#ifdef UNIT_TEST
            printf("Error: reading box header from file\n");
#endif
            return (0);
        }
    }

    boxheader_read(buf, &header, buf + 32);

    box->header = header;
    box->end = box->start + header.ExtendedSize;

    return (1);
}


static int moov_read(unsigned char *buf, void *box)
{
//Header BOXHEADER BoxType = 'moov' (0x6D6F6F76)
//Boxes     BOX[] Many other boxes which define the structure

    moov_t *moov_box = (moov_t *) box;
    unsigned char *boundry = buf + moov_box->header.ExtendedSize;
    unsigned char *sub_buf = buf + moov_box->header.length;
    boxheader_t dummy;
    int r, i, trak_index = -1;

    while (sub_buf < boundry)
    {
        r = boxheader_read(sub_buf, &dummy, boundry);
        if (r == 0)
        {
#ifdef UNIT_TEST
            printf("Error: 1 of moov's sub boxes size not right\n");
#endif
            return (0);
        }
        switch (dummy.BoxType)
        {
        case FourCC('m', 'v', 'h', 'd'):
            moov_box->mvhd.header = dummy;
            r = mvhd_read(sub_buf, (void *)&moov_box->mvhd);
            if (r == 0)
            {
#ifdef UNIT_TEST
                printf("moov-->mvhd error\n");
#endif
                return (0);
            }
            break;
        case FourCC('t', 'r', 'a', 'k'):
            trak_index++;
            if (trak_index == MAX_TRACKS)
            {
#ifdef UNIT_TEST
                printf("too many tracks:exceed MAX_TACKS=%d\n", MAX_TRACKS);
#endif
                return (0);
            }
            moov_box->trak[trak_index].header = dummy;
            r = trak_read(sub_buf, (void *)&moov_box->trak[trak_index]);
            if (r == 0)
            {
#ifdef UNIT_TEST
                printf("moov-->trak[%d] error\n", trak_index);
#endif
                return (0);
            }
            break;
        case FourCC('c', 'h', 'p', 'l'):
            //not implemented in known Open Source yet
            //delete it at the time being
            moov_box->header.deltaSize += -1 *
                                          dummy.ExtendedSize; //possibly multiple "chpl" boxes
            break;
        default:
            moov_box->header.deltaSize += -1 *
                                          dummy.ExtendedSize; //optimization: delete all other boxes
            break;
        }
        sub_buf += dummy.ExtendedSize;
    }
    if (trak_index == -1)
    {
#ifdef UNIT_TEST
        printf("Error: no trak in moov\n");
#endif
        return (0);
    }
    moov_box->track_num = trak_index + 1;
    if (sub_buf == boundry)
    {
        stbl_t *stbl;
        for (i = 0; i < moov_box->track_num; i++)
        {
            stbl = & moov_box->trak[i].mdia.minf.stbl;
            stbl->stco_co64.offset_in_file = moov_box->offset_in_file +
                                             (stbl->stco_co64.header.start - moov_box->header.start) +
                                             stbl->stco_co64.header.length + 1 + 3 + 4;
            stbl->stsz.offset_in_file = moov_box->offset_in_file +
                                        (stbl->stsz.header.start - moov_box->header.start) +
                                        stbl->stsz.header.length + 1 + 3 + 4 + 4;
        }
        return (1);
    }
    else
    {
#ifdef UNIT_TEST
        printf("sub boxes size of moov not match exactly\n");
#endif
        return (0);
    }
}


static int mvhd_read(unsigned char *buf, void *box)
{
    mvhd_t *mvhd_box = (mvhd_t *)box;
    unsigned char *boundry = buf + mvhd_box->header.ExtendedSize;
    unsigned char *sub_buf = buf + mvhd_box->header.length;
    uint32_t v;

    if (sub_buf + 1 + 3 >= boundry)
    {
#ifdef UNIT_TEST
        printf("Error: mvhd box too small and wrong\n");
#endif
        return (0);
    }
    v = bytes_read(sub_buf, 1);
    mvhd_box->Version = v;
    sub_buf += 1 + 3;
    switch (v)
    {
    case 0:
        if (sub_buf + 4 * 4 >= boundry)
        {
#ifdef UNIT_TEST
            printf("Error: mvhd box too small and wrong\n");
#endif
            return (0);
        }
        sub_buf += 4 * 2;
        mvhd_box->TimeScale = bytes_read(sub_buf, 4);
        sub_buf += 4;
        mvhd_box->Duration = (uint64_t)bytes_read(sub_buf, 4);
        break;
    case 1:
        if (sub_buf + 8 * 3 + 4 >= boundry)
        {
#ifdef UNIT_TEST
            printf("Error: mvhd box too small and wrong\n");
#endif
            return (0);
        }
        sub_buf += 8 * 2;
        mvhd_box->TimeScale = bytes_read(sub_buf, 4);
        sub_buf += 4;
        mvhd_box->Duration = bytes_read(sub_buf, 8);
        break;
    default:
#ifdef UNIT_TEST
        printf("mvhd wrong Version\n");
#endif
        return (0);
    }
    return (1);
}


static int trak_read(unsigned char *buf, void *box)
{
//Header BOXHEADER BoxType = 'trak' (0x7472616B)
//Boxes BOX[] Arbitrary number

    trak_t *trak_box = (trak_t *)box;
    unsigned char *boundry = buf + trak_box->header.ExtendedSize;
    unsigned char *sub_buf = buf + trak_box->header.length;
    boxheader_t dummy;
    int r;

    while (sub_buf < boundry)
    {
        r = boxheader_read(sub_buf, &dummy, boundry);
        if (r == 0)
        {
#ifdef UNIT_TEST
            printf("Error: 1 of trak's sub boxes size not right\n");
#endif
            return (0);
        }
        switch (dummy.BoxType)
        {
        case FourCC('t', 'k', 'h', 'd'):
            trak_box->tkhd.header = dummy;
            r = tkhd_read(sub_buf, (void *)&trak_box->tkhd);
            if (r == 0)
            {
#ifdef UNIT_TEST
                printf("moov-->trak->tkhd error\n");
#endif
                return (0);
            }
            break;
        case FourCC('m', 'd', 'i', 'a'):
            trak_box->mdia.header = dummy;
            r = mdia_read(sub_buf, (void *)&trak_box->mdia);
            if (r == 0)
            {
#ifdef UNIT_TEST
                printf("moov-->trak->mdia error\n");
#endif
                return (0);
            }
            break;
        default:
            trak_box->header.deltaSize += -1 *
                                          dummy.ExtendedSize; //optimization: delete all other boxes
            break;
        }
        sub_buf += dummy.ExtendedSize;
    }
    if (sub_buf == boundry)
        return (1);
    else
    {
#ifdef UNIT_TEST
        printf("sub boxes size of trak not match exactly\n");
#endif
        return (0);
    }
}


static int tkhd_read(unsigned char *buf, void *box)
{
    tkhd_t *tkhd_box = (tkhd_t *)box;
    unsigned char *boundry = buf + tkhd_box->header.ExtendedSize;
    unsigned char *sub_buf = buf + tkhd_box->header.length;
    uint32_t v;

    if (sub_buf + 1 + 3 >= boundry)
    {
#ifdef UNIT_TEST
        printf("Error: tkhd box too small and wrong\n");
#endif
        return (0);
    }
    v = bytes_read(sub_buf, 1);
    tkhd_box->Version = v;
    sub_buf += 1;
    tkhd_box->Flags = bytes_read(sub_buf, 3);
    sub_buf += 3;
    //now we ignored Flags at the time being
    //    UI24    Flags;            //Bit 0: this bit is set if the track is enabled
    //                            //Bit 1 = this bit is set if the track is part of the presentation
    //                            //Bit 2 = this bit is set if the track should be considered when previewing the F4V file
    switch (v)
    {
    case 0:
        if (sub_buf + 4 * 5 >= boundry)
        {
#ifdef UNIT_TEST
            printf("Error: tkhd box too small and wrong\n");
#endif
            return (0);
        }
        sub_buf += 4 * 2;
        //tkhd_box->TrackID = bytes_read(sub_buf,4);
        sub_buf += 4 * 2;
        tkhd_box->Duration = (uint64_t)bytes_read(sub_buf, 4);
        break;
    case 1:
        if (sub_buf + 8 * 3 + 4 * 2 >= boundry)
        {
#ifdef UNIT_TEST
            printf("Error: tkhd box too small and wrong\n");
#endif
            return (0);
        }
        sub_buf += 8 * 2;
        //tkhd_box->TrackID = bytes_read(sub_buf,4);
        sub_buf += 4 * 2;
        tkhd_box->Duration = bytes_read(sub_buf, 8);
        break;
    default:
#ifdef UNIT_TEST
        printf("tkhd wrong Version -- not supported\n");
#endif
        return (0);
    }

    return (1);
}


static int mdia_read(unsigned char *buf, void *box)
{
//Header BOXHEADER BoxType = 'mdia' (0x6D646961)
//Boxes BOX[] Arbitrary number of boxes that define media track properties

    mdia_t *mdia_box = (mdia_t *)box;
    unsigned char *boundry = buf + mdia_box->header.ExtendedSize;
    unsigned char *sub_buf = buf + mdia_box->header.length;
    boxheader_t dummy;
    int r;

    while (sub_buf < boundry)
    {
        r = boxheader_read(sub_buf, &dummy, boundry);
        if (r == 0)
        {
#ifdef UNIT_TEST
            printf("Error: 1 of trak's sub boxes size not right\n");
#endif
            return (0);
        }
        switch (dummy.BoxType)
        {
        case FourCC('m', 'd', 'h', 'd'):
            mdia_box->mdhd.header = dummy;
            r = mdhd_read(sub_buf, (void *)&mdia_box->mdhd);
            if (r == 0)
            {
#ifdef UNIT_TEST
                printf("moov-->trak->mdia->mdhd error\n");
#endif
                return (0);
            }
            break;
        case FourCC('m', 'i', 'n', 'f'):
            mdia_box->minf.header = dummy;
            r = minf_read(sub_buf, (void *)&mdia_box->minf);
            if (r == 0)
            {
#ifdef UNIT_TEST
                printf("moov-->trak->mdia->minf error\n");
#endif
                return (0);
            }
            break;
        default:
            mdia_box->header.deltaSize += -1 *
                                          dummy.ExtendedSize; //optimization: delete all other boxes
            break;
        }
        sub_buf += dummy.ExtendedSize;
    }
    if (sub_buf == boundry)
        return (1);
    else
    {
#ifdef UNIT_TEST
        printf("sub boxes size of mdia not match exactly\n");
#endif
        return (0);
    }
}


static int mdhd_read(unsigned char *buf, void *box)
{
    mdhd_t *mdhd_box = (mdhd_t *)box;
    unsigned char *boundry = buf + mdhd_box->header.ExtendedSize;
    unsigned char *sub_buf = buf + mdhd_box->header.length;
    uint32_t v;

    if (sub_buf + 1 + 3 >= boundry)
    {
#ifdef UNIT_TEST
        printf("Error: mdhd box too small and wrong\n");
#endif
        return (0);
    }
    v = bytes_read(sub_buf, 1);
    mdhd_box->Version = v;
    sub_buf += 1 + 3;
    switch (v)
    {
    case 0:
        if (sub_buf + 4 * 4 >= boundry)
        {
#ifdef UNIT_TEST
            printf("Error: mdhd box too small and wrong\n");
#endif
            return (0);
        }
        sub_buf += 4 * 2;
        mdhd_box->TimeScale = bytes_read(sub_buf, 4);
        sub_buf += 4;
        mdhd_box->Duration = bytes_read(sub_buf, 4);
        break;
    case 1:
        if (sub_buf + 8 * 3 + 4 >= boundry)
        {
#ifdef UNIT_TEST
            printf("Error: mdhd box too small and wrong\n");
#endif
            return (0);
        }
        sub_buf += 8 * 2;
        mdhd_box->TimeScale = bytes_read(sub_buf, 4);
        sub_buf += 4;
        mdhd_box->Duration = bytes_read(sub_buf, 8);
        break;
    default:
#ifdef UNIT_TEST
        printf("mvhd wrong Version\n");
#endif
        return (0);
    }

    return (1);
}


static int minf_read(unsigned char *buf, void *box)
{
//Header BOXHEADER BoxType = 'minf' (0x6D696E66)
//Boxes BOX[] Arbitrary number of boxes that define the track��s media information

    minf_t *minf_box = (minf_t *)box;
    unsigned char *boundry = buf + minf_box->header.ExtendedSize;
    unsigned char *sub_buf = buf + minf_box->header.length;
    boxheader_t dummy;
    int r;

    while (sub_buf < boundry)
    {
        r = boxheader_read(sub_buf, &dummy, boundry);
        if (r == 0)
        {
#ifdef UNIT_TEST
            printf("Error: 1 of minf's sub boxes size not right\n");
#endif
            return (0);
        }
        switch (dummy.BoxType)
        {
        case FourCC('s', 't', 'b', 'l'):
            minf_box->stbl.header = dummy;
            r = stbl_read(sub_buf, (void *)&minf_box->stbl);
            if (r == 0)
            {
#ifdef UNIT_TEST
                printf("moov-->trak->mdia->minf error\n");
#endif
                return (0);
            }
            break;
        default:
            minf_box->header.deltaSize += -1 *
                                          dummy.ExtendedSize; //optimization: delete all other boxes
            break;
        }
        sub_buf += dummy.ExtendedSize;
    }
    if (sub_buf == boundry)
        return (1);
    else
    {
#ifdef UNIT_TEST
        printf("sub boxes size of minf not match exactly\n");
#endif
        return (0);
    }
}


static int stbl_read(unsigned char *buf, void *box)
{
//Header BOXHEADER BoxType = 'stbl' (0x7374626C)
//Boxes BOX[] Arbitrary number of boxes that define properties about the track��s constituent samples

    stbl_t *stbl_box = (stbl_t *)box;
    unsigned char *boundry = buf + stbl_box->header.ExtendedSize;
    unsigned char *sub_buf = buf + stbl_box->header.length;
    boxheader_t dummy;
    int r;

    while (sub_buf < boundry)
    {
        r = boxheader_read(sub_buf, &dummy, boundry);
        if (r == 0)
        {
#ifdef UNIT_TEST
            printf("Error: 1 of stbl's sub boxes size not right\n");
#endif
            return (0);
        }
        switch (dummy.BoxType)
        {
        case FourCC('s', 't', 's', 'c'):
            stbl_box->stsc.header = dummy;
            r = stsc_read(sub_buf, (void *)&stbl_box->stsc);
            if (r == 0)
            {
#ifdef UNIT_TEST
                printf("moov-->trak->mdia->minf->stbl->stsc error\n");
#endif
                return (0);
            }
            break;
        case FourCC('s', 't', 't', 's'):
            stbl_box->stts.header = dummy;
            r = stts_read(sub_buf, (void *)&stbl_box->stts);
            if (r == 0)
            {
#ifdef UNIT_TEST
                printf("moov-->trak->mdia->minf->stbl->stts error\n");
#endif
                return (0);
            }
            break;
        case FourCC('s', 't', 's', 'z'):
            stbl_box->stsz.header = dummy;
            r = stsz_read(sub_buf, (void *)&stbl_box->stsz);
            if (r == 0)
            {
#ifdef UNIT_TEST
                printf("moov-->trak->mdia->minf->stbl->stsz error\n");
#endif
                return (0);
            }
            break;
        case FourCC('s', 't', 'c', 'o'):
        case FourCC('c', 'o', '6', '4'):
            stbl_box->stco_co64.header = dummy;
            r = stco_co64_read(sub_buf, (void *)&stbl_box->stco_co64);
            if (r == 0)
            {
#ifdef UNIT_TEST
                printf("moov-->trak->mdia->minf->stbl->stco/co64 error\n");
#endif
                return (0);
            }
            break;
        case FourCC('s', 't', 's', 's'):
            stbl_box->stss.header = dummy;
            r = stss_read(sub_buf, (void *)&stbl_box->stss);
            if (r == 0)
            {
#ifdef UNIT_TEST
                printf("moov-->trak->mdia->minf->stbl->stss error\n");
#endif
                return (0);
            }
            break;
        case FourCC('c', 't', 't', 's'):
            stbl_box->ctts.header = dummy;
            r = ctts_read(sub_buf, (void *)&stbl_box->ctts);
            if (r == 0)
            {
#ifdef UNIT_TEST
                printf("moov-->trak->mdia->minf->stbl->ctts error\n");
#endif
                return (0);
            }
            break;
        case FourCC('s', 't', 's', 'd'):
            stbl_box->stsd.header = dummy;
            r = stsd_read(sub_buf, (void *)&stbl_box->stsd);
            if (r == 0)
            {
#ifdef UNIT_TEST
                printf("moov-->trak->mdia->minf->stbl->stsd error\n");
#endif
                return (0);
            }
            break;
        default:
            stbl_box->header.deltaSize += -1 *
                                          dummy.ExtendedSize; //optimization: delete all other boxes
            break;
        }
        sub_buf += dummy.ExtendedSize;
    }
    if (sub_buf == boundry)
        return (1);
    else
    {
#ifdef UNIT_TEST
        printf("sub boxes size of stbl not match exactly\n");
#endif
        return (0);
    }
}


static int stsc_read(unsigned char *buf, void *box)
{
    stsc_t *stsc_box = (stsc_t *)box;
    unsigned char *boundry = buf + stsc_box->header.ExtendedSize;
    unsigned char *sub_buf = buf + stsc_box->header.length;
    uint32_t v;

    if (sub_buf + 1 + 3 + 4 >= boundry)
    {
#ifdef UNIT_TEST
        printf("Error: stsc box too small and wrong\n");
#endif
        return (0);
    }
    v = bytes_read(sub_buf + 1 + 3, 4);
    stsc_box->Count = v;
    sub_buf += 1 + 3 + 4;
    if (sub_buf + 3 * 4 * v > boundry)
    {
#ifdef UNIT_TEST
        printf("Error: stsc exceed boundry\n");
#endif
        return (0);
    }
    else if (sub_buf + 3 * 4 * v != boundry)
    {
#ifdef UNIT_TEST
        printf("Warn: stsc size not exactly match\n");
#endif
    }
    stsc_box->Entries = sub_buf;
    return (1);
}


static int stts_read(unsigned char *buf, void *box)
{
    stts_t *stts_box = (stts_t *)box;
    unsigned char *boundry = buf + stts_box->header.ExtendedSize;
    unsigned char *sub_buf = buf + stts_box->header.length;
    uint32_t v;

    if (sub_buf + 1 + 3 + 4 >= boundry)
    {
#ifdef UNIT_TEST
        printf("Error: stts box too small and wrong\n");
#endif
        return (0);
    }
    v = bytes_read(sub_buf + 1 + 3, 4);
    stts_box->Count = v;
    sub_buf += 1 + 3 + 4;
    if (sub_buf + 2 * 4 * v > boundry)
    {
#ifdef UNIT_TEST
        printf("Error: stts exceed boundry\n");
#endif
        return (0);
    }
#ifdef UNIT_TEST
    else if (sub_buf + 2 * 4 * v != boundry)
        printf("Warn: stts size not exactly match\n");
#endif

    stts_box->Entries = sub_buf;
    return (1);
}


static int stsz_read(unsigned char *buf, void *box)
{
    stsz_t *stsz_box = (stsz_t *)box;
    unsigned char *boundry = buf + stsz_box->header.ExtendedSize;
    unsigned char *sub_buf = buf + stsz_box->header.length;
    uint32_t v;

    if (sub_buf + 1 + 3 + 4 * 2 >= boundry)
    {
#ifdef UNIT_TEST
        printf("Error: stsz box too small and wrong\n");
#endif
        return (0);
    }
    sub_buf += 1 + 3;
    v = bytes_read(sub_buf, 4);
    stsz_box->ConstantSize =
        v;    //If all samples have the same size, this field is set with that constant size;otherwise it is 0
    sub_buf += 4;
    stsz_box->SizeCount = bytes_read(sub_buf, 4);
    sub_buf += 4;
    if (v == 0)
    {
        v = stsz_box->SizeCount;
        if (sub_buf + v * 4 > boundry)
        {
#ifdef UNIT_TEST
            printf("Error: stsz exceed boundry\n");
#endif
            return (0);
        }
        stsz_box->SizeTable = (UI32 *)sub_buf;
    }
#ifdef UNIT_TEST
    else
        v = 0;
    if (sub_buf + v * 4 != boundry)
        printf("Warn: stsz size not exactly match\n");
#endif

    return (1);
}


static int stco_co64_read(unsigned char *buf, void *box)
{
    stco_co64_t *stco_co64_box = (stco_co64_t *)box;
    unsigned char *boundry = buf + stco_co64_box->header.ExtendedSize;
    unsigned char *sub_buf = buf + stco_co64_box->header.length;
    uint32_t v, t = 0;

    if (sub_buf + 1 + 3 + 4 >= boundry)
    {
#ifdef UNIT_TEST
        printf("Error: stco_co64 box too small and wrong\n");
#endif
        return (0);
    }
    sub_buf += 1 + 3;
    v = bytes_read(sub_buf, 4);
    stco_co64_box->OffsetCount = v;
    sub_buf += 4;
    switch (stco_co64_box->header.BoxType)
    {
    case FourCC('s', 't', 'c', 'o'):
        t = 4;
        break;
    case FourCC('c', 'o', '6', '4'):
        t = 8;
        break;
    }
    if (sub_buf + t * v > boundry)
    {
#ifdef UNIT_TEST
        printf("Error: stsz exceed boundry\n");
#endif
        return (0);
    }
    stco_co64_box->Offsets = sub_buf;
#ifdef UNIT_TEST
    if (sub_buf + t * v != boundry)
        printf("Warn: stco_co64 size not exactly match\n");
#endif

    return (1);
}


static int stss_read(unsigned char *buf, void *box)
{
    stss_t *stss_box = (stss_t *)box;
    unsigned char *boundry = buf + stss_box->header.ExtendedSize;
    unsigned char *sub_buf = buf + stss_box->header.length;
    uint32_t v;

    if (sub_buf + 1 + 3 + 4 >= boundry)
    {
#ifdef UNIT_TEST
        printf("Error: stss box too small and wrong\n");
#endif
        return (0);
    }
    sub_buf += 1 + 3;
    v = bytes_read(sub_buf, 4);
    stss_box->SyncCount = v;
    sub_buf += 4;
    if (sub_buf + 4 * v > boundry)
    {
#ifdef UNIT_TEST
        printf("Error: stss exceed boundry\n");
#endif
        return (0);
    }
#ifdef UNIT_TEST
    else if (sub_buf + 4 * v != boundry)
        printf("Warn: stss not size exactly match\n");
#endif
    stss_box->SyncTable = (void *)sub_buf;
    return (1);
}


static int ctts_read(unsigned char *buf, void *box)
{
    ctts_t *ctts_box = (ctts_t *)box;
    unsigned char *boundry = buf + ctts_box->header.ExtendedSize;
    unsigned char *sub_buf = buf + ctts_box->header.length;
    uint32_t v;

    if (sub_buf + 4 >= boundry)
    {
#ifdef UNIT_TEST
        printf("Error: ctts box too small and wrong\n");
#endif
        return (0);
    }
    v = bytes_read(sub_buf, 4);
    ctts_box->Count = v;
    sub_buf += 4;
    if (sub_buf + 8 * v > boundry)
    {
#ifdef UNIT_TEST
        printf("Error: ctts exceed boundry\n");
#endif
        return (0);
    }
#ifdef UNIT_TEST
    else if (sub_buf + 8 * v != boundry)
        printf("Warn: ctts not size exactly match.Count=%u,ExtendedSize=%u\n", v,
               (uint32_t)ctts_box->header.ExtendedSize);
#endif
    ctts_box->Entries = sub_buf;
    return (1);
}


static int stsd_read(unsigned char *buf, void *box)
{
    stsd_t *stsd_box = (stsd_t *)box;
    unsigned char *boundry = buf + stsd_box->header.ExtendedSize;
    unsigned char *sub_buf = buf + stsd_box->header.length;

    if (sub_buf + 4 >= boundry)
    {
#ifdef UNIT_TEST
        printf("Error: stsd box too small and wrong\n");
#endif
        return (0);
    }
    return (1);
}


//count = one of [1,2,3,4,8]
static unsigned char *bytes_write(unsigned char *buf, int count,
                                  uint64_t ui)
{
    int i;

    ui <<= (8 - count) * 8;
    for (i = 0; i < count; i++)
        buf[i] = (unsigned char)(ui >> ((7 - i) * 8));

    return (buf + count);
}


static unsigned char *boxheader_write(unsigned char *buf,
                                      boxheader_t *header)
{
    uint64_t t;

    t = header->ExtendedSize + header->deltaSize;
    if (header->length == 8)
    {
        buf = bytes_write(buf, 4, t);
        memcpy(buf, header->start + 4, 4);
        buf += 4;
    }
    else
    {
        memcpy(buf, header->start, 8);
        buf = bytes_write(buf + 8, 8, t);
    }
#ifdef UNIT_TEST
    printf("--- write --- Box(%c%c%c%c,%u)\n",
           header->BoxType >> 24, header->BoxType >> 16,
           header->BoxType >> 8, header->BoxType,
           (uint32_t)t);
#endif
    return (buf);
}


static unsigned char *stsc_write(unsigned char *dst, void *box)
{
    stsc_t *stsc_box = (stsc_t *)box;
    unsigned char *buf = stsc_box->header.start;
    unsigned char *sub_buf = (unsigned char *)stsc_box->Entries;
    uint32_t i, t, newCount;
    uint32_t n1, n2;

    n1 = stsc_box->newFirstEntry;
    n2 = stsc_box->newLastEntry;
    newCount = n2 - n1 + 1;

    dst = boxheader_write(dst, & stsc_box->header);
    buf += stsc_box->header.length;
    memcpy(dst, buf, 1 + 3);
    dst += 1 + 3;
    buf += 1 + 3;
    dst = bytes_write(dst, 4, (uint64_t)newCount);
    memcpy(dst, sub_buf + n1 * 4 * 3, newCount * 4 * 3);
    for (i = n1; i <= n2; i++)
    {
        t = bytes_read(sub_buf + 4 * 3 * i, 4);
        if (t >= stsc_box->newChunkStart)
        {
            t -= stsc_box->newChunkStart - 1;
            bytes_write(dst + (i - n1) * 4 * 3, 4, (uint64_t)t);
        }
        else if (i == n1)       // add in testing phase 2009.06.27
        {
            t = 1;
            bytes_write(dst, 4, (uint64_t)t);
        }
    }
    dst += newCount * 4 * 3;
    return (dst);
}


static unsigned char *stts_write(unsigned char *dst, void *box)
{
    stts_t *stts_box = (stts_t *)box;
    unsigned char *buf = stts_box->header.start + stts_box->header.length;
    uint32_t t, ot, newCount, n1, n2;

    //assume stts_box->header already calc deltaSize
    dst = boxheader_write(dst, & stts_box->header);
    n1 = stts_box->newFirstEntry;
    n2 = stts_box->newLastEntry;
    newCount = n2 - n1 + 1;

    memcpy(dst, buf, 1 + 3);
    dst += 1 + 3;
    dst = bytes_write(dst, 4, (uint64_t)newCount);
    buf += 1 + 3 + 4;
    if (n1 > 0)
        buf += (n1 - 1) * (4 + 4);

    t = newCount * (4 + 4);
    memcpy(dst, buf, t);
    bytes_write(dst, 4, (uint64_t)stts_box->newFirstCount);
    ot = (n2 - n1) * (4 + 4);
    bytes_write(dst + ot, 4, (uint64_t)stts_box->newLastCount);
    dst += t;

    return (dst);
}


static unsigned char *stsz_write(unsigned char *dst, void *box,
                                 int no_size_table)
{
    stsz_t *stsz_box = (stsz_t *)box;
    unsigned char *buf = stsz_box->header.start;
    uint32_t ot, newCount, n1, n2;

    if (stsz_box->ConstantSize > 0)
    {
        memcpy(dst, buf, stsz_box->header.ExtendedSize);
        return (dst + stsz_box->header.ExtendedSize);
    }
    dst = boxheader_write(dst, & stsz_box->header);
    buf += stsz_box->header.length;
    memcpy(dst, buf, 1 + 3 + 4);
    dst += 1 + 3 + 4;
    buf += 1 + 3 + 4;

    n1 = stsz_box->newFirstEntry;
    n2 = stsz_box->newLastEntry;
    newCount = n2 - n1 + 1;
    dst = bytes_write(dst, 4, (uint64_t)newCount);
    buf += 4;       //bug fix: missed this line. moovie not play. 2009.06.27

    //if(n1>0)
    //    buf += (n1-1)*4; //bug -- took long time to trace out 2009.06.28
    if (no_size_table != 1)
    {
        buf += n1 * 4;
        ot = newCount * 4;
        memcpy(dst, buf, ot);
        dst += ot;
    }
    return (dst);
}


static unsigned char *stco_co64_write(unsigned char *dst, void *box)
{
    stco_co64_t *stco_co64_box = (stco_co64_t *)box;
    unsigned char *buf = stco_co64_box->header.start;
    uint32_t i, newCount, n1, n2;
    uint64_t t2;
    int64_t t;

    dst = boxheader_write(dst, & stco_co64_box->header);
    buf += stco_co64_box->header.length;
    memcpy(dst, buf, 1 + 3);
    dst += 1 + 3;
    buf += 1 + 3;

    n1 = stco_co64_box->newFirstEntry;
    n2 = stco_co64_box->newLastEntry;
    newCount = n2 - n1 + 1;
    dst = bytes_write(dst, 4, (uint64_t)newCount);
    buf += 4;

    t = stco_co64_box->deltaOffset;
    switch (stco_co64_box->header.BoxType)
    {
    case FourCC('s', 't', 'c', 'o'):
        buf += n1 * 4;
        for (i = n1; i <= n2; i++)
        {
            t2 = bytes_read(buf, 4);
            t2 += t;
            dst = bytes_write(dst, 4, t2);
            buf += 4;
        }
        break;
    case FourCC('c', 'o', '6', '4'):
        buf += n1 * 8;
        for (i = n1; i <= n2; i++)
        {
            t2 = bytes_read(buf, 8);
            t2 += t;
            dst = bytes_write(dst, 8, t2);
            buf += 8;
        }
        break;
    }

    return (dst);
}


static unsigned char *stss_write(unsigned char *dst, void *box)
{
    stss_t *stss_box = (stss_t *)box;
    unsigned char *buf = stss_box->header.start;
    uint32_t i, t, newCount, n1, n2;

    newCount = stss_box->newCount;
    if (newCount == 0) //bug fix by actual testing
        return (dst);
    dst = boxheader_write(dst, & stss_box->header);
    n1 = stss_box->newFirstSample;
    n2 = stss_box->newLastSample;

    buf += stss_box->header.length;
    memcpy(dst, buf, 1 + 3);
    dst += 1 + 3;
    dst = bytes_write(dst, 4, (uint64_t)newCount);
    buf += 1 + 3 + 4;

    for (i = 0; i < stss_box->SyncCount; i++)
    {
        t = bytes_read(buf + 4 * i, 4);
        if (t > n2)
            break;
        if (t >= n1 && t <= n2)
        {
            t -= n1 - 1;
            dst = bytes_write(dst, 4, (uint64_t)t);
        }
    }

    return (dst);
}


static int calc_new_moov_diff(moov_t *moov_box, float start_time,
                              float end_time)
{
    uint32_t i, s1, s2, c1, c2, max_chunk, s1_2, s2_1;
    uint64_t t, t1, t2, mdat_start_offset, mdat_end_offset;
    uint64_t max_duration;
    int64_t deltaSize, deltaT, dt2;
    float f1;
    stbl_t *stbl;

    if (moov_box->mvhd.TimeScale == 0)return (0);
    if (start_time < 0) start_time = 0;
    if (end_time < 0) end_time = 0;
    if (end_time != 0 && end_time < start_time)return (0);
    f1 = moov_box->mvhd.Duration / moov_box->mvhd.TimeScale;
    if (start_time >= f1)return (0);
    if (end_time == 0 || end_time > f1)end_time = f1 + 1;

    //if(end_time==(f1+1) && start_time==0)return(0);

    deltaSize = 0;
    mdat_end_offset = 0;
    max_duration = 0;

    for (i = 0; i < (unsigned int)moov_box->track_num; i++)
    {
        //time to sampleStart, sampleEnd, chunkStart, chunkEnd
        t1 = moov_box->trak[i].mdia.mdhd.TimeScale * start_time;
        t2 = moov_box->trak[i].mdia.mdhd.TimeScale * end_time;

        stbl = & moov_box->trak[i].mdia.minf.stbl;
        max_chunk = stbl->stco_co64.OffsetCount;
        s1 = duration_to_sample(t1, (unsigned char *)stbl->stts.Entries,
                                stbl->stts.Count);
        c1 = sample_to_chunk(s1, (unsigned char *)stbl->stsc.Entries,
                             stbl->stsc.Count, max_chunk, & s1, & s1_2);

        s2 = duration_to_sample(t2, (unsigned char *)stbl->stts.Entries,
                                stbl->stts.Count);
        c2 = sample_to_chunk(s2, (unsigned char *)stbl->stsc.Entries,
                             stbl->stsc.Count, max_chunk, & s2_1, & s2);

        stss_adjust(&stbl->stss, s1, s2);
        stsc_adjust(&stbl->stsc, c1, c2, (unsigned char *)stbl->stsc.Entries);
        stts_adjust(&stbl->stts, s1, s2, (unsigned char *)stbl->stts.Entries);
        stco_co64_adjust(&stbl->stco_co64, c1, c2);
        ctts_adjust(&stbl->ctts, s1, s2);

        dt2 = stbl->stsz.original_box_size - stbl->stsz.header.ExtendedSize;
        stbl->stsz.header.ExtendedSize += dt2;
        stsz_adjust(&stbl->stsz, s1, s2);

        deltaT = stbl->stsc.header.deltaSize + stbl->stts.header.deltaSize +
                 stbl->stsz.header.deltaSize + stbl->stco_co64.header.deltaSize +
                 stbl->stss.header.deltaSize + stbl->ctts.header.deltaSize +
                 stbl->stsd.header.deltaSize + dt2;
        stbl->header.deltaSize += deltaT;
        moov_box->trak[i].mdia.minf.header.deltaSize += stbl->header.deltaSize;
        moov_box->trak[i].mdia.header.deltaSize +=
            moov_box->trak[i].mdia.minf.header.deltaSize;
        moov_box->trak[i].header.deltaSize +=
            moov_box->trak[i].mdia.header.deltaSize;
        deltaSize += moov_box->trak[i].header.deltaSize;

        moov_box->trak[i].mdia.mdhd.newDuration = sample_to_duration(s1, s2,
                (unsigned char *)stbl->stts.Entries, stbl->stts.Count);
        moov_box->trak[i].tkhd.newDuration = (uint64_t)moov_box->mvhd.TimeScale *
                                             moov_box->trak[i].mdia.mdhd.newDuration /
                                             moov_box->trak[i].mdia.mdhd.TimeScale;

        if (max_duration < moov_box->trak[i].tkhd.newDuration)
            max_duration = moov_box->trak[i].tkhd.newDuration;
        t = trak_max_offset_new(stbl, c2, moov_box);
        if (t > mdat_end_offset)
            mdat_end_offset = t;
    }
    moov_box->mvhd.newDuration = max_duration;
    moov_box->header.deltaSize += deltaSize;
    moov_box->header.ExtendedSize -= 4 + 8 * 3;

    mdat_start_offset =
        moov_box->trak[0].mdia.minf.stbl.stco_co64.firstChunkOffset;
    for (i = 1; i < (unsigned int)moov_box->track_num; i++)
    {
        t = moov_box->trak[i].mdia.minf.stbl.stco_co64.firstChunkOffset;
        if (t < mdat_start_offset)
            mdat_start_offset = t;
    }
    moov_box->mdat_start_offset = mdat_start_offset;
    moov_box->mdat_end_offset = mdat_end_offset;

    return (1);
}


static uint32_t duration_to_sample(uint64_t duration,
                                   unsigned char *stts_entries, uint32_t count)
{
    uint32_t i, samp, dura, samp_acc = 0, dura_acc = 0;

    for (i = 0; i < count; i++)
    {
        samp = bytes_read(stts_entries + 2 * 4 * i, 4); //SampleCount
        dura = bytes_read(stts_entries + 2 * 4 * i + 4, 4); //SampleDelta;
        if (dura_acc + samp * dura >= duration)
            return (samp_acc + (uint32_t)((duration - dura_acc) / dura));
        samp_acc += samp;
        dura_acc += samp * dura;
    }
    return (samp_acc);
}


static uint32_t sample_to_chunk(uint32_t sample,
                                unsigned char *stsc_entries, uint32_t count, uint32_t max_chunk,
                                uint32_t  *chunkFirstSample, uint32_t *chunkLastSample)
{
    uint32_t i, chunk_p, sample_p, chunk_c, sample_acc = 0, t, chunk_delta,
                                            chunk;

    chunk_p  = bytes_read(stsc_entries, 4);       //FirstChunk;
    sample_p = bytes_read(stsc_entries + 4, 4); //SamplesPerChunk;
    if (sample <= sample_p)
    {
        *chunkFirstSample = 1;
        *chunkLastSample = sample_p;
        return (1);
    }
    for (i = 1; i < count; i++)
    {
        chunk_c = bytes_read(stsc_entries + 3 * 4 * i, 4); //FirstChunk;
        t = sample_acc + (chunk_c - chunk_p) * sample_p;
        if (sample <= t)
        {
            t = (sample - sample_acc) % sample_p;
            chunk_delta = (uint32_t)((sample - sample_acc) / sample_p);
            if (t != 0)
                chunk_delta++;
            chunk = chunk_p - 1 + chunk_delta;
            *chunkLastSample = sample_acc + chunk_delta * sample_p;
            *chunkFirstSample = *chunkLastSample - sample_p + 1;
            return (chunk);
        }
        sample_acc += (chunk_c - chunk_p) * sample_p;
        sample_p = bytes_read(stsc_entries + 3 * 4 * i + 4, 4); //SamplesPerChunk;
        chunk_p = chunk_c;
    }

    t = sample_acc + (max_chunk - chunk_p + 1) * sample_p;
    if (sample <= t)
    {
        t = (sample - sample_acc) % sample_p;
        chunk_delta = (uint32_t)((sample - sample_acc) / sample_p);
        if (t != 0)
            chunk_delta++;
        chunk = chunk_p - 1 + chunk_delta;
        *chunkLastSample = sample_acc + chunk_delta * sample_p;
        *chunkFirstSample = *chunkLastSample - sample_p + 1;
        return (chunk);

    }
    else
    {
        *chunkLastSample = 0;
        *chunkFirstSample = 0;
        return (0);
    }
}


static uint32_t sample_to_duration(uint32_t s1, uint32_t s2,
                                   unsigned char  *stts_entries, uint32_t count)
{
    uint32_t i, samp, dura, samp_acc = 0, acc = 0, min, max;
    int s1_found = 0;

    for (i = 0; i < count; i++)
    {
        samp = bytes_read(stts_entries + i * 4 * 2, 4);   //SampleCount;
        dura = bytes_read(stts_entries + i * 4 * 2 + 4, 4); //SampleDelta;
        if (s1_found == 0 && samp_acc + samp >= s1)
            s1_found = 1;
        if (s1_found == 1)
        {
            //between (samp_acc+1) and (samp_acc+samp), how many number >=s1 and <=s2
            if (samp_acc + 1 < s1)
                min = s1;
            else
                min = samp_acc + 1;
            if (samp_acc + samp < s2)
                max = samp_acc + samp;
            else
                max = s2;
            acc += (max - min + 1) * dura;
        }
        samp_acc += samp;
        if (samp_acc >= s2)
            break;
    }
    return (acc);
}


static uint32_t stsc_adjust(stsc_t *stsc, uint32_t c1, uint32_t c2,
                            unsigned char *stsc_entries)
{
    uint32_t i, t, count, newCount;
    uint32_t n1 = 0, n2 = 0;

    count = stsc->Count;
    for (i = 0; i < count; i++)
    {
        t = bytes_read(stsc_entries + 3 * 4 * i, 4); //FirstChunk;
        if (t <= c1)
            n1 = i;
        if (t > c2)
            break;
        else
            n2 = i;
    }
    newCount = n2 - n1 + 1;

    t = (count - newCount) * 4 * 3;
    stsc->header.deltaSize = -1 * t;
    stsc->newChunkStart = c1;
    stsc->newFirstEntry = n1;
    stsc->newLastEntry = n2;

    return (1);
}


static uint32_t stts_adjust(stts_t *stts, uint32_t s1, uint32_t s2,
                            unsigned char *stts_entries)
{
    uint32_t i, samp, samp_acc = 0, count, newCount, n1 = 0, n2;
    int32_t delta1 = 0, delta2;

    count = stts->Count;
    for (i = 0; i < count; i++)
    {
        samp = bytes_read(stts_entries + 2 * 4 * i, 4); //SampleCount
        if (samp_acc + samp >= s1)
        {
            n1 = i;
            stts->newFirstEntry = n1;
            delta1 = s1 - samp_acc - 1;
            stts->newFirstCount = samp - delta1;
            break;
        }
        samp_acc += samp;
    }

    n2 = n1;
    for (i = n1; i < count; i++)
    {
        samp = bytes_read(stts_entries + 2 * 4 * i, 4); //SampleCount;
        if (samp_acc + samp >= s2)
        {
            n2 = i;
            stts->newLastEntry = n2;
            delta2 = samp_acc + samp - s2;
            stts->newLastCount = samp - delta2;
            if (n2 == n1)
                stts->newLastCount -= delta1;
            break;
        }
        samp_acc += samp;
    }

    newCount = n2 - n1 + 1;
    stts->header.deltaSize = -1 * ((count - newCount) * 8);
    return (1);
}


static uint32_t stsz_adjust(stsz_t *stsz, uint32_t s1, uint32_t s2)
{
    if (stsz->ConstantSize > 0)
        return (1);

    stsz->newFirstEntry = s1 - 1;
    stsz->newLastEntry = s2 - 1;

    stsz->header.deltaSize = -1 * ((stsz->SizeCount - (s2 - s1 + 1)) * 4);
    return (1);
}


static uint32_t stco_co64_adjust(stco_co64_t *stco_co64, uint32_t c1,
                                 uint32_t c2)
{
    int t = 0;
    unsigned char *buf;
    uint64_t ot = 0;

    buf = (unsigned char *)stco_co64->Offsets;
    stco_co64->newFirstEntry = c1 - 1;
    stco_co64->newLastEntry = c2 - 1;

    switch (stco_co64->header.BoxType)
    {
    case FourCC('s', 't', 'c', 'o'):
        t = 4;
        ot = bytes_read(buf + (c1 - 1) * 4, 4);
        break;
    case FourCC('c', 'o', '6', '4'):
        t = 8;
        ot = bytes_read(buf + (c1 - 1) * 8, 8);
        break;
    }
    stco_co64->header.deltaSize = -1 * (stco_co64->OffsetCount -
                                        (c2 - c1 + 1)) * t;
    stco_co64->firstChunkOffset = ot;

    return (1);
}


static uint32_t stss_adjust(stss_t *stss, uint32_t s1, uint32_t s2)
{
    uint32_t t, i, newCount = 0, count;
    unsigned char *buf = (unsigned char *)stss->SyncTable;

    if (stss->header.ExtendedSize == 0)
        return (1);

    count = stss->SyncCount;
    for (i = 0; i < count; i++)
    {
        t = bytes_read(buf + 4 * i, 4);
        if (t > s2)
            break;
        if (t >= s1 && t <= s2)
            newCount ++;
    }
    stss->newCount = newCount;
    if (newCount == 0)      //add this branch -- bug fix 2009.06.28
        stss->header.deltaSize = -1 * stss->header.ExtendedSize;
    else
    {
        stss->newFirstSample = s1;
        stss->newLastSample = s2;
        stss->header.deltaSize = -1 * (count - newCount) * 4;
    }
    return (1);
}


static uint32_t ctts_adjust(ctts_t *ctts, uint32_t s1, uint32_t s2)
{
    if (ctts->header.ExtendedSize == 0) //ctts not exist
        return (1);
    //delete it if present
    ctts->header.deltaSize = -1 * ctts->header.ExtendedSize;
    return (1);
}


//called when stsz table not in memory
static uint64_t trak_max_offset_new(stbl_t *stbl, uint32_t chunk,
                                    moov_t *moov)
{
    uint32_t max_chunk;
    unsigned char *buf;
    uint64_t ot = 0;

    max_chunk = stbl->stco_co64.OffsetCount;
    if (chunk < max_chunk)
    {
        buf = (unsigned char *)stbl->stco_co64.Offsets;
        switch (stbl->stco_co64.header.BoxType)
        {
        case FourCC('s', 't', 'c', 'o'):
            ot = bytes_read(buf + chunk * 4, 4);
            break;
        case FourCC('c', 'o', '6', '4'):
            ot = bytes_read(buf + chunk * 8, 8);
            break;
        }
    }
    else
        ot = moov->mdat_end_offset;

    return (ot);
}


static int mini_moov_calc_size(moov_t *moov_box)
{
    stbl_t *stbl;
    trak_t *trak;
    int i;
    uint64_t newS, t;

    newS = 0;
    for (i = 0; i < moov_box->track_num; i++)
    {
        trak = & moov_box->trak[i];
        stbl = & trak->mdia.minf.stbl;

        if (stbl->stsz.ConstantSize != 0)
            t = stbl->stsz.header.ExtendedSize;
        else
            t = stbl->stsz.header.length + 1 + 3 + 4 * 2 + 8 + 4;
        t += stbl->stsc.header.ExtendedSize + stbl->stts.header.ExtendedSize +
             stbl->stss.header.ExtendedSize + stbl->stsd.header.ExtendedSize +
             stbl->stco_co64.header.ExtendedSize;

        stbl->header.ExtendedSize = stbl->header.length + t;
        trak->mdia.minf.header.ExtendedSize = trak->mdia.minf.header.length +
                                              stbl->header.ExtendedSize;
        trak->mdia.header.ExtendedSize = trak->mdia.header.length +
                                         trak->mdia.mdhd.header.ExtendedSize +
                                         trak->mdia.minf.header.ExtendedSize;
        trak->header.ExtendedSize = trak->header.length +
                                    trak->tkhd.header.ExtendedSize +
                                    trak->mdia.header.ExtendedSize;

        newS += trak->header.ExtendedSize;
    }
    moov_box->header.ExtendedSize = moov_box->header.length +
                                    moov_box->mvhd.header.ExtendedSize + newS + 4 + 8 * 3;

    return (1);
}


static int mini_moov_write(unsigned char *buf, moov_t *box)
{
    moov_t *moov_box = (moov_t *)box;
    stbl_t *stbl;
    trak_t *trak;
    int i;
    unsigned char *dst;
    uint64_t t;

    dst = buf;

    moov_box->header.deltaSize = 0;
    dst = boxheader_write(dst, &moov_box->header);
    dst = bytes_write(dst, 4, moov_box->mdat_header_length);
    dst = bytes_write(dst, 8, moov_box->offset_in_file);
    dst = bytes_write(dst, 8, moov_box->mdat_start_offset);
    dst = bytes_write(dst, 8, moov_box->mdat_end_offset);
    memcpy(dst, moov_box->mvhd.header.start,
           moov_box->mvhd.header.ExtendedSize);
    dst += moov_box->mvhd.header.ExtendedSize;

    for (i = 0; i < moov_box->track_num; i++)
    {
        trak = & moov_box->trak[i];
        stbl = & trak->mdia.minf.stbl;

        trak->header.deltaSize = 0;//trak
        dst = boxheader_write(dst, &trak->header);
        memcpy(dst, trak->tkhd.header.start, trak->tkhd.header.ExtendedSize);//tkhd
        dst += trak->tkhd.header.ExtendedSize;

        trak->mdia.header.deltaSize = 0;//mdia
        dst = boxheader_write(dst, &trak->mdia.header);
        memcpy(dst, trak->mdia.mdhd.header.start,
               trak->mdia.mdhd.header.ExtendedSize);//mdhd
        dst += trak->mdia.mdhd.header.ExtendedSize;
        trak->mdia.minf.header.deltaSize = 0;//minf
        dst = boxheader_write(dst, &trak->mdia.minf.header);
        stbl->header.deltaSize = 0;//stbl
        dst = boxheader_write(dst, &stbl->header);

        memcpy(dst, stbl->stsd.header.start, stbl->stsd.header.ExtendedSize);//stsd
        dst += stbl->stsd.header.ExtendedSize;
        memcpy(dst, stbl->stsc.header.start, stbl->stsc.header.ExtendedSize);//stsc
        dst += stbl->stsc.header.ExtendedSize;
        memcpy(dst, stbl->stts.header.start, stbl->stts.header.ExtendedSize);//stts
        dst += stbl->stts.header.ExtendedSize;
        memcpy(dst, stbl->stco_co64.header.start,
               stbl->stco_co64.header.ExtendedSize);//stco_co64
        dst += stbl->stco_co64.header.ExtendedSize;
        if (stbl->stss.header.ExtendedSize)
        {
            memcpy(dst, stbl->stss.header.start, stbl->stss.header.ExtendedSize);//stss
            dst += stbl->stss.header.ExtendedSize;
        }

        stbl->stsz.header.deltaSize = 0;//stsz
        t = stbl->stsz.header.ExtendedSize;
        stbl->stsz.header.ExtendedSize = stbl->stsz.header.length + 1 + 3 + 4 * 2 +
                                         8 + 4;
        dst = boxheader_write(dst, &stbl->stsz.header);
        memcpy(dst, stbl->stsz.header.start + stbl->stsz.header.length,
               1 + 3 + 4 * 2);
        dst += 1 + 3 + 4 * 2;
        dst = bytes_write(dst, 8,
                          moov_box->offset_in_file + (stbl->stsz.header.start -
                                  moov_box->header.start));
        dst = bytes_write(dst, 4, t);  //original_box_size
    }

    return (1);
}


static int mini_moov_read(unsigned char *buf, moov_t *moov_box)
{
    unsigned char *boundry = buf + moov_box->header.ExtendedSize;
    unsigned char *sub_buf = buf + moov_box->header.length;
    boxheader_t dummy;
    int r, trak_index = -1;

    moov_box->mdat_header_length = bytes_read(sub_buf, 4);
    moov_box->offset_in_file = bytes_read(sub_buf + 4, 8);
    moov_box->mdat_start_offset = bytes_read(sub_buf + 4 + 8, 8);
    moov_box->mdat_end_offset = bytes_read(sub_buf + 4 + 8 * 2, 8);
    sub_buf += 4 + 3 * 8;

    while (sub_buf < boundry)
    {
        r = boxheader_read(sub_buf, &dummy, boundry);
        if (r == 0)
            return (0);
        switch (dummy.BoxType)
        {
        case FourCC('m', 'v', 'h', 'd'):
            moov_box->mvhd.header = dummy;
            r = mvhd_read(sub_buf, (void *)&moov_box->mvhd);
            if (r == 0)
                return (0);
            sub_buf += dummy.ExtendedSize;
            break;
        case FourCC('t', 'r', 'a', 'k'):
            trak_index++;
            moov_box->trak[trak_index].header = dummy;
            sub_buf += dummy.length;
            break;
        case FourCC('t', 'k', 'h', 'd'):
            moov_box->trak[trak_index].tkhd.header = dummy;
            r = tkhd_read(sub_buf, (void *)&moov_box->trak[trak_index].tkhd);
            if (r == 0)
                return (0);
            sub_buf += dummy.ExtendedSize;
            break;
        case FourCC('m', 'd', 'i', 'a'):
            moov_box->trak[trak_index].mdia.header = dummy;
            sub_buf += dummy.length;
            break;
        case FourCC('m', 'd', 'h', 'd'):
            moov_box->trak[trak_index].mdia.mdhd.header = dummy;
            r = mdhd_read(sub_buf, (void *)&moov_box->trak[trak_index].mdia.mdhd);
            if (r == 0)
                return (0);
            sub_buf += dummy.ExtendedSize;
            break;
        case FourCC('m', 'i', 'n', 'f'):
            moov_box->trak[trak_index].mdia.minf.header = dummy;
            sub_buf += dummy.length;
            break;
        case FourCC('s', 't', 'b', 'l'):
            moov_box->trak[trak_index].mdia.minf.stbl.header = dummy;
            sub_buf += dummy.length;
            break;
        case FourCC('s', 't', 's', 'd'):
            moov_box->trak[trak_index].mdia.minf.stbl.stsd.header = dummy;
            r = stsd_read(sub_buf, (void *)
                          &moov_box->trak[trak_index].mdia.minf.stbl.stsd);
            if (r == 0)
                return (0);
            sub_buf += dummy.ExtendedSize;
            break;
        case FourCC('s', 't', 's', 'c'):
            moov_box->trak[trak_index].mdia.minf.stbl.stsc.header = dummy;
            r = stsc_read(sub_buf, (void *)
                          &moov_box->trak[trak_index].mdia.minf.stbl.stsc);
            if (r == 0)
                return (0);
            sub_buf += dummy.ExtendedSize;
            break;
        case FourCC('s', 't', 't', 's'):
            moov_box->trak[trak_index].mdia.minf.stbl.stts.header = dummy;
            r = stts_read(sub_buf, (void *)
                          &moov_box->trak[trak_index].mdia.minf.stbl.stts);
            if (r == 0)
                return (0);
            sub_buf += dummy.ExtendedSize;
            break;
        case FourCC('s', 't', 's', 'z'):
            moov_box->trak[trak_index].mdia.minf.stbl.stsz.header = dummy;
            moov_box->trak[trak_index].mdia.minf.stbl.stsz.ConstantSize = bytes_read(
                        sub_buf + dummy.length + 1 + 3, 4);
            moov_box->trak[trak_index].mdia.minf.stbl.stsz.SizeCount = bytes_read(
                        sub_buf + dummy.length + 1 + 3 + 4, 4);
            moov_box->trak[trak_index].mdia.minf.stbl.stsz.offset_in_file = bytes_read(
                        sub_buf + dummy.length + 1 + 3 + 8, 8);
            moov_box->trak[trak_index].mdia.minf.stbl.stsz.original_box_size =
                bytes_read(sub_buf + dummy.length + 1 + 3 + 16, 4);
            sub_buf += dummy.length + 1 + 3 + 4 * 2 + 8 + 4;
            break;
        case FourCC('s', 't', 'c', 'o'):
        case FourCC('c', 'o', '6', '4'):
            moov_box->trak[trak_index].mdia.minf.stbl.stco_co64.header = dummy;
            r = stco_co64_read(sub_buf,
                               (void *)&moov_box->trak[trak_index].mdia.minf.stbl.stco_co64);
            if (r == 0)
                return (0);
            sub_buf += dummy.ExtendedSize;
            break;
        case FourCC('s', 't', 's', 's'):
            moov_box->trak[trak_index].mdia.minf.stbl.stss.header = dummy;
            r = stss_read(sub_buf, (void *)
                          &moov_box->trak[trak_index].mdia.minf.stbl.stss);
            if (r == 0)
                return (0);
            sub_buf += dummy.ExtendedSize;
            break;
        default:
#ifdef UNIT_TEST
            printf("boundry=%u,here=%u\n", (uint32_t)(boundry - buf),
                   (uint32_t)(sub_buf - buf));
#endif
            return (0);
            break;
        }
    }
    if (trak_index == -1)
        return (0);
    moov_box->track_num = trak_index + 1;
    if (sub_buf == boundry)
        return (1);
    else
        return (0);
}


static int moov_write_chunk(moov_data_t     *moov_data, moov_t *moov_box)
{

    unsigned char *buf, * dst;
    int trak_to_send = -1, in_memory = -1;
    uint32_t already_return, acc, acc_pre, t, i;
    trak_t *trak;
    stbl_t *stbl;

    if (moov_data->remaining_bytes == 1)
    {
        moov_data->remaining_bytes = moov_box->header.ExtendedSize +
                                     moov_box->header.deltaSize;
        already_return = 0;
    }
    else
        already_return = moov_box->header.ExtendedSize + moov_box->header.deltaSize
                         - moov_data->remaining_bytes;

    acc_pre = 0;
    acc = moov_box->header.length + moov_box->mvhd.header.ExtendedSize;

    for (i = 0; i < (unsigned int)moov_box->track_num; i++)
    {
        trak = & moov_box->trak[i];
        stbl = & trak->mdia.minf.stbl;

        acc += trak->header.length;
        acc += trak->tkhd.header.ExtendedSize;
        acc += trak->mdia.header.length + trak->mdia.mdhd.header.ExtendedSize;
        acc += trak->mdia.minf.header.length + stbl->header.length;
        acc += stbl->stsd.header.ExtendedSize;
        acc += stbl->stsc.header.ExtendedSize + stbl->stsc.header.deltaSize;
        acc += stbl->stts.header.ExtendedSize + stbl->stts.header.deltaSize;
        acc += stbl->stco_co64.header.ExtendedSize +
               stbl->stco_co64.header.deltaSize;
        acc += stbl->stss.header.ExtendedSize + stbl->stss.header.deltaSize;

        if (stbl->stsz.ConstantSize > 0)
            acc += stbl->stsz.header.ExtendedSize;
        else
            acc += stbl->stsz.header.length + 1 + 3 + 4 * 2;
        if (acc > already_return)
        {
            trak_to_send = i;
            in_memory = 1;
            break;
        }
        if (stbl->stsz.ConstantSize == 0)
        {
            t = (stbl->stsz.newLastEntry - stbl->stsz.newFirstEntry + 1) * 4;
            if (acc + t > already_return)
            {
                trak_to_send = i;
                in_memory = 0;
                break;
            }
            acc += t;
        }
        acc_pre = acc;
    }

    if (in_memory == 0) //send stsz in file
    {
        moov_data->is_mem = 0;
        moov_data->remaining_bytes -= t;
        moov_data->file.start_offset = stbl->stsz.offset_in_file +
                                       stbl->stsz.header.length + 1 + 3 + 4 * 2 + stbl->stsz.newFirstEntry * 4;
        moov_data->file.data_size = t;
        if (moov_data->remaining_bytes == 0)
            return (1);
        else
            return (0);
    }
    else if (in_memory == -1)
        return (-1);

    //now in_memory=1
    buf = (unsigned char *)calloc((size_t)(acc - acc_pre), 1);
    dst = buf;

    if (trak_to_send == 0)
    {
        dst = boxheader_write(dst, &moov_box->header); //moov
        memcpy(dst, moov_box->mvhd.header.start,
               moov_box->mvhd.header.ExtendedSize);//mvhd
        if (moov_box->mvhd.Version == 0)
            bytes_write(dst + moov_box->mvhd.header.length + 1 + 3 + 4 * 3, 4,
                        (uint64_t)moov_box->mvhd.newDuration);
        else
            bytes_write(dst + moov_box->mvhd.header.length + 1 + 3 + 8 * 2 + 4, 8,
                        (uint64_t)moov_box->mvhd.newDuration);
        dst += moov_box->mvhd.header.ExtendedSize;
    }

    i = trak_to_send;
    trak = & moov_box->trak[i];
    stbl = & trak->mdia.minf.stbl;

    dst = boxheader_write(dst, &trak->header); //trak
    memcpy(dst, trak->tkhd.header.start,
           trak->tkhd.header.ExtendedSize); //tkhd
    if (trak->tkhd.Version == 0)
        bytes_write(dst + trak->tkhd.header.length + 1 + 3 + 4 * 4, 4,
                    (uint64_t)trak->tkhd.newDuration);
    else
        bytes_write(dst + trak->tkhd.header.length + 1 + 3 + 8 * 2 + 4 * 2, 8,
                    (uint64_t)trak->tkhd.newDuration);
    dst += trak->tkhd.header.ExtendedSize;


    dst = boxheader_write(dst, &trak->mdia.header); //minf
    memcpy(dst, trak->mdia.mdhd.header.start,
           trak->mdia.mdhd.header.ExtendedSize);//mdhd
    if (trak->mdia.mdhd.Version == 0)
        bytes_write(dst + trak->mdia.mdhd.header.length + 1 + 3 + 4 * 3, 4,
                    (uint64_t)trak->mdia.mdhd.newDuration);
    else
        bytes_write(dst + trak->mdia.mdhd.header.length + 1 + 3 + 8 * 2 + 4, 8,
                    (uint64_t)trak->mdia.mdhd.newDuration);
    dst += trak->mdia.mdhd.header.ExtendedSize;

    dst = boxheader_write(dst, &trak->mdia.minf.header); //minf
    dst = boxheader_write(dst, &stbl->header); //stbl

    memcpy(dst, stbl->stsd.header.start, stbl->stsd.header.ExtendedSize);//stsd
    dst += stbl->stsd.header.ExtendedSize;

    dst = stsc_write(dst, (void *)&stbl->stsc); //stsc
    dst = stts_write(dst, (void *)&stbl->stts); //stts
    dst = stco_co64_write(dst, (void *)&stbl->stco_co64); //stco_co64
    dst = stss_write(dst, (void *)&stbl->stss); //stss

    dst = stsz_write(dst, (void *)&stbl->stsz, 1); //stsz

    t = acc - acc_pre;
    moov_data->is_mem = 1;
    moov_data->remaining_bytes -= t;
    moov_data->mem.buffer = buf;
    moov_data->mem.buf_size = t;

    if (moov_data->remaining_bytes == 0)
        return (1);
    else
        return (0);
}


uint64_t get_new_moov_total_size(void *moov_ctrl)
{
    uint64_t r;
    moov_t *moov = (moov_t *)moov_ctrl;

    r = moov->header.ExtendedSize + moov->header.deltaSize;
    if (moov->mdat_header_length == 16)
        r += 16;
    else
        r += 8;
    r += moov->mdat_end_offset - moov->mdat_start_offset;
    return (r);
}

