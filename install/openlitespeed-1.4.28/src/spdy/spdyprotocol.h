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
#ifndef SPDYPROTOCOL_H
#define SPDYPROTOCOL_H
#include <spdy/protocoldef.h>
#include <sys/types.h>
#include <arpa/inet.h>
// Types of SPDY frames.

enum SpdyFrameType
{
    SPDY_FRAME_DATA = 0,
    SPDY_FRAME_SYN_STREAM = 1,
    SPDY_FRAME_FIRST_CONTROL_TYPE = SPDY_FRAME_SYN_STREAM,
    SPDY_FRAME_SYN_REPLY,
    SPDY_FRAME_RST_STREAM,
    SPDY_FRAME_SETTINGS,
    SPDY_FRAME_NOOP,  // Because it is valid in SPDY/2, kept for identifiability/enum order.
    SPDY_FRAME_PING,
    SPDY_FRAME_GOAWAY,
    SPDY_FRAME_HEADERS,
    SPDY_FRAME_WINDOW_UPDATE,
    SPDY_FRAME_CREDENTIAL,
    SPDY_FRAME_LAST_CONTROL_TYPE = SPDY_FRAME_CREDENTIAL
};
// Flags on data packets.
enum SpdyDataFlags
{
    SPDY_DATA_FLAG_NONE = 0,
    SPDY_DATA_FLAG_FIN = 1,
};

// Flags on control packets
enum SpdyControlFlags
{
    SPDY_CTRL_FLAG_NONE = 0,
    SPDY_CTRL_FLAG_FIN = 1,
    SPDY_CTRL_FLAG_UNIDIRECTIONAL = 2
};

// Flags on the SETTINGS control frame.
enum SpdySettingsControlFlags
{
    SPDY_SETTINGS_FLAG_CLEAR_PREVIOUS = 0x1
};

// Flags for settings within a SETTINGS frame.
enum SpdySettingsFlags
{
    SPDY_SETTINGS_FLAG_NONE = 0x0,
    SPDY_SETTINGS_FLAG_PLEASE_PERSIST = 0x1,
    SPDY_SETTINGS_FLAG_PERSISTED = 0x2
};

// List of known settings.
enum SpdySettingsIds
{
    SPDY_SETTINGS_UPLOAD_BANDWIDTH = 0x1,
    SPDY_SETTINGS_DOWNLOAD_BANDWIDTH = 0x2,
    // Network round trip time in milliseconds.
    SPDY_SETTINGS_ROUND_TRIP_TIME = 0x3,
    SPDY_SETTINGS_MAX_CONCURRENT_STREAMS = 0x4,
    // TCP congestion window in packets.
    SPDY_SETTINGS_CURRENT_CWND = 0x5,
    // Downstream byte retransmission rate in percentage.
    SPDY_SETTINGS_DOWNLOAD_RETRANS_RATE = 0x6,
    // Initial window size in bytes
    SPDY_SETTINGS_INITIAL_WINDOW_SIZE = 0x7
};

// Status codes for RST_STREAM frames.
enum SpdyRstErrorCode
{
    SPDY_RST_STREAM_INVALID = 0,
    SPDY_RST_STREAM_PROTOCOL_ERROR = 1,
    SPDY_RST_STREAM_INVALID_STREAM = 2,
    SPDY_RST_STREAM_REFUSED_STREAM = 3,
    SPDY_RST_STREAM_UNSUPPORTED_VERSION = 4,
    SPDY_RST_STREAM_CANCEL = 5,
    SPDY_RST_STREAM_INTERNAL_ERROR = 6,
    SPDY_RST_STREAM_FLOW_CONTROL_ERROR = 7,
    SPDY_RST_STREAM_IN_USE = 8,
    SPDY_RST_STREAM_ALREADY_CLOSED = 9,
    SPDY_RST_STREAM_INVALID_CREDENTIALS = 10,
    SPDY_RST_STREAM_FRAME_TOO_LARGE = 11,
    SPDY_RST_STREAM_NUM_STATUS_CODES = 12
};

// Status codes for GOAWAY frames.
enum SpdyGoAwayStatus
{
    SPDY_GOAWAY_INVALID = -1,
    SPDY_GOAWAY_OK = 0,
    SPDY_GOAWAY_PROTOCOL_ERROR = 1,
    SPDY_GOAWAY_INTERNAL_ERROR = 2,
    SPDY_GOAWAY_NUM_STATUS_CODES = 3,
    SPDY_GOAWAY_FLOW_CONTROL_ERROR = 7,
};

#define SPDY_FRAME_HEADER_SIZE 8

class SpdyFrameHeader
{
    struct spdy_ctl_hdr
    {
        unsigned char m_b80;
        unsigned char m_bVer;
        unsigned char m_bType0;
        unsigned char m_bType;
    };

    union
    {
        struct spdy_ctl_hdr m_ctl;
        uint32_t      m_iStreamId;

    } m_un;
    unsigned char m_bFlags;
    unsigned char m_bLength[3];
    uint32_t      m_data[];
public:
    SpdyFrameHeader() {}
    ~SpdyFrameHeader() {}

    int isControlFrame() const      {   return m_un.m_ctl.m_b80 == 0x80;  }
    unsigned char getType() const   {   return (m_un.m_ctl.m_b80 == 0x80) ? (m_un.m_ctl.m_bType) : (0);  }
    unsigned char getFlags() const  {   return m_bFlags; }
    unsigned char getVersion() const {   return m_un.m_ctl.m_bVer;   }

    uint32_t getDataStreamId() const {   return ntohl(m_un.m_iStreamId);  }
    void setStreamId(uint32_t id) {  m_un.m_iStreamId = htonl(id);  }


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
    uint32_t getData(int n) const   {   return m_data[n];   }
    uint32_t getHboData(int n) const     {   return ntohl(m_data[n]);  }
};


const char *getFrameName(unsigned char bframeType);

class SpdySettingPairs
{
    union
    {
        unsigned char m_b[4];
        uint32_t      m_ui;

    } m_unFlagId;
    uint32_t      m_uiValue;

public:
    void swapID()
    {
        unsigned char ch;
        ch = m_unFlagId.m_b[0];
        m_unFlagId.m_b[0] = m_unFlagId.m_b[3];
        m_unFlagId.m_b[3] = ch;
        ch = m_unFlagId.m_b[1];
        m_unFlagId.m_b[1] = m_unFlagId.m_b[2];
        m_unFlagId.m_b[2] = ch;
    }
    unsigned char getFlags() const { return m_unFlagId.m_b[0]; }
    uint32_t getValue() const { return ntohl(m_uiValue); }
    uint32_t getID() const  { return (ntohl(m_unFlagId.m_ui) & 0xFFFFFF); }
};

#define SPDY_MAX_DATAFRAM_SIZE    65536
#define SPDY_FCW_INIT_SIZE        65536

#endif // SPDYPROTOCOL_H
