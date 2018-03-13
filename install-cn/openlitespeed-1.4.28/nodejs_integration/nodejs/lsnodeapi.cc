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

//
//  Simple LiteSpeed (Node.js) AddOn C++ module
//  (1) provide abilities for Java Side Server Script to pass fd via domain socket.
//  (2) provide abilities for Java Side Server Script dup2 fd.
//

#include <node.h>
#include <v8.h>
using namespace v8;

#include <sys/epoll.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>

#include <stddef.h>
#include <string.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/uio.h>

#ifndef __CMSG_ALIGN
#define __CMSG_ALIGN(p) (((u_int)(p) + sizeof(int) - 1) &~(sizeof(int) - 1))
#endif

/* Length of the contents of a control message of length len */
#ifndef CMSG_LEN
#define CMSG_LEN(len)   (__CMSG_ALIGN(sizeof(struct cmsghdr)) + (len))
#endif

/* Length of the space taken up by a padded control message of
length len */
#ifndef CMSG_SPACE
#define CMSG_SPACE(len) (__CMSG_ALIGN(sizeof(struct cmsghdr)) + __CMSG_ALIGN(len))
#endif

static int litespeed_read_fd(int fd, void *ptr, int nbytes, int *recvfd)
{
    struct msghdr   msg;
    struct iovec    iov[1];
    int             n;

    int             control_space = CMSG_SPACE(sizeof(int));
    union
    {
        struct cmsghdr    cm;
        char                control[ sizeof(struct cmsghdr) + sizeof(int) + 8];
    } control_un;
    struct cmsghdr    *cmptr;

    *recvfd = -1;
    msg.msg_control = control_un.control;
    msg.msg_controllen = control_space;

    msg.msg_name = NULL;
    msg.msg_namelen = 0;

    iov[0].iov_base = (char *)ptr;
    iov[0].iov_len = nbytes;
    msg.msg_iov = iov;
    msg.msg_iovlen = 1;

    if ((n = recvmsg(fd, &msg, 0)) <= 0)
        return (n);

    if ((cmptr = CMSG_FIRSTHDR(&msg)) != NULL &&
        cmptr->cmsg_len >= CMSG_LEN(sizeof(int)))
    {
        if (cmptr->cmsg_level != SOL_SOCKET)
            return -1;
        if (cmptr->cmsg_type != SCM_RIGHTS)
            return -2;
        memmove(recvfd, CMSG_DATA(cmptr), sizeof(int));
    }
    else
        *recvfd = -1;        /* descriptor was not passed */

    return (n);
}
/* end litespeed_read_fd */


Handle<Value> Sleep(const Arguments &args)
{
    HandleScope scope;

    if (args.Length() < 1)
    {
        ThrowException(Exception::TypeError(String::New("Accept: missing fd")));
        return scope.Close(Undefined());
    }
    sleep(args[0]->NumberValue());
    Local<Number> num = Number::New(0);
    return scope.Close(num);
}

//
//  ReadFd
//
Handle<Value> ReadFd(const Arguments &args)
{
    HandleScope scope;

    if (args.Length() > 1)
    {
        int pauseTime = args[1]->NumberValue();
        if (pauseTime)
            sleep(pauseTime);
    }
    if (args.Length() < 1)
    {
        ThrowException(Exception::TypeError(String::New("Accept: missing fd")));
        return scope.Close(Undefined());
    }
    int fd = args[0]->NumberValue();
    int http_fd = -1;
    int nb = -1;
    int msgsize = -1;

    Local<Number> num;

    nb = litespeed_read_fd(fd, &msgsize, sizeof(int), &http_fd);
    if (nb != sizeof(int))
    {
        printf("Failed to read fd from domainsocket %d errno %d read-ret[%d]\n" ,
               fd, errno, nb);
        http_fd = -1;
    }

    num = Number::New(http_fd);
    return scope.Close(num);
}

Handle<Value> Close(const Arguments &args)
{
    HandleScope scope;

    if (args.Length() < 1)
    {
        ThrowException(Exception::TypeError(String::New("close: missing fd")));
        return scope.Close(Undefined());
    }
    close(args[0]->NumberValue());
    return scope.Close(Undefined());
}

Handle<Value> NumBytes(const Arguments &args)
{
    HandleScope scope;

    if (args.Length() < 1)
    {
        ThrowException(Exception::TypeError(
                           String::New("Wrong number of arguments")));
        return scope.Close(Undefined());
    }
    if (!args[0]->IsNumber())
    {
        ThrowException(Exception::TypeError(String::New("Wrong arguments")));
        return scope.Close(Undefined());
    }

    Local<Number> num;
    int fd, bytesAvail = 0;
    fd = args[0]->NumberValue();
    if (ioctl(fd, FIONREAD, &bytesAvail))
    {
        // perror("ioctl FIONREAD failed");
        // printf("errno: %d\n", errno);
        ThrowException(Exception::TypeError(String::New(
                                                "ioctl FIONREAD failed errno=" + errno)));
        num = Number::New(-1);
    }
    else
        num = Number::New(bytesAvail);
    return scope.Close(num);
}

//
//  Dup2x
//      Special dup2 which will perform check and close.
//          (1) check if the dst fd is empty.
//          (2) if empty then do the dup2 and close the src fd.
//
Handle<Value> Dup2x(const Arguments &args)
{
    HandleScope scope;

    if (args.Length() < 2)
    {
        ThrowException(Exception::TypeError(
                           String::New("Wrong number of arguments")));
        return scope.Close(Undefined());
    }
    if (!args[0]->IsNumber() || !args[1]->IsNumber())
    {
        ThrowException(Exception::TypeError(String::New("Wrong arguments")));
        return scope.Close(Undefined());
    }

    Local<Number> num;
    int from_fd = args[0]->NumberValue();
    int fd = args[1]->NumberValue();

    int bytesAvail = 0;
    if (ioctl(fd, FIONREAD, &bytesAvail))
    {
        ThrowException(Exception::TypeError(String::New(
                                                "Fd ioctl FIONREAD failed errno=" + errno)));
        num = Number::New(-1);
        return scope.Close(num);
    }

    if (bytesAvail)
    {
        /* do nothing yet - wait til the end of read*/
        num = Number::New(from_fd);
    }
    else
    {
        int needToAdd = 0;
        struct epoll_event event;
        uv_loop_t *loop = uv_default_loop();
        // printf("backend_fd = %d\n", loop ? loop->backend_fd : -1);

        errno = 0;
        if (epoll_ctl(loop->backend_fd, EPOLL_CTL_ADD, fd, &event))
        {
            if (errno == EEXIST)
                needToAdd = 1;
        }
        int dupRet;
        dupRet = dup2(from_fd, fd);
        close(from_fd);

        if (needToAdd)
        {
            event.data.fd = fd;
            event.events = EPOLLIN;
            if (epoll_ctl(loop->backend_fd, EPOLL_CTL_ADD, fd, &event))
            {
                perror("epoll_ctl: FAILED TO ADD CALLBACK");
                printf("errno = %d\n", errno);
                num = Number::New(-1);
                return scope.Close(num);
            }
        }
        num = Number::New(dupRet);
    }
    return scope.Close(num);
}

void init(Handle<Object> exports, Handle<Object> module)
{
    exports->Set(String::NewSymbol("close"),
                 FunctionTemplate::New(Close)->GetFunction());
    exports->Set(String::NewSymbol("readfd"),
                 FunctionTemplate::New(ReadFd)->GetFunction());
    exports->Set(String::NewSymbol("dup2x"),
                 FunctionTemplate::New(Dup2x)->GetFunction());
    exports->Set(String::NewSymbol("numbytes"),
                 FunctionTemplate::New(NumBytes)->GetFunction());
    exports->Set(String::NewSymbol("sleep"),
                 FunctionTemplate::New(Sleep)->GetFunction());
}

NODE_MODULE(litespeed, init)
