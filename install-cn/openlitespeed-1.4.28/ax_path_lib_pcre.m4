# ===========================================================================
#     http://www.gnu.org/software/autoconf-archive/ax_path_lib_pcre.html
# ===========================================================================
#
# SYNOPSIS
#
#   AX_PATH_LIB_PCRE [(A/NA)]
#
# DESCRIPTION
#
#   check for pcre lib and set PCRE_LIBS and PCRE_CFLAGS accordingly.
#
#   also provide --with-pcre option that may point to the $prefix of the
#   pcre installation - the macro will check $pcre/include and $pcre/lib to
#   contain the necessary files.
#
#   the usual two ACTION-IF-FOUND / ACTION-IF-NOT-FOUND are supported and
#   they can take advantage of the LIBS/CFLAGS additions.
#
# LICENSE
#
#   Copyright (c) 2008 Guido U. Draheim <guidod@gmx.de>
#
#   This program is free software; you can redistribute it and/or modify it
#   under the terms of the GNU General Public License as published by the
#   Free Software Foundation; either version 2 of the License, or (at your
#   option) any later version.
#
#   This program is distributed in the hope that it will be useful, but
#   WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
#   Public License for more details.
#
#   You should have received a copy of the GNU General Public License along
#   with this program. If not, see <http://www.gnu.org/licenses/>.
#
#   As a special exception, the respective Autoconf Macro's copyright owner
#   gives unlimited permission to copy, distribute and modify the configure
#   scripts that are the output of Autoconf when processing the Macro. You
#   need not follow the terms of the GNU General Public License when using
#   or distributing such scripts, even though portions of the text of the
#   Macro appear in them. The GNU General Public License (GPL) does govern
#   all other use of the material that constitutes the Autoconf Macro.
#
#   This special exception to the GPL applies to versions of the Autoconf
#   Macro released by the Autoconf Archive. When you make and distribute a
#   modified version of the Autoconf Macro, you may extend this special
#   exception to the GPL to apply to your modified version as well.

#serial 6

AC_DEFUN([AX_PATH_LIB_PCRE],[dnl
AC_MSG_CHECKING([lib pcre])
PCRE_LDFLAGS=
AC_ARG_WITH(pcre,
[  --with-pcre[[=prefix]]    compile xmlpcre part (via libpcre check)],,
     with_pcre="yes")
if test ".$with_pcre" = ".no" ; then
  AC_MSG_RESULT([disabled])
  m4_ifval($2,$2)
else
  AC_MSG_RESULT([(testing)])
  AC_CHECK_LIB(pcre, pcre_study)
  if test "$ac_cv_lib_pcre_pcre_study" = "yes" ; then
     PCRE_LIBS="-lpcre"
     if test "$with_pcre" != "yes" ; then
         PCRE_LDFLAGS="-L$with_pcre/$OPENLSWS_LIBDIR"
         LDFLAGS="$LDFLAGS $PCRE_LDFLAGS"
         CPPFLAGS="$CPPFLAGS -I$with_pcre/include"
     fi

     AC_MSG_CHECKING([$OPENLSWS_LIBDIR pcre])
     AC_MSG_RESULT([$PCRE_LIBS])
     m4_ifval($1,$1)
  else
     PCRE_LDFLAGS="-L$with_pcre/$OPENLSWS_LIBDIR"
     OLDLDFLAGS="$LDFLAGS" ; LDFLAGS="$LDFLAGS $PCRE_LDFLAGS"
     OLDCPPFLAGS="$CPPFLAGS" ; CPPFLAGS="$CPPFLAGS -I$with_pcre/include"
     AC_CHECK_LIB(pcre, pcre_compile)
     CPPFLAGS="$OLDCPPFLAGS"
     LDFLAGS="$OLDLDFLAGS"
     if test "$ac_cv_lib_pcre_pcre_compile" = "yes" ; then
        AC_MSG_RESULT(.setting PCRE_LIBS $PCRE_LDFLAGS -lpcre)
        PCRE_LIBS="$PCRE_LDFLAGS -lpcre"
        test -d "$with_pcre/include" && PCRE_CFLAGS="-I$with_pcre/include"
        AC_MSG_CHECKING([$OPENLSWS_LIBDIR pcre])
        AC_MSG_RESULT([$PCRE_LIBS])
        m4_ifval($1,$1)
     else
        PCRE_LDFLAGS=
        AC_MSG_CHECKING([$OPENLSWS_LIBDIR pcre])
        AC_MSG_RESULT([no, (WARNING)])
        m4_ifval($2,$2)
     fi
  fi
fi
AC_SUBST([PCRE_LIBS])
AC_SUBST([PCRE_CFLAGS])
AC_SUBST([PCRE_LDFLAGS])
])
