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
#ifndef H2PROTOCOL_H
#define H2PROTOCOL_H

#include <spdy/protocoldef.h>
#include <lsdef.h>

#include <arpa/inet.h>
#include <string.h>
#include <sys/types.h>

// Types of HTTP2 frames.
enum H2FrameType
{
    H2_FRAME_DATA           = 0,
    H2_FRAME_HEADERS,
    H2_FRAME_PRIORITY,
    H2_FRAME_RST_STREAM,
    H2_FRAME_SETTINGS,      //4,
    H2_FRAME_PUSH_PROMISE,  //5,
    H2_FRAME_PING,          //6,
    H2_FRAME_GOAWAY,        //7,
    H2_FRAME_WINDOW_UPDATE, //8,
    H2_FRAME_CONTINUATION,  //9,
    H2_FRAME_MAX_TYPE,      //10
};
// Flags on data packets.
enum H2DataFlags
{
    H2_DATA_FLAG_NONE = 0,
    H2_DATA_FLAG_FIN = 1,
};

// Flags on control packets
enum H2ControlFlags
{
    H2_CTRL_FLAG_NONE = 0,
    H2_CTRL_FLAG_FIN = 1,
};

// Flags on the SETTINGS control frame.
enum H2SettingsControlFlags
{
    H2_SETTINGS_FLAG_CLEAR_PREVIOUS = 0x1
};

// Flags for settings within a SETTINGS frame.
enum H2FrameFlags
{
    H2_FLAG_ACK         = 0x1,
    H2_FLAG_END_STREAM  = 0x1,
    H2_FLAG_END_HEADERS = 0x4,
    H2_FLAG_PADDED      = 0x8,
    H2_FLAG_PRIORITY    = 0x20,

};

// List of known settings.
enum H2SettingsIds
{
    H2_SETTINGS_HEADER_TABLE_SIZE       = 0x1,
    H2_SETTINGS_ENABLE_PUSH             = 0x2,
    // Network round trip time in milliseconds.
    H2_SETTINGS_MAX_CONCURRENT_STREAMS  = 0x3,
    // Initial window size in bytes
    H2_SETTINGS_INITIAL_WINDOW_SIZE     = 0x4,
    // TCP congestion window in packets.
    H2_SETTINGS_MAX_FRAME_SIZE          = 0x5,
    // Downstream byte retransmission rate in percentage.
    H2_SETTINGS_MAX_HEADER_LIST_SIZE    = 0x6,
};

// Status codes for RST_STREAM frames.
enum H2ErrorCode
{
    H2_ERROR_NO_ERROR              = 0,
    H2_ERROR_PROTOCOL_ERROR        = 1,
    H2_ERROR_INTERNAL_ERROR        = 2,
    H2_ERROR_FLOW_CONTROL_ERROR    = 3,
    H2_ERROR_SETTINGS_TIMEOUT      = 4,
    H2_ERROR_STREAM_CLOSED         = 5,
    H2_ERROR_FRAME_SIZE_ERROR      = 6,
    H2_ERROR_REFUSED_STREAM        = 7,
    H2_ERROR_CANCEL                = 8,
    H2_ERROR_COMPRESSION_ERROR     = 9,
    H2_ERROR_CONNECT_ERROR         = 10,
    H2_ERROR_ENHANCE_YOUR_CALM     = 11,
    H2_ERROR_INADEQUATE_SECURITY   = 12,
    H2_ERROR_HTTP_1_1_REQUIRED     = 13,
    H2_ERROR_CODE_COUNT            = 14
};


#define H2_FRAME_HEADER_SIZE        9
#define H2_PING_FRAME_PAYLOAD_SIZE  8

class H2FrameHeader
{
    unsigned char m_bLength[3];
    unsigned char m_bType;
    unsigned char m_bFlags;
    unsigned char m_iStreamId[4];

    uint32_t      m_payload[];
public:
    H2FrameHeader() {}
    ~H2FrameHeader() {}
    H2FrameHeader(uint32_t len, H2FrameType type, uint8_t flags)
        : m_bType(type)
        , m_bFlags(flags)
    {
        setLength(len);
        memset(m_iStreamId, 0, 4);
    }

    H2FrameHeader(uint32_t len, H2FrameType type, uint8_t flags,
                  uint32_t uiStreamId)
        : m_bType(type)
        , m_bFlags(flags)
    {
        setLength(len);
        setStreamId(uiStreamId);
    }


    unsigned char getType() const   {   return m_bType;  }
    unsigned char getFlags() const  {   return m_bFlags; }

    uint32_t getStreamId() const
    {
        return (((uint32_t)m_iStreamId[0]) << 24) |
               (((uint32_t)m_iStreamId[1]) << 16) |
               (((uint32_t)m_iStreamId[2]) << 8) |
               (m_iStreamId[3]);
    }

    void setStreamId(uint32_t id)
    {
        m_iStreamId[ 0 ] = (id >> 24) & 0xff;
        m_iStreamId[ 1 ] = (id >> 16) & 0xff;
        m_iStreamId[ 2 ] = (id >> 8) & 0xff;
        m_iStreamId[ 3 ] = id & 0xff;
    }


    uint32_t getLength() const
    {
        return (((uint32_t)m_bLength[0]) << 16) |
               (((uint32_t)m_bLength[1]) << 8) |
               (m_bLength[2]);
    }
    void setLength(uint32_t l)
    {
        m_bLength[ 0 ] = (l >> 16) & 0xff;
        m_bLength[ 1 ] = (l >> 8) & 0xff;
        m_bLength[ 2 ] = l & 0xff;
    }
    const uint32_t *getPayload() const  {   return m_payload;      }

    LS_NO_COPY_ASSIGN(H2FrameHeader);
};


const char *getH2FrameName(unsigned char bframeType);

class H2SettingPairs
{
    uint16_t      m_id;
    uint32_t      m_uiValue;

public:
    uint32_t getValue() const { return ntohl(m_uiValue); }
    uint16_t getID() const  { return (ntohs(m_id)); }
};

struct Priority_st
{
    uint8_t     m_exclusive;
    uint32_t    m_dependStreamId;
    uint16_t    m_weight;  //1~256
};


#define H2_MAX_DATAFRAM_SIZE        16777215
#define H2_DEFAULT_DATAFRAME_SIZE   16384
#define H2_FCW_INIT_SIZE            65535
#define H2_FCW_MAX_SIZE             (2147483647)

#define MAX_HTTP2_HEADERS_SIZE      65536
#define MAX_HEADER_TABLE_SIZE       (512 * 1024)

#endif // H2PROTOCOL_H
