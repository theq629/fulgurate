# Example filter which just replaces / with | in the second (bottom) card field.
# Note system("") to flush output.
awk 'BEGIN { FS="	"; OFS="	" } { gsub(/\//, "|", $3); print; system("") }'
