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
#include <lsr/ls_sha1.h>

#if defined( USE_OPENSSL_SHA1 )

int ls_sha1_init(ls_sha1_ctx_t *ctx)
{
    return SHA1_Init((SHA_CTX *)ctx);
}


void ls_sha1_free(ls_sha1_ctx_t *ctx)
{
    /* OpenSSL does not have a free. */
}


int ls_sha1_update(ls_sha1_ctx_t *ctx, const unsigned char *input,
                   size_t ilen)
{
    return SHA1_Update((SHA_CTX *)ctx, input, ilen);
}


int ls_sha1_finish(ls_sha1_ctx_t *ctx, unsigned char *output)
{
    return SHA1_Final(output, (SHA_CTX *)ctx);
}


unsigned char *ls_sha1(const unsigned char *input, size_t ilen,
                       unsigned char *output)
{
    return SHA1(input, ilen, output);
}



#else

#define LSR_SHA1_BUFSIZE 1024*16

#ifndef LSR_SHA1_GET_UINT32_BE
#define LSR_SHA1_GET_UINT32_BE( n, b, i )               \
    {                                                       \
        (n) = ( (uint32_t) (b)[(i)    ] << 24 )             \
              | ( (uint32_t) (b)[(i) + 1] << 16 )             \
              | ( (uint32_t) (b)[(i) + 2] <<  8 )             \
              | ( (uint32_t) (b)[(i) + 3]       );            \
    }
#endif

#ifndef LSR_SHA1_PUT_UINT32_BE
#define LSR_SHA1_PUT_UINT32_BE( n, b, i )               \
    {                                                       \
        (b)[(i)    ] = (unsigned char) ( (n) >> 24 );       \
        (b)[(i) + 1] = (unsigned char) ( (n) >> 16 );       \
        (b)[(i) + 2] = (unsigned char) ( (n) >>  8 );       \
        (b)[(i) + 3] = (unsigned char) ( (n)       );       \
    }
#endif


int ls_sha1_init(ls_sha1_ctx_t *ctx)
{
    if (memset(ctx, 0, sizeof(ls_sha1_ctx_t)) == NULL)
        return 0;

    ctx->m_total[0] = 0;
    ctx->m_total[1] = 0;

    ctx->m_digest_state[0] = 0x67452301;
    ctx->m_digest_state[1] = 0xEFCDAB89;
    ctx->m_digest_state[2] = 0x98BADCFE;
    ctx->m_digest_state[3] = 0x10325476;
    ctx->m_digest_state[4] = 0xC3D2E1F0;

    return 1;
}


void ls_sha1_free(ls_sha1_ctx_t *ctx)
{
    if (ctx == NULL)
        return;

    memset(ctx, 0, sizeof(ls_sha1_ctx_t));
}


static void ls_sha1_process(ls_sha1_ctx_t *ctx,
                            const unsigned char data[64])
{
    uint32_t temp, W[16], A, B, C, D, E;

    LSR_SHA1_GET_UINT32_BE(W[ 0], data,  0);
    LSR_SHA1_GET_UINT32_BE(W[ 1], data,  4);
    LSR_SHA1_GET_UINT32_BE(W[ 2], data,  8);
    LSR_SHA1_GET_UINT32_BE(W[ 3], data, 12);
    LSR_SHA1_GET_UINT32_BE(W[ 4], data, 16);
    LSR_SHA1_GET_UINT32_BE(W[ 5], data, 20);
    LSR_SHA1_GET_UINT32_BE(W[ 6], data, 24);
    LSR_SHA1_GET_UINT32_BE(W[ 7], data, 28);
    LSR_SHA1_GET_UINT32_BE(W[ 8], data, 32);
    LSR_SHA1_GET_UINT32_BE(W[ 9], data, 36);
    LSR_SHA1_GET_UINT32_BE(W[10], data, 40);
    LSR_SHA1_GET_UINT32_BE(W[11], data, 44);
    LSR_SHA1_GET_UINT32_BE(W[12], data, 48);
    LSR_SHA1_GET_UINT32_BE(W[13], data, 52);
    LSR_SHA1_GET_UINT32_BE(W[14], data, 56);
    LSR_SHA1_GET_UINT32_BE(W[15], data, 60);

#define LSR_SHA1_LEFT_ROTATE( x, n ) ((x << n) | ((x & 0xFFFFFFFF) >> (32 - n)))

#define LSR_SHA1_EXTEND( t )                            \
    (                                                       \
            temp = W[( t -  3 ) & 0x0F] ^ W[( t - 8 ) & 0x0F] ^ \
                   W[( t - 14 ) & 0x0F] ^ W[  t       & 0x0F],  \
            ( W[t & 0x0F] = LSR_SHA1_LEFT_ROTATE(temp,1) )      \
    )

#define LSR_SHA1_CALC( a, b, c, d, e, x )               \
    {                                                       \
        e += LSR_SHA1_LEFT_ROTATE(a,5) + LSR_SHA1_F(b,c,d)  \
             + LSR_SHA1_K + x; b = LSR_SHA1_LEFT_ROTATE(b,30);   \
    }

    A = ctx->m_digest_state[0];
    B = ctx->m_digest_state[1];
    C = ctx->m_digest_state[2];
    D = ctx->m_digest_state[3];
    E = ctx->m_digest_state[4];

#define LSR_SHA1_F( x, y, z ) (z ^ (x & (y ^ z)))
#define LSR_SHA1_K 0x5A827999

    LSR_SHA1_CALC(A, B, C, D, E, W[0]);
    LSR_SHA1_CALC(E, A, B, C, D, W[1]);
    LSR_SHA1_CALC(D, E, A, B, C, W[2]);
    LSR_SHA1_CALC(C, D, E, A, B, W[3]);
    LSR_SHA1_CALC(B, C, D, E, A, W[4]);
    LSR_SHA1_CALC(A, B, C, D, E, W[5]);
    LSR_SHA1_CALC(E, A, B, C, D, W[6]);
    LSR_SHA1_CALC(D, E, A, B, C, W[7]);
    LSR_SHA1_CALC(C, D, E, A, B, W[8]);
    LSR_SHA1_CALC(B, C, D, E, A, W[9]);
    LSR_SHA1_CALC(A, B, C, D, E, W[10]);
    LSR_SHA1_CALC(E, A, B, C, D, W[11]);
    LSR_SHA1_CALC(D, E, A, B, C, W[12]);
    LSR_SHA1_CALC(C, D, E, A, B, W[13]);
    LSR_SHA1_CALC(B, C, D, E, A, W[14]);
    LSR_SHA1_CALC(A, B, C, D, E, W[15]);
    LSR_SHA1_CALC(E, A, B, C, D, LSR_SHA1_EXTEND(16));
    LSR_SHA1_CALC(D, E, A, B, C, LSR_SHA1_EXTEND(17));
    LSR_SHA1_CALC(C, D, E, A, B, LSR_SHA1_EXTEND(18));
    LSR_SHA1_CALC(B, C, D, E, A, LSR_SHA1_EXTEND(19));

#undef LSR_SHA1_K
#undef LSR_SHA1_F

#define LSR_SHA1_F( x, y, z ) (x ^ y ^ z)
#define LSR_SHA1_K 0x6ED9EBA1

    LSR_SHA1_CALC(A, B, C, D, E, LSR_SHA1_EXTEND(20));
    LSR_SHA1_CALC(E, A, B, C, D, LSR_SHA1_EXTEND(21));
    LSR_SHA1_CALC(D, E, A, B, C, LSR_SHA1_EXTEND(22));
    LSR_SHA1_CALC(C, D, E, A, B, LSR_SHA1_EXTEND(23));
    LSR_SHA1_CALC(B, C, D, E, A, LSR_SHA1_EXTEND(24));
    LSR_SHA1_CALC(A, B, C, D, E, LSR_SHA1_EXTEND(25));
    LSR_SHA1_CALC(E, A, B, C, D, LSR_SHA1_EXTEND(26));
    LSR_SHA1_CALC(D, E, A, B, C, LSR_SHA1_EXTEND(27));
    LSR_SHA1_CALC(C, D, E, A, B, LSR_SHA1_EXTEND(28));
    LSR_SHA1_CALC(B, C, D, E, A, LSR_SHA1_EXTEND(29));
    LSR_SHA1_CALC(A, B, C, D, E, LSR_SHA1_EXTEND(30));
    LSR_SHA1_CALC(E, A, B, C, D, LSR_SHA1_EXTEND(31));
    LSR_SHA1_CALC(D, E, A, B, C, LSR_SHA1_EXTEND(32));
    LSR_SHA1_CALC(C, D, E, A, B, LSR_SHA1_EXTEND(33));
    LSR_SHA1_CALC(B, C, D, E, A, LSR_SHA1_EXTEND(34));
    LSR_SHA1_CALC(A, B, C, D, E, LSR_SHA1_EXTEND(35));
    LSR_SHA1_CALC(E, A, B, C, D, LSR_SHA1_EXTEND(36));
    LSR_SHA1_CALC(D, E, A, B, C, LSR_SHA1_EXTEND(37));
    LSR_SHA1_CALC(C, D, E, A, B, LSR_SHA1_EXTEND(38));
    LSR_SHA1_CALC(B, C, D, E, A, LSR_SHA1_EXTEND(39));

#undef LSR_SHA1_K
#undef LSR_SHA1_F

#define LSR_SHA1_F( x, y, z ) ((x & y) | (z & (x | y)))
#define LSR_SHA1_K 0x8F1BBCDC

    LSR_SHA1_CALC(A, B, C, D, E, LSR_SHA1_EXTEND(40));
    LSR_SHA1_CALC(E, A, B, C, D, LSR_SHA1_EXTEND(41));
    LSR_SHA1_CALC(D, E, A, B, C, LSR_SHA1_EXTEND(42));
    LSR_SHA1_CALC(C, D, E, A, B, LSR_SHA1_EXTEND(43));
    LSR_SHA1_CALC(B, C, D, E, A, LSR_SHA1_EXTEND(44));
    LSR_SHA1_CALC(A, B, C, D, E, LSR_SHA1_EXTEND(45));
    LSR_SHA1_CALC(E, A, B, C, D, LSR_SHA1_EXTEND(46));
    LSR_SHA1_CALC(D, E, A, B, C, LSR_SHA1_EXTEND(47));
    LSR_SHA1_CALC(C, D, E, A, B, LSR_SHA1_EXTEND(48));
    LSR_SHA1_CALC(B, C, D, E, A, LSR_SHA1_EXTEND(49));
    LSR_SHA1_CALC(A, B, C, D, E, LSR_SHA1_EXTEND(50));
    LSR_SHA1_CALC(E, A, B, C, D, LSR_SHA1_EXTEND(51));
    LSR_SHA1_CALC(D, E, A, B, C, LSR_SHA1_EXTEND(52));
    LSR_SHA1_CALC(C, D, E, A, B, LSR_SHA1_EXTEND(53));
    LSR_SHA1_CALC(B, C, D, E, A, LSR_SHA1_EXTEND(54));
    LSR_SHA1_CALC(A, B, C, D, E, LSR_SHA1_EXTEND(55));
    LSR_SHA1_CALC(E, A, B, C, D, LSR_SHA1_EXTEND(56));
    LSR_SHA1_CALC(D, E, A, B, C, LSR_SHA1_EXTEND(57));
    LSR_SHA1_CALC(C, D, E, A, B, LSR_SHA1_EXTEND(58));
    LSR_SHA1_CALC(B, C, D, E, A, LSR_SHA1_EXTEND(59));

#undef LSR_SHA1_K
#undef LSR_SHA1_F

#define LSR_SHA1_F( x, y, z ) (x ^ y ^ z)
#define LSR_SHA1_K 0xCA62C1D6

    LSR_SHA1_CALC(A, B, C, D, E, LSR_SHA1_EXTEND(60));
    LSR_SHA1_CALC(E, A, B, C, D, LSR_SHA1_EXTEND(61));
    LSR_SHA1_CALC(D, E, A, B, C, LSR_SHA1_EXTEND(62));
    LSR_SHA1_CALC(C, D, E, A, B, LSR_SHA1_EXTEND(63));
    LSR_SHA1_CALC(B, C, D, E, A, LSR_SHA1_EXTEND(64));
    LSR_SHA1_CALC(A, B, C, D, E, LSR_SHA1_EXTEND(65));
    LSR_SHA1_CALC(E, A, B, C, D, LSR_SHA1_EXTEND(66));
    LSR_SHA1_CALC(D, E, A, B, C, LSR_SHA1_EXTEND(67));
    LSR_SHA1_CALC(C, D, E, A, B, LSR_SHA1_EXTEND(68));
    LSR_SHA1_CALC(B, C, D, E, A, LSR_SHA1_EXTEND(69));
    LSR_SHA1_CALC(A, B, C, D, E, LSR_SHA1_EXTEND(70));
    LSR_SHA1_CALC(E, A, B, C, D, LSR_SHA1_EXTEND(71));
    LSR_SHA1_CALC(D, E, A, B, C, LSR_SHA1_EXTEND(72));
    LSR_SHA1_CALC(C, D, E, A, B, LSR_SHA1_EXTEND(73));
    LSR_SHA1_CALC(B, C, D, E, A, LSR_SHA1_EXTEND(74));
    LSR_SHA1_CALC(A, B, C, D, E, LSR_SHA1_EXTEND(75));
    LSR_SHA1_CALC(E, A, B, C, D, LSR_SHA1_EXTEND(76));
    LSR_SHA1_CALC(D, E, A, B, C, LSR_SHA1_EXTEND(77));
    LSR_SHA1_CALC(C, D, E, A, B, LSR_SHA1_EXTEND(78));
    LSR_SHA1_CALC(B, C, D, E, A, LSR_SHA1_EXTEND(79));

#undef LSR_SHA1_K
#undef LSR_SHA1_F

    ctx->m_digest_state[0] += A;
    ctx->m_digest_state[1] += B;
    ctx->m_digest_state[2] += C;
    ctx->m_digest_state[3] += D;
    ctx->m_digest_state[4] += E;
}


int ls_sha1_update(ls_sha1_ctx_t *ctx, const unsigned char *input,
                   size_t ilen)
{
    size_t fill;
    uint32_t left;

    if (ilen == 0)
        return 0;

    left = ctx->m_total[0] & 0x3F;
    fill = 64 - left;

    ctx->m_total[0] += (uint32_t) ilen;
    ctx->m_total[0] &= 0xFFFFFFFF;

    if (ctx->m_total[0] < (uint32_t) ilen)
        ctx->m_total[1]++;

    if ((left != 0) && (ilen >= fill))
    {
        memcpy((void *)(ctx->m_buf + left), input, fill);
        ls_sha1_process(ctx, ctx->m_buf);
        input += fill;
        ilen  -= fill;
        left = 0;
    }

    while (ilen >= 64)
    {
        ls_sha1_process(ctx, input);
        input += 64;
        ilen  -= 64;
    }

    if (ilen > 0)
        memcpy((void *)(ctx->m_buf + left), input, ilen);

    return 1;
}


static const unsigned char ls_sha1_padding[64] =
{
    0x80, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
};


int ls_sha1_finish(ls_sha1_ctx_t *ctx, unsigned char *output)
{
    uint32_t last, padn;
    uint32_t high, low;
    unsigned char msglen[8];

    high = (ctx->m_total[0] >> 29) | (ctx->m_total[1] <<  3);
    low  = (ctx->m_total[0] <<  3);

    LSR_SHA1_PUT_UINT32_BE(high, msglen, 0);
    LSR_SHA1_PUT_UINT32_BE(low,  msglen, 4);

    last = ctx->m_total[0] & 0x3F;
    padn = (last < 56) ? (56 - last) : (120 - last);

    ls_sha1_update(ctx, ls_sha1_padding, padn);
    ls_sha1_update(ctx, msglen, 8);

    LSR_SHA1_PUT_UINT32_BE(ctx->m_digest_state[0], output,  0);
    LSR_SHA1_PUT_UINT32_BE(ctx->m_digest_state[1], output,  4);
    LSR_SHA1_PUT_UINT32_BE(ctx->m_digest_state[2], output,  8);
    LSR_SHA1_PUT_UINT32_BE(ctx->m_digest_state[3], output, 12);
    LSR_SHA1_PUT_UINT32_BE(ctx->m_digest_state[4], output, 16);

    return 1;
}


unsigned char *ls_sha1(const unsigned char *input, size_t ilen,
                       unsigned char *output)
{
    ls_sha1_ctx_t ctx;

    if (ls_sha1_init(&ctx) == 0)
        return NULL;
    ls_sha1_update(&ctx, input, ilen);
    ls_sha1_finish(&ctx, output);
    ls_sha1_free(&ctx);
    return output;
}
#endif

