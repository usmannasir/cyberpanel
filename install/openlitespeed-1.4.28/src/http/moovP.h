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
/********************************
[ftyp]?
[pdin]? //-->The optional pdin box defines information about progressive download -- can ignore
[mdat]
[moov]
    [udta]? (at most 1 udta box)
    [meta]?
    [chpl]*
    [mvhd]
    [trak]+ (max ?)
        [tkhd]
        [mdia]
            [mdhd]
            [minf]
                [stbl]
                    [stsd]
                    [stsc]
                    [stts]
                    [stsz]
                    [stco]|[co64]
                    [stss]?
                    [ctts]?
***********************************/

typedef uint32_t UI8;
typedef uint32_t UI24;
typedef uint32_t UI32;
typedef uint64_t UI64;

typedef struct
{
    UI32 TotalSize;
    UI32 BoxType;
    UI64 ExtendedSize;      //If TotalSize==1
    unsigned char *start;
    UI32 length;            //8(TotalSize!=1) or 16(TotalSize==1)
    int64_t deltaSize;
} boxheader_t;//in-memory box

typedef struct
{
    boxheader_t header;
    uint64_t start;
    uint64_t end;
} box_in_file_t;//in-file box

/* sample-to-chunk mapping
typedef struct
{
    UI32 FirstChunk;
    UI32 SamplesPerChunk;
    UI32 SampleDescIndex;
} stsc_list_t;
********/
typedef struct
{
    boxheader_t header;
//  UI8     Version;        //Expected to be 0
//  UI24    Flags;          //Reserved, set to 0
    UI32    Count;          //The number of STSCRECORD entries
    void   *Entries;        //point to stsc_list_t
    uint32_t newFirstEntry;
    uint32_t newLastEntry;
    uint32_t newChunkStart;
} stsc_t;

/* chunk offsets for each chunk */
typedef struct
{
    boxheader_t header;
//  UI8     Version;        //Expected to be 0
//  UI24    Flags;          //No flags defined, set to 0
    UI32    OffsetCount;    //The number of offsets in the Offsets table
    void   *Offsets;        //A table of absolute chunk offsets within the file
    //if BoxType == 'stco¡¦ UI32[OffsetCount]
    //if BoxType == 'co64¡¦ UI64[OffsetCount]
    uint32_t newFirstEntry;
    uint32_t newLastEntry;
    int64_t deltaOffset;
    uint64_t firstChunkOffset;
    uint64_t offset_in_file;
} stco_co64_t;

/* time-to-sample mapping
typedef struct
{
    UI32 SampleCount;   //The number of consecutive samples that this STTSRECORD applies to
    UI32 SampleDelta;   //Sample duration
} stts_list_t;
**************/
typedef struct
{
    boxheader_t header;
//  UI8     Version;        //Expected to be 0
//  UI24    Flags;          //None defined, set to 0
    UI32    Count;          //The number of STTSRECORD entries
    void   *Entries;        //stts_list_t * Entries;
    uint32_t newFirstEntry;
    uint32_t newFirstCount;
    uint32_t newLastEntry;
    uint32_t newLastCount;
} stts_t;

/* the size of each sample */
typedef struct
{
    boxheader_t header;
//  UI8     Version;        //Expected to be 0
//  UI24    Flags;          //No flags defined, set to 0
    UI32    ConstantSize;   //If all samples have the same size, this field is set with that constant size;otherwise it is 0
    UI32    SizeCount;      //The number of entries in SizeTable
    UI32   *SizeTable;      //A table of sample sizes; if ConstantSize is 0, this table is empty
    uint32_t newFirstEntry;
    uint32_t newLastEntry;
    uint64_t offset_in_file;
    uint32_t original_box_size;
} stsz_t;

/* optional, specifies which samples are sync samples */
typedef struct
{
    boxheader_t header;
//  UI8     Version;        //Expected to be 0
//  UI24    Flags;          //No flags defined, set to 0
    UI32    SyncCount;      //The number of entries in SyncTable
    void   *SyncTable;      //UI32 A table of sample numbers that are also sync samples;
    //the table is sorted in ascending order of sample numbers
    uint32_t newCount;      //possibly =0
    uint32_t newFirstSample;//>0
    uint32_t newLastSample;
} stss_t;

/* The optional ctts box defines the composition time to sample mapping for a sample table. */
/* No ctts in Apple's manual!
currenly(2009.06.24) we ignore ctts box, since
 1. it's optional for Adobe
 2. no manual from Apple
 3. defintion different between Adobe and unofficial open source implemention
 4. not clear its meaning from Adobe's simple document/description
typedef struct
{
    UI32 SampleCount;   //The number of consecutive samples
    UI32 SampleOffset;  //For each sample specified by the SampleCount field,
                        //this field contains a positive integer that specifies the composition offset from the decoding time
} * ctts_list_t;
****************/
typedef struct
{
    boxheader_t header;
    UI32    Count;          //The number of STTSRECORD entries
    void   *Entries;        //ctts_list_t *
} ctts_t;

typedef struct
{
    boxheader_t header;
//  UI8     Version;    //Expected to be 0
//  UI24    Flags;      //None defined, set to 0
//  UI32    Count;      //The number of entries
//  void    *Descriptions;  //DESCRIPTIONRECORD[Count] An array of records whose types vary depending on whether the track contains audio or video data
} stsd_t;

typedef struct
{
    boxheader_t header;
    stsd_t  stsd;
    stsc_t  stsc;
    stts_t  stts;
    stco_co64_t stco_co64;
    stss_t  stss;
    ctts_t  ctts;
    stsz_t  stsz;
} stbl_t;

typedef struct
{
    boxheader_t header;
    stbl_t  stbl;
} minf_t;

typedef struct
{
    boxheader_t header;
    UI8     Version;        //Version 0 and 1 are supported
//  UI24    Flags;          //Reserved, set to 0
//  UI64    CreationTime;   //if Version == 0:UI32; if Version == 1:UI64
    //The creation time of the box,expressed as seconds elapsed since midnight, January 1, 1904 (UTC)
//  UI64    ModificationTime;//if Version == 0:UI32; if Version == 1:UI64
    //The last modification time of the box,expressed as seconds elapsed since midnight, January 1, 1904 (UTC)
    UI32    TimeScale;      //The base clock tick frequency that this track uses for timing its media
    UI64    Duration;       //if version==0:UI32; if version==1:UI64
    //The total duration of this track, measured in reference to the TimeScale
    //there are still other fields, ignored.
    uint64_t newDuration;
} mdhd_t;

typedef struct
{
    boxheader_t header;
    mdhd_t mdhd;
    minf_t minf;
} mdia_t;

typedef struct
{
    boxheader_t header;
    UI8     Version;        //Versions 0 and 1 are defined
    UI24    Flags;          //Bit 0: this bit is set if the track is enabled
    //Bit 1 = this bit is set if the track is part of the presentation
    //Bit 2 = this bit is set if the track should be considered when previewing the F4V file
//  UI64    CreationTime;   //if Version == 0:UI32; if Version == 1:UI64
    //The creation time of the track,expressed as seconds elapsed since midnight, January 1, 1904 (UTC)
//  UI64    ModificationTime;//if Version == 0:UI32; if Version == 1:UI64
    //The last modification time of the F4V file, expressed as seconds elapsed since midnight, January 1, 1904 (UTC)
//  UI32    TrackID;        //The track¡¦s unique identifier
//  UI32    Reserved;       //set to 0
    UI64    Duration;       //if Version == 0:UI32; if Version == 1:UI64
    //The duration of the track, expressed in the TimeScale defined in the mvhd box for this track
    //there are still other fields, ignored.
    uint64_t newDuration;
} tkhd_t;

typedef struct
{
    boxheader_t header;
    tkhd_t tkhd;
    mdia_t mdia;
} trak_t;

/* The optional chpl box allows an F4V file to specify individual chapters along the main timeline of an F4V file. The information in this box is provided to ActionScript. The chpl box occurs within a moov box.
 * F4V only box
typedef struct
{
    UI64 Timestamp;     //The absolute timestamp of the chapter, in reference to the master timescale and timeline of the F4V file
    UI8  TitleSize;     //The length of the Title string
    UI8* Title;         //The chapter title
} * chpl_list_t;        //An array of timestamps along the timeline; each indicates the beginning of a new chapter
***************/
typedef struct
{
    boxheader_t header;
//  UI8     Version;        //Expected to be 0
//  UI24    Flags;          //Reserved, set to 0
//  UI8     Count;          //The number of entries in the Chapters array
//  chpl_list_t * Chapters;
} chpl_t;

typedef struct
{
    boxheader_t header;
    UI8     Version;        //Either 0 or 1
//  UI24    Flags;          //Reserved, set to 0
//  UI64    CreationTime;   //if Version == 0:SI32; if Version == 1:SI64
    //The creation time of the F4V file,expressed as seconds elapsed since midnight, January 1, 1904 (UTC)
    //it's UI32/UI64 in all other place, only in mvhd it's SI32/SI64 -->should be Adobe PDF's typo
//  UI64    ModificationTime;//if Version == 0:SI32; if Version == 1:SI64
    //The last modification time of the F4V file, expressed as seconds elapsed since midnight, January 1, 1904 (UTC)
    UI32    TimeScale;      //Specifies the time coordinate system for the entire F4V file; for example,100 indicates the time units are 1/100 second each
    UI64    Duration;       //if Version == 0:SI32; if Version == 1:SI64
    //The total length of the F4V file presentation with respect to the TimeScale; this value is also the duration of the longest track in the file
    //there are still other fields, but ignored.
    uint64_t newDuration;
} mvhd_t;


#define MAX_TRACKS 6        //no official definition found. usually 2 tracks? 1 for audio, 1 for video.

typedef struct
{
    boxheader_t header;
    mvhd_t mvhd;
//  chpl_t chpl;
    trak_t trak[MAX_TRACKS];
    int track_num;                  //-1:no track;0:1 track max=MAX_TRACKS
    uint32_t mdat_header_length;    //8 or 16
    uint64_t mdat_start_offset;
    uint64_t mdat_end_offset;
    uint64_t offset_in_file;
} moov_t;

#define FourCC(a, b, c, d)  ((uint32_t)(a) << 24) + \
    ((uint32_t)(b) << 16) + \
    ((uint32_t)(c) << 8) + \
    ((uint32_t)(d))

/***************
typedef struct
{
    boxheader_t header;
    UI8     Version;        //Expected to be 0
    UI24    Flags;          //No flags defined, set to 0
    UI32    ConstantSize;   //If all samples have the same size, this field is set with that constant size;otherwise it is 0
    UI32    SizeCount;      //The number of entries in SizeTable
    uint64_t offset_in_file;
    uint32_t original_box_size;
} stsz_in_mini_moov_t;

typedef struct
{
    boxheader_t header;
    uint32_t mdat_header_length;    //8 or 16
    uint64_t mdat_start_offset;
    uint64_t mdat_end_offset;
    uint64_t offset_in_file;
} moov_in_mini_moov_t;
****************/
