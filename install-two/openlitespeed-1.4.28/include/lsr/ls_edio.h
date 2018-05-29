
#ifndef LS_EDIO_H
#define LS_EDIO_H


#ifdef __cplusplus
extern "C" {
#endif

struct ls_edio_s;
typedef int (*edio_evt_cb)(int fd, struct ls_edio_s *pHandle, short event);
typedef int (*edio_timer_cb)(int fd, struct ls_edio_s *pHandle);

struct ls_edio_s
{
    void           *pParam;
    edio_evt_cb     evtCb;
    edio_timer_cb   timerCb;
};

typedef struct ls_edio_s ls_edio_t;

#ifdef __cplusplus
}
#endif


#endif
