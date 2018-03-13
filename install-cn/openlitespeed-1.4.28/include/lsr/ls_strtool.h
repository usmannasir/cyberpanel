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
#ifndef LS_STRTOOL_H
#define LS_STRTOOL_H


#include <stddef.h>
#include <ctype.h>
#include <stdarg.h>
#include <sys/types.h>
#include <lsr/ls_types.h>


/**
 * @file
 */


#ifdef __cplusplus
extern "C" {
#endif

/**
 * @skip_leading_space
 * @brief Skips past leading spaces and tabs in a string.
 *
 * @param[in,out] p - A pointer to an input string pointer,
 *   which upon return contains a pointer to the first non-space character
 *   from the beginning of the input string.
 * @return Void.
 */
ls_inline void skip_leading_space(const char **p)
{
    while (isspace(**p))
        ++(*p);
}

/**
 * @skip_trailing_space
 * @brief Skips trailing spaces and tabs in a string.
 *
 * @param[in,out] p - A pointer to an input string pointer,
 *   which upon return contains a pointer just past the last non-space character
 *   preceding the input string pointer.
 * @return Void.
 */
ls_inline void skip_trailing_space(const char **p)
{
    while (isspace((*p)[-1]))
        --(*p);
}

/**
 * @hexdigit
 * @brief Gets a binary value for a hexadecimal digit character.
 *
 * @param[in] ch - A hex digit character.
 * @return The binary value of the hex digit character.
 */
ls_inline char hexdigit(char ch)
{
    return (((ch) <= '9') ? (ch) - '0' : ((ch) & 7) + 9);
}


/**
 * @typedef ls_parse_t
 */
typedef struct ls_parse_s
{
    const char *pbegin;
    const char *pend;
    const char *delim;
    const char *pstrend;
} ls_parse_t;

/**
 * @ls_parse
 * @brief Initializes a string parsing object.
 * @details This object manages the parsing of strings specified by the user.
 *
 * @param[in] pThis - A pointer to an allocated string parsing object.
 * @param[in] pBegin - A pointer to the beginning of the string to parse.
 * @param[in] pEnd - A pointer to the end of the string.
 * @param[in] delim - The field delimiters (cannot be an empty string).
 * @return Void.
 *
 * @see ls_parse_new, ls_parse_d
 */
ls_inline void ls_parse(
    ls_parse_t *pThis, const char *pBegin, const char *pEnd, const char *delim)
{
    pThis->pbegin = pBegin;
    pThis->pend = pEnd;
    pThis->delim = delim;
    pThis->pstrend = NULL;
}

/**
 * @ls_parse_new
 * @brief Creates a new string parsing object.
 * @details The routine allocates and initializes an object
 *   which manages the parsing of strings specified by the user.
 *
 * @param[in] pBegin - A pointer to the beginning of the string to parse.
 * @param[in] pEnd - A pointer to the end of the string.
 * @param[in] delim - The field delimiters (cannot be an empty string).
 * @return A pointer to an initialized string parsing object.
 *
 * @see ls_parse, ls_parse_delete
 */
ls_parse_t *ls_parse_new(const char *pBegin, const char *pEnd,
                         const char *delim);

/**
 * @ls_parse_d
 * @brief Destroys the contents of a string parsing object.
 *
 * @param[in] pThis - A pointer to an initialized string parsing object.
 * @return Void.
 *
 * @see ls_parse
 */
ls_inline void ls_parse_d(ls_parse_t *pThis)
{}

/**
 * @ls_parse_delete
 * @brief Destroys then deletes a string parsing object.
 * @details The object should have been created with a previous
 *   successful call to ls_parse_new.
 *
 * @param[in] pThis - A pointer to an initialized string parsing object.
 * @return Void.
 *
 * @see ls_parse_new
 */
void ls_parse_delete(ls_parse_t *pThis);

/**
 * @ls_parse_isend
 * @brief Specifies whether or not the string has been fully parsed (is the end).
 *
 * @param[in] pThis - A pointer to an initialized string parsing object.
 * @return 1 if the end, else 0.
 */
ls_inline int ls_parse_isend(const ls_parse_t *pThis)
{   return pThis->pend <= pThis->pbegin;   }

/**
 * @ls_parse_parse
 * @brief Parses or continues to parse the string
 *   managed by the string parsing object.
 *
 * @param[in] pThis - A pointer to an initialized string parsing object.
 * @return A pointer to the next token from the string.
 */
const char *ls_parse_parse(ls_parse_t *pThis);

/**
 * @ls_parse_trimparse
 * @brief Parses or continues to parse the string
 *   managed by the string parsing object,
 *   trimming white space from the beginning and end of each token.
 *
 * @param[in] pThis - A pointer to an initialized string parsing object.
 * @return A pointer to the next token from the string.
 */
ls_inline const char *ls_parse_trimparse(ls_parse_t *pThis)
{
    skip_leading_space(&pThis->pbegin);
    const char *p = ls_parse_parse(pThis);
    if ((p != NULL) && (p != pThis->pstrend))
        skip_trailing_space(&pThis->pstrend);
    return p;
}

/**
 * @ls_parse_getstrend
 * @brief Gets the end of the current string token.
 *
 * @param[in] pThis - A pointer to an initialized string parsing object.
 * @return A pointer to the end of the current token.
 */
ls_inline const char *ls_parse_getstrend(const ls_parse_t *pThis)
{   return pThis->pstrend;   }

extern const char ls_s_hex[17];

/**
 * @ls_strupper
 * @brief Converts a character string to upper case.
 *
 * @param[in] pSrc - A pointer to the source string.
 * @param[in] pDest - A pointer to the destination buffer.
 * @return The destination pointer, else NULL on error.
 */
char *ls_strupper(const char *pSrc, char *pDest);

/**
 * @ls_strnupper
 * @brief Converts a maximum defined length character string to upper case.
 * @details The destination is null-terminated if and only if
 *   there is sufficient space.
 *
 * @param[in] pSrc - A pointer to the source string.
 * @param[in] pDest - A pointer to the destination buffer.
 * @param[in,out] pCnt - On input, the maximum number of characters to process;
 *   on return, the actual number of characters.
 * @return The destination pointer, else NULL on error.
 */
char *ls_strnupper(const char *pSrc, char *pDest, int *pCnt);

/**
 * @ls_strlower
 * @brief Converts a character string to lower case.
 *
 * @param[in] pSrc - A pointer to the source string.
 * @param[in] pDest - A pointer to the destination buffer.
 * @return The destination pointer, else NULL on error.
 */
char *ls_strlower(const char *pSrc, char *pDest);

/**
 * @ls_strnlower
 * @brief Converts a maximum defined length character string to lower case.
 * @details The destination is null-terminated if and only if
 *   there is sufficient space.
 *
 * @param[in] pSrc - A pointer to the source string.
 * @param[in] pDest - A pointer to the destination buffer.
 * @param[in,out] pCnt - On input, the maximum number of characters to process;
 *   on return, the actual number of characters.
 * @return The destination pointer, else NULL on error.
 */
char *ls_strnlower(const char *pSrc, char *pDest, int *pCnt);

/**
 * @ls_strtrim
 * @brief Trims white space from the beginning and end of a string.
 *
 * @param[in] p - A pointer to the source string.
 * @return A pointer to the \e trimmed string.
 * @note Trimming is done in place.
 */
char *ls_strtrim(char *p);

/**
 * @ls_strtrim2
 * @brief Trims white space from the beginning and end of a string.
 *
 * @param[in,out] pBegin - On input, a pointer to the source string pointer;
 *   on return, the \e trimmed string pointer is returned.
 * @param[in,out] pEnd - On input, a pointer to the source string end pointer;
 *   on return, the \e trimmed string end pointer is returned.
 * @return 0.
 */
int    ls_strtrim2(const char **pBegin, const char **pEnd);

/**
 * @ls_hexencode
 * @brief Converts a character buffer to a corresponding string
 *   of ascii hexadecimal digits.
 * @details It is permissible for the destination pointer to be
 *   the same as the source pointer.
 *
 * @param[in] pSrc - A pointer to the source buffer.
 * @param[in] len - The number of characters to convert from \e pSrc.
 * @param[in] pDest - A pointer to the destination buffer.
 * @return The length of the new converted string.
 * @warning It is the responsibility of the user to ensure that
 *   there is sufficient space at the destination.
 *   This should be equal to two times the size of the input,
 *   plus one for the null-termination.
 */
int    ls_hexencode(const char *pSrc, int len, char *pDest);

/**
 * @ls_hexdecode
 * @brief Converts a character buffer of ascii hexadecimal digits
 *   to its corresponding characters.
 * @details It is permissible for the destination pointer to be
 *   the same as the source pointer.
 *
 * @param[in] pSrc - A pointer to the source buffer.
 * @param[in] len - The number of characters to convert from \e pSrc.
 * @param[in] pDest - A pointer to the destination buffer.
 * @return The length of the new converted buffer.
 */
int    ls_hexdecode(const char *pSrc, int len, char *pDest);

/**
 * @ls_strmatch
 * @brief Determines whether or not a string matches a specified pattern.
 * @details Pattern matching includes the special wildcard characters:\n
 *   \arg '?' Question Mark - Matches exactly one of any character
 *   \arg '*' Asterisk - Matches zero or more of any characters
 *
 * @param[in] pSrc - A pointer to the source string.
 * @param[in] pEnd - A pointer to the end of the string;
 *   else NULL to specify the null-termination of the source.
 * @param[in] begin - A string list iterator for tokens in the pattern to match.
 * @param[in] end - The string list end iterator.
 * @param[in] case_sens - A case sensitivity flag.
 * 1 for case sensitive, 0 for case insensitive.
 *
 * @return Zero for a match, else non-zero.
 *
 * @see ls_parsematchpattern
 */
int    ls_strmatch(const char *pSrc, const char *pEnd,
                   ls_str_t *const *begin, ls_str_t *const *end, int case_sens);

/**
 * @ls_parsematchpattern
 * @brief Separates a pattern string into its component tokens.
 * @details Pattern matching includes the special wildcard characters:\n
 *   \arg '?' Question Mark - Matches exactly one of any character
 *   \arg '*' Asterisk - Matches zero or more of any characters
 *
 * @param[in] pPattern - A pointer to the pattern string.
 * @return A pointer to a new string list object
 *   containing the pattern matching tokens, else NULL on error.
 * @warning It is the responsibility of the user to ensure the
 *   returned string list object is deleted upon completion.
 *
 * @see ls_strmatch
 */
ls_strlist_t *ls_parsematchpattern(const char *pPattern);

/**
 * @ls_strnextarg
 * @brief Gets the next token (argument) from a string.
 *
 * @param[in,out] pStr - A pointer to a string pointer.
 *   On input, it specifies the string to process;
 *   on return, its value may be different if the token was quoted.
 * @param[in] pDelim - A pointer specifying the field delimiters;
 *   if NULL, the default is space, tab, carriage return, and newline.
 * @return A pointer past the end of the current arg,
 *   which is typically the delimiter but possibly a quote character.
 */
const char *ls_strnextarg(const char **pStr, const char *pDelim);

/**
 * @ls_getline
 * @brief Gets the next newline in a character buffer.
 *
 * @param[in] pBegin - A pointer to the beginning of the buffer.
 * @param[in] pEnd - A pointer to the end of the buffer.
 * @return A pointer to the next newline character if it exists,
 *   else \e pEnd.
 */
const char *ls_getline(const char *pBegin, const char *pEnd);

/** @ls_getconfline
 * @brief Gets a line from a block of configuration.
 * @details A line will have any surrounding delimiters removed from the beginning and the end.
 *
 * @param[in,out] pParseBegin - A pointer to the \e address of the beginning of the line
 * (may include white space) and will point to the beginning of the next line when the function
 * returns. When there are no more lines, the dereferenced pointer will be greater than or equal to pParseEnd.
 * @param[in] pParseEnd - A pointer to the end of the parse buffer.
 * @param[out] pLineEnd - This will point to the address right after the end of the line.
 * @return The pointer to the beginning of the line, or NULL if there are no more lines.
 */
const char *ls_getconfline(const char **pParseBegin, const char *pParseEnd,
                           const char **pLineEnd);

/**
 * @ls_parsenextarg
 * @brief Parses a string returning the next argument,
 *   and advancing the buffer pointer.
 * @details The routine correctly handles quotes and white space.
 *
 * @param[in,out] pRuleStr - On input, a pointer to the source input pointer;
 *   on return, a pointer to the token following the argument just returned.
 * @param[in] pEnd - A pointer to the end of the input buffer.
 * @param[out] pArgBegin - A pointer to the beginning of the returned argument buffer.
 * @param[out] pArgEnd - A pointer to the end of the returned argument buffer.
 * @param[out] pError - Error message on error.
 * @return 0 on success, else -1 on error.
 */
int    ls_parsenextarg(const char **pRuleStr, const char *pEnd,
                       const char **pArgBegin, const char **pArgEnd, const char **pError);

/**
 * @ls_convertmatchtoreg
 * @brief Converts a string from a regular expression format.
 *
 * @param[in] pStr - A pointer to the beginning of the string.
 * @param[in] pBufEnd - A pointer to the end of the buffer.
 * @return A pointer to the string converted in place.
 */
char *ls_convertmatchtoreg(char *pStr, char *pBufEnd);

/**
 * @ls_findclosebracket
 * @brief Finds the matching closing character from inside a \e bracket.
 * @details The routine correctly handles nesting.
 *
 * @param[in] pBegin - A pointer to the beginning of the buffer.
 * @param[in] pEnd - A pointer to the end of the buffer.
 * @param[in] chOpen - The character which opens (starts) the \e bracket.
 * @param[in] chClose - The character which closes (ends) the \e bracket.
 * @return A pointer to the matching closing character if it exists,
 *   else \e pEnd.
 */
const char *ls_findclosebracket(const char *pBegin, const char *pEnd,
                                char chOpen, char chClose);

/**
 * @ls_findcharinbracket
 * @brief Finds a specified character inside a \e bracket.
 * @details The character must be found in the current \e bracket level
 *   before the bracket close.
 *   The routine correctly handles nesting.
 *
 * @param[in] pBegin - A pointer to the beginning of the buffer.
 * @param[in] pEnd - A pointer to the end of the buffer.
 * @param[in] searched - The character to match.
 * @param[in] chOpen - The character which opens (starts) the \e bracket.
 * @param[in] chClose - The character which closes (ends) the \e bracket.
 * @return A pointer to the matching searched character if it exists
 *   in the proper level, else NULL.
 */
const char *ls_findcharinbracket(const char *pBegin, const char *pEnd,
                                 char searched, char chOpen, char chClose);

/**
 * @ls_offset2string
 * @brief Converts an offset to an ascii string.
 *
 * @param[out] pBuf - A pointer to the output buffer.
 * @param[in] len - The length (size) in bytes of the output buffer.
 * @param[in] val - The offset value.
 * @return The length in bytes of the converted returned buffer.
 */
int    ls_offset2string(char *pBuf, int len, off_t val);

/**
 * @ls_unescapequote
 * @brief Removes the backslash escapes for a specified character in a buffer.
 *
 * @param[in] pBegin - A pointer to the beginning of the buffer.
 * @param[in] pEnd - A pointer to the end of the buffer.
 * @param[in] ch - The character escaped.
 * @return The number of characters \e unescaped.
 */
int    ls_unescapequote(char *pBegin, char *pEnd, int ch);

/**
 * @ls_lookupsubstring
 * @brief Finds a string key/value pair within a specified input buffer.
 * @details The input buffer is expected to contain a series of
 *   key/value pairs separated by a separator character.
 *   The routine eliminates spaces unless they are within a quoted token.
 *
 * @param[in] pInput - A pointer to the beginning of the input buffer.
 * @param[in] pEnd - A pointer to the end of the buffer.
 * @param[in] key - A pointer to the beginning of the key to match.
 * @param[in] keyLen - The length of the key.
 * @param[out] retLen - The length in bytes of the returned value.
 * @param[in] sep - The separator between key/value pairs.
 * @param[in] comp - The comparator which associates key to value.
 * @return A pointer to the value for the matched key upon success,
 *   else NULL if not found.
 */
const char *ls_lookupsubstring(const char *pInput, const char *pEnd,
                               const char *key, int keyLen, int *retLen, char sep, char comp);

/**
 * @ls_mempbrk
 * @brief Finds a character within a specified input buffer.
 *
 * @param[in] pInput - A pointer to the beginning of the input buffer.
 * @param[in] iSize - The length of the input buffer.
 * @param[in] accept - A pointer to a list of characters to match.
 * @param[in] acceptLen - The length of the \e accept buffer.
 * @return A pointer to the first occurance of one of the accept characters
 *   in the input buffer,
 *   else NULL if not found.
 */
const char *ls_mempbrk(
    const char *pInput, int iSize, const char *accept, int acceptLen);

/**
 * @ls_memspn
 * @brief Scans memory for a given set of bytes.
 *
 * @param[in] pInput - A pointer to the beginning of the input buffer.
 * @param[in] iSize - The length of the input buffer.
 * @param[in] accept - A pointer to a list of bytes to match.
 * @param[in] acceptLen - The length of the \e accept buffer.
 * @return The number of bytes from the start of the input buffer
 *   which are within the match list.
 *
 * @see ls_memcspn
 */
size_t ls_memspn(
    const char *pInput, int iSize, const char *accept, int acceptLen);

/**
 * @ls_memspn
 * @brief Scans memory for bytes \e not within a given set.
 *
 * @param[in] pInput - A pointer to the beginning of the input buffer.
 * @param[in] iSize - The length of the input buffer.
 * @param[in] accept - A pointer to a list of bytes to match.
 * @param[in] acceptLen - The length of the \e accept buffer.
 * @return The number of bytes from the start of the input buffer,
 *   none of which are within the match list.
 *
 * @see ls_memspn
 */
size_t ls_memcspn(
    const char *pInput, int iSize, const char *accept, int acceptLen);

void   ls_getmd5(const char *src, int len, unsigned char *dstBin);

int ls_snprintf(char *str, size_t size, const char *format, ...);

int ls_vsnprintf(char *str, size_t size, const char *format, va_list args);


#ifdef __cplusplus
}
#endif

#endif  /* LS_STRTOOL_H */

