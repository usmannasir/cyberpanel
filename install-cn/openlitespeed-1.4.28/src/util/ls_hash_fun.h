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


/*

 static long mix_master[/* 0:255 */]  =
{
    /* 000 */ 0x7043a46fL, 0x6e7eac19L, 0xcf055952L,
    /*     */ 0xbf010101L, 0x128e8a64L,
    /* 005 */ 0x8adcfef2L, 0x42e20c6cL, 0xb1095c58L,
    /*     */ 0x65361d67L, 0xc7a4b199L,
    /* 010 */ 0x52f24df2L, 0xd0549327L, 0x9a3b180fL,
    /*     */ 0x6b21f2ebL, 0x3cff1325L,
    /* 015 */ 0x07b575b9L, 0x8a23b7e2L, 0xfbd9091dL,
    /*     */ 0x834dbdf9L, 0xb68d6313L,
    /* 020 */ 0xb6d06b93L, 0xeba548afL, 0xacc917c9L,
    /*     */ 0x2dffbcfaL, 0xd301f3b5L,
    /* 025 */ 0xf1663592L, 0xf6ce9e4fL, 0x13206f02L,
    /*     */ 0xf2dc50f7L, 0x3e880a87L,
    /* 030 */ 0xabbf065dL, 0x8fabcb6dL, 0x9116f2d0L,
    /*     */ 0xcb9af152L, 0xe85aec09L,
    /* 035 */ 0xfc4fc987L, 0xa9ce535eL, 0xb849398eL,
    /*     */ 0x4d2e70d8L, 0xae19b18fL,
    /* 040 */ 0x47d5ebeaL, 0xfdc60511L, 0x3fcc44afL,
    /*     */ 0x14a68f17L, 0xa09aafdcL,
    /* 045 */ 0x594a3294L, 0xae1de1b9L, 0xfd1c1dd0L,
    /*     */ 0x18b98ee6L, 0xd357dabcL,
    /* 050 */ 0x2e8826aaL, 0xec4055f1L, 0x4c34f8a9L,
    /*     */ 0x8170e402L, 0x55eca72eL,
    /* 055 */ 0xd1bde03fL, 0x25e368ffL, 0x0b120f4aL,
    /*     */ 0x9028f728L, 0x14df0433L,
    /* 060 */ 0x6dd3601eL, 0xaa052772L, 0xe427f736L,
    /*     */ 0x13e35041L, 0x69b76914L,
    /* 065 */ 0xe3b3c01cL, 0x307d6fafL, 0xc221deccL,
    /*     */ 0xa4281a5dL, 0xa2fcaba7L,
    /* 070 */ 0x666d4a9fL, 0x02c4be93L, 0x332ecb2fL,
    /*     */ 0xf6f74ab0L, 0x2f1dfe8fL,
    /* 075 */ 0x7152a6f9L, 0xc2ea9be7L, 0x86c1899eL,
    /*     */ 0xe3bdefd7L, 0x7512901bL,
    /* 080 */ 0x994a1fbdL, 0x3d47ff0dL, 0xc6f78e66L,
    /*     */ 0x3e2d25d2L, 0x0134d573L,
    /* 085 */ 0xe1023afaL, 0xc8c66c0aL, 0xd54c12edL,
    /*     */ 0xcf6689f0L, 0x67f7677aL,
    /* 090 */ 0x767b9867L, 0xcd5b2341L, 0x1733f9bcL,
    /*     */ 0x5bc867bfL, 0xd9418811L,
    /* 095 */ 0xe7499083L, 0xdf9b12e8L, 0xec3e0928L,
    /*     */ 0xf6d08914L, 0x758e524aL,
    /* 100 */ 0xc000f455L, 0x1a786c79L, 0x8e012db1L,
    /*     */ 0x9d7b42faL, 0x25cda5f0L,
    /* 105 */ 0x5fba9220L, 0x605a11e1L, 0x6cb23e6cL,
    /*     */ 0x1b483b87L, 0xb997ee22L,
    /* 110 */ 0x877f7362L, 0x2c1768d4L, 0x1673f9adL,
    /*     */ 0xd11fe93dL, 0x04e1cde4L,
    /* 115 */ 0x50747250L, 0x005b5db6L, 0xbbaf4817L,
    /*     */ 0x7379e196L, 0xaca98701L,
    /* 120 */ 0xd24bde84L, 0x9fabbcb6L, 0x4a97882bL,
    /*     */ 0xe59a1fd8L, 0x7ec7ce10L,
    /* 125 */ 0x6780f244L, 0x2f61b3ffL, 0xa1c71c95L,
    /*     */ 0x0b2d765cL, 0xf988514dL,
    /* 130 */ 0x0a98e840L, 0x1411bc42L, 0xaa4482c2L,
    /*     */ 0x2d9d47daL, 0xf128a622L,
    /* 135 */ 0x35ba5647L, 0x18962dbdL, 0x70f6d242L,
    /*     */ 0xc7635d81L, 0x43753680L,
    /* 140 */ 0x0aeaab4cL, 0x810f2220L, 0x65d9c0b1L,
    /*     */ 0x78356c94L, 0x30f27e2fL,
    /* 145 */ 0x9d16b440L, 0x35771070L, 0xe9bc2336L,
    /*     */ 0xe935d2fdL, 0xf4720cffL,
    /* 150 */ 0x6975173cL, 0x520e2405L, 0xa9e73ce2L,
    /*     */ 0x062623a7L, 0x18e26104L,
    /* 155 */ 0xc0e4f061L, 0x464cfee9L, 0xccdc534aL,
    /*     */ 0x0f192a14L, 0x94b71649L,
    /* 160 */ 0x9aeb0675L, 0x4647e040L, 0x397f1004L,
    /*     */ 0xf4ec8dfcL, 0xbfd0006bL,
    /* 165 */ 0xc5b4ed0fL, 0xba6bccbeL, 0x2e03fe1bL,
    /*     */ 0x16f0b363L, 0xc3392942L,
    /* 170 */ 0x22d6cf9cL, 0xce55fec5L, 0x09b40463L,
    /*     */ 0xf14a310bL, 0x7bbcf76bL,
    /* 175 */ 0x7c249602L, 0xc4e99555L, 0xde625355L,
    /*     */ 0x0c1aa55dL, 0x3eaced91L,
    /* 180 */ 0x93b9ff1eL, 0x8d381f2dL, 0xbcdb5ba8L,
    /*     */ 0xff7792bcL, 0xf05a19a0L,
    /* 185 */ 0x560ffb0cL, 0x1a68fa68L, 0x02b1ce1aL,
    /*     */ 0x9a610474L, 0xd1a0fecbL,
    /* 190 */ 0xf90e8533L, 0x23f84d95L, 0x83c110c4L,
    /*     */ 0x6f90588dL, 0x9ee04455L,
    /* 195 */ 0xc40504baL, 0xfee93369L, 0x85804099L,
    /*     */ 0xabe5d01bL, 0x4b3865d6L,
    /* 200 */ 0x8a5c108fL, 0x9654f2dcL, 0xb0d19772L,
    /*     */ 0xc406152bL, 0x7be2b8a5L,
    /* 205 */ 0x892967adL, 0x6308e597L, 0xe874e16aL,
    /*     */ 0x8d2e274fL, 0x6007fc05L,
    /* 210 */ 0x4230fc39L, 0x99144de1L, 0x8dcc89b3L,
    /*     */ 0x14161bfdL, 0x498cd270L,
    /* 215 */ 0x7dbbd9f8L, 0x5628d7d0L, 0x205d9ea4L,
    /*     */ 0xf214ebfaL, 0xd1ebedafL,
    /* 220 */ 0x3237002fL, 0x147e6e5eL, 0x4483ebd3L,
    /*     */ 0xe9b05aa6L, 0x3517c363L,
    /* 225 */ 0xe8e9e8a2L, 0x19d89df6L, 0x62defab3L,
    /*     */ 0x14f4e201L, 0x57c48f3fL,
    /* 230 */ 0xb8e6e5dcL, 0x5fa6d27aL, 0x1dc3078eL,
    /*     */ 0x5ca367f9L, 0xfdcbb7ccL,
    /* 235 */ 0x2f36414bL, 0x1d3a034fL, 0x122d654fL,
    /*     */ 0xeb336078L, 0x3a8b9600L,
    /* 240 */ 0x0b5f1484L, 0x3ccfb7c6L, 0x2ff89cf1L,
    /*     */ 0x609919a6L, 0xfa83287eL,
    /* 245 */ 0xb694b7cdL, 0x77df5aeaL, 0x944508ccL,
    /*     */ 0x5581fbb8L, 0x728a05cbL,
    /* 250 */ 0x64a31712L, 0xc2f6acfaL, 0x6e560b10L,
    /*     */ 0x9d8d7ce1L, 0x0d2b2adeL, 0x0bbaa936L
};


inline size_t my_hash_string(const char *arg)
{
    unsigned long h = 0;
    unsigned char ch = *arg;
    for (; (ch = *arg) != 0; ++arg)
    {
        h = ((h << 1) | (h >> 31)) ^
            mix_master[ *arg ];
    }
    return h;
}
* /
