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
#include <inttypes.h>

#ifdef __cplusplus
extern "C" {
#endif

/*    return: -1 -- error. not an mp4/mov/f4v file
 *             1 -- return mini_moov
 *
 *    desc:    get_mini_moov first
*/
extern int get_mini_moov(
    int fd,                        //in - video file descriptor
    unsigned char **mini_moov,     //out
    uint32_t *mini_moov_size     //out
);

typedef struct
{
    struct
    {
        void *buffer;                 //out - caller should free it
        uint32_t buf_size;            //out - returned buffer size
    } mem;
    struct
    {
        uint64_t start_offset;        //out - offset in file
        uint32_t data_size;            //out - total bytes in file
    } file;
    int is_mem;                        //out - is_mem=1:data in memory; is_mem=0:data in file
    uint32_t remaining_bytes;        //in-out. when==1, first call get_moov
    float    start_time;
} moov_data_t;
/*    return: -1 -- error. not an mp4/mov/f4v file
 *             0 -- return part moov box
 *             1 -- return last part of moov
 *
 *    desc:    return moov box
*/
extern int get_moov(
    int fd,                        //in - video file descriptor
    float start_time,            //in - seconds
    float end_time,                //in - seconds. 0 means end of moovie
    moov_data_t     *moov_data,    //out - store returned moov data
    unsigned char *mini_moov,     //in
    uint32_t mini_moov_size        //in
);


/*    return: -1 -- failure
 *             1 -- success
 *
 *    desc:    return mdat box
*/
extern int get_mdat(
    int fd,                        //in - video file descriptor
    float start_time,            //in - seconds
    float end_time,                //in - seconds. 0 means end of moovie
    uint64_t *mdat_start,        //out
    uint64_t *mdat_size,        //out
    int *mdat_64bit,             //out
    unsigned char *mini_moov,     //in
    uint32_t mini_moov_size        //in
);

#ifdef __cplusplus
}
#endif
