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
#ifndef OUTPUTSTREAM_H
#define OUTPUTSTREAM_H

class IOVec;
class OutputStream
{
public:
    OutputStream() {};
    virtual ~OutputStream() {};
    // Output stream interfaces
    virtual int write(const char *pBuf, int size) = 0;
    virtual int writev(const struct iovec *vector, int count) = 0;
    virtual int writev(IOVec &vector);   // = 0;
    virtual int writev(IOVec &vector, int total);
    virtual int flush() = 0;
    virtual int close() = 0;
    int writevToWrite(const struct iovec *vector, int count);

};


#endif
