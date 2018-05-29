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
#include <lsr/ls_md5.h>

#include <assert.h>
#include <string.h>

#if defined( USE_OPENSSL_MD5 )

int ls_md5_init(ls_md5_ctx_t *ctx)
{
    return MD5_Init((MD5_CTX *)ctx);
}

int ls_md5_update(ls_md5_ctx_t *ctx, const void *p, size_t len)
{
    return MD5_Update((MD5_CTX *)ctx, p, len);
}

int ls_md5_final(unsigned char *ret, ls_md5_ctx_t *ctx)
{
    return MD5_Final(ret, (MD5_CTX *)ctx);
}

unsigned char *ls_md5(const unsigned char *p, size_t len,
                      unsigned char *ret)
{
    return MD5(p, len, ret);
}

#else

#define LSR_MD5_F_FN( x, y, z )          ((z) ^ ((x) & ((y) ^ (z))))
#define LSR_MD5_G_FN( x, y, z )          ((y) ^ ((z) & ((x) ^ (y))))
#define LSR_MD5_H_FN( x, y, z )          ((x) ^ (y) ^ (z))
#define LSR_MD5_I_FN( x, y, z )          ((y) ^ ((x) | ~(z)))

#define LSR_MD5_STEP( f, a, b, c, d, x, t, s ) \
    (a) += f((b), (c), (d)) + (x) + (t); \
    (a) = (((a) << (s)) | (((a) & 0xffffffff) >> (32 - (s)))); \
    (a) += (b);

#if defined(__i386__) || defined(__x86_64__) || defined(__vax__)
#define LSR_MD5_G1(n) \
    (*(uint32_t *)&ptr[(n) * 4])
#define LSR_MD5_G(n) \
    LSR_MD5_G1(n)
#else
#define LSR_MD5_G1(n) \
    (ctx->chunk[(n)] = \
                       (uint32_t)ptr[(n) * 4] | \
                       ((uint32_t)ptr[(n) * 4 + 1] << 8) | \
                       ((uint32_t)ptr[(n) * 4 + 2] << 16) | \
                       ((uint32_t)ptr[(n) * 4 + 3] << 24))
#define LSR_MD5_G(n) \
    (ctx->chunk[(n)])
#endif

static const void *ls_md5_transform(ls_md5_ctx_t *ctx, const void *p,
                                    unsigned long size);


int ls_md5_init(ls_md5_ctx_t *ctx)
{
    ctx->A = 0x67452301;
    ctx->B = 0xefcdab89;
    ctx->C = 0x98badcfe;
    ctx->D = 0x10325476;
    ctx->lo = 0;
    ctx->hi = 0;
    return 1;
}

int ls_md5_update(ls_md5_ctx_t *ctx, const void *p, size_t len)
{
    uint32_t iCurrLo;
    unsigned long used, available;

    iCurrLo = ctx->lo;
    if ((ctx->lo = (iCurrLo + len) & 0x1fffffff) < iCurrLo)
        ctx->hi++;
    ctx->hi += len >> 29;
    used = iCurrLo & 0x3f;
    if (used)
    {
        available = 64 - used;
        if (len < available)
        {
            memcpy(&ctx->shiftBuf[used], p, len);
            return 0;
        }
        memcpy(&ctx->shiftBuf[used], p, available);
        p = (const unsigned char *)p + available;
        len -= available;
        ls_md5_transform(ctx, ctx->shiftBuf, 64);
    }
    if (len >= 64)
    {
        p = ls_md5_transform(ctx, p, len & ~(unsigned long)0x3f);
        len &= 0x3f;
    }
    memcpy(ctx->shiftBuf, p, len);
    return 1;
}

int ls_md5_final(unsigned char *ret, ls_md5_ctx_t *ctx)
{
    unsigned long used, available;

    used = ctx->lo & 0x3f;
    ctx->shiftBuf[used++] = 0x80;
    available = 64 - used;
    if (available < 8)
    {
        memset(&ctx->shiftBuf[used], 0, available);
        ls_md5_transform(ctx, ctx->shiftBuf, 64);
        used = 0;
        available = 64;
    }
    memset(&ctx->shiftBuf[used], 0, available - 8);

    ctx->lo <<= 3;
    ctx->shiftBuf[56] = ctx->lo;
    ctx->shiftBuf[57] = ctx->lo >> 8;
    ctx->shiftBuf[58] = ctx->lo >> 16;
    ctx->shiftBuf[59] = ctx->lo >> 24;
    ctx->shiftBuf[60] = ctx->hi;
    ctx->shiftBuf[61] = ctx->hi >> 8;
    ctx->shiftBuf[62] = ctx->hi >> 16;
    ctx->shiftBuf[63] = ctx->hi >> 24;

    ls_md5_transform(ctx, ctx->shiftBuf, 64);

    ret[0] = ctx->A;
    ret[1] = ctx->A >> 8;
    ret[2] = ctx->A >> 16;
    ret[3] = ctx->A >> 24;
    ret[4] = ctx->B;
    ret[5] = ctx->B >> 8;
    ret[6] = ctx->B >> 16;
    ret[7] = ctx->B >> 24;
    ret[8] = ctx->C;
    ret[9] = ctx->C >> 8;
    ret[10] = ctx->C >> 16;
    ret[11] = ctx->C >> 24;
    ret[12] = ctx->D;
    ret[13] = ctx->D >> 8;
    ret[14] = ctx->D >> 16;
    ret[15] = ctx->D >> 24;

    memset(ctx, 0, sizeof(*ctx));

    return 1;
}

unsigned char *ls_md5(const unsigned char *p, size_t len,
                      unsigned char *ret)
{
    assert(ret);
    ls_md5_ctx_t ctx;

    if (!ls_md5_init(&ctx))
        return NULL;
    ls_md5_update(&ctx, p, len);
    ls_md5_final(ret, &ctx);
    memset(&ctx, 0, sizeof(ls_md5_ctx_t));
    return ret;
}

static const void *ls_md5_transform(ls_md5_ctx_t *ctx, const void *p,
                                    unsigned long size)
{
    const unsigned char *ptr;
    uint32_t a0, b0, c0, d0;
    uint32_t a, b, c, d;
    ptr = (const unsigned char *)p;

    a0 = ctx->A;
    b0 = ctx->B;
    c0 = ctx->C;
    d0 = ctx->D;

    do
    {
        a = a0;
        b = b0;
        c = c0;
        d = d0;

        LSR_MD5_STEP(LSR_MD5_F_FN, a0, b0, c0, d0, LSR_MD5_G1(0), 0xd76aa478, 7)
        LSR_MD5_STEP(LSR_MD5_F_FN, d0, a0, b0, c0, LSR_MD5_G1(1), 0xe8c7b756, 12)
        LSR_MD5_STEP(LSR_MD5_F_FN, c0, d0, a0, b0, LSR_MD5_G1(2), 0x242070db, 17)
        LSR_MD5_STEP(LSR_MD5_F_FN, b0, c0, d0, a0, LSR_MD5_G1(3), 0xc1bdceee, 22)
        LSR_MD5_STEP(LSR_MD5_F_FN, a0, b0, c0, d0, LSR_MD5_G1(4), 0xf57c0faf, 7)
        LSR_MD5_STEP(LSR_MD5_F_FN, d0, a0, b0, c0, LSR_MD5_G1(5), 0x4787c62a, 12)
        LSR_MD5_STEP(LSR_MD5_F_FN, c0, d0, a0, b0, LSR_MD5_G1(6), 0xa8304613, 17)
        LSR_MD5_STEP(LSR_MD5_F_FN, b0, c0, d0, a0, LSR_MD5_G1(7), 0xfd469501, 22)
        LSR_MD5_STEP(LSR_MD5_F_FN, a0, b0, c0, d0, LSR_MD5_G1(8), 0x698098d8, 7)
        LSR_MD5_STEP(LSR_MD5_F_FN, d0, a0, b0, c0, LSR_MD5_G1(9), 0x8b44f7af, 12)
        LSR_MD5_STEP(LSR_MD5_F_FN, c0, d0, a0, b0, LSR_MD5_G1(10), 0xffff5bb1, 17)
        LSR_MD5_STEP(LSR_MD5_F_FN, b0, c0, d0, a0, LSR_MD5_G1(11), 0x895cd7be, 22)
        LSR_MD5_STEP(LSR_MD5_F_FN, a0, b0, c0, d0, LSR_MD5_G1(12), 0x6b901122, 7)
        LSR_MD5_STEP(LSR_MD5_F_FN, d0, a0, b0, c0, LSR_MD5_G1(13), 0xfd987193, 12)
        LSR_MD5_STEP(LSR_MD5_F_FN, c0, d0, a0, b0, LSR_MD5_G1(14), 0xa679438e, 17)
        LSR_MD5_STEP(LSR_MD5_F_FN, b0, c0, d0, a0, LSR_MD5_G1(15), 0x49b40821, 22)

        LSR_MD5_STEP(LSR_MD5_G_FN, a0, b0, c0, d0, LSR_MD5_G(1), 0xf61e2562, 5)
        LSR_MD5_STEP(LSR_MD5_G_FN, d0, a0, b0, c0, LSR_MD5_G(6), 0xc040b340, 9)
        LSR_MD5_STEP(LSR_MD5_G_FN, c0, d0, a0, b0, LSR_MD5_G(11), 0x265e5a51, 14)
        LSR_MD5_STEP(LSR_MD5_G_FN, b0, c0, d0, a0, LSR_MD5_G(0), 0xe9b6c7aa, 20)
        LSR_MD5_STEP(LSR_MD5_G_FN, a0, b0, c0, d0, LSR_MD5_G(5), 0xd62f105d, 5)
        LSR_MD5_STEP(LSR_MD5_G_FN, d0, a0, b0, c0, LSR_MD5_G(10), 0x02441453, 9)
        LSR_MD5_STEP(LSR_MD5_G_FN, c0, d0, a0, b0, LSR_MD5_G(15), 0xd8a1e681, 14)
        LSR_MD5_STEP(LSR_MD5_G_FN, b0, c0, d0, a0, LSR_MD5_G(4), 0xe7d3fbc8, 20)
        LSR_MD5_STEP(LSR_MD5_G_FN, a0, b0, c0, d0, LSR_MD5_G(9), 0x21e1cde6, 5)
        LSR_MD5_STEP(LSR_MD5_G_FN, d0, a0, b0, c0, LSR_MD5_G(14), 0xc33707d6, 9)
        LSR_MD5_STEP(LSR_MD5_G_FN, c0, d0, a0, b0, LSR_MD5_G(3), 0xf4d50d87, 14)
        LSR_MD5_STEP(LSR_MD5_G_FN, b0, c0, d0, a0, LSR_MD5_G(8), 0x455a14ed, 20)
        LSR_MD5_STEP(LSR_MD5_G_FN, a0, b0, c0, d0, LSR_MD5_G(13), 0xa9e3e905, 5)
        LSR_MD5_STEP(LSR_MD5_G_FN, d0, a0, b0, c0, LSR_MD5_G(2), 0xfcefa3f8, 9)
        LSR_MD5_STEP(LSR_MD5_G_FN, c0, d0, a0, b0, LSR_MD5_G(7), 0x676f02d9, 14)
        LSR_MD5_STEP(LSR_MD5_G_FN, b0, c0, d0, a0, LSR_MD5_G(12), 0x8d2a4c8a, 20)

        LSR_MD5_STEP(LSR_MD5_H_FN, a0, b0, c0, d0, LSR_MD5_G(5), 0xfffa3942, 4)
        LSR_MD5_STEP(LSR_MD5_H_FN, d0, a0, b0, c0, LSR_MD5_G(8), 0x8771f681, 11)
        LSR_MD5_STEP(LSR_MD5_H_FN, c0, d0, a0, b0, LSR_MD5_G(11), 0x6d9d6122, 16)
        LSR_MD5_STEP(LSR_MD5_H_FN, b0, c0, d0, a0, LSR_MD5_G(14), 0xfde5380c, 23)
        LSR_MD5_STEP(LSR_MD5_H_FN, a0, b0, c0, d0, LSR_MD5_G(1), 0xa4beea44, 4)
        LSR_MD5_STEP(LSR_MD5_H_FN, d0, a0, b0, c0, LSR_MD5_G(4), 0x4bdecfa9, 11)
        LSR_MD5_STEP(LSR_MD5_H_FN, c0, d0, a0, b0, LSR_MD5_G(7), 0xf6bb4b60, 16)
        LSR_MD5_STEP(LSR_MD5_H_FN, b0, c0, d0, a0, LSR_MD5_G(10), 0xbebfbc70, 23)
        LSR_MD5_STEP(LSR_MD5_H_FN, a0, b0, c0, d0, LSR_MD5_G(13), 0x289b7ec6, 4)
        LSR_MD5_STEP(LSR_MD5_H_FN, d0, a0, b0, c0, LSR_MD5_G(0), 0xeaa127fa, 11)
        LSR_MD5_STEP(LSR_MD5_H_FN, c0, d0, a0, b0, LSR_MD5_G(3), 0xd4ef3085, 16)
        LSR_MD5_STEP(LSR_MD5_H_FN, b0, c0, d0, a0, LSR_MD5_G(6), 0x04881d05, 23)
        LSR_MD5_STEP(LSR_MD5_H_FN, a0, b0, c0, d0, LSR_MD5_G(9), 0xd9d4d039, 4)
        LSR_MD5_STEP(LSR_MD5_H_FN, d0, a0, b0, c0, LSR_MD5_G(12), 0xe6db99e5, 11)
        LSR_MD5_STEP(LSR_MD5_H_FN, c0, d0, a0, b0, LSR_MD5_G(15), 0x1fa27cf8, 16)
        LSR_MD5_STEP(LSR_MD5_H_FN, b0, c0, d0, a0, LSR_MD5_G(2), 0xc4ac5665, 23)

        LSR_MD5_STEP(LSR_MD5_I_FN, a0, b0, c0, d0, LSR_MD5_G(0), 0xf4292244, 6)
        LSR_MD5_STEP(LSR_MD5_I_FN, d0, a0, b0, c0, LSR_MD5_G(7), 0x432aff97, 10)
        LSR_MD5_STEP(LSR_MD5_I_FN, c0, d0, a0, b0, LSR_MD5_G(14), 0xab9423a7, 15)
        LSR_MD5_STEP(LSR_MD5_I_FN, b0, c0, d0, a0, LSR_MD5_G(5), 0xfc93a039, 21)
        LSR_MD5_STEP(LSR_MD5_I_FN, a0, b0, c0, d0, LSR_MD5_G(12), 0x655b59c3, 6)
        LSR_MD5_STEP(LSR_MD5_I_FN, d0, a0, b0, c0, LSR_MD5_G(3), 0x8f0ccc92, 10)
        LSR_MD5_STEP(LSR_MD5_I_FN, c0, d0, a0, b0, LSR_MD5_G(10), 0xffeff47d, 15)
        LSR_MD5_STEP(LSR_MD5_I_FN, b0, c0, d0, a0, LSR_MD5_G(1), 0x85845dd1, 21)
        LSR_MD5_STEP(LSR_MD5_I_FN, a0, b0, c0, d0, LSR_MD5_G(8), 0x6fa87e4f, 6)
        LSR_MD5_STEP(LSR_MD5_I_FN, d0, a0, b0, c0, LSR_MD5_G(15), 0xfe2ce6e0, 10)
        LSR_MD5_STEP(LSR_MD5_I_FN, c0, d0, a0, b0, LSR_MD5_G(6), 0xa3014314, 15)
        LSR_MD5_STEP(LSR_MD5_I_FN, b0, c0, d0, a0, LSR_MD5_G(13), 0x4e0811a1, 21)
        LSR_MD5_STEP(LSR_MD5_I_FN, a0, b0, c0, d0, LSR_MD5_G(4), 0xf7537e82, 6)
        LSR_MD5_STEP(LSR_MD5_I_FN, d0, a0, b0, c0, LSR_MD5_G(11), 0xbd3af235, 10)
        LSR_MD5_STEP(LSR_MD5_I_FN, c0, d0, a0, b0, LSR_MD5_G(2), 0x2ad7d2bb, 15)
        LSR_MD5_STEP(LSR_MD5_I_FN, b0, c0, d0, a0, LSR_MD5_G(9), 0xeb86d391, 21)

        a0 += a;
        b0 += b;
        c0 += c;
        d0 += d;

        ptr += 64;
    }
    while (size -= 64);
    ctx->A = a0;
    ctx->B = b0;
    ctx->C = c0;
    ctx->D = d0;
    return ptr;
}


#endif
