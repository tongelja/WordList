#!/bin/bash

timestamp=$( date +'%Y%m%y_%H%M' )
word_doc="myWords.${timestamp}.doc"
echo " " > ${word_doc}
counter=0

echo
for i in $( cat words.out ); do
    counter=$((counter+1))

    python3 words.py --word ${i} >> ${word_doc}  2>/dev/null
    RC=$?

    if [[ ${RC} -ne 0 ]]; then
        echo -e "\nError on $i\n\c"
    else
        echo -e "\r${counter}\c"
    fi

done
echo
 

