
/* ocsp.c */
/*
 * Written by Tom Titchener <Tom_Titchener@groove.net> for the OpenSSL
 * project.
 */

/**
 * With regards to LiteSpeed Technologies: As of March 15, 2017, BoringSSL
 * does not have a full implementation of OCSP Stapling. LiteSpeed products
 * need to have OCSP Stapling available, therefore this file was created.
 * LiteSpeed Technologies did not write any of the code used in this file;
 * only the bare minimum was ported over from OpenSSL for use with BoringSSL.
 * Minor tweaks may have been made to accomodate the changes to the data
 * structures in BoringSSL.
 *
 * Ported by Kevin Fwu (kfwu@litespeedtech.com)
 */

/*
 * History: This file was transfered to Richard Levitte from CertCo by Kathy
 * Weinhold in mid-spring 2000 to be included in OpenSSL or released as a
 * patch kit.
 */

/* ====================================================================
 * Copyright (c) 1998-2000 The OpenSSL Project.  All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 *
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 *
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in
 *    the documentation and/or other materials provided with the
 *    distribution.
 *
 * 3. All advertising materials mentioning features or use of this
 *    software must display the following acknowledgment:
 *    "This product includes software developed by the OpenSSL Project
 *    for use in the OpenSSL Toolkit. (http://www.openssl.org/)"
 *
 * 4. The names "OpenSSL Toolkit" and "OpenSSL Project" must not be used to
 *    endorse or promote products derived from this software without
 *    prior written permission. For written permission, please contact
 *    openssl-core@openssl.org.
 *
 * 5. Products derived from this software may not be called "OpenSSL"
 *    nor may "OpenSSL" appear in their names without prior written
 *    permission of the OpenSSL Project.
 *
 * 6. Redistributions of any form whatsoever must retain the following
 *    acknowledgment:
 *    "This product includes software developed by the OpenSSL Project
 *    for use in the OpenSSL Toolkit (http://www.openssl.org/)"
 *
 * THIS SOFTWARE IS PROVIDED BY THE OpenSSL PROJECT ``AS IS'' AND ANY
 * EXPRESSED OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
 * PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE OpenSSL PROJECT OR
 * ITS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
 * NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 * LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
 * HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
 * STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
 * OF THE POSSIBILITY OF SUCH DAMAGE.
 * ====================================================================
 *
 * This product includes cryptographic software written by Eric Young
 * (eay@cryptsoft.com).  This product includes software written by Tim
 * Hudson (tjh@cryptsoft.com).
 *
 */

#include <sslpp/ocsp/ocsp.h>
#include <openssl/asn1t.h>
#include <openssl/asn1.h>

#ifdef OPENSSL_IS_BORINGSSL

#include <string.h>

#ifdef  __cplusplus
extern "C" {
#endif

ASN1_SEQUENCE(OCSP_CERTID) = {
        ASN1_SIMPLE(OCSP_CERTID, hashAlgorithm, X509_ALGOR),
        ASN1_SIMPLE(OCSP_CERTID, issuerNameHash, ASN1_OCTET_STRING),
        ASN1_SIMPLE(OCSP_CERTID, issuerKeyHash, ASN1_OCTET_STRING),
        ASN1_SIMPLE(OCSP_CERTID, serialNumber, ASN1_INTEGER)
} ASN1_SEQUENCE_END(OCSP_CERTID)

IMPLEMENT_ASN1_FUNCTIONS(OCSP_CERTID)

ASN1_SEQUENCE(OCSP_ONEREQ) = {
        ASN1_SIMPLE(OCSP_ONEREQ, reqCert, OCSP_CERTID),
        ASN1_EXP_SEQUENCE_OF_OPT(OCSP_ONEREQ, singleRequestExtensions, X509_EXTENSION, 0)
} ASN1_SEQUENCE_END(OCSP_ONEREQ)

IMPLEMENT_ASN1_FUNCTIONS(OCSP_ONEREQ)

ASN1_SEQUENCE(OCSP_REQINFO) = {
        ASN1_EXP_OPT(OCSP_REQINFO, version, ASN1_INTEGER, 0),
        ASN1_EXP_OPT(OCSP_REQINFO, requestorName, GENERAL_NAME, 1),
        ASN1_SEQUENCE_OF(OCSP_REQINFO, requestList, OCSP_ONEREQ),
        ASN1_EXP_SEQUENCE_OF_OPT(OCSP_REQINFO, requestExtensions, X509_EXTENSION, 2)
} ASN1_SEQUENCE_END(OCSP_REQINFO)

IMPLEMENT_ASN1_FUNCTIONS(OCSP_REQINFO)

ASN1_SEQUENCE(OCSP_SIGNATURE) = {
        ASN1_SIMPLE(OCSP_SIGNATURE, signatureAlgorithm, X509_ALGOR),
        ASN1_SIMPLE(OCSP_SIGNATURE, signature, ASN1_BIT_STRING),
        ASN1_EXP_SEQUENCE_OF_OPT(OCSP_SIGNATURE, certs, X509, 0)
} ASN1_SEQUENCE_END(OCSP_SIGNATURE)

IMPLEMENT_ASN1_FUNCTIONS(OCSP_SIGNATURE)

ASN1_SEQUENCE(OCSP_REQUEST) = {
        ASN1_SIMPLE(OCSP_REQUEST, tbsRequest, OCSP_REQINFO),
        ASN1_EXP_OPT(OCSP_REQUEST, optionalSignature, OCSP_SIGNATURE, 0)
} ASN1_SEQUENCE_END(OCSP_REQUEST)

IMPLEMENT_ASN1_FUNCTIONS(OCSP_REQUEST)

ASN1_SEQUENCE(OCSP_RESPBYTES) = {
            ASN1_SIMPLE(OCSP_RESPBYTES, responseType, ASN1_OBJECT),
            ASN1_SIMPLE(OCSP_RESPBYTES, response, ASN1_OCTET_STRING)
} ASN1_SEQUENCE_END(OCSP_RESPBYTES)

IMPLEMENT_ASN1_FUNCTIONS(OCSP_RESPBYTES)

ASN1_SEQUENCE(OCSP_RESPONSE) = {
        ASN1_SIMPLE(OCSP_RESPONSE, responseStatus, ASN1_ENUMERATED),
        ASN1_EXP_OPT(OCSP_RESPONSE, responseBytes, OCSP_RESPBYTES, 0)
} ASN1_SEQUENCE_END(OCSP_RESPONSE)

IMPLEMENT_ASN1_FUNCTIONS(OCSP_RESPONSE)

ASN1_CHOICE(OCSP_RESPID) = {
           ASN1_EXP(OCSP_RESPID, value.byName, X509_NAME, 1),
           ASN1_EXP(OCSP_RESPID, value.byKey, ASN1_OCTET_STRING, 2)
} ASN1_CHOICE_END(OCSP_RESPID)

IMPLEMENT_ASN1_FUNCTIONS(OCSP_RESPID)

ASN1_SEQUENCE(OCSP_REVOKEDINFO) = {
        ASN1_SIMPLE(OCSP_REVOKEDINFO, revocationTime, ASN1_GENERALIZEDTIME),
        ASN1_EXP_OPT(OCSP_REVOKEDINFO, revocationReason, ASN1_ENUMERATED, 0)
} ASN1_SEQUENCE_END(OCSP_REVOKEDINFO)

IMPLEMENT_ASN1_FUNCTIONS(OCSP_REVOKEDINFO)

ASN1_CHOICE(OCSP_CERTSTATUS) = {
        ASN1_IMP(OCSP_CERTSTATUS, value.good, ASN1_NULL, 0),
        ASN1_IMP(OCSP_CERTSTATUS, value.revoked, OCSP_REVOKEDINFO, 1),
        ASN1_IMP(OCSP_CERTSTATUS, value.unknown, ASN1_NULL, 2)
} ASN1_CHOICE_END(OCSP_CERTSTATUS)

IMPLEMENT_ASN1_FUNCTIONS(OCSP_CERTSTATUS)

ASN1_SEQUENCE(OCSP_SINGLERESP) = {
           ASN1_SIMPLE(OCSP_SINGLERESP, certId, OCSP_CERTID),
           ASN1_SIMPLE(OCSP_SINGLERESP, certStatus, OCSP_CERTSTATUS),
           ASN1_SIMPLE(OCSP_SINGLERESP, thisUpdate, ASN1_GENERALIZEDTIME),
           ASN1_EXP_OPT(OCSP_SINGLERESP, nextUpdate, ASN1_GENERALIZEDTIME, 0),
           ASN1_EXP_SEQUENCE_OF_OPT(OCSP_SINGLERESP, singleExtensions, X509_EXTENSION, 1)
} ASN1_SEQUENCE_END(OCSP_SINGLERESP)

IMPLEMENT_ASN1_FUNCTIONS(OCSP_SINGLERESP)

ASN1_SEQUENCE(OCSP_RESPDATA) = {
           ASN1_EXP_OPT(OCSP_RESPDATA, version, ASN1_INTEGER, 0),
           ASN1_SIMPLE(OCSP_RESPDATA, responderId, OCSP_RESPID),
           ASN1_SIMPLE(OCSP_RESPDATA, producedAt, ASN1_GENERALIZEDTIME),
           ASN1_SEQUENCE_OF(OCSP_RESPDATA, responses, OCSP_SINGLERESP),
           ASN1_EXP_SEQUENCE_OF_OPT(OCSP_RESPDATA, responseExtensions, X509_EXTENSION, 1)
} ASN1_SEQUENCE_END(OCSP_RESPDATA)

IMPLEMENT_ASN1_FUNCTIONS(OCSP_RESPDATA)

ASN1_SEQUENCE(OCSP_BASICRESP) = {
           ASN1_SIMPLE(OCSP_BASICRESP, tbsResponseData, OCSP_RESPDATA),
           ASN1_SIMPLE(OCSP_BASICRESP, signatureAlgorithm, X509_ALGOR),
           ASN1_SIMPLE(OCSP_BASICRESP, signature, ASN1_BIT_STRING),
           ASN1_EXP_SEQUENCE_OF_OPT(OCSP_BASICRESP, certs, X509, 0)
} ASN1_SEQUENCE_END(OCSP_BASICRESP)

IMPLEMENT_ASN1_FUNCTIONS(OCSP_BASICRESP)


#define sk_OCSP_ONEREQ_push(sk, p)                             \
  sk_push(CHECKED_CAST(_STACK *, STACK_OF(OCSP_ONEREQ) *, sk), \
          CHECKED_CAST(void *, const OCSP_ONEREQ *, p))

#define sk_OCSP_SINGLERESP_num(sk) \
  sk_num(CHECKED_CAST(const _STACK *, const STACK_OF(OCSP_SINGLERESP) *, sk))

#define sk_OCSP_SINGLERESP_value(sk, i) \
  ((const OCSP_SINGLERESP *)sk_value(   \
      CHECKED_CAST(const _STACK *, const STACK_OF(OCSP_SINGLERESP) *, sk), (i)))

/* Get response status */

int OCSP_response_status(OCSP_RESPONSE *resp)
{
    return ASN1_ENUMERATED_get(resp->responseStatus);
}

/*
 * Extract basic response from OCSP_RESPONSE or NULL if no basic response
 * present.
 */

OCSP_BASICRESP *OCSP_response_get1_basic(OCSP_RESPONSE *resp)
{
    OCSP_RESPBYTES *rb;
    rb = resp->responseBytes;
    if (!rb) {
        OPENSSL_PUT_ERROR(OCSP, OCSP_R_NO_RESPONSE_DATA);
        return NULL;
    }
    if (OBJ_obj2nid(rb->responseType) != NID_id_pkix_OCSP_basic) {
        OPENSSL_PUT_ERROR(OCSP, OCSP_R_NOT_BASIC_RESPONSE);
        return NULL;
    }

    return (OCSP_BASICRESP *)ASN1_item_unpack(rb->response, ASN1_ITEM_rptr(OCSP_BASICRESP));
}

OCSP_CERTID *OCSP_cert_to_id(const EVP_MD *dgst, X509 *subject, X509 *issuer)
{
    X509_NAME *iname;
    ASN1_INTEGER *serial;
    ASN1_BIT_STRING *ikey;
#ifndef OPENSSL_NO_SHA1
    if (!dgst)
        dgst = EVP_sha1();
#endif
    if (subject) {
        iname = X509_get_issuer_name(subject);
        serial = X509_get_serialNumber(subject);
    } else {
        iname = X509_get_subject_name(issuer);
        serial = NULL;
    }
    ikey = X509_get0_pubkey_bitstr(issuer);
    return OCSP_cert_id_new(dgst, iname, ikey, serial);
}

OCSP_CERTID *OCSP_cert_id_new(const EVP_MD *dgst,
                              X509_NAME *issuerName,
                              ASN1_BIT_STRING *issuerKey,
                              ASN1_INTEGER *serialNumber)
{
    int nid;
    unsigned int i;
    X509_ALGOR *alg;
    OCSP_CERTID *cid = NULL;
    unsigned char md[EVP_MAX_MD_SIZE];

    if (!(cid = OCSP_CERTID_new()))
        goto err;

    alg = cid->hashAlgorithm;
    if (alg->algorithm != NULL)
        ASN1_OBJECT_free(alg->algorithm);
    if ((nid = EVP_MD_type(dgst)) == NID_undef) {
        OPENSSL_PUT_ERROR(OCSP, OCSP_R_UNKNOWN_NID);
        goto err;
    }
    if (!(alg->algorithm = (ASN1_OBJECT *)OBJ_nid2obj(nid)))
        goto err;
    if ((alg->parameter = ASN1_TYPE_new()) == NULL)
        goto err;
    alg->parameter->type = V_ASN1_NULL;

    if (!X509_NAME_digest(issuerName, dgst, md, &i))
        goto digerr;
    if (!(ASN1_OCTET_STRING_set(cid->issuerNameHash, md, i)))
        goto err;

    /* Calculate the issuerKey hash, excluding tag and length */
    if (!EVP_Digest(issuerKey->data, issuerKey->length, md, &i, dgst, NULL))
        goto err;

    if (!(ASN1_OCTET_STRING_set(cid->issuerKeyHash, md, i)))
        goto err;

    if (serialNumber) {
        ASN1_INTEGER_free(cid->serialNumber);
        if (!(cid->serialNumber = ASN1_INTEGER_dup(serialNumber)))
            goto err;
    }
    return cid;
 digerr:
    OPENSSL_PUT_ERROR(OCSP, OCSP_R_DIGEST_ERR);
 err:
    if (cid)
        OCSP_CERTID_free(cid);
    return NULL;
}


/**
 * In OpenSSL, this was constructed in a define (IMPLEMENT_ASN1_DUP_FUNCTIONS).
 * However, this will cause issues because ASN1_item_dup returns a void *.
 * Instead, just implement the function here.
 */
OCSP_CERTID *OCSP_CERTID_dup(OCSP_CERTID *x)
{
    return (OCSP_CERTID *)ASN1_item_dup(ASN1_ITEM_rptr(OCSP_CERTID), x);
}

/*
 * Utility functions related to sending OCSP requests and extracting relevant
 * information from the response.
 */

/*
 * Add an OCSP_CERTID to an OCSP request. Return new OCSP_ONEREQ pointer:
 * useful if we want to add extensions.
 */

OCSP_ONEREQ *OCSP_request_add0_id(OCSP_REQUEST *req, OCSP_CERTID *cid)
{
    OCSP_ONEREQ *one = NULL;

    if (!(one = OCSP_ONEREQ_new()))
        goto err;
    if (one->reqCert)
        OCSP_CERTID_free(one->reqCert);
    one->reqCert = cid;
    if (req && !sk_OCSP_ONEREQ_push(req->tbsRequest->requestList, one)) {
        one->reqCert = NULL; /* do not free on error */
        goto err;
    }
    return one;
 err:
    OCSP_ONEREQ_free(one);
    return NULL;
}

static int ocsp_find_signer(X509 **psigner, OCSP_BASICRESP *bs,
                            STACK_OF(X509) *certs, X509_STORE *st,
                            unsigned long flags);
static X509 *ocsp_find_signer_sk(STACK_OF(X509) *certs, OCSP_RESPID *id);
static int ocsp_check_issuer(OCSP_BASICRESP *bs, STACK_OF(X509) *chain,
                             unsigned long flags);
static int ocsp_check_ids(STACK_OF(OCSP_SINGLERESP) *sresp,
                          OCSP_CERTID **ret);
static int ocsp_match_issuerid(X509 *cert, OCSP_CERTID *cid,
                               STACK_OF(OCSP_SINGLERESP) *sresp);
static int ocsp_check_delegated(X509 *x, int flags);

/* Verify a basic response message */

int OCSP_basic_verify(OCSP_BASICRESP *bs, STACK_OF(X509) *certs,
                      X509_STORE *st, unsigned long flags)
{
    X509 *signer, *x;
    STACK_OF(X509) *chain = NULL;
    STACK_OF(X509) *untrusted = NULL;
    X509_STORE_CTX ctx;
    size_t i;
    int ret = 0;
    ret = ocsp_find_signer(&signer, bs, certs, st, flags);
    if (!ret) {
        OPENSSL_PUT_ERROR(OCSP, OCSP_R_SIGNER_CERTIFICATE_NOT_FOUND);
        goto end;
    }
    if ((ret == 2) && (flags & OCSP_TRUSTOTHER))
        flags |= OCSP_NOVERIFY;
    if (!(flags & OCSP_NOSIGS)) {
        EVP_PKEY *skey;
        skey = X509_get_pubkey(signer);
        if (skey) {
            ret = OCSP_BASICRESP_verify(bs, skey, 0);
            EVP_PKEY_free(skey);
        }
        if (!skey || ret <= 0) {
            OPENSSL_PUT_ERROR(OCSP, OCSP_R_SIGNATURE_FAILURE);
            goto end;
        }
    }
    if (!(flags & OCSP_NOVERIFY)) {
        int init_res;
        if (flags & OCSP_NOCHAIN) {
            untrusted = NULL;
        } else if (bs->certs && certs) {
            untrusted = sk_X509_dup(bs->certs);
            for (i = 0; i < sk_X509_num(certs); i++) {
                if (!sk_X509_push(untrusted, sk_X509_value(certs, i))) {
                    OPENSSL_PUT_ERROR(OCSP, ERR_R_MALLOC_FAILURE);
                    goto end;
                }
            }
        } else {
            untrusted = bs->certs;
        }
        init_res = X509_STORE_CTX_init(&ctx, st, signer, untrusted);
        if (!init_res) {
            ret = -1;
            OPENSSL_PUT_ERROR(OCSP, ERR_R_X509_LIB);
            goto end;
        }

        X509_STORE_CTX_set_purpose(&ctx, X509_PURPOSE_OCSP_HELPER);
        ret = X509_verify_cert(&ctx);
        chain = X509_STORE_CTX_get1_chain(&ctx);
        X509_STORE_CTX_cleanup(&ctx);
        if (ret <= 0) {
            i = X509_STORE_CTX_get_error(&ctx);
            OPENSSL_PUT_ERROR(OCSP, OCSP_R_CERTIFICATE_VERIFY_ERROR);
            ERR_add_error_data(2, "Verify error:",
                               X509_verify_cert_error_string(i));
            goto end;
        }
        if (flags & OCSP_NOCHECKS) {
            ret = 1;
            goto end;
        }
        /*
         * At this point we have a valid certificate chain need to verify it
         * against the OCSP issuer criteria.
         */
        ret = ocsp_check_issuer(bs, chain, flags);

        /* If fatal error or valid match then finish */
        if (ret != 0)
            goto end;

        /*
         * Easy case: explicitly trusted. Get root CA and check for explicit
         * trust
         */
        if (flags & OCSP_NOEXPLICIT)
            goto end;

        x = sk_X509_value(chain, sk_X509_num(chain) - 1);
        if (X509_check_trust(x, NID_OCSP_sign, 0) != X509_TRUST_TRUSTED) {
            OPENSSL_PUT_ERROR(OCSP, OCSP_R_ROOT_CA_NOT_TRUSTED);
            goto end;
        }
        ret = 1;
    }

 end:
    if (chain)
        sk_X509_pop_free(chain, X509_free);
    if (bs->certs && certs)
        sk_X509_free(untrusted);
    return ret;
}

static int ocsp_find_signer(X509 **psigner, OCSP_BASICRESP *bs,
                            STACK_OF(X509) *certs, X509_STORE *st,
                            unsigned long flags)
{
    X509 *signer;
    OCSP_RESPID *rid = bs->tbsResponseData->responderId;
    if ((signer = ocsp_find_signer_sk(certs, rid))) {
        *psigner = signer;
        return 2;
    }
    if (!(flags & OCSP_NOINTERN) &&
        (signer = ocsp_find_signer_sk(bs->certs, rid))) {
        *psigner = signer;
        return 1;
    }
    /* Maybe lookup from store if by subject name */

    *psigner = NULL;
    return 0;
}

static X509 *ocsp_find_signer_sk(STACK_OF(X509) *certs, OCSP_RESPID *id)
{
    size_t i;
    unsigned char tmphash[SHA_DIGEST_LENGTH], *keyhash;
    X509 *x;

    /* Easy if lookup by name */
    if (id->type == V_OCSP_RESPID_NAME)
        return X509_find_by_subject(certs, id->value.byName);

    /* Lookup by key hash */

    /* If key hash isn't SHA1 length then forget it */
    if (id->value.byKey->length != SHA_DIGEST_LENGTH)
        return NULL;
    keyhash = id->value.byKey->data;
    /* Calculate hash of each key and compare */
    for (i = 0; i < sk_X509_num(certs); i++) {
        x = sk_X509_value(certs, i);
        X509_pubkey_digest(x, EVP_sha1(), tmphash, NULL);
        if (!memcmp(keyhash, tmphash, SHA_DIGEST_LENGTH))
            return x;
    }
    return NULL;
}

static int ocsp_check_issuer(OCSP_BASICRESP *bs, STACK_OF(X509) *chain,
                             unsigned long flags)
{
    STACK_OF(OCSP_SINGLERESP) *sresp;
    X509 *signer, *sca;
    OCSP_CERTID *caid = NULL;
    int i;
    sresp = bs->tbsResponseData->responses;

    if (sk_X509_num(chain) <= 0) {
        OPENSSL_PUT_ERROR(OCSP, OCSP_R_NO_CERTIFICATES_IN_CHAIN);
        return -1;
    }

    /* See if the issuer IDs match. */
    i = ocsp_check_ids(sresp, &caid);

    /* If ID mismatch or other error then return */
    if (i <= 0)
        return i;

    signer = sk_X509_value(chain, 0);
    /* Check to see if OCSP responder CA matches request CA */
    if (sk_X509_num(chain) > 1) {
        sca = sk_X509_value(chain, 1);
        i = ocsp_match_issuerid(sca, caid, sresp);
        if (i < 0)
            return i;
        if (i) {
            /* We have a match, if extensions OK then success */
            if (ocsp_check_delegated(signer, flags))
                return 1;
            return 0;
        }
    }

    /* Otherwise check if OCSP request signed directly by request CA */
    return ocsp_match_issuerid(signer, caid, sresp);
}

/*
 * Check the issuer certificate IDs for equality. If there is a mismatch with
 * the same algorithm then there's no point trying to match any certificates
 * against the issuer. If the issuer IDs all match then we just need to check
 * equality against one of them.
 */

static int ocsp_check_ids(STACK_OF(OCSP_SINGLERESP) *sresp, OCSP_CERTID **ret)
{
    OCSP_CERTID *tmpid, *cid;
    int i, idcount;

    idcount = sk_OCSP_SINGLERESP_num(sresp);
    if (idcount <= 0) {
        OPENSSL_PUT_ERROR(OCSP, OCSP_R_RESPONSE_CONTAINS_NO_REVOCATION_DATA);
        return -1;
    }

    cid = sk_OCSP_SINGLERESP_value(sresp, 0)->certId;

    *ret = NULL;

    for (i = 1; i < idcount; i++) {
        tmpid = sk_OCSP_SINGLERESP_value(sresp, i)->certId;
        /* Check to see if IDs match */
        if (OCSP_id_issuer_cmp(cid, tmpid)) {
            /* If algoritm mismatch let caller deal with it */
            if (OBJ_cmp(tmpid->hashAlgorithm->algorithm,
                        cid->hashAlgorithm->algorithm))
                return 2;
            /* Else mismatch */
            return 0;
        }
    }

    /* All IDs match: only need to check one ID */
    *ret = cid;
    return 1;
}

static int ocsp_match_issuerid(X509 *cert, OCSP_CERTID *cid,
                               STACK_OF(OCSP_SINGLERESP) *sresp)
{
    /* If only one ID to match then do it */
    if (cid) {
        const EVP_MD *dgst;
        X509_NAME *iname;
        int mdlen;
        unsigned char md[EVP_MAX_MD_SIZE];
        if (!(dgst = EVP_get_digestbyobj(cid->hashAlgorithm->algorithm))) {
            OPENSSL_PUT_ERROR(OCSP, OCSP_R_UNKNOWN_MESSAGE_DIGEST);
            return -1;
        }

        mdlen = EVP_MD_size(dgst);
        if (mdlen < 0)
            return -1;
        if ((cid->issuerNameHash->length != mdlen) ||
            (cid->issuerKeyHash->length != mdlen))
            return 0;
        iname = X509_get_subject_name(cert);
        if (!X509_NAME_digest(iname, dgst, md, NULL))
            return -1;
        if (memcmp(md, cid->issuerNameHash->data, mdlen))
            return 0;
        X509_pubkey_digest(cert, dgst, md, NULL);
        if (memcmp(md, cid->issuerKeyHash->data, mdlen))
            return 0;

        return 1;

    } else {
        /* We have to match the whole lot */
        size_t i;
        int ret;
        OCSP_CERTID *tmpid;
        for (i = 0; i < sk_OCSP_SINGLERESP_num(sresp); i++) {
            tmpid = sk_OCSP_SINGLERESP_value(sresp, i)->certId;
            ret = ocsp_match_issuerid(cert, tmpid, NULL);
            if (ret <= 0)
                return ret;
        }
        return 1;
    }
}

static int ocsp_check_delegated(X509 *x, int flags)
{
    X509_check_purpose(x, -1, 0);
    if ((x->ex_flags & EXFLAG_XKUSAGE) && (x->ex_xkusage & XKU_OCSP_SIGN))
        return 1;
    OPENSSL_PUT_ERROR(OCSP, OCSP_R_MISSING_OCSPSIGNING_USAGE);
    return 0;
}

/* Extract an OCSP_SINGLERESP response with a given index */

OCSP_SINGLERESP *OCSP_resp_get0(OCSP_BASICRESP *bs, int idx)
{
    if (!bs)
        return NULL;
    return (OCSP_SINGLERESP *)sk_OCSP_SINGLERESP_value(
        bs->tbsResponseData->responses, idx);
}

/*
 * Extract status information from an OCSP_SINGLERESP structure. Note: the
 * revtime and reason values are only set if the certificate status is
 * revoked. Returns numerical value of status.
 */

int OCSP_single_get0_status(OCSP_SINGLERESP *single, int *reason,
                            ASN1_GENERALIZEDTIME **revtime,
                            ASN1_GENERALIZEDTIME **thisupd,
                            ASN1_GENERALIZEDTIME **nextupd)
{
    int ret;
    OCSP_CERTSTATUS *cst;
    if (!single)
        return -1;
    cst = single->certStatus;
    ret = cst->type;
    if (ret == V_OCSP_CERTSTATUS_REVOKED) {
        OCSP_REVOKEDINFO *rev = cst->value.revoked;
        if (revtime)
            *revtime = rev->revocationTime;
        if (reason) {
            if (rev->revocationReason)
                *reason = ASN1_ENUMERATED_get(rev->revocationReason);
            else
                *reason = -1;
        }
    }
    if (thisupd)
        *thisupd = single->thisUpdate;
    if (nextupd)
        *nextupd = single->nextUpdate;
    return ret;
}

int OCSP_id_issuer_cmp(OCSP_CERTID *a, OCSP_CERTID *b)
{
    int ret;
    ret = OBJ_cmp(a->hashAlgorithm->algorithm, b->hashAlgorithm->algorithm);
    if (ret)
        return ret;
    ret = ASN1_OCTET_STRING_cmp(a->issuerNameHash, b->issuerNameHash);
    if (ret)
        return ret;
    return ASN1_OCTET_STRING_cmp(a->issuerKeyHash, b->issuerKeyHash);
}

int OCSP_id_cmp(OCSP_CERTID *a, OCSP_CERTID *b)
{
    int ret;
    ret = OCSP_id_issuer_cmp(a, b);
    if (ret)
        return ret;
    return ASN1_INTEGER_cmp(a->serialNumber, b->serialNumber);
}

/* Look single response matching a given certificate ID */

int OCSP_resp_find(OCSP_BASICRESP *bs, OCSP_CERTID *id, int last)
{
    size_t i;
    STACK_OF(OCSP_SINGLERESP) *sresp;
    OCSP_SINGLERESP *single;
    if (!bs)
        return -1;
    if (last < 0)
        last = 0;
    else
        last++;
    sresp = bs->tbsResponseData->responses;
    for (i = last; i < sk_OCSP_SINGLERESP_num(sresp); i++) {
        single = (OCSP_SINGLERESP *)sk_OCSP_SINGLERESP_value(sresp, i);
        if (!OCSP_id_cmp(id, single->certId))
            return (int)i;
    }
    return -1;
}


/*
 * This function combines the previous ones: look up a certificate ID and if
 * found extract status information. Return 0 is successful.
 */

int OCSP_resp_find_status(OCSP_BASICRESP *bs, OCSP_CERTID *id, int *status,
                          int *reason,
                          ASN1_GENERALIZEDTIME **revtime,
                          ASN1_GENERALIZEDTIME **thisupd,
                          ASN1_GENERALIZEDTIME **nextupd)
{
    int i;
    OCSP_SINGLERESP *single;
    i = OCSP_resp_find(bs, id, -1);
    /* Maybe check for multiple responses and give an error? */
    if (i < 0)
        return 0;
    single = OCSP_resp_get0(bs, i);
    i = OCSP_single_get0_status(single, reason, revtime, thisupd, nextupd);
    if (status)
        *status = i;
    return 1;
}

/*
 * Check validity of thisUpdate and nextUpdate fields. It is possible that
 * the request will take a few seconds to process and/or the time wont be
 * totally accurate. Therefore to avoid rejecting otherwise valid time we
 * allow the times to be within 'nsec' of the current time. Also to avoid
 * accepting very old responses without a nextUpdate field an optional maxage
 * parameter specifies the maximum age the thisUpdate field can be.
 */

int OCSP_check_validity(ASN1_GENERALIZEDTIME *thisupd,
                        ASN1_GENERALIZEDTIME *nextupd, long nsec, long maxsec)
{
    int ret = 1;
    time_t t_now, t_tmp;
    time(&t_now);
    /* Check thisUpdate is valid and not more than nsec in the future */
    if (!ASN1_GENERALIZEDTIME_check(thisupd)) {
        OPENSSL_PUT_ERROR(OCSP, OCSP_R_ERROR_IN_THISUPDATE_FIELD);
        ret = 0;
    } else {
        t_tmp = t_now + nsec;
        if (X509_cmp_time(thisupd, &t_tmp) > 0) {
            OPENSSL_PUT_ERROR(OCSP, OCSP_R_STATUS_NOT_YET_VALID);
            ret = 0;
        }

        /*
         * If maxsec specified check thisUpdate is not more than maxsec in
         * the past
         */
        if (maxsec >= 0) {
            t_tmp = t_now - maxsec;
            if (X509_cmp_time(thisupd, &t_tmp) < 0) {
                OPENSSL_PUT_ERROR(OCSP, OCSP_R_STATUS_TOO_OLD);
                ret = 0;
            }
        }
    }

    if (!nextupd)
        return ret;

    /* Check nextUpdate is valid and not more than nsec in the past */
    if (!ASN1_GENERALIZEDTIME_check(nextupd)) {
        OPENSSL_PUT_ERROR(OCSP, OCSP_R_ERROR_IN_NEXTUPDATE_FIELD);
        ret = 0;
    } else {
        t_tmp = t_now - nsec;
        if (X509_cmp_time(nextupd, &t_tmp) < 0) {
            OPENSSL_PUT_ERROR(OCSP, OCSP_R_STATUS_EXPIRED);
            ret = 0;
        }
    }

    /* Also don't allow nextUpdate to precede thisUpdate */
    if (ASN1_STRING_cmp(nextupd, thisupd) < 0) {
        OPENSSL_PUT_ERROR(OCSP, OCSP_R_NEXTUPDATE_BEFORE_THISUPDATE);
        ret = 0;
    }

    return ret;
}

#ifdef  __cplusplus
}
#endif // OPENSSL_IS_BORINGSSL

#endif

