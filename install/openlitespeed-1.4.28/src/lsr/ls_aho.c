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
#include <lsr/ls_aho.h>
#include <lsr/ls_pool.h>

typedef struct ls_aho_gotonode_s ls_aho_gotonode_t;

struct ls_aho_gotonode_s
{
    unsigned char       label;
    ls_aho_state_t     *state;
    ls_aho_gotonode_t  *next;
};

struct ls_aho_state_s
{
    unsigned int        id;
    size_t              output;
    ls_aho_state_t     *fail;
    ls_aho_state_t     *next;
    ls_aho_gotonode_t  *first;
    unsigned int        goto_size;
    unsigned char      *children_labels;
    ls_aho_state_t    **children_states;
};


static ls_aho_state_t *ls_aho_initstate();
static int ls_aho_insertgoto(ls_aho_state_t *state,
                             ls_aho_gotonode_t *node);
static int ls_aho_setgoto(
    ls_aho_state_t *pFromState, unsigned char sym, ls_aho_state_t *pToState);
static ls_aho_state_t *ls_aho_getgoto(
    ls_aho_state_t *state, unsigned char sym, int madeTree);
static int ls_aho_optimize(ls_aho_state_t *state, int case_sensitive);
static void ls_aho_freegoto(ls_aho_gotonode_t *node);
static void ls_aho_freenodes(ls_aho_state_t *state, int case_sensitive);
static void ls_aho_copy_helper(ls_aho_state_t *pState, char *pBuf,
                               int iCurLen,
                               int inc, ls_aho_t *pThis);


ls_aho_t *ls_aho_new(int case_sensitive)
{
    ls_aho_t *pThis = ls_palloc(sizeof(ls_aho_t));
    if (ls_aho(pThis, case_sensitive) == 0)
    {
        if (pThis != NULL)
            ls_pfree(pThis);
        return NULL;
    }
    return pThis;
}


int ls_aho(ls_aho_t *pThis, int case_sensitive)
{
    if (pThis == NULL)
        return 0;
    pThis->next_state = 1;
    pThis->zero_state = ls_aho_initstate();
    if (pThis->zero_state == NULL)
        return 0;
    pThis->case_sensitive = case_sensitive;
    return 1;
}


void ls_aho_d(ls_aho_t *pThis)
{
    if ((pThis != NULL) && (pThis->zero_state != NULL))
        ls_aho_freenodes(pThis->zero_state, pThis->case_sensitive);
    return;
}


void ls_aho_delete(ls_aho_t *pThis)
{
    ls_aho_d(pThis);
    ls_pfree(pThis);
}


int ls_aho_addpattern(ls_aho_t *pThis, const char *pattern, size_t size)
{
    ls_aho_state_t *pState, *ptr = NULL;
    size_t j = 0;
    int ret;
    unsigned char ch;

    pState = pThis->zero_state;
    while (j != size)
    {
        ch = *(pattern + j);
        if (pThis->case_sensitive == 0)
            ch = tolower(ch);
        ptr = ls_aho_getgoto(pState, ch, 0);
        if (ptr == NULL)
            break;
        if (ptr->output > 0)
        {
#ifdef LS_AHO_DEBUG
            printf("-----pattern=%s, this pattern can be safely ignored\
 - its prefix is a pattern\n", pattern);
#endif
            return 1;
        }
        pState = ptr;
        ++j;
    }
    if (j == size)
    {
        if (ptr->output == 0)
        {
            ptr->output = j;
            ls_aho_freegoto(ptr->first);
            ptr->first = NULL;
            ptr->goto_size = 0;
#ifdef LS_AHO_DEBUG
            printf("-----pattern=%s, this pattern discards previous patterns\
 - it's a prefix of previous ones\n", pattern);
#endif
            return 1;
        }
        else if (ptr->output == j)
        {
#ifdef LS_AHO_DEBUG
            printf("info:same pattern already exists\n");
#endif
            return 1;
        }
#ifdef LS_AHO_DEBUG
        else
        {
            printf("warning: impossible, logic error somewhere\n");
            return 0;
        }
#endif
    }

    while (j != size)
    {
        if ((ptr = ls_aho_initstate()) == NULL)
            return (0);
        ptr->id = pThis->next_state++;
        ch = *(pattern + j);
        if (pThis->case_sensitive == 0)
            ch = tolower(ch);
        if ((ret = ls_aho_setgoto(pState, ch, ptr)) == 0)
        {
            ls_pfree(ptr);
            return 0;
        }
        pState = ptr;
        ++j;
    }
    ptr->output = size;
    return 1;
}


int ls_aho_addfromfile(ls_aho_t *pThis, const char *filename)
{
    char buf[LS_AHO_MAX_STRING_LEN], *pStart, *pEnd;
    FILE *fp;
    int ret;

    if ((fp = fopen(filename, "rb")) == NULL)
    {
#ifdef LS_AHO_DEBUG
        printf("failed to open file: %s\n", filename);
#endif
        return 0;
    }
    /* no problem when a line exceed max length --
     *   it'll be split into multiple lines
     */
    while (fgets(buf, LS_AHO_MAX_STRING_LEN, fp) != NULL)
    {
        /* trim whitespace */
        pStart = buf;
        while (isspace(*pStart) && *pStart != '\0')
            ++pStart;
        /* ignore empty or comment line */
        if (*pStart == '\0' || *pStart == '#')
            continue;
        pEnd = buf + strlen(buf) - 1;
        while (isspace(*pEnd))
            --pEnd;
        *(++pEnd) = '\0';   /* needed later for strstr() */
        ret = ls_aho_addpattern(pThis, pStart, pEnd - pStart);
        /* not include the last '\0' */
        if (ret == 0)
            return 0;
    }
    fclose(fp);
    return 1;
}


int ls_aho_maketree(ls_aho_t *pThis)
{
    ls_aho_state_t *pState, *ptr, *pIter, *pHead, *pTail;
    ls_aho_gotonode_t *pNode;
    unsigned char sym;

    pHead = NULL;
    pTail = NULL;

    /* all goto_node under zero_state */
    for (pNode = pThis->zero_state->first; pNode != NULL; pNode = pNode->next)
    {
        ptr = pNode->state;
        if (pHead == NULL)
        {
            pHead = ptr;
            pTail = ptr;
        }
        else
        {
            pTail->next = ptr;
            pTail = ptr;
        }
        ptr->fail = pThis->zero_state;
    }
    // following is the most tricky part
    // set fail() for depth > 0
    for (; pHead != NULL; pHead = pHead->next)
    {
        pIter = pHead;
        // now pIter's all goto_node
        for (pNode = pIter->first; pNode != NULL; pNode = pNode->next)
        {
            ptr = pNode->state;
            sym = pNode->label;
            /* no need to set leaf's fail function --
             *   only if each pattern is unique
             * if non-unique pattern allowed,
             *   have to comment off following if statement --
             *   otherwise, may cause segment fault
             */
            //if (ptr->output == 0){    // or ptr->first == NULL
            pTail->next = ptr;
            pTail = ptr;
            pState = pIter->fail;
            while (ls_aho_getgoto(pState, sym, 1) == NULL)
                pState = pState->fail;
            ptr->fail = ls_aho_getgoto(pState, sym, 1);
            //}
        }
    }
    return 1;
}


int ls_aho_optimizetree(ls_aho_t *pThis)
{
    return ls_aho_optimize(pThis->zero_state, pThis->case_sensitive);
}


ls_aho_t *ls_aho_copy(ls_aho_t *pThis)
{
    char buf[4096];
    unsigned int inc = 1;
    ls_aho_state_t *pZero = pThis->zero_state;
    ls_aho_t *pNew = ls_aho_new(pThis->case_sensitive);
    if ((pZero == NULL) || (pZero->goto_size == 0))
        return pNew;
    if (pThis->case_sensitive)
        ++inc;
    ls_aho_copy_helper(pZero, buf, 0, inc, pNew);
    return pNew;
}


unsigned int ls_aho_search(ls_aho_t *pThis,
                           ls_aho_state_t *start_state, const char *string, size_t size,
                           size_t startpos,
                           size_t *out_start, size_t *out_end, ls_aho_state_t **out_last_state)
{
    ls_aho_state_t *pZero = pThis->zero_state;
    ls_aho_state_t *aAccept[LS_AHO_MAX_FIRST_CHARS];
    unsigned char uc;
    const char *pInputPtr;
    size_t iStringIter;
    int i;
    int iChildPtr = pZero->goto_size;
    int iNumChildren = pZero->goto_size;

    if (start_state == NULL)
        start_state = pZero;

    memset(aAccept, 0, sizeof(aAccept));
    for (i = 0; i < iNumChildren; ++i)
        aAccept[pZero->children_labels[i]] = pZero->children_states[i];

    for (iStringIter = startpos; iStringIter < size; ++iStringIter)
    {
        if ((iChildPtr == iNumChildren) && (start_state == pZero))
        {
            for (pInputPtr = string + iStringIter; pInputPtr < string + size;
                 ++pInputPtr)
            {
                if (*pInputPtr < 0) // Out of range
                    continue;
                if ((start_state = aAccept[(int) * pInputPtr]) != 0)
                    break;
            }
            if (pInputPtr >= string + size)
            {
                *out_start = -1;
                *out_end = -1;
                *out_last_state = start_state;
                return 0;
            }
            iStringIter = pInputPtr - string + 1;
            if (iStringIter >= size)
                break;
        }
        uc = *(string + iStringIter);
        do
        {
            iNumChildren = start_state->goto_size;
            for (iChildPtr = 0; iChildPtr < iNumChildren; ++iChildPtr)
            {
                if (uc == start_state->children_labels[iChildPtr])
                    break;
            }
            if (iChildPtr == iNumChildren)
            {
                start_state = start_state->fail;
                if (start_state == pZero)
                    break;
            }
        }
        while (iChildPtr == iNumChildren);
        if ((iChildPtr != iNumChildren) || (start_state != pZero))
        {
            start_state = start_state->children_states[iChildPtr];
            if (start_state->output != 0)
            {
                *out_start = iStringIter - start_state->output + 1;
                *out_end = iStringIter + 1;
                *out_last_state = start_state;
                return start_state->id;
            }
        }
    }
    *out_start = -1;
    *out_end = -1;
    *out_last_state = start_state;
    return 0;
}


ls_aho_state_t *ls_aho_initstate()
{
    ls_aho_state_t *pThis =
        (ls_aho_state_t *)ls_palloc(sizeof(ls_aho_state_t));
    if (pThis == NULL)
        return NULL;
    pThis->id = 0;
    pThis->output = 0;
    pThis->fail = NULL;
    pThis->next = NULL;
    pThis->first = NULL;
    pThis->goto_size = 0;
    pThis->children_labels = NULL;
    pThis->children_states = NULL;

    return pThis;
}


static int ls_aho_insertgoto(ls_aho_state_t *state,
                             ls_aho_gotonode_t *node)
{
    ls_aho_gotonode_t *ptr, *ptr2;
    unsigned char sym = node->label;

    if ((ptr = state->first) == NULL)
    {
        state->first = node;
        state->goto_size = 1;
        node->next = NULL;
        return 1;
    }
    if (ptr->label > sym)
    {
        state->first = node;
        ++state->goto_size;
        node->next = ptr;
        return 1;
    }
    for (ptr2 = ptr; ptr != NULL && ptr->label < sym; ptr = ptr->next)
        ptr2 = ptr;
#ifdef LS_AHO_DEBUG
    if (p != NULL && p->label == sym)
    {
        printf("impossible! fatal error\n");
        return 0;
    }
#endif
    // insert between ptr2 and ptr
    ptr2->next = node;
    node->next = ptr;
    ++state->goto_size;
    return 1;
}


static int ls_aho_setgoto(
    ls_aho_state_t *pFromState, unsigned char sym, ls_aho_state_t *pToState)
{
    ls_aho_gotonode_t *pEdge;
    pEdge = (ls_aho_gotonode_t *)ls_palloc(sizeof(ls_aho_gotonode_t));
    if (pEdge == NULL)
        return 0;

    pEdge->label = sym;
    pEdge->state = pToState;
    pEdge->next = NULL;

    ls_aho_insertgoto(pFromState, pEdge);
    return 1;
}


static ls_aho_state_t *ls_aho_getgoto(
    ls_aho_state_t *state, unsigned char sym, int madeTree)
{
    ls_aho_gotonode_t *pNode;
    unsigned char uc;

    pNode = state->first;
    while (pNode != NULL)
    {
        uc = pNode->label;
        if (uc == sym)
            return pNode->state;
        else if (uc > sym)
            break;

        pNode = pNode->next;
    }
    return ((madeTree != 0) && (state->id == 0)) ? state : NULL;
}


static int ls_aho_optimize(ls_aho_state_t *state, int case_sensitive)
{
    ls_aho_gotonode_t *pNextChild, *pChild = state->first;
    int i = 0;
    if (state->first == NULL)
        return 1;

    if (case_sensitive == 0)
        state->goto_size <<= 1;

    if ((state->children_labels = (unsigned char *)
                                  ls_palloc(sizeof(unsigned char) * (state->goto_size))) == NULL)
        return 0;
    if ((state->children_states = (ls_aho_state_t **)
                                  ls_palloc(sizeof(ls_aho_state_t *) * (state->goto_size))) == NULL)
        return 0;
    state->first = NULL;
    while (pChild != NULL)
    {
        if (case_sensitive != 0)
        {
            state->children_labels[i] = pChild->label;
            state->children_states[i] = pChild->state;
        }
        else
        {
            state->children_labels[i] = toupper(pChild->label);
            state->children_states[i++] = pChild->state;
            state->children_labels[i] = tolower(pChild->label);
            state->children_states[i] = pChild->state;
        }

        if (ls_aho_optimize(pChild->state, case_sensitive) == 0)
            return 0;
        ++i;
        pNextChild = pChild->next;
        ls_pfree(pChild);
        pChild = pNextChild;
    }
    return 1;
}


static void ls_aho_freegoto(ls_aho_gotonode_t *node)
{
    ls_aho_state_t *ptr;
    ls_aho_gotonode_t *pNextNode;

    pNextNode = node->next;
    ptr = node->state;
    if (ptr->first != NULL)
        ls_aho_freegoto(ptr->first);
    ls_pfree(ptr);
    if (pNextNode != NULL)
        ls_aho_freegoto(pNextNode);
    ls_pfree(node);
}


static void ls_aho_freenodes(ls_aho_state_t *state, int case_sensitive)
{
    // Goto nodes are deallocated in optimize.
    size_t i;
    if (state->children_states != NULL)
    {
        for (i = 0; i < state->goto_size; ++i)
        {
            ls_aho_freenodes(state->children_states[i], case_sensitive);
            state->children_states[i] = NULL;
            //if case insensitive, skip one to prevent double freeing
            if (case_sensitive == 0)
                state->children_states[++i] = NULL;
        }
        ls_pfree(state->children_labels);
        state->children_labels = NULL;
        ls_pfree(state->children_states);
        state->children_states = NULL;
    }
    ls_pfree(state);
}

#define LS_AHO_SEPARATOR 244

static void ls_aho_copy_helper(ls_aho_state_t *pState, char *pBuf,
                               int iCurLen,
                               int inc, ls_aho_t *pThis)
{
    unsigned int i;
    if (pState->goto_size == 0)
    {
        // pattern is finished
        ls_aho_addpattern(pThis, pBuf, iCurLen);
        return;
    }
    for (i = 0; i < pState->goto_size; i += inc)
    {
        pBuf[iCurLen] = pState->children_labels[i];
        ls_aho_copy_helper(pState->children_states[i], pBuf, iCurLen + 1, inc,
                           pThis);
    }
}


