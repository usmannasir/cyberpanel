#!/bin/sh

#
# For the special case "if", we nees to update the astyle/ASFormatter.cpp, in this way, we bypass the for, while and switch. 
#                if (shouldPadHeader
#                        && (!isNonParenHeader
#                            || (currentHeader == &AS_CASE && peekNextChar() == '(')
#                            || (currentHeader == &AS_CATCH && peekNextChar() == '('))
#                        && charNum < (int) currentLine.length() - 1 && !isWhiteSpace(currentLine[charNum + 1]))
#-                    appendSpacePad();
#+                {
#+                    if ( currentHeader != &AS_SWITCH && currentHeader != &AS_WHILE && currentHeader != &AS_FOR )
#+                        appendSpacePad();
#+                }
#
#void ASFormatter::padParens(void)
# ...
#                    if (shouldPadHeader
#                            && prevWord.length() > 0
#                            && isCharPotentialHeader(prevWord, 0))
#                        prevWordH = ASBeautifier::findHeader(prevWord, 0, headers);
#                    if (prevWordH != NULL)
#+                    {
#+                        //We treat while and for and switch not a header
#+                        if ( prevWordH != &AS_SWITCH && prevWordH != &AS_WHILE && prevWordH != &AS_FOR )
#                            prevIsParenHeader = true;
#+                    }
#                    else if (prevWord == "return")  // don't unpad
#
#
#

createFileList()
{
    FILENAME=$1
    rm -rf $FILENAME
    find . -iname "*.c" | grep -v UnitTest++ | grep -v build/ | grep -v modules/pagespeed/psol > $FILENAME
    find . -iname "*.cpp" | grep -v UnitTest++ | grep -v build/ | grep -v modules/pagespeed/psol >> $FILENAME
    find . -iname "*.h" | grep -v UnitTest++ | grep -v build/ | grep -v modules/pagespeed/psol >> $FILENAME
}


dealFile()
{
    local FILENAME=$1
    echo "Dealing with file: $FILENAME"
    astyle  -A1 -s4 -K -w -m0 -p -H -U -k3 -W3 -xj -c -xC75 -n -O -q "$FILENAME"
    astyle  -A1 -s4 -K -w -m0 -p -H -U -k3 -W3 -xj -c -xC75 -n -O -q "$FILENAME"
#    /usr/bin/sed -i -r -e "s/[(][ ]((const[ ])?(unsigned[ ])?(struct[ ])?\w+[ ][*])[ ][)]/(\1)/" -e "s/[(][ ]((const[ ])?(unsigned[ ])?(struct[ ])?\w+[ ][*])[ ][)]/(\1)/"  "$FILENAME"
#    /usr/bin/sed -i -e "s/( int )/(int)/"  -e "s/( short )/(short)/"  -e "s/( unsigned long )/(unsigned long)/" -e "s/( long )/(long)/"  -e "s/( long long )/(long long)/"   "$FILENAME" 
#    /usr/bin/sed -i -e "s/( ( /(( /" -e "s/) ) )/) ))/" -e "s/ ) )/ ))/" -e "s/ ) )/ ))/" -e "s/())/() )/" -e "s/return ;/return;/"   "$FILENAME"
}

if [ "x$1" != "x" ] ; then 
    if [ -f $1 ] ; then 
        dealFile $1
    else
        echo "File $1 does not exist".
        echo
    fi
else
    createFileList ./todolist
    for FILENAME in `cat ./todolist`; do dealFile $FILENAME ; done
fi

echo "Done."
echo






