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
#ifndef WORKCREW_H
#define WORKCREW_H

#include <lsdef.h>
#include <thread/worker.h>
#include <util/objarray.h>

#if defined(linux) || defined(__linux) || defined(__linux__) || defined(__gnu_linux__)
#define LS_WORKCREW_LF
#endif

//#define LS_WORKCREW_DEBUG
#ifdef LS_WORKCREW_DEBUG
#include <stdio.h>
#endif

/**
 * @file
 *
 * To use Work Crew:
 *
 * A class must have WorkCrew as a member.
 *      It must either contain or have access to a queue for storing finished items.
 *      It must implement a (static)processing function.
 *      Optionally inherit or have access to an Event Notifier.
 *
 * After WorkCrew construction, jobs may be added at any time.
 * Call startJobProcessor when ready to start processing.
 *
 * StopProcessing and resize may be called at any time after construction.
 */


class EventNotifier;
typedef struct ls_lfnodei_s ls_lfnodei_t;
typedef struct ls_lfqueue_s ls_lfqueue_t;

#ifndef LS_WORKCREW_LF
class PThreadWorkQueue;
#endif

#define LS_WORKCREW_MINWORKER 1
#define LS_WORKCREW_MAXWORKER 32

/**
 * @typedef WorkCrewProcessFn
 * @brief The user must provide a processing function.
 * @details This function will be used when the worker receives
 * a job item from the job queue.
 *
 * @param[in] item - The job item to process.
 * @return NULL if successful, Not NULL if unsuccessful.  If unsuccessful,
 * the worker thread will stop, passing the return value back to the parent.
 */
typedef void *(*WorkCrewProcessFn)(ls_lfnodei_t *item);

class WorkCrew
{
#ifdef LS_WORKCREW_LF
    ls_lfqueue_t       *m_pJobQueue;
#else
    PThreadWorkQueue   *m_pJobQueue;
#endif
    ls_lfqueue_t       *m_pFinishedQueue;
    EventNotifier      *m_pNotifier;
    TObjArray<Worker>   m_crew;
    WorkCrewProcessFn   m_pProcess;

private:

    /** wcWorkerFn
     * @internal This function is the work function passed into the worker.
     * This is used so the thread knows which work crew to get the parameters
     * from.
     */
    static void *wcWorkerFn(void *arg)
    {
        WorkCrew *wc = (WorkCrew *)arg;
        return wc->getAndProcessJob();
    }

    /** @getJob
     * @internal This function attempts to get a job from the job queue.
     */
    ls_lfnodei_t *getJob();

    /** @getAndProcessJob
     * @internal This function tries to get a job from the job queue,
     * and if there is one, processes it and puts it in the finished queue.
     */
    void *getAndProcessJob();

    /** @increaseTo
     * @internal This function increases the number of worker threads to
     * the value provided.
     */
    int increaseTo(int numMembers);

    /** @decreaseTo
     * @internal This function decreases the number of worker threads to
     * the value provided.
     */
    int decreaseTo(int numMembers);

    /** @putFinishedItem
     * @internal This function puts an item into the finished queue and
     * notifies the Event Notifier if there is one.
     */
    int putFinishedItem(ls_lfnodei_t *item);

public:
    /** @WorkCrew
     * @brief The Work Crew Constructor. Initializes the members.
     * @details If provided, the Event Notifier will be notified when
     * a job is finished.
     *
     * @param[in] en - An optional initialized event notifier.
     */
    WorkCrew(EventNotifier *en = NULL);

    /** @~WorkCrew
     * @brief The Work Crew Destructor.
     * @details This function will end any thread still running and delete the
     * job queue.  This function will \b not free anything left in the queue.
     */
    ~WorkCrew();

    /** @startJobProcessor
     * @brief Starts the Workers to begin processing the jobs.
     *
     * @param[in] numWorkers - The number of worker threads.  Must be within
     * LS_WORKCREW_MINWORKER and LS_WORKCREW_MAXWORKER.
     * @param[in] pFinishedQueue - The finished queue to put the completed
     * jobs in.
     * @param[in] processor - The function that will handle the jobs.
     * @return 0 if successful, else -1 if not.
     *
     * @see WorkCrewProcessFn
     */
    int startJobProcessor(int numWorkers, ls_lfqueue_t *pFinishedQueue,
                          WorkCrewProcessFn processor);

    /** @stopProcessing
     * @brief Stops any worker threads and resets the finished queue.
     *
     * @return Void.
     */
    void stopProcessing();

    /** @size
     * @brief Returns the current number of workers
     * @return current workers
     */
    int size();

    /** @resize
     * @brief Resizes the number of workers to the number provided.
     * @details If the value is out of range
     * (LS_WORKCREW_MINWORKER - LS_WORKCREW_MAXWORKER), it will be
     * resized to the closest value within the range.  A negative number
     * will result in unsuccessful resize.
     *
     * @param[in] numMembers - The number of workers to resize the crew to.
     * @return 0 if successful, else -1 if unsuccessful.
     */
    int resize(int numMembers);

    /** @addJob
     * @brief Adds a job to the job queue.
     * @details This function adds the item to the job queue for the workers
     * to work on.  The item will be passed in to the
     * \link #WorkCrewProcessFn processing function.\endlink
     *
     * @param[in] item - The job item to pass into the processing function.
     * @return 0 if successful, else -1 if unsuccessful.
     */
    int addJob(ls_lfnodei_t *item);



    LS_NO_COPY_ASSIGN(WorkCrew);
};




#endif //WORKCREW_H

