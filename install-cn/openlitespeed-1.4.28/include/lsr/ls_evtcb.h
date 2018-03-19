

#ifndef LS_EVTCB_H
#define LS_EVTCB_H


#ifdef __cplusplus
extern "C" {
#endif


struct evtcbnode_s;
typedef struct evtcbhead_s
{
    struct evtcbnode_s *evtcb_head;
    struct evtcbhead_s **back_ref_ptr;
}
evtcbhead_t;


/**
 * @typedef evtcb_pf
 * @brief The callback function for scheduling event.
 *
 */
typedef int (*evtcb_pf)(evtcbhead_t *pSession,
                        const long lParam, void *pParam);


#ifdef __cplusplus
}
#endif


#endif
