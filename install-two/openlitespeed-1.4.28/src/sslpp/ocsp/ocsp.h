
/* ocsp.h */
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


#ifndef HEADER_OCSP_H
# define HEADER_OCSP_H

# include <openssl/ossl_typ.h>
# include <openssl/x509.h>
# include <openssl/x509v3.h>
# include <openssl/safestack.h>

#ifdef OPENSSL_IS_BORINGSSL

#ifdef  __cplusplus
extern "C" {
#endif

/* Various flags and values */

# define OCSP_DEFAULT_NONCE_LENGTH       16

# define OCSP_NOCERTS                    0x1
# define OCSP_NOINTERN                   0x2
# define OCSP_NOSIGS                     0x4
# define OCSP_NOCHAIN                    0x8
# define OCSP_NOVERIFY                   0x10
# define OCSP_NOEXPLICIT                 0x20
# define OCSP_NOCASIGN                   0x40
# define OCSP_NODELEGATED                0x80
# define OCSP_NOCHECKS                   0x100
# define OCSP_TRUSTOTHER                 0x200
# define OCSP_RESPID_KEY                 0x400
# define OCSP_NOTIME                     0x800

/*-  CertID ::= SEQUENCE {
 *       hashAlgorithm            AlgorithmIdentifier,
 *       issuerNameHash     OCTET STRING, -- Hash of Issuer's DN
 *       issuerKeyHash      OCTET STRING, -- Hash of Issuers public key (excluding the tag & length fields)
 *       serialNumber       CertificateSerialNumber }
 */
typedef struct ocsp_cert_id_st {
    X509_ALGOR *hashAlgorithm;
    ASN1_OCTET_STRING *issuerNameHash;
    ASN1_OCTET_STRING *issuerKeyHash;
    ASN1_INTEGER *serialNumber;
} OCSP_CERTID;

DECLARE_STACK_OF(OCSP_CERTID)

/*-  Request ::=     SEQUENCE {
 *       reqCert                    CertID,
 *       singleRequestExtensions    [0] EXPLICIT Extensions OPTIONAL }
 */
typedef struct ocsp_one_request_st {
    OCSP_CERTID *reqCert;
    STACK_OF(X509_EXTENSION) *singleRequestExtensions;
} OCSP_ONEREQ;

DECLARE_STACK_OF(OCSP_ONEREQ)
DECLARE_ASN1_SET_OF(OCSP_ONEREQ)

/*-  TBSRequest      ::=     SEQUENCE {
 *       version             [0] EXPLICIT Version DEFAULT v1,
 *       requestorName       [1] EXPLICIT GeneralName OPTIONAL,
 *       requestList             SEQUENCE OF Request,
 *       requestExtensions   [2] EXPLICIT Extensions OPTIONAL }
 */
typedef struct ocsp_req_info_st {
    ASN1_INTEGER *version;
    GENERAL_NAME *requestorName;
    STACK_OF(OCSP_ONEREQ) *requestList;
    STACK_OF(X509_EXTENSION) *requestExtensions;
} OCSP_REQINFO;

/*-  Signature       ::=     SEQUENCE {
 *       signatureAlgorithm   AlgorithmIdentifier,
 *       signature            BIT STRING,
 *       certs                [0] EXPLICIT SEQUENCE OF Certificate OPTIONAL }
 */
typedef struct ocsp_signature_st {
    X509_ALGOR *signatureAlgorithm;
    ASN1_BIT_STRING *signature;
    STACK_OF(X509) *certs;
} OCSP_SIGNATURE;

/*-  OCSPRequest     ::=     SEQUENCE {
 *       tbsRequest                  TBSRequest,
 *       optionalSignature   [0]     EXPLICIT Signature OPTIONAL }
 */
typedef struct ocsp_request_st {
    OCSP_REQINFO *tbsRequest;
    OCSP_SIGNATURE *optionalSignature; /* OPTIONAL */
} OCSP_REQUEST;

/*-  OCSPResponseStatus ::= ENUMERATED {
 *       successful            (0),      --Response has valid confirmations
 *       malformedRequest      (1),      --Illegal confirmation request
 *       internalError         (2),      --Internal error in issuer
 *       tryLater              (3),      --Try again later
 *                                       --(4) is not used
 *       sigRequired           (5),      --Must sign the request
 *       unauthorized          (6)       --Request unauthorized
 *   }
 */
# define OCSP_RESPONSE_STATUS_SUCCESSFUL          0
# define OCSP_RESPONSE_STATUS_MALFORMEDREQUEST     1
# define OCSP_RESPONSE_STATUS_INTERNALERROR        2
# define OCSP_RESPONSE_STATUS_TRYLATER             3
# define OCSP_RESPONSE_STATUS_SIGREQUIRED          5
# define OCSP_RESPONSE_STATUS_UNAUTHORIZED         6

/*-  ResponseBytes ::=       SEQUENCE {
 *       responseType   OBJECT IDENTIFIER,
 *       response       OCTET STRING }
 */
typedef struct ocsp_resp_bytes_st {
    ASN1_OBJECT *responseType;
    ASN1_OCTET_STRING *response;
} OCSP_RESPBYTES;

/*-  OCSPResponse ::= SEQUENCE {
 *      responseStatus         OCSPResponseStatus,
 *      responseBytes          [0] EXPLICIT ResponseBytes OPTIONAL }
 */
typedef struct ocsp_response_st {
    ASN1_ENUMERATED *responseStatus;
    OCSP_RESPBYTES *responseBytes;
} OCSP_RESPONSE;
DECLARE_ASN1_FUNCTIONS(OCSP_RESPONSE)

/*-  ResponderID ::= CHOICE {
 *      byName   [1] Name,
 *      byKey    [2] KeyHash }
 */
# define V_OCSP_RESPID_NAME 0
# define V_OCSP_RESPID_KEY  1
typedef struct ocsp_responder_id_st {
    int type;
    union {
        X509_NAME *byName;
        ASN1_OCTET_STRING *byKey;
    } value;
} OCSP_RESPID;

DECLARE_STACK_OF(OCSP_RESPID)
DECLARE_ASN1_FUNCTIONS(OCSP_RESPID)

/*-  KeyHash ::= OCTET STRING --SHA-1 hash of responder's public key
 *                            --(excluding the tag and length fields)
 */

/*-  RevokedInfo ::= SEQUENCE {
 *       revocationTime              GeneralizedTime,
 *       revocationReason    [0]     EXPLICIT CRLReason OPTIONAL }
 */
typedef struct ocsp_revoked_info_st {
    ASN1_GENERALIZEDTIME *revocationTime;
    ASN1_ENUMERATED *revocationReason;
} OCSP_REVOKEDINFO;

/*-  CertStatus ::= CHOICE {
 *       good                [0]     IMPLICIT NULL,
 *       revoked             [1]     IMPLICIT RevokedInfo,
 *       unknown             [2]     IMPLICIT UnknownInfo }
 */
# define V_OCSP_CERTSTATUS_GOOD    0
# define V_OCSP_CERTSTATUS_REVOKED 1
# define V_OCSP_CERTSTATUS_UNKNOWN 2
typedef struct ocsp_cert_status_st {
    int type;
    union {
        ASN1_NULL *good;
        OCSP_REVOKEDINFO *revoked;
        ASN1_NULL *unknown;
    } value;
} OCSP_CERTSTATUS;

/*-  SingleResponse ::= SEQUENCE {
 *      certID                       CertID,
 *      certStatus                   CertStatus,
 *      thisUpdate                   GeneralizedTime,
 *      nextUpdate           [0]     EXPLICIT GeneralizedTime OPTIONAL,
 *      singleExtensions     [1]     EXPLICIT Extensions OPTIONAL }
 */
typedef struct ocsp_single_response_st {
    OCSP_CERTID *certId;
    OCSP_CERTSTATUS *certStatus;
    ASN1_GENERALIZEDTIME *thisUpdate;
    ASN1_GENERALIZEDTIME *nextUpdate;
    STACK_OF(X509_EXTENSION) *singleExtensions;
} OCSP_SINGLERESP;

DECLARE_STACK_OF(OCSP_SINGLERESP)
DECLARE_ASN1_SET_OF(OCSP_SINGLERESP)

/*-  ResponseData ::= SEQUENCE {
 *      version              [0] EXPLICIT Version DEFAULT v1,
 *      responderID              ResponderID,
 *      producedAt               GeneralizedTime,
 *      responses                SEQUENCE OF SingleResponse,
 *      responseExtensions   [1] EXPLICIT Extensions OPTIONAL }
 */
typedef struct ocsp_response_data_st {
    ASN1_INTEGER *version;
    OCSP_RESPID *responderId;
    ASN1_GENERALIZEDTIME *producedAt;
    STACK_OF(OCSP_SINGLERESP) *responses;
    STACK_OF(X509_EXTENSION) *responseExtensions;
} OCSP_RESPDATA;

/*-  BasicOCSPResponse       ::= SEQUENCE {
 *      tbsResponseData      ResponseData,
 *      signatureAlgorithm   AlgorithmIdentifier,
 *      signature            BIT STRING,
 *      certs                [0] EXPLICIT SEQUENCE OF Certificate OPTIONAL }
 */
  /*
   * Note 1: The value for "signature" is specified in the OCSP rfc2560 as
   * follows: "The value for the signature SHALL be computed on the hash of
   * the DER encoding ResponseData." This means that you must hash the
   * DER-encoded tbsResponseData, and then run it through a crypto-signing
   * function, which will (at least w/RSA) do a hash-'n'-private-encrypt
   * operation.  This seems a bit odd, but that's the spec.  Also note that
   * the data structures do not leave anywhere to independently specify the
   * algorithm used for the initial hash. So, we look at the
   * signature-specification algorithm, and try to do something intelligent.
   * -- Kathy Weinhold, CertCo
   */
  /*
   * Note 2: It seems that the mentioned passage from RFC 2560 (section
   * 4.2.1) is open for interpretation.  I've done tests against another
   * responder, and found that it doesn't do the double hashing that the RFC
   * seems to say one should.  Therefore, all relevant functions take a flag
   * saying which variant should be used.  -- Richard Levitte, OpenSSL team
   * and CeloCom
   */
typedef struct ocsp_basic_response_st {
    OCSP_RESPDATA *tbsResponseData;
    X509_ALGOR *signatureAlgorithm;
    ASN1_BIT_STRING *signature;
    STACK_OF(X509) *certs;
} OCSP_BASICRESP;

/*-
 *   CRLReason ::= ENUMERATED {
 *        unspecified             (0),
 *        keyCompromise           (1),
 *        cACompromise            (2),
 *        affiliationChanged      (3),
 *        superseded              (4),
 *        cessationOfOperation    (5),
 *        certificateHold         (6),
 *        removeFromCRL           (8) }
 */
# define OCSP_REVOKED_STATUS_NOSTATUS               -1
# define OCSP_REVOKED_STATUS_UNSPECIFIED             0
# define OCSP_REVOKED_STATUS_KEYCOMPROMISE           1
# define OCSP_REVOKED_STATUS_CACOMPROMISE            2
# define OCSP_REVOKED_STATUS_AFFILIATIONCHANGED      3
# define OCSP_REVOKED_STATUS_SUPERSEDED              4
# define OCSP_REVOKED_STATUS_CESSATIONOFOPERATION    5
# define OCSP_REVOKED_STATUS_CERTIFICATEHOLD         6
# define OCSP_REVOKED_STATUS_REMOVEFROMCRL           8


# define PEM_STRING_OCSP_REQUEST "OCSP REQUEST"
# define PEM_STRING_OCSP_RESPONSE "OCSP RESPONSE"

# define d2i_OCSP_RESPONSE_bio(bp,p) ASN1_d2i_bio_of(OCSP_RESPONSE,OCSP_RESPONSE_new,d2i_OCSP_RESPONSE,bp,p)

# define OCSP_BASICRESP_verify(a,r,d) ASN1_item_verify(ASN1_ITEM_rptr(OCSP_RESPDATA),\
        a->signatureAlgorithm,a->signature,a->tbsResponseData,r)

OCSP_CERTID *OCSP_CERTID_dup(OCSP_CERTID *id);

OCSP_CERTID *OCSP_cert_to_id(const EVP_MD *dgst, X509 *subject, X509 *issuer);

OCSP_CERTID *OCSP_cert_id_new(const EVP_MD *dgst,
                              X509_NAME *issuerName,
                              ASN1_BIT_STRING *issuerKey,
                              ASN1_INTEGER *serialNumber);

OCSP_ONEREQ *OCSP_request_add0_id(OCSP_REQUEST *req, OCSP_CERTID *cid);

int OCSP_response_status(OCSP_RESPONSE *resp);
OCSP_BASICRESP *OCSP_response_get1_basic(OCSP_RESPONSE *resp);

int OCSP_resp_find_status(OCSP_BASICRESP *bs, OCSP_CERTID *id, int *status,
                          int *reason,
                          ASN1_GENERALIZEDTIME **revtime,
                          ASN1_GENERALIZEDTIME **thisupd,
                          ASN1_GENERALIZEDTIME **nextupd);
int OCSP_check_validity(ASN1_GENERALIZEDTIME *thisupd,
                        ASN1_GENERALIZEDTIME *nextupd, long sec, long maxsec);

int OCSP_id_issuer_cmp(OCSP_CERTID *a, OCSP_CERTID *b);


DECLARE_ASN1_FUNCTIONS(OCSP_BASICRESP)
DECLARE_ASN1_FUNCTIONS(OCSP_CERTID)
DECLARE_ASN1_FUNCTIONS(OCSP_REQUEST)

int OCSP_basic_verify(OCSP_BASICRESP *bs, STACK_OF(X509) *certs,
                      X509_STORE *st, unsigned long flags);

/* BEGIN ERROR CODES */
/*
 * The following lines are auto generated by the script mkerr.pl. Any changes
 * made after this point may be overwritten when the script is next run.
 */
// void ERR_load_OCSP_strings(void);

/* Error codes for the OCSP functions. */

/* Function codes. */
# define OCSP_F_ASN1_STRING_ENCODE                        100
# define OCSP_F_D2I_OCSP_NONCE                            102
# define OCSP_F_OCSP_BASIC_ADD1_STATUS                    103
# define OCSP_F_OCSP_BASIC_SIGN                           104
# define OCSP_F_OCSP_BASIC_VERIFY                         105
# define OCSP_F_OCSP_CERT_ID_NEW                          101
# define OCSP_F_OCSP_CHECK_DELEGATED                      106
# define OCSP_F_OCSP_CHECK_IDS                            107
# define OCSP_F_OCSP_CHECK_ISSUER                         108
# define OCSP_F_OCSP_CHECK_VALIDITY                       115
# define OCSP_F_OCSP_MATCH_ISSUERID                       109
# define OCSP_F_OCSP_PARSE_URL                            114
# define OCSP_F_OCSP_REQUEST_SIGN                         110
# define OCSP_F_OCSP_REQUEST_VERIFY                       116
# define OCSP_F_OCSP_RESPONSE_GET1_BASIC                  111
# define OCSP_F_OCSP_SENDREQ_BIO                          112
# define OCSP_F_OCSP_SENDREQ_NBIO                         117
# define OCSP_F_PARSE_HTTP_LINE1                          118
# define OCSP_F_REQUEST_VERIFY                            113

/* Reason codes. */
# define OCSP_R_BAD_DATA                                  100
# define OCSP_R_CERTIFICATE_VERIFY_ERROR                  101
# define OCSP_R_DIGEST_ERR                                102
# define OCSP_R_ERROR_IN_NEXTUPDATE_FIELD                 122
# define OCSP_R_ERROR_IN_THISUPDATE_FIELD                 123
# define OCSP_R_ERROR_PARSING_URL                         121
# define OCSP_R_MISSING_OCSPSIGNING_USAGE                 103
# define OCSP_R_NEXTUPDATE_BEFORE_THISUPDATE              124
# define OCSP_R_NOT_BASIC_RESPONSE                        104
# define OCSP_R_NO_CERTIFICATES_IN_CHAIN                  105
# define OCSP_R_NO_CONTENT                                106
# define OCSP_R_NO_PUBLIC_KEY                             107
# define OCSP_R_NO_RESPONSE_DATA                          108
# define OCSP_R_NO_REVOKED_TIME                           109
# define OCSP_R_PRIVATE_KEY_DOES_NOT_MATCH_CERTIFICATE    110
# define OCSP_R_REQUEST_NOT_SIGNED                        128
# define OCSP_R_RESPONSE_CONTAINS_NO_REVOCATION_DATA      111
# define OCSP_R_ROOT_CA_NOT_TRUSTED                       112
# define OCSP_R_SERVER_READ_ERROR                         113
# define OCSP_R_SERVER_RESPONSE_ERROR                     114
# define OCSP_R_SERVER_RESPONSE_PARSE_ERROR               115
# define OCSP_R_SERVER_WRITE_ERROR                        116
# define OCSP_R_SIGNATURE_FAILURE                         117
# define OCSP_R_SIGNER_CERTIFICATE_NOT_FOUND              118
# define OCSP_R_STATUS_EXPIRED                            125
# define OCSP_R_STATUS_NOT_YET_VALID                      126
# define OCSP_R_STATUS_TOO_OLD                            127
# define OCSP_R_UNKNOWN_MESSAGE_DIGEST                    119
# define OCSP_R_UNKNOWN_NID                               120
# define OCSP_R_UNSUPPORTED_REQUESTORNAME_TYPE            129

#ifdef  __cplusplus
}
#endif
#endif // OPENSSL_IS_BORINGSSL

#endif


