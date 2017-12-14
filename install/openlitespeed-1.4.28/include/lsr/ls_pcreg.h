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
#ifndef LS_PCREG_H
#define LS_PCREG_H


#include <lsr/ls_types.h>
#include <pcre.h>

#define LSR_PCRE_WORKSPACE_LEN 50

#define LSR_PCRE_DFA_MODE           (1<<0)
#define LSR_PCRE_CACHE_COMPILED     (1<<1)

/**
 * @file
 */

//#define _USE_PCRE_JIT_

#ifdef __cplusplus
extern "C" {
#endif

typedef struct ls_pcre_s ls_pcre_t;
typedef struct ls_pcreres_s ls_pcreres_t;
typedef struct ls_pcresub_s ls_pcresub_t;
typedef struct ls_pcresubent_s ls_pcresubent_t;

/**
 * @typedef ls_pcre_t
 * @brief The base pcre structure.  Used for pcre compilation and execution.
 */
struct ls_pcre_s
{
    pcre       *regex;
    pcre_extra *extra;
    int         substr;
    char       *pattern;
};

/**
 * @typedef ls_pcreres_t
 * @brief A structure to hold the pcre results in one struct.
 */
struct ls_pcreres_s
{
    const char *pbuf;
    int         ovector[30];
    int         matches;
};

/**
 * @typedef ls_pcresub_t
 * @brief Contains the list of the substitution entries.
 */
struct ls_pcresub_s
{
    char               *parsed;
    ls_pcresubent_t    *plist;
    ls_pcresubent_t    *plistend;
};

/**
 * @typedef ls_pcresubent_t
 * @brief A substitution entry.
 * result.
 */
struct ls_pcresubent_s
{
    int         strbegin;
    int         strlen;
    int         param;
};

/** @ls_pcre_new
 * @brief Creates a new pcre object and initializes it.
 * Must be \link #ls_pcre_delete deleted \endlink when finished.
 *
 * @return The created pcre object, or NULL if it failed.
 *
 * @see ls_pcre_delete
 */
ls_pcre_t         *ls_pcre_new();

/** @ls_pcre
 * @brief Initializes a given pcre object.
 * Must be \link #ls_pcre_d destroyed \endlink when finished.
 *
 * @param[in] pThis - A pointer to an allocated pcre object.
 * @return The initialized pcre object, or NULL if it failed.
 *
 * @see ls_pcre_d
 */
ls_pcre_t         *ls_pcre(ls_pcre_t *pThis);

/** @ls_pcre_d
 * @brief Destroys the pcre object.  DOES NOT FREE THE STRUCT ITSELF!
 *
 * @param[in] pThis - A pointer to an initialized pcre object.
 * @return Void.
 *
 * @see ls_pcre
 */
void                ls_pcre_d(ls_pcre_t *pThis);

/** @ls_pcre_delete
 * @brief Destroys and deletes the pcre object.
 * @details The object should have been created with a previous
 *   successful call to ls_pcre_new.
 *
 * @param[in] pThis - A pointer to an initialized pcre object.
 * @return Void.
 *
 * @see ls_pcre_new
 */
void                ls_pcre_delete(ls_pcre_t *pThis);

/** @ls_pcre_load
 * @brief Load a ls_pcre object with the same Regex pattern and compile flags.
 *
 * @param[in] pRegex - A pointer to the Regex to match against.
 * @param[in] iFlags - The compile flags to match against.
 * @return a pointer to the ls_pcre object if successful, else NULL.
 *
 * @see ls_pcre_store
 */
ls_pcre_t         *ls_pcre_load(const char *pRegex, unsigned long iFlags);

/** @ls_pcre_store
 * @brief Stores a ls_pcre_t object with the compile flags.
 * @details NOTE: The ls_pcre_t object must be allocated via ls_pcre_new.
 *
 * @param[in] pThis - A pointer to the ls_pcre_t object to store.
 * @param[in] iFlags - The compile flags used for the compilation of pThis.
 * @return 1 if successful, else 0 if another ls_pcre_t object with the same
 * parameters is already stored.
 *
 * @see ls_pcre_load
 */
int                ls_pcre_store(ls_pcre_t *pThis, unsigned long iFlags);

/** @ls_pcre_result
 * @brief Initializes a given pcre result object.
 *
 * @param[in] pThis - A pointer to an allocated pcre result object.
 * @return The initialized result object, or NULL if it failed.
 *
 * @see ls_pcreres_d
 */
ls_pcreres_t  *ls_pcre_result(ls_pcreres_t *pThis);

/** @ls_pcre_sub
 * @brief Initializes a given pcre sub object.
 * Must be \link #ls_pcresub_d destroyed \endlink when finished.
 *
 * @param[in] pThis - A pointer to an allocated pcre sub object.
 * @return The initialized sub object, or NULL if it failed.
 *
 * @see ls_pcresub_d
 */
ls_pcresub_t     *ls_pcre_sub(ls_pcresub_t *pThis);

/** @ls_pcreres_new
 * @brief Creates a new pcre result object and initializes it.
 * Must be \link #ls_pcreres_delete deleted \endlink when finished.
 *
 * @return The created result object, or NULL if it failed.
 *
 * @see ls_pcreres_delete
 */
ls_pcreres_t  *ls_pcreres_new();

/** @ls_pcreres_d
 * @brief Destroys the pcre result object.  DOES NOT FREE THE STRUCT ITSELF!
 *
 * @param[in] pThis - A pointer to an initialized pcre result object.
 * @return Void.
 *
 * @see ls_pcre_result
 */
void                ls_pcreres_d(ls_pcreres_t *pThis);

/** @ls_pcreres_delete
 * @brief Destroys and deletes the pcre result object.
 * @details The object should have been created with a previous
 *   successful call to ls_pcreres_new.
 *
 * @param[in] pThis - A pointer to an initialized pcre result object.
 * @return Void.
 *
 * @see ls_pcreres_new
 */
void                ls_pcreres_delete(ls_pcreres_t *pThis);

/** @ls_pcresub_new
 * @brief Creates a new pcre sub object and initializes it.
 * Must be \link #ls_pcresub_delete deleted \endlink when finished.
 *
 * @return The created pcre sub object, or NULL if it failed.
 *
 * @see ls_pcresub_delete
 */
ls_pcresub_t     *ls_pcresub_new();

/** @ls_pcresub_copy
 * @brief Copies the sub internals from src to dest.
 *
 * @param[in] dest - A pointer to an initialized pcre sub object.
 * @param[in] src - A pointer to an initialized pcre sub object.
 * @return Dest if successful, NULL if not.
 *
 * @see ls_pcresub_d
 */
ls_pcresub_t     *ls_pcresub_copy(ls_pcresub_t *dest,
                                  const ls_pcresub_t *src);

/** @ls_pcresub_d
 * @brief Destroys the pcre sub object.  DOES NOT FREE THE STRUCT ITSELF!
 *
 * @param[in] pThis - A pointer to an initialized pcre sub object.
 * @return Void.
 *
 * @see ls_pcre_sub
 */
void                ls_pcresub_d(ls_pcresub_t *pThis);

/** @ls_pcresub_delete
 * @brief Destroys and deletes the pcre sub object.
 * @details The object should have been created with a previous
 *   successful call to ls_pcresub_new.
 *
 * @param[in] pThis - A pointer to an initialized pcre sub object.
 * @return Void.
 *
 * @see ls_pcresub_new
 */
void                ls_pcresub_delete(ls_pcresub_t *pThis);

/** @ls_pcreres_setbuf
 * @brief Sets the result buf to \e pBuf.
 * @note This does not create a deep copy!
 *
 * @param[in] pThis - A pointer to an initialized pcre result object.
 * @param[in] pBuf - A pointer to the buffer to set the struct buf to.
 * @return Void.
 */
ls_inline void  ls_pcreres_setbuf(ls_pcreres_t *pThis, const char *pBuf)
{   pThis->pbuf = pBuf;        }

/** @ls_pcreres_setmatches
 * @brief Sets the number of matches to \e matches.
 *
 * @param[in] pThis - A pointer to an initialized pcre result object.
 * @param[in] matches - The number of matches to set the object to.
 * @return Void.
 */
ls_inline void  ls_pcreres_setmatches(ls_pcreres_t *pThis, int matches)
{   pThis->matches = matches;  }

/** @ls_pcreres_getvector
 * @brief Gets the ovector from the result.
 *
 * @param[in] pThis - A pointer to an initialized pcre result object.
 * @return a pointer to the ovector.
 */
ls_inline int  *ls_pcreres_getvector(ls_pcreres_t *pThis)
{   return pThis->ovector;    }

/** @ls_pcres_getmatches
 * @brief Gets the matches from the result.
 *
 * @param[in] pThis - A pointer to an initialized result object.
 * @return The matches count.
 */
ls_inline int   ls_pcres_getmatches(ls_pcreres_t *pThis)
{   return pThis->matches;    }

/** @ls_pcreres_getsubstr
 * @brief Gets the substring from the result.
 *
 * @param[in] pThis - A pointer to an initialized pcre result object.
 * @param[in] i - The index of the substring to get.
 * @param[out] pValue - A pointer to the resulting substring.
 * @return The length of the substring.
 */
int ls_pcreres_getsubstr(const ls_pcreres_t *pThis, int i, char **pValue);

#ifdef _USE_PCRE_JIT_
#if !defined(__sparc__) && !defined(__sparc64__)
void ls_pcre_init_jit_stack();
pcre_jit_stack *ls_pcre_get_jit_stack();
void ls_pcre_release_jit_stack(void *pValue);
#endif
#endif

/** @ls_pcre_parseoptions
 * @brief Parses a character representation of pcre compilation options.
 * @details The following options are available:
 * - a: Anchored
 * - d: DFA mode
 * - i: Case Insensitive
 * - j: Jit mode
 * - m: Multiline
 * - o: Cache Compiled
 * - s: DOTALL, . = any char
 * - u: UTF8
 * - x: Extended
 * - **D: Duplicate Names
 * - **J: Javascript Compatible
 * - U: UTF8 & skip checking validity of pattern.
 *
 * ** Only for PCRE version >= 6.
 *
 * The user should check the return to determine if DFA exec or regular exec
 * should be used and if the ls_pcre_t object should be stored.
 *
 * @param[in] pOptions - A pointer to the character representation of the
 * options.
 * @param[in] iOptLen - The number of characters in pOptions.
 * @param[out] iFlags - A pointer to the completed conversion of the options.
 * @return A numerical representation of the flags to be parsed by the user.
 */
int ls_pcre_parseoptions(const char *pOptions, size_t iOptLen,
                         unsigned long *iFlags);

/** @ls_pcre_compile
 * @brief Compiles the pcre object to get it ready for exec.  Must
 * \link #ls_pcre_release release \endlink at the end if successful.
 *
 * @param[in] pThis - A pointer to an initialized pcre object.
 * @param[in] regex - The regex to use.
 * @param[in] options - Pcre options.
 * @param[in] matchLimit - A limit on the number of matches.  0 to ignore.
 * @param[in] recursionLimit - A limit on the number of recursions.  0 to ignore.
 * @return 0 on success, -1 on failure.
 *
 * @see ls_pcre_release
 */
int ls_pcre_compile(ls_pcre_t *pThis, const char *regex,
                    int options, int matchLimit, int recursionLimit);

/** @ls_pcre_exec
 * @brief Executes the regex matching.
 *
 * @param[in] pThis - A pointer to an initialized pcre object.
 * @param[in] subject - The subject string to search.
 * @param[in] length - The length of the subject string.
 * @param[in] startoffset - The offset of the subject to start at.
 * @param[in] options - The options to provide to pcre.
 * @param[out] ovector - The output vector for the result.
 * @param[in] ovecsize - The number of elements in the vector (multiple of 3).
 * @return The number of successful matches.
 */
ls_inline int   ls_pcre_exec(ls_pcre_t *pThis, const char *subject,
                             int length,
                             int startoffset, int options, int *ovector, int ovecsize)
{
#ifdef _USE_PCRE_JIT_
#if !defined(__sparc__) && !defined(__sparc64__)
    pcre_jit_stack *stack = ls_pcre_get_jit_stack();
    pcre_assign_jit_stack(pThis->m_extra, NULL, stack);
#endif
#endif
    return pcre_exec(pThis->regex, pThis->extra, subject, length, startoffset,
                     options, ovector, ovecsize);
}

/** @ls_pcre_execresult
 * @brief Executes the regex matching, storing the result in a pcre result object.
 *
 * @param[in] pThis - A pointer to an initialized pcre object.
 * @param[in] subject - The subject string to search.
 * @param[in] length - The length of the subject string.
 * @param[in] startoffset - The offset of the subject to start at.
 * @param[in] options - The options to provide to pcre.
 * @param[out] pRes - A pointer to an initialized output result object.
 * @return The number of successful matches.
 */
ls_inline int  ls_pcre_execresult(ls_pcre_t *pThis, const char *subject,
                                  int length,
                                  int startoffset, int options, ls_pcreres_t *pRes)
{
    ls_pcreres_setmatches(pRes, pcre_exec(pThis->regex, pThis->extra, subject,
                                          length, startoffset, options, ls_pcreres_getvector(pRes), 30));
    return ls_pcres_getmatches(pRes);
}

/** @ls_pcre_dfaexec
 * @brief Executes the regex matching.
 * @details Uses the DFA algorithm.
 *
 * @param[in] pThis - A pointer to an initialized pcre object.
 * @param[in] subject - The subject string to search.
 * @param[in] length - The length of the subject string.
 * @param[in] startoffset - The offset of the subject to start at.
 * @param[in] options - The options to provide to pcre.
 * @param[out] ovector - The output vector for the result.
 * @param[in] ovecsize - The number of elements in the vector (multiple of 3).
 * @return The number of successful matches.
 */
ls_inline int  ls_pcre_dfaexec(ls_pcre_t *pThis, const char *subject,
                               int length,
                               int startoffset, int options, int *ovector, int ovecsize)
{
#if PCRE_MAJOR >= 6
    int aWorkspace[LSR_PCRE_WORKSPACE_LEN];
    return pcre_dfa_exec(pThis->regex, pThis->extra, subject, length,
                         startoffset,
                         options, ovector, ovecsize, aWorkspace, LSR_PCRE_WORKSPACE_LEN);
#else
    return LS_FAIL;
#endif
}

/** @ls_pcre_dfaexecresult
 * @brief Executes the regex matching, storing the result in a pcre result object.
 * @details Uses the DFA algorithm.
 *
 * @param[in] pThis - A pointer to an initialized pcre object.
 * @param[in] subject - The subject string to search.
 * @param[in] length - The length of the subject string.
 * @param[in] startoffset - The offset of the subject to start at.
 * @param[in] options - The options to provide to pcre.
 * @param[out] pRes - A pointer to an initialized output result object.
 * @return The number of successful matches.
 */
ls_inline int  ls_pcre_dfaexecresult(ls_pcre_t *pThis, const char *subject,
                                     int length, int startoffset, int options,
                                     ls_pcreres_t *pRes)
{
#if PCRE_MAJOR >= 6
    int aWorkspace[LSR_PCRE_WORKSPACE_LEN];
    ls_pcreres_setmatches(pRes, pcre_dfa_exec(pThis->regex, pThis->extra,
                          subject, length, startoffset, options,
                          ls_pcreres_getvector(pRes), 30,
                          aWorkspace, LSR_PCRE_WORKSPACE_LEN));
    return ls_pcres_getmatches(pRes);
#else
    return LS_FAIL;
#endif
}

/** @ls_pcre_release
 * @brief Releases anything that was initialized by the pcre compile/exec calls.
 * MUST BE CALLED IF COMPILE/EXEC ARE CALLED.
 *
 * @param[in] pThis - A pointer to an initialized pcre object.
 * @return Void.
 */
void                ls_pcre_release(ls_pcre_t *pThis);

/** @ls_pcre_getsubstrcnt
 * @brief Gets the number of substrings in the pcre.
 *
 * @param[in] pThis - A pointer to an initialized pcre object.
 * @return The substring count.
 */
ls_inline int   ls_pcre_getsubstrcnt(ls_pcre_t *pThis)
{   return pThis->substr;   }

/** @ls_pcre_getnamedsubcnt
 * @brief Gets the number of Named Subpatterns from the Pattern.
 *
 * @param[in] pThis - A pointer to an initialized pcre object.
 * @return The Named Subpattern count.
 */
int ls_pcre_getnamedsubcnt(ls_pcre_t *pThis);

/** @ls_pcre_getnamedsubs
 * @brief Gets the named subpatterns from the pcre object after execution.
 * @details The array of patterns must be allocated before calling this
 * function.  The size of the array is determined by a previous call to
 * \link #ls_pcre_getnamedsubcnt get named sub count.\endlink
 *
 * @param[in] pThis - A pointer to an initialized pcre object.
 * @param[in] pRes - A pointer to an initialized pcre result object.
 * @param[out] pSubPats - A pointer to an allocated array of string pairs.
 * This will contain the name patterns upon return.
 * @param[in] iCount - The maximum number of Named Patterns allowed.
 * @return Number of named patterns if successful, else -1.
 */
int ls_pcre_getnamedsubs(const ls_pcre_t *pThis, const ls_pcreres_t *pRes,
                         ls_strpair_t *pSubPats, int iCount);

/** @ls_pcresub_release
 * @brief Releases anything that was initialized by the pcre sub compile/exec calls.
 * MUST BE CALLED IF SUB COMPILE/EXEC ARE CALLED.
 *
 * @param[in] pThis - A pointer to an initialized pcre sub object.
 * @return Void.
 */
void    ls_pcresub_release(ls_pcresub_t *pThis);

/** @ls_pcresub_compile
 * @brief Sets up the pcre sub object to get it ready for substitution.
 * Must \link #ls_pcresub_release release \endlink after
 * \link #ls_pcresub_exec executing. \endlink
 *
 * @param[in] pThis - A pointer to an initialized sub object.
 * @param[in] rule - The rule to apply to the substrings.
 * @return 0 on success, -1 on failure.
 */
int     ls_pcresub_compile(ls_pcresub_t *pThis, const char *rule);

/** @ls_pcresub_exec
 * @brief Applies the rule from \link #ls_pcresub_compile sub compile \endlink
 * to the result.  The output buffer must be allocated before calling this function.
 * @note Please notice that ovector and ovec_num are \e input parameters.  They should
 * be the output from a call to \link #ls_pcre_exec pcre exec \endlink that was called
 * prior to calling this function.
 *
 * @param[in] pThis - A pointer to an initialized sub object.
 * @param[in] input - The original subject string.
 * @param[in] ovector - The result from pcre exec.
 * @param[in] ovec_num - The number of matches as returned by exec.
 * @param[out] output - The allocated output buffer for the result of the substitution.
 * @param[out] length - The length of the output.
 * @return 0 on success, -1 on failure.
 *
 * @see ls_pcre_exec
 */
int     ls_pcresub_exec(ls_pcresub_t *pThis, const char *input,
                        const int *ovector, int ovec_num, char *output, int *length);

/** @ls_pcresub_getlen
 * @brief Gets the final length of the substring post exec.
 * @details This may be used to determine the length of the buffer for
 * ls_pcresub_exec.
 *
 * @param[in] pThis - A pointer to an initialized sub object.
 * @param[in] input - The original subject string.
 * @param[in] ovector - The result from pcre exec.
 * @param[in] ovec_num - The number of matches as returned by exec.
 * @return The final length of the substring.
 */
int     ls_pcresub_getlen(ls_pcresub_t *pThis, const char *input,
                          const int *ovector, int ovec_num);

#ifdef __cplusplus
}
#endif
#endif //LS_PCREG_H
