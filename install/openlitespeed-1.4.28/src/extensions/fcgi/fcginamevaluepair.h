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
#ifndef FCGINAMEVALUEPAIR_H
#define FCGINAMEVALUEPAIR_H



class FcgiNameValuePair
{
    FcgiNameValuePair();
    ~FcgiNameValuePair();
public:
    static int append(char *pBuf, int &size,
                      const char *pName, int nameLen,
                      const char *pValue, int valLen);
    static int append(char *pBuf, int &size,
                      const char *pName, const char *pValue);
    static int decode(char *pBuf, int size,
                      char *&pName, int &nameLen,
                      char *&pVal, int &valLen);
};

#endif
