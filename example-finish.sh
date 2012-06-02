# Example finish command which extracts the pronunciation part of the second card field and saves it to a log file. Fail if the log file already exists, to avoid overwriting anything. More usefully we could do something like play a corresponding sound file here.
log=./example-finish.log
[ -e "$log" ] || awk 'BEGIN { FS="       " } { gsub(/:.*$/, "", $3); print $3 }' > "$log"
